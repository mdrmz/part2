import threading
import requests
import cv2
import urllib.parse
import logging
import numpy as np

class APIManager:
    def __init__(self, api_url: str):
        self.api_url = api_url
    def _is_valid_url(self, url: str) -> bool:
        try: parts = urllib.parse.urlparse(url); return parts.scheme in ("http", "https") and bool(parts.netloc)
        except Exception: return False
    def send_plate_data(self, plate_text: str, camera_id: str, frame: np.ndarray):
        try:
            thread = threading.Thread(target=self._send_request, args=(plate_text, camera_id, frame), daemon=True)
            thread.start()
        except Exception as e:
            logging.error(f"API gönderme thread'i başlatılırken hata: {e}", exc_info=True)
    def _send_request(self, plate_text: str, camera_id: str, frame: np.ndarray):
        if not self.api_url or not self._is_valid_url(self.api_url):
            logging.error(f"API_URL geçersiz: '{self.api_url}'. Gönderim iptal."); return
        success, encoded_image = cv2.imencode('.jpg', frame)
        if not success:
            logging.error("Görüntü JPEG'e çevrilemedi."); return
        payload = {'plate': plate_text, 'gate': camera_id}
        files = {'image': ('capture.jpg', encoded_image.tobytes(), 'image/jpeg')}
        logging.info(f"API isteği hazırlanıyor: URL='{self.api_url}', Payload={payload}")
        try:
            session = requests.Session(); session.trust_env = False
            resp = session.post(self.api_url, files=files, data=payload, timeout=15)
            logging.info(f"API Cevabı: Durum Kodu={resp.status_code}, Cevap={resp.text[:200]}")
        except Exception as e:
            logging.error(f"API'ye bağlanırken hata: {e}", exc_info=True)