import RPi.GPIO as GPIO
import time

PIN = 18

print("GPIO 18 pini uzerinden dogrudan PWM gonderiliyor...")
print("Lutfen fanin donup donmedigini kontrol et. Cikmak icin CTRL+C'ye bas.")

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN, GPIO.OUT)

# 1000 Hz frekansinda PWM baslatiliyor
pwm = GPIO.PWM(PIN, 1000)
pwm.start(0)

try:
    while True:
        # Fanin hizini yavas yavas %0'dan %100'e cikar (ChatGPT'nin verdigi ornek kod)
        for i in range(0, 101, 10):
            print(f"Guc: %{i}")
            pwm.ChangeDutyCycle(i)
            time.sleep(1)
            
        # Istersen asagidaki satirlari acarak %100'den %0'a yavas yavas dusmesini de saglayabilirsin
        # for i in range(100, -1, -10):
        #     print(f"Guc: %{i}")
        #     pwm.ChangeDutyCycle(i)
        #     time.sleep(1)

except KeyboardInterrupt:
    print("\nTest sonlandiriliyor...")
    pwm.stop()
    GPIO.cleanup()
