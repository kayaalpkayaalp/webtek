"""
actuators.py — Donanım Çıkış Kontrol Modülü
=============================================
- Fan 1 / Fan 2 (röle + PWM hız)
- Isıtıcı (röle)
- Tente motoru (PWM + yön)
- Kapı lambası (PWM)

Donanım yoksa simülasyon modunda sadece log basar.
"""

import logging

log = logging.getLogger("actuators")

# ── Donanım İmport ───────────────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    log.warning("⚠️  RPi.GPIO bulunamadı — simülasyon modu aktif.")

from config import (
    FAN_1_PIN, FAN_2_PIN,
    HEATER_PIN,
    DOOR_LIGHT_PWM_PIN, DOOR_LIGHT_FREQ,
    TENT_ENA_PIN, TENT_IN1_PIN, TENT_IN2_PIN,
    TENT_SPEEDS,
)

# ── PWM Nesneleri ─────────────────────────────────────────────────────────────
_light_pwm = None
_tent_pwm  = None


def setup_gpio():
    """GPIO pinlerini başlat."""
    global _light_pwm, _tent_pwm

    if not HARDWARE_AVAILABLE:
        log.info("[SIM] GPIO ayarları yapıldı (simülasyon)")
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Röle pinleri (çıkış — başlangıçta HIGH = kapalı)
    for pin in [FAN_1_PIN, FAN_2_PIN, HEATER_PIN]:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)

    # Tente motor pinleri
    GPIO.setup(TENT_ENA_PIN, GPIO.OUT)
    GPIO.setup(TENT_IN1_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(TENT_IN2_PIN, GPIO.OUT, initial=GPIO.LOW)

    # Kapı lambası PWM
    GPIO.setup(DOOR_LIGHT_PWM_PIN, GPIO.OUT)
    _light_pwm = GPIO.PWM(DOOR_LIGHT_PWM_PIN, DOOR_LIGHT_FREQ)
    _light_pwm.start(0)

    # Tente motor hız PWM
    _tent_pwm = GPIO.PWM(TENT_ENA_PIN, 1000)
    _tent_pwm.start(0)

    log.info("✅ GPIO kurulumu tamamlandı.")


def cleanup_gpio():
    """Program kapanırken GPIO'yu temizle."""
    if not HARDWARE_AVAILABLE:
        return
    try:
        if _light_pwm: _light_pwm.stop()
        if _tent_pwm:  _tent_pwm.stop()
        GPIO.cleanup()
        log.info("GPIO temizlendi.")
    except Exception as e:
        log.warning(f"GPIO cleanup hatası: {e}")


# ── Durum Takibi (sadece değiştiğinde log bas) ────────────────────────────────
_last_states = {}

# ── Fan Kontrolü ──────────────────────────────────────────────────────────────
# Tek röleli basit fan:  off=HIGH, on=LOW (optolü röle çoğunlukla ters çalışır)
# PWM hız için ek bir MOSFET veya L298N kartı gerekir.
# Bu örnekte: off → röle HIGH, slow/medium/fast → röle LOW (tam hız röle ile)
# Gerçekçi PWM için FAN_X_PWM_PIN ayrı bir pin tanımlaması gerekir.

def apply_fan_state(fan_number: int, state: str):
    pin = FAN_1_PIN if fan_number == 1 else FAN_2_PIN
    key = f"fan_{fan_number}"

    if _last_states.get(key) != state:
        speed_map = {"off": "KAPALI", "slow": "YAVAŞ", "medium": "ORTA", "fast": "HIZLI"}
        log.info(f"💨 Fan {fan_number}: {speed_map.get(state, state)}")
        _last_states[key] = state

    if not HARDWARE_AVAILABLE:
        return

    if state == "off":
        GPIO.output(pin, GPIO.HIGH)
    else:
        GPIO.output(pin, GPIO.LOW)


# ── Isıtıcı Kontrolü ──────────────────────────────────────────────────────────
def apply_heater_state(state: str):
    on = (state == "on")

    if _last_states.get("heater") != state:
        log.info(f"🔥 Isıtıcı: {'AÇIK' if on else 'KAPALI'}")
        _last_states["heater"] = state

    if not HARDWARE_AVAILABLE:
        return

    GPIO.output(HEATER_PIN, GPIO.LOW if on else GPIO.HIGH)


# ── Tente Motor Kontrolü ──────────────────────────────────────────────────────
def apply_tent_state(state: str):
    duty = TENT_SPEEDS.get(state, 0)

    if _last_states.get("tent") != state:
        log.info(f"🏕️  Tente: {state.upper()} (%{duty} duty cycle)")
        _last_states["tent"] = state

    if not HARDWARE_AVAILABLE:
        return

    if state == "closed":
        _tent_pwm.ChangeDutyCycle(0)
        GPIO.output(TENT_IN1_PIN, GPIO.LOW)
        GPIO.output(TENT_IN2_PIN, GPIO.LOW)
    else:
        GPIO.output(TENT_IN1_PIN, GPIO.HIGH)
        GPIO.output(TENT_IN2_PIN, GPIO.LOW)
        _tent_pwm.ChangeDutyCycle(duty)


# ── Kapı Lambası PWM ──────────────────────────────────────────────────────────
def apply_door_light(intensity: int):
    """
    intensity: 0-100 arası parlaklık değeri
    """
    intensity = max(0, min(100, intensity))

    if _last_states.get("light") != intensity:
        log.info(f"💡 Kapı Lambası: %{intensity}")
        _last_states["light"] = intensity

    if not HARDWARE_AVAILABLE:
        return

    _light_pwm.ChangeDutyCycle(intensity)
