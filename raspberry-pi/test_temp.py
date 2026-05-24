import time
from sensors import read_temperatures

print("==================================================")
print(" TEK SENSÖR OKUMA TESTİ (MAIN.PY İLE BİREBİR AYNI)")
print("==================================================")
print("Sensörler okunuyor, lütfen bekleyin...\n")

try:
    # Ana programın (main.py) kullandığı fonksiyonu BİREBİR çağırıyoruz
    temp1, temp2 = read_temperatures()
    
    if temp1 is not None:
        print(f"✅ BAŞARILI! Sensör Okundu.")
        print(f"🌡️ Salon Sıcaklığı (Sensör 1) : {temp1} °C")
        
        if temp2 is not None:
            print(f"🌡️ Yatak Odası (Sensör 2)     : {temp2} °C")
    else:
        print("❌ HATA: Sensör okunamadı!")
        print("Sistem '/sys/bus/w1/devices/28-*' dizininde sensör bulamadı.")
        print("Sorun donanımsal (kablo, direnç eksikliği veya pin temassızlığı).")

except Exception as e:
    print(f"Beklenmeyen bir hata oluştu: {e}")

print("\n==================================================")
