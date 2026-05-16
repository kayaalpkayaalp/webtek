import { useState, useEffect, useRef } from 'react';

const API_BASE = import.meta.env.PROD ? '' : 'http://localhost:3000';

function App() {
  const [deviceStates, setDeviceStates] = useState({
    tent: 'closed',
    heater: 'off',
    fan_1: 'off',
    fan_2: 'off',
    door_light: '0',
    room_1_temp: '',
    room_2_temp: '',
    rain_status: 'dry',
    last_photo: '',
    pi_connected: 'false',
  });
  const [email, setEmail] = useState('');
  const [emailStatus, setEmailStatus] = useState('');
  const [captureStatus, setCaptureStatus] = useState('');
  const [notification, setNotification] = useState(null);
  const [photoBase64, setPhotoBase64] = useState(null);
  const prevRainRef = useRef('dry');
  const isDraggingLightRef = useRef(false);

  // ---- Durum verilerini 3 saniyede bir çek ----
  useEffect(() => {
    const fetchStatus = () => {
      fetch(`${API_BASE}/api/status`)
        .then(res => res.json())
        .then(data => {
          if (data.message === 'success') {
            const newData = data.data;
            setDeviceStates(prev => {
              // Yağmur başladı bildirimi
              if (prev.rain_status === 'dry' && newData.rain_status === 'raining') {
                showNotification('warning', '🌧️ Yağmur başladı!');
              }
              if (prev.rain_status === 'raining' && newData.rain_status === 'dry') {
                showNotification('success', '☀️ Yağmur durdu.');
              }
              
              // Kullanıcı kaydırıcıyı sürüklüyorsa, sunucudan gelen ışık değerini yoksay (zıplamayı önle)
              if (isDraggingLightRef.current) {
                delete newData.door_light;
              }

              return { ...prev, ...newData };
            });
          }
        })
        .catch(err => console.error('Durum alınamadı:', err));
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 1500);
    return () => clearInterval(interval);
  }, []);

  const showNotification = (type, message) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  const updateDeviceState = async (deviceName, value) => {
    setDeviceStates(prev => ({ ...prev, [deviceName]: value }));
    try {
      const res = await fetch(`${API_BASE}/api/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_name: deviceName, state_value: value })
      });
      const data = await res.json();
      // API'den gelen güncel state'i uygula (rain otomasyonu olabilir)
      if (data.data) {
        setDeviceStates(prev => ({ ...prev, ...data.data }));
      }
    } catch (err) {
      console.error(`${deviceName} güncellenemedi:`, err);
    }
  };

  // Fotoğrafı API'den çek
  const fetchPhoto = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/photo`);
      const data = await res.json();
      if (data.photo) {
        setPhotoBase64(data.photo);
      }
    } catch (err) {
      console.error('Fotoğraf alınamadı:', err);
    }
  };

  // last_photo değiştiğinde fotoğrafı yeniden çek
  useEffect(() => {
    if (deviceStates.last_photo) {
      fetchPhoto();
    }
  }, [deviceStates.last_photo]);

  const handleCapturePhoto = async () => {
    setCaptureStatus('📸 Fotoğraf çekiliyor...');
    try {
      await fetch(`${API_BASE}/api/capture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger: true })
      });
      setCaptureStatus('✅ İstek Pi\'ye iletildi');
      // 3sn sonra fotoğrafı güncelle
      setTimeout(async () => {
        await fetchPhoto();
        setCaptureStatus('');
      }, 3000);
    } catch (err) {
      setCaptureStatus('❌ Pi\'ye ulaşılamadı');
      setTimeout(() => setCaptureStatus(''), 3000);
    }
  };

  const handleSendEmail = async () => {
    if (!email) {
      setEmailStatus('⚠️ Lütfen geçerli bir e-posta girin.');
      return;
    }
    setEmailStatus('📤 Gönderiliyor...');
    try {
      const res = await fetch(`${API_BASE}/api/email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await res.json();
      setEmailStatus(data.message);
      setTimeout(() => setEmailStatus(''), 5000);
    } catch (err) {
      setEmailStatus('❌ Gönderim başarısız.');
      setTimeout(() => setEmailStatus(''), 3000);
    }
  };

  const isRaining = deviceStates.rain_status === 'raining';
  const isPiConnected = deviceStates.pi_connected === 'true';
  const lightPct = parseInt(deviceStates.door_light) || 0;

  return (
    <>
      {/* Bildirim Toast */}
      {notification && (
        <div className={`toast toast-${notification.type}`}>
          {notification.message}
        </div>
      )}

      <header>
        <div className="header-badges">
          <div className={`pi-badge ${isPiConnected ? 'connected' : 'disconnected'}`}>
            <span className="pi-dot"></span>
            {isPiConnected ? 'Pi Bağlı' : 'Pi Çevrimdışı'}
          </div>
          <div className={`rain-badge ${!isPiConnected ? 'dry' : (isRaining ? 'raining' : 'dry')}`} style={!isPiConnected ? { opacity: 0.6 } : {}}>
            {!isPiConnected ? '❓ Veri Yok' : (isRaining ? '🌧️ Yağmur Var' : '☀️ Hava Açık')}
          </div>
        </div>
        <h1 className="dashboard-title">Akıllı Ev Merkezi</h1>
        <p className="dashboard-subtitle">Raspberry Pi Kontrol Paneli</p>
      </header>

      <div className="dashboard-grid">

        {/* =================== 1. Hava & Tente =================== */}
        <div className="card">
          <div className="card-header">
            <h2>🏕️ Balkon Tentesi</h2>
            <div className={`status-indicator ${!isPiConnected ? 'badge-ok' : (isRaining ? 'badge-warn' : 'badge-ok')}`} style={!isPiConnected ? { opacity: 0.6 } : {}}>
              <div className={`status-dot ${!isPiConnected ? 'safe' : (isRaining ? 'raining' : 'safe')}`} style={!isPiConnected ? { background: '#94a3b8', boxShadow: 'none' } : {}}></div>
              {!isPiConnected ? 'Veri Yok' : (isRaining ? 'Yağmur!' : 'Hava Kuru')}
            </div>
          </div>
          <div className="card-content">
            {isRaining && (
              <div className="auto-banner" style={{background: 'var(--danger)'}}>
                🌧️ Yağmur yağıyor, tenteyi kapatmayı unutmayın!
              </div>
            )}
            <p className="label-text">Motor Hız Kontrolü</p>
            <div className="button-group">
              <button
                className={deviceStates.tent === 'closed' ? 'active danger-active' : ''}
                onClick={() => updateDeviceState('tent', 'closed')}>
                ⛔ Durdur
              </button>
              <button
                className={deviceStates.tent === 'forward' ? 'active primary-active' : ''}
                onClick={() => updateDeviceState('tent', 'forward')}>
                🔼 Aç (İleri)
              </button>
              <button
                className={deviceStates.tent === 'backward' ? 'active primary-active' : ''}
                onClick={() => updateDeviceState('tent', 'backward')}>
                🔽 Kapat (Geri)
              </button>
            </div>
          </div>
        </div>

        {/* =================== 2. Sıcaklık & Isıtıcı =================== */}
        <div className="card">
          <div className="card-header">
            <h2>🔥 Isıtma Sistemi</h2>
            <div className={`status-indicator ${deviceStates.heater === 'on' ? 'badge-danger' : 'badge-ok'}`}>
              <div className={`status-dot ${deviceStates.heater === 'on' ? 'active' : 'inactive'}`}></div>
              {deviceStates.heater === 'on' ? 'Isıtıcı Açık' : 'Isıtıcı Kapalı'}
            </div>
          </div>
          <div className="card-content">
            <div className="temp-grid">
              <div className="temp-card">
                <span className="temp-label">🛋️ Salon</span>
                <span className="temp-val">
                  {isPiConnected && deviceStates.room_1_temp ? (
                    <>
                      {deviceStates.room_1_temp}
                      <small style={{ fontSize: '1rem' }}>°C</small>
                    </>
                  ) : (
                    <span style={{ fontSize: '1.2rem', color: '#94a3b8' }}>
                      {isPiConnected ? 'Sensör Yok' : 'Veri Yok'}
                    </span>
                  )}
                </span>
                <span className="temp-src">DS18B20 Sensör</span>
              </div>
              <div className="temp-card">
                <span className="temp-label">🛏️ Yatak Odası</span>
                <span className="temp-val">
                  {isPiConnected && deviceStates.room_2_temp ? (
                    <>
                      {deviceStates.room_2_temp}
                      <small style={{ fontSize: '1rem' }}>°C</small>
                    </>
                  ) : (
                    <span style={{ fontSize: '1.2rem', color: '#94a3b8' }}>
                      {isPiConnected ? 'Sensör Yok' : 'Veri Yok'}
                    </span>
                  )}
                </span>
                <span className="temp-src">DS18B20 Sensör</span>
              </div>
            </div>
            <p className="label-text" style={{ marginTop: '0.5rem' }}>Merkezi Şerit Isıtıcı (Her İki Oda)</p>
            <button
              className={`primary-action ${deviceStates.heater === 'on' ? 'danger-action' : ''}`}
              onClick={() => updateDeviceState('heater', deviceStates.heater === 'on' ? 'off' : 'on')}>
              {deviceStates.heater === 'on' ? '🔥 Isıtıcıyı Kapat' : '❄️ Isıtıcıyı Aç'}
            </button>
          </div>
        </div>

        {/* =================== 3. Soğutma Fanları =================== */}
        <div className="card">
          <div className="card-header">
            <h2>❄️ Soğutma Fanları</h2>
          </div>
          <div className="card-content">
            <div>
              <p className="label-text">🛋️ Salon Fanı</p>
              <div className="button-group">
                <button className={deviceStates.fan_1 === 'off' ? 'active danger-active' : ''} onClick={() => updateDeviceState('fan_1', 'off')}>Kapalı</button>
                <button className={deviceStates.fan_1 === 'slow' ? 'active primary-active' : ''} onClick={() => updateDeviceState('fan_1', 'slow')}>Yavaş</button>
                <button className={deviceStates.fan_1 === 'medium' ? 'active primary-active' : ''} onClick={() => updateDeviceState('fan_1', 'medium')}>Orta</button>
                <button className={deviceStates.fan_1 === 'fast' ? 'active primary-active' : ''} onClick={() => updateDeviceState('fan_1', 'fast')}>Hızlı</button>
              </div>
            </div>
            <div style={{ marginTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '1rem' }}>
              <p className="label-text">🛏️ Yatak Odası Fanı</p>
              <div className="button-group">
                <button className={deviceStates.fan_2 === 'off' ? 'active danger-active' : ''} onClick={() => updateDeviceState('fan_2', 'off')}>Kapalı</button>
                <button className={deviceStates.fan_2 === 'slow' ? 'active primary-active' : ''} onClick={() => updateDeviceState('fan_2', 'slow')}>Yavaş</button>
                <button className={deviceStates.fan_2 === 'medium' ? 'active primary-active' : ''} onClick={() => updateDeviceState('fan_2', 'medium')}>Orta</button>
                <button className={deviceStates.fan_2 === 'fast' ? 'active primary-active' : ''} onClick={() => updateDeviceState('fan_2', 'fast')}>Hızlı</button>
              </div>
            </div>
          </div>
        </div>

        {/* =================== 4. Kapı Aydınlatma =================== */}
        <div className="card">
          <div className="card-header">
            <h2>💡 Dış Kapı Aydınlatma</h2>
            <div className="status-indicator" style={
              !isPiConnected ? { background: '#1e293b', borderColor: '#334155', color: '#94a3b8' } :
              {
                background: `rgba(245, 158, 11, ${lightPct / 200 + 0.1})`,
                borderColor: 'rgba(245, 158, 11, 0.4)'
              }
            }>
              {!isPiConnected ? 'Veri Yok' : `%${lightPct}`}
            </div>
          </div>
          <div className="card-content">
            <p className="label-text">12V Kapı Lambası — PWM Parlaklık Kontrolü</p>
            <div className="slider-container">
              <div className="slider-labels">
                <span>0%</span>
                <span style={{ color: 'var(--accent-warning)', fontWeight: '700' }}>%{lightPct}</span>
                <span>100%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={lightPct}
                onPointerDown={() => { isDraggingLightRef.current = true; }}
                onChange={(e) => setDeviceStates(prev => ({ ...prev, door_light: e.target.value }))}
                onPointerUp={(e) => {
                  isDraggingLightRef.current = false;
                  updateDeviceState('door_light', e.target.value);
                }}
              />
            </div>
            <div className="light-visualizer">
              <div className="light-fill" style={{ width: !isPiConnected ? '0%' : `${lightPct}%`, background: !isPiConnected ? '#475569' : '' }}>
                {isPiConnected && lightPct > 20 && <span className="light-label">💡 {lightPct}%</span>}
              </div>
            </div>
          </div>
        </div>

        {/* =================== 5. Kamera & E-posta =================== */}
        <div className="card card-wide">
          <div className="card-header">
            <h2>📷 Güvenlik Kamerası</h2>
            <div className="status-indicator">
              <div className="rec-dot" style={{ display: 'inline-block', marginRight: '6px' }}></div>
              Canlı
            </div>
          </div>
          <div className="card-content">
            <div className="camera-section">
              {/* Kamera önizleme / son fotoğraf */}
              <div className="camera-feed">
                <div className="camera-grid-lines"></div>
                <div className="rec-indicator">
                  <div className="rec-dot"></div>
                  REC
                </div>
                {photoBase64 ? (
                  <img
                    src={`data:image/jpeg;base64,${photoBase64}`}
                    alt="Son kamera görüntüsü"
                    style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '10px' }}
                  />
                ) : (
                  <span style={{ color: 'rgba(255,255,255,0.35)', fontWeight: '600', letterSpacing: '2px', fontSize: '0.85rem' }}>
                    KAMERA BEKLİYOR
                  </span>
                )}
              </div>

              {/* Fotoğraf çek + E-posta bölümü yan yana */}
              <div className="camera-controls">
                <button
                  className="primary-action capture-btn"
                  onClick={handleCapturePhoto}
                  style={{ background: 'linear-gradient(135deg, #7c3aed, #6d28d9)' }}>
                  📸 Fotoğraf Çek
                </button>
                {captureStatus && (
                  <p className="status-msg">{captureStatus}</p>
                )}

                <div className="divider"></div>

                <p className="label-text">✉️ Son Fotoğrafı Gmail ile Gönder</p>
                <div className="input-wrapper">
                  <span className="input-icon">@</span>
                  <input
                    type="email"
                    placeholder="ornek@gmail.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSendEmail()}
                  />
                </div>
                <button className="primary-action" onClick={handleSendEmail}>
                  📤 Fotoğrafı E-Posta ile Gönder
                </button>
                {emailStatus && (
                  <p className="status-msg" style={{
                    color: emailStatus.startsWith('✅') ? 'var(--accent-success)' : 'var(--accent-warning)'
                  }}>
                    {emailStatus}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

      </div>
    </>
  );
}

export default App;
