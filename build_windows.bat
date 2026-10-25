@echo off
cd /d "%~dp0"
set "LOG=%~dp0build_log.txt"
set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
echo === HandMouse build %date% %time% === > "%LOG%"
if not exist "%PYEXE%" (
  echo Installing Python 3.11...
  winget install -e --id Python.Python.3.11 --scope user --silent --accept-package-agreements --accept-source-agreements >> "%LOG%" 2>&1
)
if not exist "%PYEXE%" (
  echo NO_PYTHON >> "%LOG%"
  goto end
)
echo Installing packages... please wait
if not exist .venv "%PYEXE%" -m venv .venv >> "%LOG%" 2>&1
.venv\Scripts\python -m pip install -q mediapipe==0.10.14 opencv-python pyautogui pyinstaller >> "%LOG%" 2>&1
.venv\Scripts\python -c "import mediapipe, cv2, pyautogui" >nul 2>&1 || (
  echo Installing Visual C++ runtime...
  winget install -e --id Microsoft.VCRedist.2015+.x64 --force --silent --accept-package-agreements --accept-source-agreements >> "%LOG%" 2>&1
)
.venv\Scripts\python -c "import mediapipe, cv2, pyautogui; print('IMPORT_OK')" >> "%LOG%" 2>&1 || (
  echo IMPORT_FAILED >> "%LOG%"
  goto end
)
echo Building exe...
.venv\Scripts\pyinstaller --noconfirm --clean --windowed --name HandMouse --collect-data mediapipe hand_mouse.py >> "%LOG%" 2>&1
if not exist dist\HandMouse\HandMouse.exe (
  echo BUILD_FAILED >> "%LOG%"
  goto end
)
powershell -NoProfile -Command "Compress-Archive -Force dist\HandMouse HandMouse-windows.zip" >> "%LOG%" 2>&1
echo BUILD_DONE >> "%LOG%"
:end
echo === END %time% === >> "%LOG%"
start "" notepad "%LOG%"
