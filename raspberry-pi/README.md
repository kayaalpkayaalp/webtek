# 🍓 Raspberry Pi — Akıllı Ev Kontrol Scripti

Bu klasördeki Python scriptleri Raspberry Pi'de çalışarak web arayüzüyle haberleşir.

---

## 📁 Dosya Yapısı

```
raspberry-pi/
├── main.py          ← Ana döngü (buradan çalıştır)
├── config.py        ← GPIO pin numaraları ve API URL
├── sensors.py       ← DHT11 sıcaklık + yağmur sensörü okuma
├── actuators.py     ← Fan, ısıtıcı, tente motoru, kapı lambası
├── camera.py        ← Fotoğraf çekme ve API'ye yükleme
├── requirements.txt ← Python kütüphane gereksinimleri
└── photos/          ← Geçici fotoğraf klasörü (otomatik oluşur)
```

---

## ⚡ Kurulum (Raspberry Pi'de Terminal)

### 1. Sistem Paketlerini Kur
```bash
sudo apt update
sudo apt install -y python3-pip python3-picamera2 libgpiod2
```

### 2. Python Kütüphanelerini Kur
```bash
cd ~/akilli-ev/raspberry-pi
pip install -r requirements.txt
```

### 3. API URL'ini Ayarla
`config.py` dosyasını aç ve `API_URL`'i güncelle:
```python
# Vercel'e deploy ettikten sonra:
API_URL = "https://akilli-ev-xxx.vercel.app/api"

# Yerel test için (PC ve Pi aynı ağdaysa PC'nin IP'si):
API_URL = "http://192.168.1.100:3000/api"
```

### 4. Gmail Uygulama Şifresi (E-posta Gönderimi İçin)
Web sunucusunda (`api/index.js`) `.env` dosyası oluştur:
```
GMAIL_USER=senin_mailin@gmail.com
GMAIL_PASS=xxxx_xxxx_xxxx_xxxx
```
Gmail → Hesap → Güvenlik → 2 Adımlı Doğrulama → **Uygulama Şifreleri**

---

## 🚀 Çalıştırma

```bash
python3 main.py
```

Sistem başlatıcıya eklemek için (Pi açılışında otomatik çalışsın):
```bash
sudo nano /etc/rc.local
# Satır ekle (exit 0'dan önce):
python3 /home/pi/akilli-ev/raspberry-pi/main.py &
```

---

## 🔌 Devre Bağlantı Özeti

| Cihaz              | GPIO Pin | Bağlantı Tipi     |
|--------------------|----------|-------------------|
| Salon Fanı         | GPIO 17  | Röle IN1          |
| Yatak Odası Fanı   | GPIO 27  | Röle IN2          |
| Şerit Isıtıcı      | GPIO 22  | Röle IN3          |
| Kapı Lambası       | GPIO 18  | MOSFET/PWM        |
| Tente Motor (ENA)  | GPIO 23  | L298N ENA (PWM)   |
| Tente Motor (IN1)  | GPIO 24  | L298N IN1         |
| Tente Motor (IN2)  | GPIO 25  | L298N IN2         |
| DHT11 Salon        | GPIO 4   | Data              |
| DHT11 Yatak Odası  | GPIO 5   | Data              |
| Yağmur Sensörü     | GPIO 6   | Digital Output    |
| PIR Hareket        | GPIO 16  | Digital Output    |

---

## 🌊 Sistem Akışı

```
Web Arayüzü
    ↕  (HTTP REST API — her 3 saniyede bir)
Node.js Sunucusu (Vercel / Localhost)
    ↕  (polling + fotoğraf upload)
Raspberry Pi (main.py)
    ├── sensors.py  → DHT11, yağmur sensörü okur → API'ye POST eder
    ├── actuators.py → Fan, ısıtıcı, tente, lamba → GPIO çıkış
    └── camera.py   → PIR tetikle / web isteği → fotoğraf çek → API'ye yükle
```

---

## 🤖 Otomasyonlar

| Tetikleyici           | Otomatik Eylem                          |
|-----------------------|-----------------------------------------|
| Yağmur algılandı      | Tente yavaş/orta hıza alınır            |
| Web'den "Fotoğraf Çek"| Pi fotoğraf çeker, API'ye yükler        |
| PIR hareket algılar   | Pi otomatik fotoğraf çeker (10sn cooldown) |
| Yağmur durdu          | Web'de bildirim gösterilir              |
