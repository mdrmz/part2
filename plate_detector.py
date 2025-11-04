import logging
from ultralytics import YOLO

class PlateDetector:
    def __init__(self, model_path: str):
        try:
            self.model = YOLO(model_path)
            logging.info(f"YOLOv8 Plaka Tespit modeli '{model_path}' başarıyla yüklendi.")
        except Exception as e:
            logging.error(f"HATA: YOLO modeli yüklenemedi. {e}", exc_info=True)
            raise e
    def detect(self, image):
        results = self.model.predict(image, verbose=False)
        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append((x1, y1, x2, y2))
        return detections