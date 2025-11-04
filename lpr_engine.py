#!/usr/bin/env python3
import cv2
import logging
import platform
from .plate_detector import PlateDetector
from .plate_recognizer import PlateRecognizer
from .gate_controller import GateController

IS_RASPBERRY_PI = platform.system() == "Linux" and "arm" in platform.machine()

class LPREngine:
    def __init__(self, detector_model_path: str, recognizer_model_path: str,
                 db_config: dict = None, servo_pin: int = None):
        self.logger = logging.getLogger("LPREngine")
        # PlateDetector: model_path değişkenine göre yükleme yapmalı (kendi implementasyonuna göre)
        self.detector = PlateDetector(model_path=detector_model_path)
        # PlateRecognizer: EasyOCR + fallback içeren daha toleranslı recognizer
        self.recognizer = PlateRecognizer(char_model_path=recognizer_model_path, use_gpu=False)
        if IS_RASPBERRY_PI and servo_pin is not None:
            self.gate_controller = GateController(servo_pin=servo_pin)
        else:
            self.gate_controller = None
        self.db_config = db_config

    def _check_whitelist(self, plate: str) -> bool:
        # Test ortamında db_config yoksa atla
        if not self.db_config:
            self.logger.debug("DB config yok, whitelist atlanıyor.")
            return False
        try:
            import mysql.connector
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            query = "SELECT ozel_erisim FROM araclar WHERE plaka = %s"
            cursor.execute(query, (plate,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result and result[0] == 1:
                self.logger.info(f"Plaka {plate} whitelist'te.")
                return True
        except Exception as e:
            self.logger.warning(f"Whitelist kontrol hatası: {e}")
        return False

    def process_image(self, image):
        """
        image: BGR OpenCV görüntüsü
        Adımlar:
         1) Algılama - detector.detect() -> liste (x1,y1,x2,y2) normalized veya pixel
         2) Her plaka bölgesi için crop, ön işlem, recognizer.recognize(crop)
         3) Bulunan plaka ve bbox listesini döndür
        """
        if image is None:
            return []

        h_orig, w_orig = image.shape[:2]
        # Tespit için genelde model input'u sabit; detector implementasyonuna göre getir
        try:
            # detector.detect() beklenen format: list of boxes in pixel koordinatı veya normalized [0-1]
            plate_boxes = self.detector.detect(image)
        except Exception as e:
            self.logger.exception(f"Detector çalışırken hata: {e}")
            return []

        results = []
        for box in plate_boxes:
            # Normalize edilmiş olabilir -> detector sınıfında tutarlı hale getir
            x1, y1, x2, y2 = box
            # clamp
            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(w_orig, int(x2))
            y2 = min(h_orig, int(y2))
            if x2 <= x1 or y2 <= y1:
                continue
            plate_crop = image[y1:y2, x1:x2]
            if plate_crop.size == 0:
                continue

            try:
                plate_text = self.recognizer.recognize(plate_crop)
            except Exception as e:
                self.logger.exception(f"Recognizer hata verdi: {e}")
                plate_text = None

            if plate_text:
                results.append((plate_text, (x1, y1, x2, y2)))
                # whitelist kontrol & gate açma
                try:
                    if self._check_whitelist(plate_text) and self.gate_controller:
                        self.gate_controller.open_gate()
                except Exception as e:
                    self.logger.warning(f"Gate kontrolünde hata: {e}")
        return results