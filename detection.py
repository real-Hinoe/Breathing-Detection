import cv2
import numpy as np
import mediapipe as mp
import time
import os


class HandsDetection:
    def __init__(self):
        self.cv_img = None

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(False)
        self.npDraw = mp.solutions.drawing_utils

        self.pTime = 0
        self.cTime = 0

    def set_img(self, cv_img):
        self.cv_img = cv_img

    def find_hands(self):
        img = cv2.flip(self.cv_img, 1)  # Mirror flip

        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.hands.process(imgRGB)
        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                for id, lm in enumerate(handLms.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    if id == 8 or id == 12:
                        cv2.circle(img, (cx, cy), 10, (255, 0, 255),
                                   cv2.FILLED)

                self.npDraw.draw_landmarks(img, handLms,
                                           self.mpHands.HAND_CONNECTIONS)

        self.cTime = time.time()
        fps = 1 / (self.cTime - self.pTime)
        self.pTime = self.cTime
        cv2.putText(img, str(int(fps)), (10, 30), cv2.FONT_HERSHEY_PLAIN, 2,
                    (255, 0, 0), 2)  # ФреймРейт

        return img
