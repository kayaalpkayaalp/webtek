"""
sensors.py — Sensör Okuma Modülü
==================================
- DHT11 / DHT22 sıcaklık sensörü okuma (iki oda)
- DS18B20 (1-Wire) sıcaklık sensörü okuma (opsiyonel, GPIO 4)
- Yağmur sensörü okuma (dijital)
- PIR hareket sensörü okuma

Gerçek donanımda: import adafruit_dht ve RPi.GPIO kullan.
Simülasyon modunda: Sahte değerler döndürülür.
"""

import logging
import random
import os
import glob

log = logging.getLogger("sensors")

# ── Donanım İmport'u ─────────────────────────────────────────────────────────
try:
    import board
    import adafruit_dht
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    log.warning("⚠️  RPi kütüphaneleri bulunamadı. Simülasyon modunda çalışıyor.")

from config import (
    DHT_SENSOR_TYPE,
    ROOM1_DHT_PIN,
    ROOM2_DHT_PIN,
    RAIN_SENSOR_PIN,
    RAIN_ACTIVE_LOW,
)

# ── DHT Sensör Nesneleri (gerçek donanımda) ──────────────────────────────────
_dht1 = None
_dht2 = None

def _init_dht_sensors():
    global _dht1, _dht2
    if not HARDWARE_AVAILABLE:
        return
    try:
        # DHT1 (Room 1)
        try:
            pin1 = getattr(board, f"D{ROOM1_DHT_PIN}")
            SensorClass = adafruit_dht.DHT11 if DHT_SENSOR_TYPE == 11 else adafruit_dht.DHT22
            _dht1 = SensorClass(pin1, use_pulseio=False)
        except Exception as e:
            log.warning(f"DHT1 (Pin {ROOM1_DHT_PIN}) başlatılamadı: {e}")

        # DHT2 (Room 2)
        try:
            pin2 = getattr(board, f"D{ROOM2_DHT_PIN}")
            SensorClass = adafruit_dht.DHT11 if DHT_SENSOR_TYPE == 11 else adafruit_dht.DHT22
            _dht2 = SensorClass(pin2, use_pulseio=False)
        except Exception as e:
            log.warning(f"DHT2 (Pin {ROOM2_DHT_PIN}) başlatılamadı: {e}")

        log.info("✅ DHT sensörler kontrol edildi.")
    except Exception as e:
        log.error(f"DHT sensör genel başlatma hatası: {e}")


# ── 1-Wire (DS18B20) Okuma Logic ─────────────────────────────────────────────
def read_ds18b20_all():
    """
    /sys/bus/w1/devices/ altındaki TÜM DS18B20 sensörlerini oku.
    Döndürür: Liste [temp1, temp2, ...]
    """
    if not HARDWARE_AVAILABLE:
        return []

    temps = []
    try:
        base_dir = '/sys/bus/w1/devices/'
        device_folders = glob.glob(base_dir + '28*')
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
    İki odanın sıcaklığını oku.
    Döndürür: (room1_temp: int|None, room2_temp: int|None)
    
    Not: Eğer 1-Wire (GPIO 4) hattında sensörler varsa onları kullanır.
    """
    if not HARDWARE_AVAILABLE:
        # Simülasyon: Gerçekçi dalgalı değerler
        base1 = 23
        base2 = 22
        return (
            base1 + random.choice([-1, 0, 0, 1]),
            base2 + random.choice([-1, 0, 0, 1]),
        )

    ds_temps = read_ds18b20_all()
    
    # --- Room 1 (Salon) ---
    t1 = None
    if len(ds_temps) >= 1:
        t1 = ds_temps[0]
        if not hasattr(read_temperatures, "_ds1_logged"):
            log.info(f"📌 1-Wire Sensör 1 algılandı ({t1}°C), Salon için kullanılıyor.")
            read_temperatures._ds1_logged = True
    elif _dht1:
        try:
            t1 = int(_dht1.temperature) if _dht1.temperature is not None else None
        except Exception:
            t1 = None

    # --- Room 2 (Yatak Odası) ---
    t2 = None
    if len(ds_temps) >= 2:
        t2 = ds_temps[1]
        if not hasattr(read_temperatures, "_ds2_logged"):
            log.info(f"📌 1-Wire Sensör 2 algılandı ({t2}°C), Yatak Odası için kullanılıyor.")
            read_temperatures._ds2_logged = True
    elif _dht2:
        try:
            t2 = int(_dht2.temperature) if _dht2.temperature is not None else None
        except Exception:
            t2 = None

    return t1, t2


def read_rain_sensor() -> str:
    """
    Yağmur sensörünü oku.
    Döndürür: 'raining' veya 'dry'
    """
    if not HARDWARE_AVAILABLE:
        # Simülasyon: %5 ihtimalle yağmur
        return "raining" if random.random() < 0.05 else "dry"

    try:
        pin_value = GPIO.input(RAIN_SENSOR_PIN)
        # RAIN_ACTIVE_LOW=True: LOW gelince yağmur var
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
    """Sensör giriş pinlerini başlat (actuators.py'deki setup_gpio'dan sonra çağrılmalı)."""
    if not HARDWARE_AVAILABLE:
        return
    try:
        from config import PIR_PIN
        GPIO.setup(RAIN_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        log.info("✅ Sensör GPIO pinleri başlatıldı (yağmur + PIR).")
        
        # 1-Wire modüllerini yükle (DS18B20 için)
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')
        
    except Exception as e:
        log.warning(f"Sensör GPIO kurulum hatası: {e}")


# Modül yüklendiğinde DHT sensörleri başlat
_init_dht_sensors()
