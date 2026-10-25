"""Hand Mouse: 웹캠 손동작으로 마우스 조작
손바닥 이동=커서 / 엄지+검지 집기=클릭·드래그(두 번=더블클릭) / 엄지+중지=우클릭
검지+중지만 펴고 위아래=스크롤 / 주먹=일시정지 / q·ESC=종료 / 마우스를 왼쪽 위 모서리로=비상정지
"""
import math
import sys
import threading
import time

import cv2
import mediapipe as mp
import pyautogui

MARGIN = 0.27     # 카메라 가운데 영역만 사용(클수록 감도↑: 손을 조금만 움직여도 화면 끝까지)
NEAR_SIZE = 0.20  # 이 크기(가까운 손)일 때 기본 감도
MAX_BOOST = 2.2   # 손이 멀어질 때 감도를 최대 몇 배까지 올릴지
STEADY = 0.3      # 떨림 억제(작을수록 안정적, 대신 반응이 느려짐)
SPEED = 0.003     # 빠르게 움직일 때 따라오는 정도(클수록 빠른 동작에 덜 늦음)
DEADZONE = 6      # 이 픽셀보다 작은 움직임은 무시
GLIDE = 0.18      # 커서가 목표로 미끄러지듯 따라가는 정도(작을수록 더 부드럽고 느긋함)
GLIDE_HZ = 120    # 커서 갱신 횟수(초당)
PINCH_ON, PINCH_OFF = 0.33, 0.45
SCROLL_NOTCH = 120 if sys.platform.startswith("win") else 1  # 휠 한 칸
SCROLL_STEP = 0.035  # 손가락을 이만큼(화면 높이 대비) 움직일 때마다 한 칸 스크롤
SCROLL_WAIT = 0.3    # 두 손가락을 편 직후 이 시간(초) 동안은 스크롤하지 않음
POSE_FRAMES = 3      # 손 모양이 이 프레임 수만큼 이어져야 모드 변경(오인식 방지)
CLICK_COOLDOWN = 0.5 # 스크롤을 끝낸 뒤 이 시간(초) 동안은 클릭하지 않음
CAM_INDEX = 0

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0
SW, SH = pyautogui.size()


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def active_gain(size):
    """손이 멀어질수록(작게 보일수록) 감도를 점점 올리고, 가까워지면 기본 감도로 복구"""
    boost = clamp(NEAR_SIZE / max(size, 1e-6), 1.0, MAX_BOOST)
    return boost / (1 - 2 * MARGIN)


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


class Glide(threading.Thread):
    """카메라(초당 30번)보다 훨씬 자주(초당 120번) 커서를 조금씩 움직여 끊김 없이 부드럽게 이동"""

    def __init__(self):
        super().__init__(daemon=True)
        self.x, self.y = pyautogui.position()
        self.tx, self.ty = self.x, self.y
        self.stop = threading.Event()
        self.failsafe = False

    def target(self, x, y):
        self.tx, self.ty = clamp(x, 2, SW - 3), clamp(y, 2, SH - 3)

    def run(self):
        last = None
        while not self.stop.wait(1 / GLIDE_HZ):
            self.x += (self.tx - self.x) * GLIDE
            self.y += (self.ty - self.y) * GLIDE
            pos = (round(self.x), round(self.y))
            if pos != last:
                try:
                    pyautogui.moveTo(*pos)
                except pyautogui.FailSafeException:
                    self.failsafe = True
                    return
                last = pos


