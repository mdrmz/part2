#!/usr/bin/env python3
import cv2
import numpy as np
import logging

# EasyOCR ve pytesseract fallback
try:
    import easyocr
    HAS_EASYOCR = True
except Exception:
    HAS_EASYOCR = False

try:
    import pytesseract
    HAS_TESSERACT = True
except Exception:
    HAS_TESSERACT = False

class PlateRecognizer:
    def __init__(self, char_model_path: str = None, use_gpu: bool = False):
        self.logger = logging.getLogger("PlateRecognizer")
        self.char_model_path = char_model_path
        self.use_gpu = use_gpu and HAS_EASYOCR
        if HAS_EASYOCR:
            try:
                self.reader = easyocr.Reader(['en'], gpu=self.use_gpu)
            except Exception as e:
                self.logger.warning(f"EasyOCR başlatılamadı: {e}")
                self.reader = None
        else:
            self.reader = None
            self.logger.info("EasyOCR yok; sadece Tesseract fallback kullanılacak (varsa).")

    def _preprocess_for_ocr(self, img):
        # Gri, kontrast arttırma, adaptive threshold
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # histogram eşitleme (kontrast)
        gray = cv2.equalizeHist(gray)
        # küçük blur ile gürültü azalt
        gray = cv2.GaussianBlur(gray, (3,3), 0)
        # adaptive threshold, daha iyi metin ayrımı için
        th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
        return th

    def _cleanup_text(self, text: str):
        if not text: return ""
        # Büyük harfe çevir, Türkçe plaka kurallarına göre temizleme
        text = text.upper()
        # sadece alfanümerik ve - gibi karakterleri tut
        import re
        cleaned = re.sub(r'[^A-Z0-9ÇĞİÖŞÜ\-]', '', text)
        # Bazı OCR hatalarını düzelt (O -> 0 gibi)
        cleaned = cleaned.replace('O', '0')  # dikkat: 'O' harfi ile '0' rakam karışımı olabilir
        # İlk karakterlerin plakaya uygunluğunu kontrol etmek istersen buradan ekleme yap
        return cleaned

    def recognize(self, plate_img):
        """
        plate_img: BGR crop
        Dönüş: bulunan plaka string veya None
        Strateji:
         1) EasyOCR (varsa) ile dene
         2) Başarısızsa Tesseract fallback
         3) Kısmi sonuçlarda basit temizleme uygula
        """
        if plate_img is None or plate_img.size == 0:
            return None

        # Ön işleme
        prep = self._preprocess_for_ocr(plate_img)

        # 1) EasyOCR
        text = None
        if self.reader:
            try:
                # easyocr expects RGB
                rgb = cv2.cvtColor(plate_img, cv2.COLOR_BGR2RGB)
                results = self.reader.readtext(rgb, detail=0)
                if results:
                    # results listesinde birden çok parça olabilir; birleştir
                    candidate = "".join(results)
                    text = self._cleanup_text(candidate)
                    if text:
                        self.logger.debug(f"EasyOCR sonucu: {text}")
                        return text
            except Exception as e:
                self.logger.debug(f"EasyOCR hata: {e}")

        # 2) Tesseract fallback (daha agresif ön işlemle)
        if HAS_TESSERACT:
            try:
                # Tesseract için görüntüyü biraz büyüt
                scale = 2
                large = cv2.resize(prep, (prep.shape[1]*scale, prep.shape[0]*scale), interpolation=cv2.INTER_LINEAR)
                config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZÇĞİÖŞÜ0123456789-"
                ocr_result = pytesseract.image_to_string(large, config=config)
                cleaned = self._cleanup_text(ocr_result)
                if cleaned:
                    self.logger.debug(f"Tesseract sonucu: {cleaned}")
                    return cleaned
            except Exception as e:
                self.logger.debug(f"Tesseract hata: {e}")

        # 3) Eğer henüz bir sonuç yoksa, farklı açılardan/filtrelerden yeniden dene (örnek)
        # (Opsiyonel: morphology, edge detect vb. eklersin)
        return None