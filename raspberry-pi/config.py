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

# Fanlar (PWM Hız Kontrolü - Doğrudan GPIO)
FAN_1_PIN = 18  # Salon Fanı (Hardware PWM destekli)
FAN_2_PIN = 26  # Yatak Odası Fanı (GPIO 19 Stepper için ayrıldığı için 26'ya alındı)

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

# Tente Motor Sürücü (ULN2003 Stepper Motor)
TENT_STEP_PINS = [5, 6, 13, 19]  # IN1, IN2, IN3, IN4

# Tente Motor Hız Değerleri (Adım bekleme süresi saniye cinsinden)
TENT_SPEEDS = {
    "closed": 0,
    "slow":   0.005,
    "medium": 0.003,
    "fast":   0.001,
}

# Sıcaklık Sensörleri (DHT11)
DHT_SENSOR_TYPE = 11   # 11 = DHT11, 22 = DHT22
ROOM1_DHT_PIN   = 4    # Salon
ROOM2_DHT_PIN   = 5    # Yatak Odası

# Yağmur Sensörü (Dijital çıkış)
RAIN_SENSOR_PIN = 27   # DO pini (LOW=yağmur var, HIGH=kuru — bazı modüller ters)
RAIN_ACTIVE_LOW = True  # Çoğu modül LOW geldiğinde algılar

# PIR Hareket Sensörü (Kapı kamerası tetikleyici)
PIR_PIN = 16
