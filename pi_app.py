import time
import requests
# import RPi.GPIO as GPIO  # Raspberry Pi üzerinde donanımları kontrol etmek için kullanılır.

# NOT: Vercel'e deploy edildi.
API_URL = "https://webtek-alpha.vercel.app/api"

# GPIO PIN TANIMLAMALARI (Örnek)
FAN_1_PIN = 17
FAN_2_PIN = 27
HEATER_1_PIN = 22
HEATER_2_PIN = 23
LIGHT_PWM_PIN = 18
BULB_PWM_PIN = 25  # Ampul parlaklık kontrolü (PWM)

# BH1750 I2C Adresi
BH1750_ADDR = 0x23

def setup_gpio():
    print("GPIO PIN ayarları yapılıyor...")
    # GPIO.setmode(GPIO.BCM)
    # GPIO.setup(FAN_1_PIN, GPIO.OUT)
    # GPIO.setup(FAN_2_PIN, GPIO.OUT)
    # GPIO.setup(HEATER_1_PIN, GPIO.OUT)
    # GPIO.setup(HEATER_2_PIN, GPIO.OUT)
    # GPIO.setup(LIGHT_PWM_PIN, GPIO.OUT)
    
    # Global yap ki diğer fonksiyonlardan pwn ayarlayabilelim
    # global light_pwm
    # light_pwm = GPIO.PWM(LIGHT_PWM_PIN, 100) # 100Hz frekans
    # light_pwm.start(0)

def read_temperature_sensor():
    # Burada DHT11 veya LM35 sıcaklık sensöründen okuma yapılır.
    # Şimdilik örnek / rastgele değer dönüyoruz:
    return 24, 23  # room_1_temp, room_2_temp

def read_bh1750_light():
    """BH1750 ışık sensöründen ortam ışık seviyesini oku (lux cinsinden)."""
    # import smbus2
    # bus = smbus2.SMBus(1)
    # data = bus.read_i2c_block_data(BH1750_ADDR, 0x10, 2)  # Continuous H-Res Mode
    # lux = (data[0] << 8 | data[1]) / 1.2
    # return round(lux, 1)
    
    # Şimdilik örnek değer dönüyoruz:
    return 350  # lux

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
    
    # 2. ISITICI KONTROLÜ (Salon)
    if state.get("heater_1") == "on":
        print("Salon Isıtıcı: AÇIK")
        # GPIO.output(HEATER_1_PIN, GPIO.HIGH)
    else:
        print("Salon Isıtıcı: KAPALI")
        # GPIO.output(HEATER_1_PIN, GPIO.LOW)

    # 3. ISITICI KONTROLÜ (Yatak Odası)
    if state.get("heater_2") == "on":
        print("Yatak Odası Isıtıcı: AÇIK")
        # GPIO.output(HEATER_2_PIN, GPIO.HIGH)
    else:
        print("Yatak Odası Isıtıcı: KAPALI")
        # GPIO.output(HEATER_2_PIN, GPIO.LOW)
        
    # 3. KAPI AYDINLATMASI (PWM - 0 ile 100 arası)
    light_intensity = int(state.get("door_light", 0))
    print(f"Kapı Işığı Şiddeti: %{light_intensity}")
    # light_pwm.ChangeDutyCycle(light_intensity)

    # 4. AMPUL PARLAKLIK KONTROLÜ (PWM - 0 ile 100 arası)
    bulb_val = int(state.get("bulb_brightness", 0))
    print(f"Ampul Parlaklığı: %{bulb_val}")
    # bulb_pwm.ChangeDutyCycle(bulb_val)

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
            ambient_lux = read_bh1750_light()
            
            # Not: Eğer değer webdeki (current_state'teki) değerden farklıysa güncelle ki 
            # sürekli aynı datayı post etmesin, gereksiz API yorulmasın.
            if int(current_state.get('room_1_temp', 0)) != room_1:
                requests.post(f"{API_URL}/update", json={"device_name": "room_1_temp", "state_value": room_1})
                
            if int(current_state.get('room_2_temp', 0)) != room_2:
                requests.post(f"{API_URL}/update", json={"device_name": "room_2_temp", "state_value": room_2})
            
            # BH1750 ortam ışık sensörü verisini gönder
            if float(current_state.get('ambient_light', 0)) != ambient_lux:
                requests.post(f"{API_URL}/update", json={"device_name": "ambient_light", "state_value": ambient_lux})
                
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
