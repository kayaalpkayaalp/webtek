import os
import glob
import time

def read_temp_raw(device_file):
    try:
        with open(device_file, 'r') as f:
            lines = f.readlines()
        return lines
    except Exception as e:
        print(f"Okuma hatası: {e}")
        return []

def read_temp(device_file):
    lines = read_temp_raw(device_file)
    if not lines:
        return None
        
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw(device_file)
        
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c
    return None

if __name__ == "__main__":
    print("--------------------------------------------------")
    print(" DS18B20 SICAKLIK SENSÖRÜ TEST ARACI")
    print("--------------------------------------------------")
    print("\n1. İşletim sistemi klasörleri kontrol ediliyor (/sys/bus/w1/devices/)...")
    
    base_dir = '/sys/bus/w1/devices/'
    try:
        all_devices = os.listdir(base_dir)
        print(f"Bulunan TÜM cihaz/klasör isimleri: {all_devices}")
    except FileNotFoundError:
        print("HATA: 1-Wire sistemi aktif değil! (raspi-config'den açın)")
        exit()

    print("\n2. Geçerli sıcaklık sensörleri (28- ile başlayanlar) aranıyor...")
    valid_sensors = glob.glob(base_dir + '28*')
    
    if len(valid_sensors) == 0:
        print("HATA: Geçerli (28- ile başlayan) hiçbir sıcaklık sensörü BULUNAMADI!")
        print("\nOlası Sebepler:")
        print("- 4.7k ohm Direnç eksik (Sarı ile Kırmızı kablo arasına takın).")
        print("- Sarı DATA kablosu Pi'nin 4 numaralı (Fiziksel Pin 7) pini DIŞINDA bir yere takılı.")
        print("- Sensör arızalı veya ters bağlandığı için yandı.")
        print("- Listede '00-' ile başlayan cihazlar varsa, bağlantınız kısa devre yapıyor veya havada (floating) demektir.")
    else:
        print(f"BAŞARILI: {len(valid_sensors)} adet geçerli sensör bulundu!")
        for sensor_path in valid_sensors:
            device_file = sensor_path + '/w1_slave'
            sensor_name = os.path.basename(sensor_path)
            temp = read_temp(device_file)
            print(f"-> Sensör ({sensor_name}): {temp} °C")
    
    print("\nTest bitti.")
    print("--------------------------------------------------")
