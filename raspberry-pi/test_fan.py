import RPi.GPIO as GPIO
import time

PIN = 18

print("--- AOD4184 MODUL TESTI ---")
print("Webden bagimsiz olarak fan hizi her 3 saniyede bir degisecek.")
print("Cikmak icin CTRL+C'ye bas.\n")

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN, GPIO.OUT)

# 1000 Hz frekansinda PWM baslatiliyor
pwm = GPIO.PWM(PIN, 1000)
pwm.start(0)

# Test edilecek PWM oranlari (Orijinal ayarlar)
# Eger fan ters calisiyorsa (Active-Low), asagidaki degerlerin 
# ters etki (100'de durma, 0'da calisma) gosterdigini fark edeceksin.
test_levels = [0, 40, 70, 100]

try:
    while True:
        for level in test_levels:
            print(f"-> PWM Seviyesi ayarlaniyor: %{level}")
            pwm.ChangeDutyCycle(level)
            time.sleep(3)  # Her seviyede 3 saniye bekle

except KeyboardInterrupt:
    print("\nTest sonlandiriliyor...")
    pwm.stop()
    GPIO.cleanup()
