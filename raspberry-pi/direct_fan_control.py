import time, json, requests, RPi.GPIO as GPIO

# ---------------------------------------------------------------------------
# Direct on/off control of Fan 1 (GPIO 18) via the Web API.
# ---------------------------------------------------------------------------
API_URL = "https://webtek-alpha.vercel.app/api"
POLL_INTERVAL = 2  # seconds between API polls

FAN_PIN = 18

# ---------------------------------------------------------------------------
# ACTIVE‑LOW handling (False = normal logic, True = inverted)
# ---------------------------------------------------------------------------
ACTIVE_LOW = False

# ---------------------------------------------------------------------------
# GPIO setup – performed only once.
# ---------------------------------------------------------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(FAN_PIN, GPIO.OUT)

# Ensure fan is off at start
if ACTIVE_LOW:
    GPIO.output(FAN_PIN, GPIO.LOW)   # LOW = OFF for active‑low
else:
    GPIO.output(FAN_PIN, GPIO.LOW)   # LOW = OFF for normal logic

print("--- Direct Fan 1 ON/OFF Control (Web API) ---")
print("Press CTRL+C to stop.\n")

prev_state = None

try:
    while True:
        try:
            response = requests.get(f"{API_URL}/pi-poll", timeout=5)
            if response.status_code != 200:
                print(f"⛔ API responded with status {response.status_code}, retrying…")
                time.sleep(POLL_INTERVAL)
                continue

            data = response.json().get("data", {})
            state = data.get("fan_1", "off")  # default to off

            # Only act when state changes.
            if state != prev_state:
                if ACTIVE_LOW:
                    # In active‑low, "fast" → LOW (turn on), "off" → HIGH (turn off)
                    gpio_state = GPIO.LOW if state == "fast" else GPIO.HIGH
                else:
                    # Normal logic: "fast" → HIGH, "off" → LOW
                    gpio_state = GPIO.HIGH if state == "fast" else GPIO.LOW

                GPIO.output(FAN_PIN, gpio_state)
                print(f"⚙️  Web command: fan_1 = '{state}' → GPIO {'HIGH' if gpio_state == GPIO.HIGH else 'LOW'}")
                prev_state = state
            # else: same state – keep current output

        except Exception as e:
            print(f"❗ API error: {e}")

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("\n🛑 Program stopped by user.")
    # Turn fan off before cleanup
    if ACTIVE_LOW:
        GPIO.output(FAN_PIN, GPIO.HIGH)
    else:
        GPIO.output(FAN_PIN, GPIO.LOW)
    GPIO.cleanup()
