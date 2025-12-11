import cv2
import mediapipe as mp


class TorsoDetection:
    """
    Класс распознавания торса (грудной клетки и живота)
    """

    def __init__(self, frame_skip=0):
        # Грузим нейронку
        self.mpPose = mp.solutions.pose
        self.pose = self.mpPose.Pose(False)
        self.npDraw = mp.solutions.drawing_utils
        self.frame_skip = frame_skip
        self.last_results = None

        self.frame_idx = 0
        # Точки, по которым рисуется область грудной клетки
        self.found_points = {}
        self.found_torso = False

    def process(self, cv_img):
        img = cv2.flip(cv_img, 1)  # Зеркалим изображение
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Пропускаем каждые "frame_skip" кадров.
        if self.frame_idx % (self.frame_skip + 1) == 0:
            self.frame_idx = 0 if self.frame_idx != 0 else self.frame_idx
            # Обычно в алгоритм подается черно-белое изображение, но MediaPipe
            # распознает только RBG
            results = self.pose.process(imgRGB)
            self.last_results = results

            if results.pose_landmarks:
                h, w, _ = img.shape
                landmarks = results.pose_landmarks.landmark

                # Получаем координаты плеч и бёдер
                left_shoulder = landmarks[
                    self.mpPose.PoseLandmark.LEFT_SHOULDER
                ]
                right_shoulder = landmarks[
                    self.mpPose.PoseLandmark.RIGHT_SHOULDER
                ]
                left_hip = landmarks[
                    self.mpPose.PoseLandmark.LEFT_HIP
                ]
                right_hip = landmarks[
                    self.mpPose.PoseLandmark.RIGHT_HIP
                ]

                # Преобразуем в пиксели
                def to_pixel(landmark):
                    return int(landmark.x * w), int(landmark.y * h)

                ls = to_pixel(left_shoulder)
                rs = to_pixel(right_shoulder)
                lh = to_pixel(left_hip)
                rh = to_pixel(right_hip)

                # Центр между плечами (верх грудной клетки)
                top_center = ((ls[0] + rs[0]) // 2, (ls[1] + rs[1]) // 2)
                # Центр между бёдрами (низ туловища)
                bottom_center = ((lh[0] + rh[0]) // 2, (lh[1] + rh[1]) // 2)

                # Примерная область для грудной клетки
                # (от чуть выше плеч до диафрагмы)
                top_y_chest = int(
                    top_center[1] - 0.1 * (bottom_center[1] - top_center[1])
                )
                bottom_y_chest = int(
                    top_center[1] + 0.4 * (bottom_center[1] - top_center[1])
                )
                left_x_chest = min(ls[0], rs[0])
                right_x_chest = max(ls[0], rs[0])

                # Примерная область для живота
                # (от чуть ниже диафрагмы до чуть выше бедер)
                top_y_abdomen = int(
                    top_center[1] + 1.0 * (bottom_center[1] - top_center[1])
                )
                bottom_y_abdomen = int(
                    top_center[1] + 0.6 * (bottom_center[1] - top_center[1])
                )

                left_x_abdomen = min(ls[0], rs[0])
                right_x_abdomen = max(ls[0], rs[0])

                # Отрисовка прямоугольников
                cv2.rectangle(img,
                              (left_x_chest, top_y_chest),
                              (right_x_chest, bottom_y_chest),
                              (0, 255, 0), 2)
                cv2.rectangle(img,
                              (left_x_abdomen, top_y_abdomen),
                              (right_x_abdomen, bottom_y_abdomen),
                              (0, 0, 255), 2)

                self.found_torso = True

                for key, value in {
                    "top_y_chest": top_y_chest,
                    "bottom_y_chest": bottom_y_chest,
                    "left_x_chest": left_x_chest,
                    "right_x_chest": right_x_chest,
                    "top_y_abdomen": top_y_abdomen,
                    "bottom_y_abdomen": bottom_y_abdomen,
                    "left_x_abdomen": left_x_abdomen,
                    "right_x_abdomen": right_x_abdomen,
                }.items():
                    self.found_points[key] = value

            else:
                self.found_torso = False

        # Если кадр пропущен - рисуем прошлые распознанные позиции
        else:
            if self.last_results.pose_landmarks:
                # Отрисовка прямоугольника
                cv2.rectangle(img,
                              (
                                  self.found_points['left_x_chest'],
                                  self.found_points['top_y_chest']
                              ),
                              (
                                  self.found_points['right_x_chest'],
                                  self.found_points['bottom_y_chest']
                              ),
                              (0, 255, 0), 2)
                cv2.rectangle(img,
                              (
                                  self.found_points['left_x_abdomen'],
                                  self.found_points['top_y_abdomen']
                              ),
                              (
                                  self.found_points['right_x_abdomen'],
                                  self.found_points['bottom_y_abdomen']
                              ),
                              (0, 0, 255), 2)

        self.frame_idx += 1

        return img, self.found_torso


class HandsDetection:
    """
    Класс распознавания рук (ранний пример работы алгоритма)
    """

    def __init__(self, frame_skip=0):
        # Грузим нейронку, распознающую руки
        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(False)
        self.npDraw = mp.solutions.drawing_utils
        self.frame_skip = frame_skip
        self.last_results = None

        self.frame_idx = 0
        self.found_lms = 0

    def process(self, cv_img):
        img = cv2.flip(cv_img, 1)  # Зеркалим изображение

        # Пропускаем каждые "frame_skip" кадров.
        if self.frame_idx % (self.frame_skip + 1) == 0:
            self.frame_idx = 0 if self.frame_idx != 0 else self.frame_idx
            # Обычно в алгоритм подается черно-белое изображение, но MediaPipe
            # распознает только RBG
            imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = self.hands.process(imgRGB)
            self.last_results = results
            if results.multi_hand_landmarks:
                # Находим позиции (landmarks) на ладонях
                for handLms in results.multi_hand_landmarks:
                    # Считаем количество позиций на ладонях
                    self.found_lms += len(handLms.landmark)
                    for i, lm in enumerate(handLms.landmark):
                        h, w, c = img.shape
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        if i == 8 or i == 12:
                            # Выделяем кончик указательного и среднего пальцев
                            cv2.circle(img, (cx, cy), 10, (255, 0, 255),
                                       cv2.FILLED)

                    self.npDraw.draw_landmarks(img, handLms,
                                               self.mpHands.HAND_CONNECTIONS)
            else:
                self.found_lms = 0
        # Если кадр пропущен - рисуем прошлые распознанные позиции
        else:
            if self.last_results.multi_hand_landmarks:
                for handLms in self.last_results.multi_hand_landmarks:
                    for i, lm in enumerate(handLms.landmark):
                        h, w, c = img.shape
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        if i == 8 or i == 12:
                            cv2.circle(img, (cx, cy), 10, (255, 0, 255),
                                       cv2.FILLED)

                    self.npDraw.draw_landmarks(img, handLms,
                                               self.mpHands.HAND_CONNECTIONS)

        if self.found_lms == 0:
            result = 0  # не обнаружено ладоней
        elif self.found_lms == 21:
            result = 1  # обнаружена одна ладонь
        elif self.found_lms == 42:
            result = 2  # обнаружено две ладони
        else:
            result = -1  # fail-safe случай

        self.frame_idx += 1
        self.found_lms = 0

        return img, result
