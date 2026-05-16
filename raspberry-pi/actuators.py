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

try:
    import board
    import busio
    import adafruit_pca9685
    PCA_AVAILABLE = True
except ImportError:
    PCA_AVAILABLE = False
    log.warning("⚠️  PCA9685 kütüphanesi bulunamadı. Lütfen kurun: pip install adafruit-circuitpython-pca9685")

from config import (
    PCA_FAN_1_CHANNEL, PCA_FAN_2_CHANNEL, FAN_SPEEDS,
    HEATER_PIN,
    DOOR_LIGHT_PWM_PIN, DOOR_LIGHT_FREQ,
    TENT_ENA_PIN, TENT_IN1_PIN, TENT_IN2_PIN,
    TENT_SPEEDS,
)

# ── PWM Nesneleri ─────────────────────────────────────────────────────────────
_light_pwm = None
_tent_pwm  = None
pca        = None  # PCA9685 nesnesi


def setup_gpio():
    """GPIO pinlerini başlat."""
    global _light_pwm, _tent_pwm, pca, PCA_AVAILABLE

    if not HARDWARE_AVAILABLE:
        log.info("[SIM] GPIO ayarları yapıldı (simülasyon)")
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Isıtıcı rölesi (başlangıçta HIGH = kapalı)
    GPIO.setup(HEATER_PIN, GPIO.OUT, initial=GPIO.HIGH)

    # PCA9685 I2C Sürücü (Fanlar için)
    if PCA_AVAILABLE:
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            pca = adafruit_pca9685.PCA9685(i2c)
            pca.frequency = 50  # 50 Hz frekans (Fanlar için daha düşük gürültü/EMI)
            log.info("✅ PCA9685 I2C Sürücüsü başlatıldı (Fanlar).")
            
            # Başlangıçta fanları kapat
            if PCA_FAN_1_CHANNEL is not None: pca.channels[PCA_FAN_1_CHANNEL].duty_cycle = 0
            if PCA_FAN_2_CHANNEL is not None: pca.channels[PCA_FAN_2_CHANNEL].duty_cycle = 0
        except Exception as e:
            log.error(f"❌ PCA9685 başlatılamadı: {e}")
            PCA_AVAILABLE = False

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
        if pca:
            if PCA_FAN_1_CHANNEL is not None: pca.channels[PCA_FAN_1_CHANNEL].duty_cycle = 0
            if PCA_FAN_2_CHANNEL is not None: pca.channels[PCA_FAN_2_CHANNEL].duty_cycle = 0
            pca.deinit()
        GPIO.cleanup()
        log.info("GPIO temizlendi.")
    except Exception as e:
        log.warning(f"GPIO cleanup hatası: {e}")


# ── Durum Takibi (sadece değiştiğinde log bas) ────────────────────────────────
_last_states = {}

# ── Fan Kontrolü ──────────────────────────────────────────────────────────────
# Fanlar PCA9685 I2C modülü üzerinden kontrol edilir.
# PCA9685 16-bit çözünürlüğe sahiptir (0 - 65535 arası değer alır).

def apply_fan_state(fan_number: int, state: str):
    key = f"fan_{fan_number}"
    duty_percent = FAN_SPEEDS.get(state, 0)
    
    # Yüzdelik değeri PCA9685 için 16-bit (0-65535) değere dönüştür:
    duty_16bit = int(65535 * (duty_percent / 100.0))

    if _last_states.get(key) != state:
        speed_map = {"off": "KAPALI", "slow": "YAVAŞ", "medium": "ORTA", "fast": "HIZLI"}
        log.info(f"💨 Fan {fan_number}: {speed_map.get(state, state)} (%{duty_percent} duty cycle - PCA9685)")
        _last_states[key] = state

        if PCA_AVAILABLE and pca is not None:
            try:
                if fan_number == 1 and PCA_FAN_1_CHANNEL is not None:
                    pca.channels[PCA_FAN_1_CHANNEL].duty_cycle = duty_16bit
                elif fan_number == 2 and PCA_FAN_2_CHANNEL is not None:
                    pca.channels[PCA_FAN_2_CHANNEL].duty_cycle = duty_16bit
            except OSError as e:
                log.error(f"❌ PCA9685 İletişim Hatası (Fan {fan_number} güncellenemedi): {e}")
                # Hata durumunda _last_states'i geri alalım ki bir sonraki döngüde tekrar denesin
                _last_states.pop(key, None)


# ── Isıtıcı Kontrolü ──────────────────────────────────────────────────────────
def apply_heater_state(state: str):
    on = (state == "on")

    if _last_states.get("heater") != state:
        log.info(f"🔥 Isıtıcı: {'AÇIK' if on else 'KAPALI'}")
        _last_states["heater"] = state

        if HARDWARE_AVAILABLE:
            GPIO.output(HEATER_PIN, GPIO.LOW if on else GPIO.HIGH)


# ── Tente Motor Kontrolü ──────────────────────────────────────────────────────
def apply_tent_state(state: str):
    duty = TENT_SPEEDS.get(state, 0)

    if _last_states.get("tent") != state:
        log.info(f"🏕️  Tente: {state.upper()} (%{duty} duty cycle)")
        _last_states["tent"] = state

        if HARDWARE_AVAILABLE:
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

        if HARDWARE_AVAILABLE:
            _light_pwm.ChangeDutyCycle(intensity)
