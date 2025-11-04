# core_engine/gate_controller.py

import logging
import time
import platform # İşletim sistemini algılamak için

# Sadece Raspberry Pi üzerinde çalışıyorsak bu kütüphaneleri import etmeyi dene
IS_RASPBERRY_PI = platform.system() == "Linux" and "arm" in platform.machine()

if IS_RASPBERRY_PI:
    try:
        from gpiozero import Servo
        from gpiozero.pins.pigpio import PiGPIOFactory
        logging.info("Raspberry Pi sistemi algılandı, GPIO kütüphaneleri yüklendi.")
    except ImportError:
        logging.error("Pi sistemi algılandı ANCAK 'gpiozero' veya 'pigpio' kütüphaneleri bulunamadı.")
        IS_RASPBERRY_PI = False # Hata olursa, Pi'de değilmiş gibi davran
else:
    logging.warning(f"Raspberry Pi olmayan bir sistem ({platform.system()}) algılandı. Servo motor (GPIO) devre dışı bırakıldı.")

class GateController:
    def __init__(self, servo_pin=18):
        self.servo = None
        self.angle_release = -0.5  # Bırakma pozisyonu (-1.0 ile 1.0 arası)
        self.angle_press = 0.5   # Basma pozisyonu (-1.0 ile 1.0 arası)
        
        # Sadece Pi üzerindeysek servoyu başlatmayı dene
        if IS_RASPBERRY_PI:
            try:
                factory = PiGPIOFactory() 
                self.servo = Servo(servo_pin, pin_factory=factory)
                self.servo.value = self.angle_release 
                logging.info(f"Servo motor GPIO {servo_pin} pininde başlatıldı.")
            except Exception as e:
                logging.error(f"HATA: Servo motor başlatılamadı: {e}")

    def open_gate(self):
        # Sadece Pi üzerindeysek ve servo başarıyla başlatıldıysa tuşa bas
        if IS_RASPBERRY_PI and self.servo:
            try:
                logging.info("KAPI AÇILIYOR: Tuşa basılıyor...")
                self.servo.value = self.angle_press; time.sleep(0.5)
                self.servo.value = self.angle_release
                logging.info("Tuş bırakıldı.")
            except Exception as e:
                logging.error(f"Servo kontrolü sırasında hata: {e}")
        else:
            # Eğer Pi'de değilsek (Windows testimizdeysek), sadece log atla
            logging.info("[TEST MODU] Kapı açma komutu tetiklendi (servo bağlı değil).")
            return