# PyInstaller 설정: pyinstaller hand_mouse.spec --noconfirm
import sys
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("mediapipe")  # 손 인식 모델 파일 포함

a = Analysis(["hand_mouse.py"], datas=datas)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="HandMouse", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="HandMouse")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="HandMouse.app",
        bundle_identifier="com.dailycoops.handmouse",
        info_plist={
            "NSCameraUsageDescription": "손동작 인식을 위해 카메라를 사용합니다.",
            "CFBundleShortVersionString": "1.0.0",
        },
    )
