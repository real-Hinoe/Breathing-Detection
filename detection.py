import cv2
import mediapipe as mp


class HandsDetection:
    """
    Класс распознавания рук
    """
    def __init__(self, frame_skip=0):
        # Грузим нейронку, распознающую руки
        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(False)
        self.npDraw = mp.solutions.drawing_utils
        self.frame_skip = frame_skip
        self.last_results = None

        self.frame_idx = 0

    def find_hands(self, cv_img):
        img = cv2.flip(cv_img, 1)  # Зеркалим изображение

        # Пропускаем каждые "frame_skip" кадров.
        if self.frame_idx % (self.frame_skip + 1) == 0:
            # Обычно в алгоритм подается черно-белое изображение, но MediaPipe
            # распознает только RBG
            imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = self.hands.process(imgRGB)
            self.last_results = results
            if results.multi_hand_landmarks:
                # Находим позиции (landmarks) на ладони
                for handLms in results.multi_hand_landmarks:
                    for i, lm in enumerate(handLms.landmark):
                        h, w, c = img.shape
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        if i == 8 or i == 12:
                            # Выделяем кончик указательного и среднего пальца
                            cv2.circle(img, (cx, cy), 10, (255, 0, 255),
                                       cv2.FILLED)

                    self.npDraw.draw_landmarks(img, handLms,
                                               self.mpHands.HAND_CONNECTIONS)
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

        self.frame_idx += 1

        return img
