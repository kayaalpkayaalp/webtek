import time
import requests
import RPi.GPIO as GPIO

# Direkt PWM kontrolü – sadece Fan 1 (GPIO 18) ile çalışır.
API_URL = "https://webtek-alpha.vercel.app/api"
POLL_INTERVAL = 2  # saniye

FAN_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(FAN_PIN, GPIO.OUT)

pwm = GPIO.PWM(FAN_PIN, 1000)  # 1kHz PWM
pwm.start(0)

# PWM değerleri (off=0, slow=40, medium=70, fast=100)
FAN_SPEEDS = {
    "off": 0,
    "slow": 40,
    "medium": 70,
    "fast": 100,
}

print("--- Direkt Fan 1 PWM Kontrolü (Web API) ---")
print("CTRL+C ile durdurabilirsiniz.\n")

try:
    while True:
        try:
            resp = requests.get(f"{API_URL}/pi-poll", timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                state = data.get("fan_1", "off")
                duty = FAN_SPEEDS.get(state, 0)
                pwm.ChangeDutyCycle(duty)
                print(f"Web komutu: {state} → PWM %{duty}")
            else:
                print("API yanıt vermedi, tekrar deneniyor...")
        except Exception as e:
            print(f"API hatası: {e}")
        time.sleep(POLL_INTERVAL)
except KeyboardInterrupt:
    print("\nProgram sonlandırıldı.")
    pwm.stop()
    GPIO.cleanup()
