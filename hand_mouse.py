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

MARGIN = 0.18     # 카메라 가장자리 무시 비율
SMOOTH = 0.35     # 커서 부드러움(작을수록 부드러움)
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


def main():
    hands = mp.solutions.hands.Hands(max_num_hands=1, model_complexity=0,
                                     min_detection_confidence=0.7, min_tracking_confidence=0.6)
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        pyautogui.alert("웹캠을 열 수 없습니다. 카메라 권한을 확인해 주세요.", "Hand Mouse")
        return
    sx, sy = pyautogui.position()
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
                    nx = clamp((lm[5].x - MARGIN) / (1 - 2 * MARGIN), 0, 1)
                    ny = clamp((lm[5].y - MARGIN) / (1 - 2 * MARGIN), 0, 1)
                    sx += (nx * (SW - 1) - sx) * SMOOTH
                    sy += (ny * (SH - 1) - sy) * SMOOTH
                    pyautogui.moveTo(clamp(sx, 2, SW - 3), clamp(sy, 2, SH - 3))
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
