import RPi.GPIO as GPIO
import time

FAN_PIN = 18

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(FAN_PIN, GPIO.OUT)
    # Başlangıçta kapalı tutalım
    GPIO.output(FAN_PIN, GPIO.LOW)

def test_loop():
    print("💨 Fan test programı başlatıldı (GPIO 18).")
    print("Durdurmak için klavyeden CTRL+C tuşlarına basın.\n")
    
    while True:
        print("🟢 Fan AÇIK (12V Güç Veriliyor...)")
        GPIO.output(FAN_PIN, GPIO.HIGH)
        time.sleep(3)
        
        print("🔴 Fan KAPALI (Güç Kesildi)")
        GPIO.output(FAN_PIN, GPIO.LOW)
        time.sleep(10)

if __name__ == '__main__':
    setup()
    try:
        test_loop()
    except KeyboardInterrupt:
        print("\n🛑 Test durduruldu.")
    finally:
        GPIO.cleanup()
        print("🧹 GPIO pinleri temizlendi.")
