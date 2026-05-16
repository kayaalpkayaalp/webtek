"""
sensors.py — Sensör Okuma Modülü
==================================
- DS18B20 (1-Wire) sıcaklık sensörü okuma (GPIO 4 üzerinde 1 veya 2 sensör)
- Yağmur sensörü okuma (dijital)
- PIR hareket sensörü okuma

NOT: Simülasyon modu YOK. Sensör bağlı değilse None döner, veri gönderilmez.
"""

import logging
import os
import glob
import time

log = logging.getLogger("sensors")

# ── Donanım İmport'u ─────────────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    log.warning("⚠️  RPi.GPIO bulunamadı. Donanım erişimi yok.")

from config import (
    RAIN_SENSOR_PIN,
    RAIN_ACTIVE_LOW,
)


# ── 1-Wire (DS18B20) Okuma — GPIO 4 ─────────────────────────────────────────
def read_ds18b20_all():
    """
    /sys/bus/w1/devices/ altındaki TÜM DS18B20 sensörlerini oku.
    GPIO 4'e paralel bağlanan her sensörün benzersiz adresi var (28-xxxx).
    Döndürür: Liste [temp1, temp2, ...]
    Sensör yoksa boş liste döner.
    """
    temps = []
    try:
        base_dir = '/sys/bus/w1/devices/'
        device_folders = sorted(glob.glob(base_dir + '28*'))
        for folder in device_folders:
            try:
                device_file = folder + '/w1_slave'
                with open(device_file, 'r') as f:
                    lines = f.readlines()
                if lines[0].strip()[-3:] == 'YES':
                    equals_pos = lines[1].find('t=')
                    if equals_pos != -1:
                        temp_string = lines[1][equals_pos+2:]
                        temps.append(int(float(temp_string) / 1000.0))
            except Exception:
                continue
    except Exception:
        pass
    return temps


def read_temperatures() -> tuple:
    """
    İki odanın sıcaklığını oku (GPIO 4 üzerindeki DS18B20 sensörlerinden).
    Döndürür: (room1_temp: int|None, room2_temp: int|None)
    
    - 1 sensör bağlıysa: her iki odaya aynı değeri gönder
    - 2 sensör bağlıysa: (salon_temp, yatak_temp)
    - Hiç sensör yoksa:   (None, None)
    """
    ds_temps = read_ds18b20_all()

    # --- Room 1 (Salon) ---
    t1 = None
    if len(ds_temps) >= 1:
        t1 = ds_temps[0]
        if not hasattr(read_temperatures, "_ds1_logged"):
            log.info(f"📌 1-Wire Sensör 1 algılandı ({t1}°C) → Salon")
            read_temperatures._ds1_logged = True

    # --- Room 2 (Yatak Odası) ---
    t2 = None
    if len(ds_temps) >= 2:
        t2 = ds_temps[1]
        if not hasattr(read_temperatures, "_ds2_logged"):
            log.info(f"📌 1-Wire Sensör 2 algılandı ({t2}°C) → Yatak Odası")
            read_temperatures._ds2_logged = True
    elif len(ds_temps) == 1:
        # Tek sensör varsa aynı değeri yatak odasına da ata
        t2 = ds_temps[0]
        if not hasattr(read_temperatures, "_ds2_single_logged"):
            log.info(f"📌 Tek sensör var — aynı değer Yatak Odası'na da atandı ({t2}°C)")
            read_temperatures._ds2_single_logged = True

    # Her döngüde sensör sayısını logla (sadece değiştiğinde)
    current_count = len(ds_temps)
    prev_count = getattr(read_temperatures, "_prev_count", -1)
    if current_count != prev_count:
        log.info(f"🌡️  Toplam {current_count} adet DS18B20 sensörü bulundu (GPIO 4).")
        read_temperatures._prev_count = current_count

    return t1, t2


def read_rain_sensor() -> str:
    """
    Yağmur sensörünü oku.
    Döndürür: 'raining' veya 'dry'
    Sensör bağlı değilse 'dry' döner.
    """
    if not HARDWARE_AVAILABLE:
        return "dry"

    try:
        pin_value = GPIO.input(RAIN_SENSOR_PIN)
        if RAIN_ACTIVE_LOW:
            return "raining" if pin_value == GPIO.LOW else "dry"
        else:
            return "raining" if pin_value == GPIO.HIGH else "dry"
    except Exception as e:
        log.warning(f"Yağmur sensörü okunamadı: {e}")
        return "dry"


def read_pir() -> bool:
    """
    PIR hareket sensörünü oku.
    Döndürür: True (hareket var) / False
    """
    if not HARDWARE_AVAILABLE:
        return False
    try:
        from config import PIR_PIN
        return GPIO.input(PIR_PIN) == GPIO.HIGH
    except Exception as e:
        log.warning(f"PIR sensörü okunamadı: {e}")
        return False


# ── Sensör GPIO Kurulumu ──────────────────────────────────────────────────────
def setup_sensor_gpio():
    """Sensör giriş pinlerini başlat."""
    if not HARDWARE_AVAILABLE:
        log.warning("⚠️  Donanım yok, sensör GPIO başlatılamadı.")
        return
    try:
        from config import PIR_PIN
        GPIO.setup(RAIN_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        log.info("✅ Sensör GPIO pinleri başlatıldı (yağmur + PIR).")

        # 1-Wire modüllerini yükle (DS18B20 için gerekli)
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')
        log.info("✅ 1-Wire modülleri yüklendi (DS18B20 için).")

        # Sensörlerin /sys/bus/w1/devices/ altında görünmesini bekle
        log.info("⏳ DS18B20 sensörlerinin tanınması bekleniyor (maks 10 sn)...")
        for i in range(10):
            time.sleep(1)
            devices = glob.glob('/sys/bus/w1/devices/28*')
            if devices:
                log.info(f"✅ {len(devices)} adet DS18B20 sensörü bulundu! ({i+1} sn sonra)")
                for d in devices:
                    log.info(f"   📌 Sensör: {os.path.basename(d)}")
                break
        else:
            log.warning("⚠️  10 saniye beklendi ama DS18B20 sensörü bulunamadı!")
            log.warning("   → Bağlantıyı kontrol edin: DATA → GPIO4, VCC → 3.3V, GND → GND")
            log.warning("   → 4.7kΩ pull-up direnç DATA ile VCC arasında olmalı")
            log.warning("   → /boot/config.txt'de 'dtoverlay=w1-gpio' satırı olmalı")

    except Exception as e:
        log.warning(f"Sensör GPIO kurulum hatası: {e}")
