import platform
import logging
import cv2
import numpy as np
from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap

logger = logging.getLogger(__name__)
LOWER_GREEN = np.array([35, 50, 50])
UPPER_GREEN = np.array([85, 255, 255])
MIN_CONTOUR_AREA = 100


def find_available_cameras():
    """Находит и возвращает список доступных камер"""
    cameras = []

    # Пробуем открыть камеры с индексами от 0 до 2
    for i in range(2):
        cap = None
        try:
            is_mac = platform.system() == "Darwin"
            backend = cv2.CAP_AVFOUNDATION if is_mac else cv2.CAP_DSHOW
            cap = cv2.VideoCapture(i, backend)

            if not cap.isOpened():
                break
            else:
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
            break
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

    def __init__(self, cam_index=0, cap_width=1280, cap_height=720, fps=30,
                 target_label=None, description_label=None):
        super().__init__()
        self.run_flag = True
        self.cam_index = cam_index
        self.base_cap_width = cap_width
        self.base_cap_height = cap_height
        self.label = target_label
        self.desc_label = description_label

        self.fps = fps
        self.prev = 0

    def run(self):
        """Основной цикл потока: открывает камеру, читает кадры, эмитит сигнал."""
        is_mac = platform.system() == "Darwin"
        backend = cv2.CAP_AVFOUNDATION if is_mac else cv2.CAP_DSHOW
        cap1 = cv2.VideoCapture(self.cam_index, backend)
        cap2 = cv2.VideoCapture(self.cam_index + 1, backend)

        # Получаем реальное разрешение камер
        cap1_w = cap1.get(cv2.CAP_PROP_FRAME_WIDTH)
        cap1_h = cap1.get(cv2.CAP_PROP_FRAME_HEIGHT)
        cap2_w = cap2.get(cv2.CAP_PROP_FRAME_WIDTH)
        cap2_h = cap2.get(cv2.CAP_PROP_FRAME_HEIGHT)

        # Масштабируем площадь минимальной площади
        min_area_scaled = ((max(cap1_w, cap2_w) // 2) * (max(cap1_h, cap2_h) // 2)
                           // MIN_CONTOUR_AREA)

        if not cap1.isOpened():
            cap1.release()
            cap1 = cv2.VideoCapture(self.cam_index, backend)
        if not cap2.isOpened():
            cap2.release()
            cap2 = cv2.VideoCapture(self.cam_index + 1, backend)

        def sort_contours_bottom_to_left(contours, y_threshold=30):
            """
            Сортировка контуров: снизу вверх, затем слева направо.
            """
            if not contours:
                return []

            bounding_boxes = [cv2.boundingRect(c) for c in contours]
            indexed_boxes = list(enumerate(bounding_boxes))

            # Сортируем по Y (снизу вверх - обратный порядок)
            indexed_boxes.sort(key=lambda k: k[1][1], reverse=True)

            sorted_contours = []
            used_indices = set()

            for i, box in indexed_boxes:
                if i in used_indices:
                    continue

                # Находим все объекты в той же "строке"
                row_boxes = [(i, box)]
                used_indices.add(i)

                for j, other_box in indexed_boxes:
                    if j in used_indices:
                        continue
                    if abs(other_box[1] - box[1]) <= y_threshold:
                        row_boxes.append((j, other_box))
                        used_indices.add(j)

                # Сортируем строку слева направо
                row_boxes.sort(key=lambda k: k[1][0])

                # Добавляем контуры в итоговый список
                for idx, _ in row_boxes:
                    sorted_contours.append(contours[idx])

            return sorted_contours

        def process_frame(frame, camera_id,
                          lower_green=LOWER_GREEN,
                          upper_green=UPPER_GREEN,
                          min_area=min_area_scaled):
            """
            Обработка кадра: выделение зеленых контуров и нумерация.
            """
            if frame is None or frame.size == 0:
                return None, None, 0

            # Преобразование в HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Маска для зеленого цвета
            process_mask = cv2.inRange(hsv, lower_green, upper_green)

            # Морфологические операции для очистки
            kernel = np.ones((5, 5), np.uint8)
            process_mask = cv2.morphologyEx(process_mask, cv2.MORPH_OPEN, kernel)
            process_mask = cv2.morphologyEx(process_mask, cv2.MORPH_CLOSE, kernel)

            # Поиск контуров
            contours, _ = cv2.findContours(process_mask, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)

            # Фильтрация по площади
            contours = [c for c in contours if cv2.contourArea(c) > min_area]

            # Сортировка контуров
            sorted_contours = sort_contours_bottom_to_left(contours)

            # Отрисовка
            process_output = frame.copy()
            for i, contour in enumerate(sorted_contours, start=1):
                x, y, w, h = cv2.boundingRect(contour)

                # # Рисуем контур
                # cv2.drawContours(process_output, [contour], -1, (0, 255, 0), 2)

                # Рисуем прямоугольник
                cv2.rectangle(process_output, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Добавляем номер с указанием камеры
                label = f"Cam{camera_id}:#{i}"
                cv2.putText(process_output, label, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            return process_output, process_mask, len(sorted_contours)

        while self.run_flag:
            ret1, cv_img1 = cap1.read()
            ret2, cv_img2 = cap2.read()
            # Ставим заданный FPS
            cv2.waitKey(1000 // self.fps)
            if not ret1:
                # Камера не работает
                self.detection_desc_signal.emit("Ожидание запуска камеры...")
                # небольшая пауза чтобы не крутить цикл вхолостую
                self.msleep(10)
                continue
            if not ret2:
                # Камера не работает
                self.detection_desc_signal.emit("Ожидание запуска камеры...")
                # небольшая пауза чтобы не крутить цикл вхолостую
                self.msleep(10)
                continue

            # Обработка кадров
            output1, mask1, count1 = process_frame(cv_img1, 0)
            output2, mask2, count2 = process_frame(cv_img2, 0)

            # Объединенное окно
            combined = np.hstack([cv2.resize(output1, (self.base_cap_width, self.base_cap_height)),
                                  cv2.resize(output2, (self.base_cap_width, self.base_cap_height))])

            # Конвертация в QPixmap
            pix = convert_cv_qt(combined).scaled(
                self.label.width(),
                self.label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.detection_desc_signal.emit("")
            self.change_pixmap_signal.emit(pix)

            # Небольшой отдых, чтобы не 100% загружать CPU
            self.msleep(5)

        cap1.release()
        cap2.release()

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
