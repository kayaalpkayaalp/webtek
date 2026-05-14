import time, json, requests, RPi.GPIO as GPIO

# ---------------------------------------------------------------------------
# Direct PWM control of Fan 1 (GPIO 18) via the Web API.
# ---------------------------------------------------------------------------
API_URL = "https://webtek-alpha.vercel.app/api"
POLL_INTERVAL = 2  # seconds between API polls

FAN_PIN = 18

# ---------------------------------------------------------------------------
# ACTIVE‑LOW handling
# Set to True if your fan driver (MOSFET, relay, etc.) is active‑low.
# When ACTIVE_LOW is True the PWM values are inverted so that "fast" => 0% (full power)
# and "off"   => 100% (motor stopped).
# ---------------------------------------------------------------------------
ACTIVE_LOW = False

if ACTIVE_LOW:
    FAN_SPEEDS = {
        "off":    100,   # 100% PWM → motor OFF
        "slow":   60,    # 60% PWM  → ~40% speed
        "medium": 30,    # 30% PWM  → ~70% speed
        "fast":   0,     # 0% PWM   → 100% speed (full power)
    }
else:
    FAN_SPEEDS = {
        "off":    0,
        "slow":   40,
        "medium": 70,
        "fast":   100,
    }

# ---------------------------------------------------------------------------
# GPIO setup – performed only once.
# ---------------------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(FAN_PIN, GPIO.OUT)

pwm = GPIO.PWM(FAN_PIN, 1000)   # 1 kHz PWM frequency
pwm.start(0)

print("--- Direkt Fan 1 PWM Kontrolü (Web API) ---")
print("CTRL+C ile durdurabilirsiniz.\n")

prev_state = None  # track last received fan command

try:
    while True:
        try:
            response = requests.get(f"{API_URL}/pi-poll", timeout=5)
            if response.status_code != 200:
                print(f"⛔ API yanıt vermedi (status {response.status_code}), tekrar deneniyor…")
                time.sleep(POLL_INTERVAL)
                continue

            # -------------------------------------------------------------------
            # Debug: show raw JSON for inspection (nice formatted output)
            # -------------------------------------------------------------------
            try:
                pretty = json.dumps(response.json(), indent=2, ensure_ascii=False)
                print("🔎 API JSON:", pretty)
            except Exception:
                print("🔎 API RAW TEXT:", response.text[:120], "…")

            data = response.json().get("data", {})
            state = data.get("fan_1", "off")
            duty = FAN_SPEEDS.get(state, 0)

            # Apply PWM only when the command actually changes – prevents stutter.
            if state != prev_state:
                pwm.ChangeDutyCycle(duty)
                print(f"⚙️  Web komutu: fan_1 = \"{state}\" → PWM %{duty}")
                prev_state = state
            else:
                # same command as before – do nothing (quiet)
                pass

        except Exception as e:
            print(f"❗ API hatası: {e}")

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("\n🛑 Program sonlandırıldı.")
    pwm.stop()
    GPIO.cleanup()
