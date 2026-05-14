#!/usr/bin/env python3
"""
Akıllı Ev — Raspberry Pi Ana Kontrol Programı
=============================================
Görevler:
  1. Web API'den komutları al (3 sn polling)
  2. Sensörlerden (DHT11, yağmur) okunan değerleri API'ye gönder
  3. Röleleri / PWM çıkışlarını güncelle (fan, ısıtıcı, tente motoru, kapı lambası)
  4. Kapı hareketi algılanınca fotoğraf çek ve API'ye yükle
  5. Capture isteği varsa da fotoğraf çek

Gereksinimler:
  pip install -r requirements.txt

Çalıştırma:
  python main.py
"""

import time
import threading
import logging
from config import API_URL, POLL_INTERVAL
from sensors import read_temperatures, read_rain_sensor, setup_sensor_gpio
from actuators import (
    setup_gpio,
    cleanup_gpio,
    apply_fan_state,
    apply_heater_state,
    apply_tent_state,
    apply_door_light,
)
from camera import capture_and_upload
import requests

# ── Loglama ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("pi-main")


def update_api(device_name: str, state_value) -> bool:
    """Tek bir cihaz değerini API'ye POST et."""
    try:
        r = requests.post(
            f"{API_URL}/update",
            json={"device_name": device_name, "state_value": str(state_value)},
            timeout=5,
        )
        return r.status_code == 200
    except requests.exceptions.RequestException as e:
        log.warning(f"API güncelleme hatası ({device_name}): {e}")
        return False


def poll_loop():
    """
    Ana döngü:
      - API'den durum al
      - Sensörleri oku ve API'ye gönder
      - Donanımı güncelle
    """
    setup_gpio()
    setup_sensor_gpio()
    update_api("pi_connected", "true")
    log.info(f"✅ Raspberry Pi başlatıldı. API: {API_URL}")

    last_state = {}

    while True:
        try:
            # ── 1. Web Arayüzündeki Komutları Al ──────────────────
            response = requests.get(f"{API_URL}/pi-poll", timeout=5)
            if response.status_code != 200:
                log.warning("API yanıt vermedi, tekrar deneniyor...")
                time.sleep(POLL_INTERVAL)
                continue

            data = response.json()
            state = data.get("data", {})

            # ── 2. Donanımı Güncelle ──────────────────────────────
            apply_fan_state(1, state.get("fan_1", "off"))
            apply_fan_state(2, state.get("fan_2", "off"))
            apply_heater_state(state.get("heater", "off"))
            apply_tent_state(state.get("tent", "closed"))
            apply_door_light(int(state.get("door_light", 0)))

            # ── 3. Fotoğraf çekme isteği varsa tetikle ───────────
            if state.get("capture_requested") == "true":
                log.info("📸 Fotoğraf çekme isteği alındı!")
                threading.Thread(
                    target=capture_and_upload,
                    kwargs={"api_url": API_URL},
                    daemon=True
                ).start()

            # ── 4. Sıcaklık Sensörlerini Oku ─────────────────────
            room1_temp, room2_temp = read_temperatures()

            if room1_temp is not None and str(room1_temp) != str(state.get("room_1_temp", "")):
                update_api("room_1_temp", room1_temp)
                log.info(f"🌡️  Salon sıcaklığı: {room1_temp}°C")

            if room2_temp is not None and str(room2_temp) != str(state.get("room_2_temp", "")):
                update_api("room_2_temp", room2_temp)
                log.info(f"🌡️  Yatak odası sıcaklığı: {room2_temp}°C")

            # ── 5. Yağmur Sensörünü Oku ───────────────────────────
            rain_status = read_rain_sensor()  # 'raining' veya 'dry'

            if rain_status != state.get("rain_status", "dry"):
                update_api("rain_status", rain_status)
                if rain_status == "raining":
                    log.info("🌧️  Yağmur algılandı! Web arayüzüne gönderildi.")
                else:
                    log.info("☀️  Yağmur durdu.")

            last_state = state

        except requests.exceptions.RequestException as e:
            log.error(f"❌ API bağlantı hatası: {e}")
            update_api("pi_connected", "false")

        except Exception as e:
            log.exception(f"Beklenmeyen hata: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        poll_loop()
    except KeyboardInterrupt:
        log.info("\n🛑 Program kapatılıyor...")
        update_api("pi_connected", "false")
        cleanup_gpio()
