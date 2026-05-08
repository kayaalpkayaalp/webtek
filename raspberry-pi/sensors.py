"""
sensors.py — Sensör Okuma Modülü
==================================
- DHT11 / DHT22 sıcaklık sensörü okuma (iki oda)
- Yağmur sensörü okuma (dijital)
- PIR hareket sensörü okuma

Gerçek donanımda: import adafruit_dht ve RPi.GPIO kullan.
Simülasyon modunda: Sahte değerler döndürülür.
"""

import logging
import random

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
        pin1 = getattr(board, f"D{ROOM1_DHT_PIN}")
        pin2 = getattr(board, f"D{ROOM2_DHT_PIN}")
        SensorClass = adafruit_dht.DHT11 if DHT_SENSOR_TYPE == 11 else adafruit_dht.DHT22
        _dht1 = SensorClass(pin1, use_pulseio=False)
        _dht2 = SensorClass(pin2, use_pulseio=False)
        log.info("✅ DHT sensörler başlatıldı.")
    except Exception as e:
        log.error(f"DHT sensör başlatma hatası: {e}")


def read_temperatures() -> tuple:
    """
    İki odanın sıcaklığını oku.
    Döndürür: (room1_temp: int, room2_temp: int)
    """
    if not HARDWARE_AVAILABLE or _dht1 is None:
        # Simülasyon: Gerçekçi dalgalı değerler
        base1 = 23
        base2 = 22
        return (
            base1 + random.choice([-1, 0, 0, 1]),
            base2 + random.choice([-1, 0, 0, 1]),
        )

    try:
        t1 = int(_dht1.temperature) if _dht1.temperature else 22
    except Exception:
        t1 = 22

    try:
        t2 = int(_dht2.temperature) if _dht2.temperature else 21
    except Exception:
        t2 = 21

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


# Modül yüklendiğinde DHT sensörleri başlat
_init_dht_sensors()