def main():
    hands = mp.solutions.hands.Hands(max_num_hands=1, model_complexity=1,
                                     min_detection_confidence=0.7, min_tracking_confidence=0.6)
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        pyautogui.alert("웹캠을 열 수 없습니다. 카메라 권한을 확인해 주세요.", "Hand Mouse")
        return
    fx, fy = OneEuro(STEADY, SPEED, 0.5), OneEuro(STEADY, SPEED, 0.5)
    glide = Glide()
    glide.start()
    cx, cy = glide.x, glide.y
    dragging, last_right, scroll_prev = False, 0.0, None
    scroll_start, size = 0.0, NEAR_SIZE
    mode, pending, pending_n, scroll_end = "MOVE", None, 0, 0.0
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
                # 손가락이 펴졌는지: 손가락 끝이 둘째 마디보다 손목에서 더 멀면 편 것 (손 방향과 무관)
                up = [dist(lm[t], lm[0]) > dist(lm[t - 2], lm[0]) * 1.05 for t in (8, 12, 16, 20)]
                pinch = dist(lm[4], lm[8]) / scale
                rpinch = dist(lm[4], lm[12]) / scale
                size += (scale - size) * 0.05  # 손 크기(=거리)를 천천히 반영해 감도가 점점 바뀌게
                now = time.time()

                # 1) 이번 프레임의 손 모양 판단 (스크롤 모양은 엄지 위치와 상관없이 스크롤로 고정)
                if dragging:
                    pose = "MOVE"
                elif up[0] and up[1] and not up[2] and not up[3]:
                    pose = "SCROLL"
                elif not any(up):
                    pose = "PAUSE"
                else:
                    pose = "MOVE"
                # 2) 같은 모양이 몇 프레임 이어질 때만 모드를 바꿔 순간적인 오인식 방지
                if pose == mode:
                    pending, pending_n = None, 0
                elif pose == pending:
                    pending_n += 1
                    if pending_n >= POSE_FRAMES:
                        if mode == "SCROLL":
                            scroll_end = now
                        mode, pending, pending_n = pose, None, 0
                else:
                    pending, pending_n = pose, 1
                status = mode

                if mode == "SCROLL":  # 스크롤 중에는 클릭·우클릭을 절대 하지 않음
                    y = (lm[8].y + lm[12].y) / 2
                    if scroll_prev is None:  # 막 두 손가락을 폈을 때: 기준점만 잡고 대기
                        scroll_start, scroll_prev, sy = now, y, y
                    sy += (y - sy) * 0.4  # 손가락 떨림 완화
                    if now - scroll_start < SCROLL_WAIT:
                        scroll_prev = sy
                    elif abs(scroll_prev - sy) >= SCROLL_STEP:  # 일정 거리 이상 움직였을 때만 한 칸씩
                        steps = int((scroll_prev - sy) / SCROLL_STEP)
                        pyautogui.scroll(steps * SCROLL_NOTCH)
                        scroll_prev -= steps * SCROLL_STEP
                else:
                    scroll_prev = None

                if mode == "MOVE":
                    px = sum(lm[i].x for i in (0, 5, 9, 17)) / 4  # 손바닥 중심: 손가락 움직임에 덜 흔들림
                    py = sum(lm[i].y for i in (0, 5, 9, 17)) / 4
                    gain = active_gain(size)
                    tx = fx(clamp(0.5 + (px - 0.5) * gain, 0, 1) * (SW - 1), now)
                    ty = fy(clamp(0.5 + (py - 0.5) * gain, 0, 1) * (SH - 1), now)
                    if math.hypot(tx - cx, ty - cy) > DEADZONE * gain * (1 - 2 * MARGIN):  # 멀리 있을 땐 떨림 허용폭도 같이 키움
                        cx, cy = tx, ty
                        glide.target(cx, cy)
                    can_click = now - scroll_end > CLICK_COOLDOWN  # 스크롤 직후 잠깐은 클릭 막기
                    if not dragging and can_click and pinch < PINCH_ON and pinch < rpinch:  # 엄지가 검지에 더 가까울 때만
                        pyautogui.mouseDown()
                        dragging = True
                    elif dragging and pinch > PINCH_OFF:
                        pyautogui.mouseUp()
                        dragging = False
                    if (not dragging and can_click and rpinch < PINCH_ON and rpinch < pinch
                            and now - last_right > 0.6):  # 엄지가 중지에 더 가까울 때만
                        pyautogui.click(button="right")
                        last_right = now
                    if dragging:
                        status = "DRAG"
                mp.solutions.drawing_utils.draw_landmarks(frame, hand, mp.solutions.hands.HAND_CONNECTIONS)
            else:
                if dragging:
                    pyautogui.mouseUp()
                    dragging = False
                scroll_prev, pending, pending_n = None, None, 0
                if mode == "SCROLL":
                    scroll_end = time.time()
                mode = "MOVE"
            h, w = frame.shape[:2]
            half = 0.5 / active_gain(size)  # 노란 네모 = 화면 전체에 대응하는 손 이동 범위
            cv2.rectangle(frame, (int(w * (0.5 - half)), int(h * (0.5 - half))),
                          (int(w * (0.5 + half)), int(h * (0.5 + half))), (0, 200, 255), 2)
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("Hand Mouse (q: quit)", frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
            if cv2.getWindowProperty("Hand Mouse (q: quit)", cv2.WND_PROP_VISIBLE) < 1:
                break  # 창의 X 버튼으로 닫아도 종료
            if glide.failsafe:
                break
    except pyautogui.FailSafeException:
        pass
    finally:
        glide.stop.set()
        if dragging:
            pyautogui.mouseUp()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
