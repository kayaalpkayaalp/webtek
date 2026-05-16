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
import threading
import time

log = logging.getLogger("actuators")

# ── Donanım İmport ───────────────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    log.warning("⚠️  RPi.GPIO bulunamadı — simülasyon modu aktif.")

from config import (
    FAN_1_PIN, FAN_2_PIN, FAN_SPEEDS,
    HEATER_PIN,
    DOOR_LIGHT_PWM_PIN, DOOR_LIGHT_FREQ,
    TENT_STEP_PINS, TENT_SPEEDS,
)

# ── PWM ve Durum Nesneleri ────────────────────────────────────────────────────
_light_pwm = None
_fan1_pwm  = None
_fan2_pwm  = None

# Stepper Motor Global Durumları
_tent_state = "closed"
_tent_thread = None

# ULN2003 Half-Step (8 Adım) Dizilimi
_STEP_SEQ = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1]
]

def _stepper_worker():
    """Tente step motorunu arkaplanda döndüren iş parçacığı"""
    step_index = 0
    while True:
        state = _tent_state
        if state == "closed" or not HARDWARE_AVAILABLE:
            # Kapalıysa motoru serbest bırak (ısınmaması için akımı kes)
            if HARDWARE_AVAILABLE:
                for pin in TENT_STEP_PINS:
                    GPIO.output(pin, GPIO.LOW)
            time.sleep(0.1)
            continue
            
        delay = TENT_SPEEDS.get(state, 0.002)
        direction = -1 if state == "backward" else 1
        
        # Bir adım at
        for pin_idx in range(4):
            GPIO.output(TENT_STEP_PINS[pin_idx], _STEP_SEQ[step_index][pin_idx])
            
        step_index = (step_index + direction) % 8
        time.sleep(delay)


def setup_gpio():
    """GPIO pinlerini başlat."""
    global _light_pwm, _fan1_pwm, _fan2_pwm, _tent_thread

    if not HARDWARE_AVAILABLE:
        log.info("[SIM] GPIO ayarları yapıldı (simülasyon)")
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Isıtıcı rölesi (başlangıçta HIGH = kapalı)
    GPIO.setup(HEATER_PIN, GPIO.OUT, initial=GPIO.HIGH)

    # Fan pinleri (PWM MOSFET için doğrudan GPIO)
    GPIO.setup(FAN_1_PIN, GPIO.OUT)
    _fan1_pwm = GPIO.PWM(FAN_1_PIN, 1000) # 1kHz
    _fan1_pwm.start(0)

    GPIO.setup(FAN_2_PIN, GPIO.OUT)
    _fan2_pwm = GPIO.PWM(FAN_2_PIN, 1000)
    _fan2_pwm.start(0)

    # Tente motor pinleri (ULN2003 Stepper)
    for pin in TENT_STEP_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
        
    # Stepper iş parçacığını başlat
    if _tent_thread is None:
        _tent_thread = threading.Thread(target=_stepper_worker, daemon=True)
        _tent_thread.start()
        log.info("✅ ULN2003 Stepper iş parçacığı başlatıldı.")

    # Kapı lambası PWM
    GPIO.setup(DOOR_LIGHT_PWM_PIN, GPIO.OUT)
    _light_pwm = GPIO.PWM(DOOR_LIGHT_PWM_PIN, DOOR_LIGHT_FREQ)
    _light_pwm.start(0)

    log.info("✅ GPIO kurulumu tamamlandı.")


def cleanup_gpio():
    """Program kapanırken GPIO'yu temizle."""
    if not HARDWARE_AVAILABLE:
        return
    try:
        if _light_pwm: _light_pwm.stop()
        if _fan1_pwm:  _fan1_pwm.stop()
        if _fan2_pwm:  _fan2_pwm.stop()
        
        for pin in TENT_STEP_PINS:
            GPIO.output(pin, GPIO.LOW)
        GPIO.cleanup()
        log.info("GPIO temizlendi.")
    except Exception as e:
        log.warning(f"GPIO cleanup hatası: {e}")


# ── Durum Takibi (sadece değiştiğinde log bas) ────────────────────────────────
_last_states = {}

# ── Fan Kontrolü ──────────────────────────────────────────────────────────────
# Fanlar HW-532 (MOSFET) kullanılarak PWM ile kontrol edilir.

def apply_fan_state(fan_number: int, state: str):
    key = f"fan_{fan_number}"
    duty = FAN_SPEEDS.get(state, 0)
    pwm_obj = _fan1_pwm if fan_number == 1 else _fan2_pwm

    if _last_states.get(key) != state:
        speed_map = {"off": "KAPALI", "slow": "YAVAŞ", "medium": "ORTA", "fast": "HIZLI"}
        log.info(f"💨 Fan {fan_number}: {speed_map.get(state, state)} (%{duty} duty cycle - GPIO)")
        _last_states[key] = state

        if HARDWARE_AVAILABLE and pwm_obj is not None:
            pwm_obj.ChangeDutyCycle(duty)


# ── Isıtıcı Kontrolü ──────────────────────────────────────────────────────────
def apply_heater_state(state: str):
    on = (state == "on")

    if _last_states.get("heater") != state:
        log.info(f"🔥 Isıtıcı: {'AÇIK' if on else 'KAPALI'}")
        _last_states["heater"] = state

        if HARDWARE_AVAILABLE:
            GPIO.output(HEATER_PIN, GPIO.LOW if on else GPIO.HIGH)


# ── Tente Motor Kontrolü (ULN2003 Stepper) ────────────────────────────────────
def apply_tent_state(state: str):
    global _tent_state
    if _last_states.get("tent") != state:
        log.info(f"🏕️  Tente: {state.upper()} (Stepper mod)")
        _last_states["tent"] = state
        _tent_state = state


# ── Kapı Lambası PWM ──────────────────────────────────────────────────────────
def apply_door_light(intensity: int):
    """
    intensity: 0-100 arası parlaklık değeri
    """
    intensity = max(0, min(100, intensity))

    if _last_states.get("light") != intensity:
        log.info(f"💡 Kapı Lambası: %{intensity}")
        _last_states["light"] = intensity

        if HARDWARE_AVAILABLE:
            _light_pwm.ChangeDutyCycle(intensity)
