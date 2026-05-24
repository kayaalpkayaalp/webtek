import time
import requests
import smbus2  # I2C haberleşmesi için (BH1750 sensörü)
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

# BH1750 I2C Ayarları (SDA = GPIO2 / Pin3, SCL = GPIO3 / Pin5)
BH1750_ADDR = 0x23          # ADDR pini GND'ye bağlıysa 0x23, VCC'ye bağlıysa 0x5C
BH1750_CONTINUOUS_H_RES = 0x10  # Sürekli yüksek çözünürlük modu (1 lux hassasiyet)

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
    """BH1750 ışık sensöründen ortam ışık seviyesini oku (lux cinsinden).
    
    Bağlantı:
      - VCC → 3.3V (Pin 1)
      - GND → GND  (Pin 6)
      - SDA → GPIO2 (Pin 3)
      - SCL → GPIO3 (Pin 5)
      - ADDR → GND  (adres 0x23 için)
    """
    try:
        bus = smbus2.SMBus(1)  # Raspberry Pi I2C bus 1
        # Sürekli yüksek çözünürlük modunda ölçüm başlat
        bus.write_byte(BH1750_ADDR, BH1750_CONTINUOUS_H_RES)
        time.sleep(0.18)  # Ölçüm için 180ms bekle (max çözünürlük)
        # 2 byte veri oku
        data = bus.read_i2c_block_data(BH1750_ADDR, BH1750_CONTINUOUS_H_RES, 2)
        bus.close()
        # Lux hesapla: (yüksek byte << 8 + düşük byte) / 1.2
        lux = round((data[0] << 8 | data[1]) / 1.2, 1)
        print(f"BH1750 Işık Seviyesi: {lux} lux")
        return lux
    except Exception as e:
        print(f"⚠️ BH1750 sensör okunamadı: {e}")
        return None

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
            if ambient_lux is not None and float(current_state.get('ambient_light', 0)) != ambient_lux:
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
