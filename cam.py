import platform
import logging
import sys
import cv2
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class VideoThread(QThread):
    """Отдельный поток для захвата кадров с камеры.
    Использует OpenCV VideoCapture и отправляет кадры в главный поток через pyqtSignal.
    """

    change_pixmap_signal = pyqtSignal(QPixmap)
    detection_desc_signal = pyqtSignal(str)

    def __init__(self, cam_index=0, cap_width=640, cap_height=360, fps=30,
                 target_label=None, description_label=None):
        super().__init__()
        self.run_flag = True
        self.cam_index = cam_index
        self.cap_width = cap_width
        self.cap_height = cap_height
        self.label = target_label
        self.desc_label = description_label
        self.import_success = False
        self.processor = None

        self.fps = fps
        self.prev = 0

    def run(self):
        """Основной цикл потока: открывает камеру, читает кадры, эмитит сигнал."""
        is_mac = platform.system() == "Darwin"
        backend = cv2.CAP_AVFOUNDATION if is_mac else cv2.CAP_DSHOW
        cap = cv2.VideoCapture(self.cam_index, backend)

        # Попробуем установить пониженное разрешение (ускоряет обработку)
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cap_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cap_height)
        except Exception:
            pass

        # ВАЖНО: хоть у нас уже и загружена библиотека MediaPipe,
        # данный кусок кода нужен, чтобы программа не крашнулась при попытке
        # запустить камеру, когда библиотека еще не успела загрузиться.

        logging.info("loading mediapipe...")
        # Импорт HandsDetection (MediaPipe)
        try:
            from detection import HandsDetection
            self.import_success = True
            self.processor = HandsDetection()
            logging.info("mediapipe loaded")
        except Exception as e:
            logging.exception(f"Failed to load!\n{e}")

        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(self.cam_index)

        while self.run_flag:
            ret, cv_img = cap.read()
            # Ставим заданный FPS
            cv2.waitKey(1000 // self.fps)
            if not ret:
                # небольшая пауза чтобы не крутить цикл вхолостую
                self.msleep(10)
                continue

            if self.import_success:
                # BGR numpy array & кол-во ладоней
                processed, n_hands = self.processor.find_hands(cv_img)
            else:
                # в случае ошибки просто отправляем сырой кадр
                processed, n_hands = cv_img, -1

            if n_hands == 0:
                self.detection_desc_signal.emit("Не обнаружено ладоней")
            elif n_hands == 1:
                self.detection_desc_signal.emit("Обнаружена одна ладонь")
            elif n_hands == 2:
                self.detection_desc_signal.emit("Обнаружено две ладони")
            else:
                self.detection_desc_signal.emit("Undefined")

            # Конвертация в QPixmap
            pix = convert_cv_qt(processed).scaled(
                self.label.width(),
                self.label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.change_pixmap_signal.emit(pix)

            # Небольшой отдых, чтобы не 100% загружать CPU
            self.msleep(5)

        cap.release()

    def stop(self):
        """Останавливает поток и дожидается завершения."""
        self.run_flag = False
        self.wait()


def convert_cv_qt(cv_img):
    """Преобразует кадр OpenCV (BGR) в QPixmap для отображения в QLabel."""
    rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_image.shape
    qimg = QImage(rgb_image.data, w, h, ch * w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)


class CameraController:
    """
    Запускает VideoThread, получает кадры и обновляет целевой QLabel.
    Может принимать произвольный «обработчик кадров» (processor).
    """

    def __init__(self, target_label, description_label=None, cam_index=0):
        self.label = target_label
        self.desc_label = description_label
        self.cam_index = cam_index
        self.thread = None

    def start(self):
        """Запускает поток захвата, если он ещё не активен."""
        if self.thread and self.thread.isRunning():
            return
        self.thread = VideoThread(self.cam_index, target_label=self.label,
                                  description_label=self.desc_label)
        self.thread.change_pixmap_signal.connect(self.on_frame)
        self.thread.detection_desc_signal.connect(self.on_detection)
        self.thread.start()

    def stop(self):
        """Останавливает поток и очищает QLabel."""
        if self.thread:
            try:
                self.thread.change_pixmap_signal.disconnect(self.on_frame)
            except Exception:
                pass
            self.thread.stop()
            self.thread = None
        if hasattr(self.label, "setPixmap"):
            self.label.setPixmap(QPixmap())

    def on_frame(self, pix):
        """Обрабатывает кадр и выводит его на экран."""
        self.label.setPixmap(pix)

    def on_detection(self, string):
        """Выводит информацию об обработанном кадре"""
        self.desc_label.setText(string)
