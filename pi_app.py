import time
import requests
# import RPi.GPIO as GPIO  # Raspberry Pi üzerinde donanımları kontrol etmek için kullanılır.

# NOT: Vercel'e deploy edildi.
API_URL = "https://webtek-alpha.vercel.app/api"

# GPIO PIN TANIMLAMALARI (Örnek)
FAN_1_PIN = 17
FAN_2_PIN = 27
HEATER_PIN = 22
LIGHT_PWM_PIN = 18

def setup_gpio():
    print("GPIO PIN ayarları yapılıyor...")
    # GPIO.setmode(GPIO.BCM)
    # GPIO.setup(FAN_1_PIN, GPIO.OUT)
    # GPIO.setup(FAN_2_PIN, GPIO.OUT)
    # GPIO.setup(HEATER_PIN, GPIO.OUT)
    # GPIO.setup(LIGHT_PWM_PIN, GPIO.OUT)
    
    # Global yap ki diğer fonksiyonlardan pwn ayarlayabilelim
    # global light_pwm
    # light_pwm = GPIO.PWM(LIGHT_PWM_PIN, 100) # 100Hz frekans
    # light_pwm.start(0)

def read_temperature_sensor():
    # Burada DHT11 veya LM35 sıcaklık sensöründen okuma yapılır.
    # Şimdilik örnek / rastgele değer dönüyoruz:
    return 24, 23  # room_1_temp, room_2_temp

def update_pi_hardware(state):
    print("--- Gelen API Verilerine Göre Donanım Güncelleniyor ---")
    
    # 1. FAN KONTROLÜ
    if state.get("fan_1") == "off":
        print("Fan 1: KAPALI")
        # GPIO.output(FAN_1_PIN, GPIO.LOW)
    elif state.get("fan_1") == "fast":
        print("Fan 1: HIZLI ÇALIŞIYOR")
        # GPIO.output(FAN_1_PIN, GPIO.HIGH)
        # PWM kullanarak hız ayarı da yapılabilir.
    
    # 2. ISITICI KONTROLÜ
    if state.get("heater") == "on":
        print("Isıtıcı: AÇIK")
        # GPIO.output(HEATER_PIN, GPIO.HIGH)
    else:
        print("Isıtıcı: KAPALI")
        # GPIO.output(HEATER_PIN, GPIO.LOW)
        
    # 3. KAPI AYDINLATMASI (PWM - 0 ile 100 arası)
    light_intensity = int(state.get("door_light", 0))
    print(f"Kapı Işığı Şiddeti: %{light_intensity}")
    # light_pwm.ChangeDutyCycle(light_intensity)

def main_loop():
    setup_gpio()
    
    print(f"Raspberry Pi Sistemi Başlatıldı. {API_URL} dinleniyor...")
    while True:
        try:
            # 1. API'DEN WEB ARAYÜZÜNDEKİ KOMUTLARI AL (GET)
            response = requests.get(f"{API_URL}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                current_state = data.get("data", {})
                
                # Alınan komutlara göre röleleri/motorları çalıştır
                update_pi_hardware(current_state)

            # 2. RASPBERRY PI'DAKI SENSÖR BİLGİLERİNİ WEB'E GÖNDER (POST)
            # Örneğin sıcaklık sensörünü okup arayüze güncel halini yollayalım:
            room_1, room_2 = read_temperature_sensor()
            
            # Not: Eğer değer webdeki (current_state'teki) değerden farklıysa güncelle ki 
            # sürekli aynı datayı post etmesin, gereksiz API yorulmasın.
            if int(current_state.get('room_1_temp', 0)) != room_1:
                requests.post(f"{API_URL}/update", json={"device_name": "room_1_temp", "state_value": room_1})
                
            if int(current_state.get('room_2_temp', 0)) != room_2:
                requests.post(f"{API_URL}/update", json={"device_name": "room_2_temp", "state_value": room_2})
                
        except requests.exceptions.RequestException as e:
            print(f"Uyarı: API ile bağlantı kurulamadı. Hata: {e}")
            
        print("--------------------------------------------------")
        time.sleep(3)  # Her 3 saniyede bir döngüyü tekrarla

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nProgram kapatılıyor...")
        # GPIO.cleanup()
