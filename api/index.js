const express = require('express');
const cors = require('cors');
const path = require('path');
const nodemailer = require('nodemailer');

const app = express();
app.use(cors());
app.use(express.json({ limit: '5mb' }));

// ============================================================
// VERİ DEPOLAMA — Vercel KV (Upstash Redis) veya In-Memory
// ============================================================
// Vercel'de: KV_REST_API_URL ve KV_REST_API_TOKEN env var gerekir
// Lokal'de: In-memory obje kullanır (test için yeterli)
// ============================================================

let kvStore = null;

// Vercel KV bağlantısını dene
async function getKV() {
  if (kvStore) return kvStore;
  try {
    const { kv } = require('@vercel/kv');
    // Test bağlantısı
    await kv.ping();
    kvStore = kv;
    console.log('✅ Vercel KV (Upstash Redis) bağlantısı kuruldu');
    return kv;
  } catch (e) {
    console.log('⚠️  Vercel KV bulunamadı — In-memory mod aktif (lokal geliştirme)');
    return null;
  }
}

// In-memory fallback (lokal geliştirme için)
const memoryStore = {};

const DEFAULT_STATE = {
  tent:              'closed',
  heater:            'off',
  fan_1:             'off',
  fan_2:             'off',
  door_light:        '0',
  room_1_temp:       '22',
  room_2_temp:       '21',
  rain_status:       'dry',
  last_photo:        '',
  last_photo_base64: '',
  pi_connected:      'false',
  capture_requested: 'false',
};

// KV'den veya bellekten tüm durumu oku
async function getAllState() {
  const kv = await getKV();
  if (kv) {
    const state = await kv.hgetall('akilli_ev_state');
    if (!state || Object.keys(state).length === 0) {
      // İlk çalıştırma: varsayılanları yükle
      await kv.hset('akilli_ev_state', DEFAULT_STATE);
      return { ...DEFAULT_STATE };
    }
    return { ...DEFAULT_STATE, ...state };
  }
  // In-memory fallback
  if (Object.keys(memoryStore).length === 0) {
    Object.assign(memoryStore, DEFAULT_STATE);
  }
  return { ...memoryStore };
}

// Tek bir değeri güncelle
async function setState(key, value) {
  const kv = await getKV();
  if (kv) {
    await kv.hset('akilli_ev_state', { [key]: value.toString() });
  } else {
    memoryStore[key] = value.toString();
  }
}

// Birden fazla değeri güncelle
async function setMultiState(obj) {
  const kv = await getKV();
  if (kv) {
    await kv.hset('akilli_ev_state', obj);
  } else {
    Object.assign(memoryStore, obj);
  }
}


// ============================================================
// NODEMAILER TRANSPORTER
// Gmail SMTP: Google Hesabı → Güvenlik → Uygulama Şifreleri
// ============================================================
const createTransporter = () => nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.GMAIL_USER || 'your_email@gmail.com',
    pass: process.env.GMAIL_PASS || 'your_app_password_here'
  }
});


// ============================================================
// API 1 — GET /api/status → Tüm cihaz durumlarını getir
// Web arayüzü bu endpoint'i 3 saniyede bir çeker
// ============================================================
app.get('/api/status', async (req, res) => {
  try {
    const data = await getAllState();
    res.json({ message: 'success', data });
  } catch (err) {
    console.error('Status hatası:', err);
    res.status(500).json({ error: err.message });
  }
});


// ============================================================
// API 2 — POST /api/update → Cihaz durumunu güncelle
//   Body: { device_name, state_value }
//   Yağmur otomasyonu dahil
// ============================================================
app.post('/api/update', async (req, res) => {
  const { device_name, state_value } = req.body;
  if (!device_name || state_value === undefined) {
    return res.status(400).json({ error: 'device_name veya state_value eksik' });
  }

  try {
    await setState(device_name, state_value);

    // ===== YAĞMUR OTOMASYONU =====
    if (device_name === 'rain_status' && state_value === 'raining') {
      const state = await getAllState();
      if (state.tent !== 'closed') {
        const autoSpeed = state.tent === 'fast' ? 'medium' : 'slow';
        await setState('tent', autoSpeed);
        console.log(`[Otomasyon] Yağmur algılandı → Tente ${autoSpeed} hıza alındı`);
      }
    }

    const updatedState = await getAllState();
    res.json({ message: 'success', data: updatedState });
  } catch (err) {
    console.error('Update hatası:', err);
    res.status(500).json({ error: err.message });
  }
});


