import time, json, requests, RPi.GPIO as GPIO

# ---------------------------------------------------------------------------
# Direct PWM control of Fan 1 (GPIO 18) via the Web API.
# ---------------------------------------------------------------------------
API_URL = "https://webtek-alpha.vercel.app/api"
POLL_INTERVAL = 2  # seconds between API polls

FAN_PIN = 18

# ---------------------------------------------------------------------------
# ACTIVE‑LOW handling (set to False because we want 3.3 V for "fast")
# ---------------------------------------------------------------------------
ACTIVE_LOW = False

# Only two states are needed for the requested behavior:
#   "fast" -> full 3.3 V (PWM 100%)
#   "off"  -> 0 V (PWM 0%)
if ACTIVE_LOW:
    FAN_SPEEDS = {
        "off":    100,  # 100% PWM → motor OFF (active‑low)
        "fast":   0,    # 0% PWM   → full power
    }
else:
    FAN_SPEEDS = {
        "off":    0,    # 0% PWM → motor OFF
        "fast":   100,  # 100% PWM → full 3.3 V
    }

# ---------------------------------------------------------------------------
# GPIO setup – performed only once.
# ---------------------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(FAN_PIN, GPIO.OUT)

pwm = GPIO.PWM(FAN_PIN, 1000)   # 1 kHz PWM frequency
pwm.start(0)

print("--- Direct Fan 1 PWM Control (Web API) ---")
print("Press CTRL+C to stop.\n")

prev_state = None  # Track the last fan command

try:
    while True:
        try:
            response = requests.get(f"{API_URL}/pi-poll", timeout=5)
            if response.status_code != 200:
                print(f"⛔ API responded with status {response.status_code}, retrying…")
                time.sleep(POLL_INTERVAL)
                continue

            # Parse JSON – we only need the "fan_1" key.
            data = response.json().get("data", {})
            state = data.get("fan_1", "off")  # default to "off" if missing

            # Determine duty cycle based on the mapping.
            duty = FAN_SPEEDS.get(state, 0)

            # Apply PWM only when the command actually changes.
            if state != prev_state:
                pwm.ChangeDutyCycle(duty)
                print(f"⚙️  Web command: fan_1 = '{state}' → PWM %{duty}")
                prev_state = state
            # else: same state – do nothing (keep current voltage)

        except Exception as e:
            print(f"❗ API error: {e}")

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("\n🛑 Program stopped by user.")
    pwm.stop()
    GPIO.cleanup()
