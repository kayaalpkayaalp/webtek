"""
config.py — Raspberry Pi Yapılandırma
======================================
Bu dosyada GPIO pin numaralarını ve API URL'ini ayarla.

GPIO Pin Haritası (BCM numaralandırması):
  - Fan 1 (Salon)           : GPIO 18  — PWM (HW-532 vb.)
  - Fan 2 (Yatak Odası)     : GPIO 19  — PWM (HW-532 vb.)
  - Isıtıcı (Şerit)         : GPIO 22  — Röle IN3
  - Kapı Lambası (PWM)       : GPIO 17  — L298N/MOSFET
  - Tente Motor PWM          : GPIO 23  — Motor sürücü
  - Tente Motor Yön A        : GPIO 24  — Motor sürücü IN1
  - Tente Motor Yön B        : GPIO 25  — Motor sürücü IN2
  - DHT11 Sensör 1 (Salon)   : GPIO 4
  - DHT11 Sensör 2 (Yatak)   : GPIO 5
  - Yağmur Sensörü (DO)      : GPIO 6   — Dijital çıkış (0=kuru, 1=ıslak)
  - PIR Hareket Sensörü      : GPIO 16  — Kapı hareketi

NOT: Eğer servo motor kullanıyorsan TENT_PWM_PIN'e servo bağla.
     DC motor için H-bridge (L298N) kullan.
"""

# ─── API Adresi ─────────────────────────────────────────────────────────────
# Vercel'e deploy edildi:
API_URL = "https://webtek-alpha.vercel.app/api"

# Yerel test için (gerekirse bu satırı aç, üsttekini kapat):
# API_URL = "http://localhost:3000/api"

# ─── Polling Aralığı (saniye) ────────────────────────────────────────────────
POLL_INTERVAL = 1.5  # Her 1.5 saniyede bir API'yi kontrol et

# ─── GPIO Pin Numaraları (BCM) ───────────────────────────────────────────────

# Fanlar (PCA9685 I2C Modülü Üzerinden)
PCA_FAN_1_CHANNEL = 15  # 15. Kanal (Salon/Ana Fan)
# Eğer 2. fan da karta bağlanacaksa buraya kanal numarasını girebilirsiniz (örn: 14)
PCA_FAN_2_CHANNEL = None # Şimdilik sadece 1 fan kullanıldığı için None

# Fan Hız Değerleri (duty cycle %)
FAN_SPEEDS = {
    "off":    0,
    "slow":   40,
    "medium": 70,
    "fast":   100,
}

# Isıtıcı Rölesi
HEATER_PIN  = 22

# Kapı Lambası (PWM ile 0-100 parlaklık)
DOOR_LIGHT_PWM_PIN = 17  # 18 numaralı pini fan için ayırdığımızdan bunu 17'ye aldık.
DOOR_LIGHT_FREQ    = 100  # Hz

# Tente Motor Sürücü (L298N veya benzeri)
TENT_ENA_PIN = 23   # PWM hız
TENT_IN1_PIN = 24   # Yön 1
TENT_IN2_PIN = 25   # Yön 2

# Tente Motor Hız Değerleri (duty cycle %)
TENT_SPEEDS = {
    "closed": 0,
    "slow":   40,
    "medium": 65,
    "fast":   100,
}

# Sıcaklık Sensörleri (DHT11)
DHT_SENSOR_TYPE = 11   # 11 = DHT11, 22 = DHT22
ROOM1_DHT_PIN   = 4    # Salon
ROOM2_DHT_PIN   = 5    # Yatak Odası

# Yağmur Sensörü (Dijital çıkış)
RAIN_SENSOR_PIN = 6    # DO pini (LOW=yağmur var, HIGH=kuru — bazı modüller ters)
RAIN_ACTIVE_LOW = True  # Çoğu modül LOW geldiğinde algılar

# PIR Hareket Sensörü (Kapı kamerası tetikleyici)
PIR_PIN = 16
