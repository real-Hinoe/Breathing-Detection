import platform
import logging
import cv2
import numpy as np
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

logger = logging.getLogger(__name__)


def find_available_cameras():
    """Находит и возвращает список доступных камер"""
    cameras = []

    # Пробуем открыть камеры с индексами от 0 до 10
    for i in range(10):
        cap = None
        try:
            is_mac = platform.system() == "Darwin"
            backend = cv2.CAP_AVFOUNDATION if is_mac else cv2.CAP_DSHOW
            cap = cv2.VideoCapture(i, backend)

            if cap.isOpened():
                # Пробуем прочитать кадр для проверки
                ret, frame = cap.read()
                if ret:
                    # Получаем информацию о камере
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)

                    camera_info = {
                        'index': i,
                        'width': width,
                        'height': height,
                        'fps': fps if fps > 0 else 30
                    }
                    cameras.append(camera_info)
                    logger.info(f"Найдена камера {i}: {width}x{height}@{fps}fps")
        except Exception as e:
            logger.warning(f"Ошибка при проверке камеры {i}: {e}")
        finally:
            if cap is not None:
                cap.release()

    return cameras


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

            # Конвертация в HSV
            hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)

            h_min = 35
            h_max = 95
            s_min = 55
            s_max = 255
            v_min = 100
            v_max = 255

            lower = np.array([h_min, s_min, v_min])
            upper = np.array([h_max, s_max, v_max])

            mask = cv2.inRange(hsv, lower, upper)
            result = cv2.bitwise_and(cv_img, cv_img, mask=mask)

            # Конвертация в QPixmap
            pix = convert_cv_qt(result).scaled(
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
        logger.info(f"Video capture started with camera index {self.cam_index}")

    def stop(self):
        """Останавливает поток и очищает QLabel."""
        if self.thread:
            try:
                self.thread.change_pixmap_signal.disconnect(self.on_frame)
            except Exception:
                pass
            self.thread.stop()
            self.thread = None
            logger.info("Video capture stopped")
        if hasattr(self.label, "setPixmap"):
            self.label.setPixmap(QPixmap())

    def on_frame(self, pix):
        """Обрабатывает кадр и выводит его на экран."""
        self.label.setPixmap(pix)

    def on_detection(self, string):
        """Выводит информацию об обработанном кадре"""
        self.desc_label.setText(string)