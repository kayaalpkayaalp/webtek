import { useState, useEffect, useRef } from 'react';

const API_BASE = import.meta.env.PROD ? '' : 'http://localhost:3000';

function App() {
  const [deviceStates, setDeviceStates] = useState({
    tent: 'closed',
    heater_1: 'off',
    heater_2: 'off',
    fan_1: 'off',
    fan_2: 'off',
    room_1_temp: '',
    room_2_temp: '',
    rain_status: 'dry',
    last_photo: '',
    pi_connected: 'false',
    ambient_light: '',
    bulb_brightness: '0',
  });
  const [email, setEmail] = useState('');
  const [emailStatus, setEmailStatus] = useState('');
  const [captureStatus, setCaptureStatus] = useState('');
  const [notification, setNotification] = useState(null);
  const [photoBase64, setPhotoBase64] = useState(null);
  const prevRainRef = useRef('dry');
  const isDraggingBulbRef = useRef(false);

  // Canlı saat (sadece görsel)
  const [currentTime, setCurrentTime] = useState(new Date());

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
              if (isDraggingBulbRef.current) {
                delete newData.bulb_brightness;
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

  // Saat güncellemesi
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
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
  const bulbPct = parseInt(deviceStates.bulb_brightness) || 0;
  const ambientLux = deviceStates.ambient_light ? parseFloat(deviceStates.ambient_light) : null;

  // Lux seviyesine göre açıklama ve renk
  const getLuxInfo = (lux) => {
    if (lux === null) return { label: 'Veri Yok', color: '#94a3b8', level: 0 };
    if (lux < 50) return { label: 'Çok Karanlık', color: '#6366f1', level: 1 };
    if (lux < 200) return { label: 'Loş', color: '#8b5cf6', level: 2 };
    if (lux < 500) return { label: 'Normal', color: '#f59e0b', level: 3 };
    if (lux < 1000) return { label: 'Aydınlık', color: '#fb923c', level: 4 };
    return { label: 'Çok Parlak', color: '#fbbf24', level: 5 };
  };
  const luxInfo = getLuxInfo(ambientLux);

  const formatTime = (date) => {
    return date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };
  const formatDate = (date) => {
    return date.toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  };

  return (
    <>
      {/* Bildirim Toast */}
      {notification && (
        <div className={`toast toast-${notification.type}`}>
          {notification.message}
        </div>
      )}

      {/* Floating Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-brand">
            <div className="brand-icon">🏠</div>
            <div>
              <h1>Akıllı Ev</h1>
              <p className="header-date">{formatDate(currentTime)}</p>
            </div>
          </div>
          <div className="header-clock">{formatTime(currentTime)}</div>
          <div className="header-status">
            <div className={`status-pill ${isPiConnected ? 'pill-success' : 'pill-danger'}`}>
              <span className="pill-dot"></span>
              {isPiConnected ? 'Pi Bağlı' : 'Pi Çevrimdışı'}
            </div>
            <div className={`status-pill ${!isPiConnected ? 'pill-muted' : (isRaining ? 'pill-info' : 'pill-warm')}`}>
              {!isPiConnected ? '❓ Veri Yok' : (isRaining ? '🌧️ Yağmur' : '☀️ Açık')}
            </div>
          </div>
        </div>
      </header>

      <main className="dashboard">
        <div className="dashboard-grid">

          {/* =================== 1. Balkon Tentesi =================== */}
          <div className="device-card card-tent" style={{'--card-accent': '#8b5cf6'}}>
            <div className="card-glow"></div>
            <div className="card-header">
              <div className="card-icon-wrap" style={{'--icon-bg': 'rgba(139, 92, 246, 0.15)'}}>🏕️</div>
              <div className="card-title-area">
                <h2>Balkon Tentesi</h2>
                <span className={`mini-badge ${!isPiConnected ? '' : (isRaining ? 'badge-rain' : 'badge-clear')}`}>
                  {!isPiConnected ? 'Veri Yok' : (isRaining ? '🌧️ Yağmur!' : '☀️ Kuru')}
                </span>
              </div>
            </div>
            <div className="card-body">
              {isRaining && (
                <div className="alert-banner alert-rain">
                  🌧️ Yağmur yağıyor, tenteyi kapatmayı unutmayın!
                </div>
              )}
              <button
                className={`action-btn ${deviceStates.tent === 'closed' ? 'btn-idle' : 'btn-danger pulse-anim'}`}
                onClick={() => updateDeviceState('tent', 'closed')}>
                {deviceStates.tent === 'closed' ? '✅ Motor Beklemede' : '⛔ Motoru Durdur'}
              </button>
              <div className="tent-directions">
                <div className="direction-group">
                  <span className="direction-label">🔼 Aç (İleri)</span>
                  <div className="speed-btns">
                    <button className={deviceStates.tent === 'forward_slow' ? 'active accent' : ''} onClick={() => updateDeviceState('tent', 'forward_slow')}>🐢 Yavaş</button>
                    <button className={deviceStates.tent === 'forward_medium' ? 'active accent' : ''} onClick={() => updateDeviceState('tent', 'forward_medium')}>🚶 Orta</button>
                    <button className={deviceStates.tent === 'forward_fast' ? 'active accent' : ''} onClick={() => updateDeviceState('tent', 'forward_fast')}>🚀 Hızlı</button>
                  </div>
                </div>
                <div className="direction-group">
                  <span className="direction-label">🔽 Kapat (Geri)</span>
                  <div className="speed-btns">
                    <button className={deviceStates.tent === 'backward_slow' ? 'active warn' : ''} onClick={() => updateDeviceState('tent', 'backward_slow')}>🐢 Yavaş</button>
                    <button className={deviceStates.tent === 'backward_medium' ? 'active warn' : ''} onClick={() => updateDeviceState('tent', 'backward_medium')}>🚶 Orta</button>
                    <button className={deviceStates.tent === 'backward_fast' ? 'active warn' : ''} onClick={() => updateDeviceState('tent', 'backward_fast')}>🚀 Hızlı</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* =================== 2. Isıtma Sistemi =================== */}
          <div className="device-card card-heat" style={{'--card-accent': '#f97316'}}>
            <div className="card-glow"></div>
            <div className="card-header">
              <div className="card-icon-wrap" style={{'--icon-bg': 'rgba(249, 115, 22, 0.15)'}}>🔥</div>
              <div className="card-title-area">
                <h2>Isıtma Sistemi</h2>
                <span className={`mini-badge ${(deviceStates.heater_1 === 'on' || deviceStates.heater_2 === 'on') ? 'badge-hot' : 'badge-off'}`}>
                  {deviceStates.heater_1 === 'on' && deviceStates.heater_2 === 'on'
                    ? '🔥 İkisi Açık'
                    : deviceStates.heater_1 === 'on'
                      ? '🔥 Salon Açık'
                      : deviceStates.heater_2 === 'on'
                        ? '🔥 Yatak Odası Açık'
                        : 'Kapalı'}
                </span>
              </div>
            </div>
            <div className="card-body">
              {/* Salon */}
              <div className="room-block">
                <div className="room-info">
                  <div className="room-header">
                    <span className="room-name">🛋️ Salon</span>
                    <span className="sensor-tag">DS18B20</span>
                  </div>
                  <div className="temp-display">
                    {isPiConnected && deviceStates.room_1_temp ? (
                      <>
                        <span className="temp-number">{deviceStates.room_1_temp}</span>
                        <span className="temp-unit">°C</span>
                      </>
                    ) : (
                      <span className="temp-na">{isPiConnected ? 'Sensör Yok' : 'Veri Yok'}</span>
                    )}
                  </div>
                </div>
                <button
                  className={`action-btn ${deviceStates.heater_1 === 'on' ? 'btn-danger' : 'btn-primary'}`}
                  onClick={() => updateDeviceState('heater_1', deviceStates.heater_1 === 'on' ? 'off' : 'on')}>
                  {deviceStates.heater_1 === 'on' ? '🔥 Salon Isıtıcıyı Kapat' : '❄️ Salon Isıtıcıyı Aç'}
                </button>
              </div>

              <div className="room-divider"></div>

              {/* Yatak Odası */}
              <div className="room-block">
                <div className="room-info">
                  <div className="room-header">
                    <span className="room-name">🛏️ Yatak Odası</span>
                    <span className="sensor-tag">DS18B20</span>
                  </div>
                  <div className="temp-display">
                    {isPiConnected && deviceStates.room_2_temp ? (
                      <>
                        <span className="temp-number">{deviceStates.room_2_temp}</span>
                        <span className="temp-unit">°C</span>
                      </>
                    ) : (
                      <span className="temp-na">{isPiConnected ? 'Sensör Yok' : 'Veri Yok'}</span>
                    )}
                  </div>
                </div>
                <button
                  className={`action-btn ${deviceStates.heater_2 === 'on' ? 'btn-danger' : 'btn-primary'}`}
                  onClick={() => updateDeviceState('heater_2', deviceStates.heater_2 === 'on' ? 'off' : 'on')}>
                  {deviceStates.heater_2 === 'on' ? '🔥 Yatak Odası Isıtıcıyı Kapat' : '❄️ Yatak Odası Isıtıcıyı Aç'}
                </button>
              </div>
            </div>
          </div>

          {/* =================== 3. Soğutma Fanları =================== */}
          <div className="device-card card-fan" style={{'--card-accent': '#06b6d4'}}>
            <div className="card-glow"></div>
            <div className="card-header">
              <div className="card-icon-wrap" style={{'--icon-bg': 'rgba(6, 182, 212, 0.15)'}}>❄️</div>
              <div className="card-title-area">
                <h2>Soğutma Fanları</h2>
              </div>
            </div>
            <div className="card-body">
              <div className="fan-room">
                <span className="fan-room-label">🛋️ Salon Fanı</span>
                <div className="seg-control">
                  <button className={deviceStates.fan_1 === 'off' ? 'active off' : ''} onClick={() => updateDeviceState('fan_1', 'off')}>Kapalı</button>
                  <button className={deviceStates.fan_1 === 'slow' ? 'active on' : ''} onClick={() => updateDeviceState('fan_1', 'slow')}>Yavaş</button>
                  <button className={deviceStates.fan_1 === 'medium' ? 'active on' : ''} onClick={() => updateDeviceState('fan_1', 'medium')}>Orta</button>
                  <button className={deviceStates.fan_1 === 'fast' ? 'active on' : ''} onClick={() => updateDeviceState('fan_1', 'fast')}>Hızlı</button>
                </div>
              </div>
              <div className="room-divider"></div>
              <div className="fan-room">
                <span className="fan-room-label">🛏️ Yatak Odası Fanı</span>
                <div className="seg-control">
                  <button className={deviceStates.fan_2 === 'off' ? 'active off' : ''} onClick={() => updateDeviceState('fan_2', 'off')}>Kapalı</button>
                  <button className={deviceStates.fan_2 === 'slow' ? 'active on' : ''} onClick={() => updateDeviceState('fan_2', 'slow')}>Yavaş</button>
                  <button className={deviceStates.fan_2 === 'medium' ? 'active on' : ''} onClick={() => updateDeviceState('fan_2', 'medium')}>Orta</button>
                  <button className={deviceStates.fan_2 === 'fast' ? 'active on' : ''} onClick={() => updateDeviceState('fan_2', 'fast')}>Hızlı</button>
                </div>
              </div>
            </div>
          </div>

          {/* =================== 4. Aydınlatma Kontrolü =================== */}
          <div className="device-card card-light" style={{'--card-accent': '#eab308'}}>
            <div className="card-glow"></div>
            <div className="card-header">
              <div className="card-icon-wrap" style={{'--icon-bg': 'rgba(234, 179, 8, 0.15)'}}>🔆</div>
              <div className="card-title-area">
                <h2>Aydınlatma</h2>
                <span className="mini-badge" style={{
                  background: isPiConnected ? `rgba(${luxInfo.level >= 3 ? '251,191,36' : '99,102,241'}, 0.15)` : 'rgba(148,163,184,0.08)',
                  color: isPiConnected ? luxInfo.color : '#94a3b8'
                }}>
                  {!isPiConnected ? 'Veri Yok' : luxInfo.label}
                </span>
              </div>
            </div>
            <div className="card-body">
              {/* Ortam Işık Sensörü */}
              <div className="light-sensor-area">
                <span className="section-label">☀️ Ortam Işığı — BH1750</span>
                <div className="lux-card">
                  <span className="lux-big" style={{ color: luxInfo.color }}>
                    {isPiConnected && ambientLux !== null ? ambientLux : '—'}
                  </span>
                  <span className="lux-unit-label">lux</span>
                  <span className="lux-desc" style={{ color: luxInfo.color }}>
                    {isPiConnected ? luxInfo.label : 'Pi Bağlı Değil'}
                  </span>
                </div>
                <div className="lux-bar-wrap">
                  <div className="lux-bar-ends"><span>🌙</span><span>☀️</span></div>
                  <div className="lux-track">
                    <div className="lux-fill" style={{
                      width: isPiConnected && ambientLux !== null
                        ? `${Math.min((ambientLux / 2000) * 100, 100)}%`
                        : '0%',
                      background: isPiConnected
                        ? 'linear-gradient(90deg, #6366f1, #8b5cf6, #f59e0b, #fbbf24)'
                        : '#475569'
                    }}></div>
                  </div>
                </div>
              </div>

              <div className="room-divider"></div>

              {/* Ampul Parlaklık Kontrolü */}
              <div className="bulb-area">
                <span className="section-label">💡 Ampul Parlaklığı — PWM</span>
                <div className="bulb-slider-row">
                  <span className="slider-edge">Kapalı</span>
                  <span className="slider-value" style={{ color: bulbPct > 0 ? '#fbbf24' : '#94a3b8' }}>%{bulbPct}</span>
                  <span className="slider-edge">Tam</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={bulbPct}
                  className="range-input"
                  onPointerDown={() => { isDraggingBulbRef.current = true; }}
                  onChange={(e) => setDeviceStates(prev => ({ ...prev, bulb_brightness: e.target.value }))}
                  onPointerUp={(e) => {
                    isDraggingBulbRef.current = false;
                    updateDeviceState('bulb_brightness', e.target.value);
                  }}
                />
                <div className="bulb-visual">
                  <div className="bulb-emoji-wrap">
                    <span className="bulb-emoji" style={{
                      filter: `brightness(${0.3 + (bulbPct / 100) * 1.5})`,
                      opacity: bulbPct > 0 ? 1 : 0.3,
                      textShadow: bulbPct > 50 ? `0 0 ${bulbPct / 3}px rgba(251, 191, 36, 0.8)` : 'none'
                    }}>💡</span>
                    <span className="bulb-state">
                      {bulbPct === 0 ? 'Kapalı' : bulbPct < 30 ? 'Kısık' : bulbPct < 70 ? 'Orta' : 'Tam Güç'}
                    </span>
                  </div>
                  <div className="bulb-progress-track">
                    <div className="bulb-progress-fill" style={{
                      width: `${bulbPct}%`,
                      background: bulbPct > 0
                        ? 'linear-gradient(90deg, rgba(251, 191, 36, 0.3), rgba(251, 191, 36, 0.9))'
                        : '#475569',
                      boxShadow: bulbPct > 20 ? `0 0 ${bulbPct / 5}px rgba(251, 191, 36, 0.5)` : 'none'
                    }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* =================== 5. Güvenlik Kamerası =================== */}
          <div className="device-card card-camera card-full" style={{'--card-accent': '#10b981'}}>
            <div className="card-glow"></div>
            <div className="card-header">
              <div className="card-icon-wrap" style={{'--icon-bg': 'rgba(16, 185, 129, 0.15)'}}>📷</div>
              <div className="card-title-area">
                <h2>Güvenlik Kamerası</h2>
                <span className="mini-badge badge-live">
                  <span className="rec-dot-mini"></span> Canlı
                </span>
              </div>
            </div>
            <div className="card-body">
              <div className="camera-layout">
                {/* Kamera önizleme */}
                <div className="camera-preview">
                  <div className="camera-overlay-grid"></div>
                  <div className="camera-rec-tag">
                    <span className="rec-dot-mini"></span> REC
                  </div>
                  {photoBase64 ? (
                    <img
                      src={`data:image/jpeg;base64,${photoBase64}`}
                      alt="Son kamera görüntüsü"
                    />
                  ) : (
                    <span className="camera-placeholder">KAMERA BEKLİYOR</span>
                  )}
                </div>

                {/* Kontroller */}
                <div className="camera-actions">
                  <button className="action-btn btn-capture" onClick={handleCapturePhoto}>
                    📸 Fotoğraf Çek
                  </button>
                  {captureStatus && (
                    <p className="feedback-msg">{captureStatus}</p>
                  )}

                  <div className="room-divider"></div>

                  <span className="section-label">✉️ Son Fotoğrafı Gmail ile Gönder</span>
                  <div className="email-input-wrap">
                    <span className="email-at">@</span>
                    <input
                      type="email"
                      placeholder="ornek@gmail.com"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleSendEmail()}
                    />
                  </div>
                  <button className="action-btn btn-primary" onClick={handleSendEmail}>
                    📤 Fotoğrafı Gönder
                  </button>
                  {emailStatus && (
                    <p className="feedback-msg" style={{
                      color: emailStatus.startsWith('✅') ? '#10b981' : '#f59e0b'
                    }}>
                      {emailStatus}
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>

        </div>
      </main>
    </>
  );
}

export default App;
