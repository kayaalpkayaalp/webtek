"""
camera.py — Raspberry Pi Kamera Modülü
========================================
- picamera2 ile fotoğraf çek (Raspberry Pi OS Bullseye+)
- Çekilen fotoğrafı base64 olarak /api/capture endpointine yükle
- PIR hareket sensörü ile otomatik çekim desteği

Gereksinim:
  sudo apt install -y python3-picamera2
  pip install requests
"""

import os
import time
import base64
import logging
import requests
from datetime import datetime

log = logging.getLogger("camera")

# ── Kamera İmport ─────────────────────────────────────────────────────────────
try:
    from picamera2 import Picamera2
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False
    log.warning("⚠️  picamera2 bulunamadı — kamera simülasyon modunda.")

# Fotoğrafların geçici olarak kaydedileceği yer
PHOTO_DIR = os.path.join(os.path.dirname(__file__), "photos")
os.makedirs(PHOTO_DIR, exist_ok=True)


def _take_photo() -> str | None:
    """
    Fotoğraf çek ve dosya yolunu döndür.
    Kamera yoksa None döner.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(PHOTO_DIR, f"capture_{ts}.jpg")

    if not CAMERA_AVAILABLE:
        log.info(f"[SIM] 📸 Fotoğraf çekildi (simülasyon): {filename}")
        # Simülasyon için boş dosya oluştur
        with open(filename, "wb") as f:
            f.write(b"")  # Gerçek uygulamada test görseli kullanılabilir
        return filename

    try:
        cam = Picamera2()
        config = cam.create_still_configuration(
            main={"size": (1280, 720)},
            lores={"size": (640, 480)},
        )
        cam.configure(config)
        cam.start()
        time.sleep(1.5)  # Kameranın ısınması için bekle
        cam.capture_file(filename)
        cam.close()
        log.info(f"📸 Fotoğraf çekildi: {filename}")
        return filename
    except Exception as e:
        log.error(f"Fotoğraf çekme hatası: {e}")
        return None


def capture_and_upload(api_url: str) -> bool:
    """
    Fotoğraf çek ve API'ye base64 olarak yükle.
    Vercel'de dosya sistemi olmadığı için base64 JSON olarak gönderilir.
    Döndürür: True (başarılı) / False
    """
    photo_path = _take_photo()
    if not photo_path or not os.path.exists(photo_path):
        log.error("Fotoğraf çekilemedi veya dosya bulunamadı.")
        return False

    try:
        # Fotoğrafı base64'e çevir
        with open(photo_path, "rb") as f:
            photo_b64 = base64.b64encode(f.read()).decode("utf-8")

        # API'ye JSON olarak gönder
        response = requests.post(
            f"{api_url}/capture",
            json={"photo_base64": photo_b64},
            timeout=30,
        )

        if response.status_code == 200:
            log.info(f"✅ Fotoğraf API'ye yüklendi (base64): {response.json()}")
            # Yüklendikten sonra lokal dosyayı sil (yer tasarrufu)
            os.remove(photo_path)
            return True
        else:
            log.warning(f"API yükleme başarısız: {response.status_code} {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        log.error(f"Fotoğraf yükleme bağlantı hatası: {e}")
        return False
    except Exception as e:
        log.exception(f"Beklenmeyen fotoğraf yükleme hatası: {e}")
        return False


def start_motion_triggered_capture(api_url: str):
    """
    PIR sensörü izle; hareket algılanınca otomatik fotoğraf çek.
    Bu fonksiyon ayrı bir thread'de çalıştırılmalıdır.
    """
    from sensors import read_pir
    from config import POLL_INTERVAL

    log.info("🎯 PIR tabanlı otomatik kamera izlemesi başlatıldı.")
    last_triggered = 0

    while True:
        try:
            if read_pir():
                now = time.time()
                # Aynı anda tekrar tetiklemeyi önle (10 sn cooldown)
                if now - last_triggered > 10:
                    log.info("🚶 Kapıda hareket algılandı! Otomatik fotoğraf çekiliyor...")
                    capture_and_upload(api_url)
                    last_triggered = now
        except Exception as e:
            log.warning(f"PIR izleme hatası: {e}")

        time.sleep(0.5)
