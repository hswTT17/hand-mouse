"""Hand Mouse: 웹캠 손동작으로 마우스 조작
손바닥 이동=커서 / 엄지+검지 집기=클릭·드래그(두 번=더블클릭) / 엄지+중지=우클릭
검지+중지만 펴고 위아래=스크롤 / 주먹=일시정지 / q·ESC=종료 / 마우스를 왼쪽 위 모서리로=비상정지
"""
import math
import sys
import time

import cv2
import mediapipe as mp
import pyautogui

MARGIN = 0.15     # 카메라 가장자리 무시 비율
STEADY = 0.6      # 떨림 억제(작을수록 안정적, 대신 반응이 느려짐)
SPEED = 0.004     # 빠르게 움직일 때 따라오는 정도(클수록 빠른 동작에 덜 늦음)
DEADZONE = 4      # 이 픽셀보다 작은 움직임은 무시
PINCH_ON, PINCH_OFF = 0.33, 0.45
SCROLL_GAIN = 4000 if sys.platform.startswith("win") else 100
CAM_INDEX = 0

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0
SW, SH = pyautogui.size()


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class OneEuro:
    """천천히 움직일 땐 떨림을 강하게 거르고, 빠르게 움직일 땐 바로 따라오는 필터"""

    def __init__(self, min_cutoff, beta, d_cutoff=1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.x = self.dx = self.t = None

    @staticmethod
    def _alpha(cutoff, dt):
        r = 2 * math.pi * cutoff * dt
        return r / (r + 1)

    def __call__(self, x, t):
        if self.t is None or t - self.t > 0.5:
            self.x, self.dx, self.t = x, 0.0, t
            return x
        dt = max(t - self.t, 1e-3)
        a_d = self._alpha(self.d_cutoff, dt)
        self.dx += a_d * ((x - self.x) / dt - self.dx)
        a = self._alpha(self.min_cutoff + self.beta * abs(self.dx), dt)
        self.x += a * (x - self.x)
        self.t = t
        return self.x


def main():
    hands = mp.solutions.hands.Hands(max_num_hands=1, model_complexity=1,
                                     min_detection_confidence=0.7, min_tracking_confidence=0.6)
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        pyautogui.alert("웹캠을 열 수 없습니다. 카메라 권한을 확인해 주세요.", "Hand Mouse")
        return
    fx, fy = OneEuro(STEADY, SPEED), OneEuro(STEADY, SPEED)
    cx, cy = pyautogui.position()
    dragging, last_right, scroll_prev = False, 0.0, None
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            res = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            status = "NO HAND"
            if res.multi_hand_landmarks:
                hand = res.multi_hand_landmarks[0]
                lm = hand.landmark
                scale = dist(lm[0], lm[9]) or 1e-6
                up = [lm[t].y < lm[t - 2].y for t in (8, 12, 16, 20)]
                pinch = dist(lm[4], lm[8]) / scale
                rpinch = dist(lm[4], lm[12]) / scale
                status = "MOVE"
                if not dragging and not any(up):
                    status = "PAUSE"
                elif not dragging and up == [True, True, False, False] and pinch > PINCH_OFF:
                    status = "SCROLL"
                    y = (lm[8].y + lm[12].y) / 2
                    amt = 0 if scroll_prev is None else int((scroll_prev - y) * SCROLL_GAIN)
                    if amt:
                        pyautogui.scroll(amt)
                    scroll_prev = y
                if status != "SCROLL":
                    scroll_prev = None
                if status == "MOVE":
                    px = sum(lm[i].x for i in (0, 5, 9, 17)) / 4  # 손바닥 중심: 손가락 움직임에 덜 흔들림
                    py = sum(lm[i].y for i in (0, 5, 9, 17)) / 4
                    now = time.time()
                    tx = fx(clamp((px - MARGIN) / (1 - 2 * MARGIN), 0, 1) * (SW - 1), now)
                    ty = fy(clamp((py - MARGIN) / (1 - 2 * MARGIN), 0, 1) * (SH - 1), now)
                    if math.hypot(tx - cx, ty - cy) > DEADZONE:
                        cx, cy = tx, ty
                        pyautogui.moveTo(clamp(cx, 2, SW - 3), clamp(cy, 2, SH - 3))
                    if not dragging and pinch < PINCH_ON:
                        pyautogui.mouseDown()
                        dragging = True
                    elif dragging and pinch > PINCH_OFF:
                        pyautogui.mouseUp()
                        dragging = False
                    if not dragging and rpinch < PINCH_ON and time.time() - last_right > 0.6:
                        pyautogui.click(button="right")
                        last_right = time.time()
                    if dragging:
                        status = "DRAG"
                mp.solutions.drawing_utils.draw_landmarks(frame, hand, mp.solutions.hands.HAND_CONNECTIONS)
            else:
                if dragging:
                    pyautogui.mouseUp()
                    dragging = False
                scroll_prev = None
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("Hand Mouse (q: quit)", frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
    except pyautogui.FailSafeException:
        pass
    finally:
        if dragging:
            pyautogui.mouseUp()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