// ============================================================
// API 3 — POST /api/capture → Fotoğraf çek / yükle
//   Pi fotoğrafı base64 olarak gönderir (Vercel'de dosya sistemi yok)
//   Web arayüzünden tetikleme isteği de buraya gelir
// ============================================================
app.post('/api/capture', async (req, res) => {
  try {
    // Pi'den fotoğraf geldi (base64 formatında)
    if (req.body && req.body.photo_base64) {
      const timestamp = new Date().toISOString();
      await setMultiState({
        last_photo_base64: req.body.photo_base64,
        last_photo: timestamp,
        capture_requested: 'false',
      });
      console.log(`[Kamera] Fotoğraf alındı: ${timestamp}`);
      return res.json({ message: 'Fotoğraf başarıyla kaydedildi', timestamp });
    }

    // Web'den tetikleme isteği (Pi'yi bekle)
    await setState('capture_requested', 'true');
    console.log('[Kamera] Fotoğraf çekme isteği oluşturuldu');
    res.json({ message: 'Fotoğraf çekme isteği Pi\'ye iletildi' });
  } catch (err) {
    console.error('Capture hatası:', err);
    res.status(500).json({ error: err.message });
  }
});


// ============================================================
// API 4 — GET /api/photo → Son fotoğrafı base64 olarak getir
// ============================================================
app.get('/api/photo', async (req, res) => {
  try {
    const state = await getAllState();
    if (state.last_photo_base64) {
      res.json({
        message: 'success',
        photo: state.last_photo_base64,
        timestamp: state.last_photo,
      });
    } else {
      res.json({ message: 'no_photo', photo: null });
    }
  } catch (err) {
    console.error('Photo hatası:', err);
    res.status(500).json({ error: err.message });
  }
});


// ============================================================
// API 5 — POST /api/email → Son fotoğrafı Gmail ile gönder
//   Body: { email }
// ============================================================
app.post('/api/email', async (req, res) => {
  const { email } = req.body;
  if (!email) {
    return res.status(400).json({ error: 'E-posta adresi gerekli' });
  }

  try {
    const state = await getAllState();
    const base64Photo = state.last_photo_base64;

    const mailOptions = {
      from: `"Akıllı Ev Sistemi" <${process.env.GMAIL_USER || 'your_email@gmail.com'}>`,
      to: email,
      subject: '📸 Akıllı Ev — Kapı Kamera Görüntüsü',
      html: `
        <div style="font-family:Arial,sans-serif;background:#0f172a;color:#f8fafc;padding:24px;border-radius:12px">
          <h2 style="color:#3b82f6">🏠 Akıllı Ev Güvenlik Bildirimi</h2>
          <p>Kapınızda biri var! Kameradan çekilen fotoğraf ektedir.</p>
          <p style="color:#94a3b8;font-size:12px">Tarih: ${new Date().toLocaleString('tr-TR')}</p>
        </div>
      `,
      attachments: base64Photo
        ? [{
            filename: 'kapi_fotografi.jpg',
            content: base64Photo,
            encoding: 'base64',
          }]
        : []
    };

    const transporter = createTransporter();
    await transporter.sendMail(mailOptions);
    console.log(`[E-posta] ${email} adresine gönderildi`);
    res.json({ message: `✅ Fotoğraf ${email} adresine başarıyla gönderildi!` });
  } catch (err) {
    console.error('[E-posta] Gönderim hatası:', err.message);
    res.status(500).json({ message: `❌ Gönderim başarısız: ${err.message}` });
  }
});


// ============================================================
// API 6 — GET /api/pi-poll → Pi'nin kullanacağı birleşik endpoint
//   Hem state'i döner hem de bekleyen komutları (capture_requested)
// ============================================================
app.get('/api/pi-poll', async (req, res) => {
  try {
    const state = await getAllState();

    // capture_requested flag'ini sıfırla (tek seferlik)
    if (state.capture_requested === 'true') {
      await setState('capture_requested', 'false');
    }

    // Pi her poll'da bağlantı durumunu günceller
    await setState('pi_connected', 'true');

    res.json({ message: 'success', data: state });
  } catch (err) {
    console.error('Pi-poll hatası:', err);
    res.status(500).json({ error: err.message });
  }
});


// ============================================================
// BAŞLAT (Lokal geliştirme için)
// ============================================================
if (require.main === module) {
  const port = process.env.PORT || 3000;
  app.listen(port, () => {
    console.log(`✅ Sunucu çalışıyor: http://localhost:${port}`);
  });
}

module.exports = app;
