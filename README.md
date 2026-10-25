# Hand Mouse — 손동작으로 노트북 조작하기

웹캠으로 손을 인식해서 마우스처럼 쓰는 프로그램입니다.

## 다운로드 · 설치
[Releases](../../releases/latest)에서 내 컴퓨터에 맞는 파일을 받으세요.

**Windows** — `HandMouse-windows.zip` 압축 풀기 → `HandMouse` 폴더 안의 `HandMouse.exe` 실행
- "Windows의 PC 보호" 창이 뜨면 `추가 정보` → `실행`
- 실행이 안 되면 [Visual C++ 재배포 패키지](https://aka.ms/vs/17/release/vc_redist.x64.exe)를 설치하세요.

**Mac** — `HandMouse-mac.zip` 압축 풀기 → `HandMouse.app`을 응용 프로그램 폴더로 이동
- 처음 한 번은 우클릭 → `열기`
- 시스템 설정 → 개인정보 보호 및 보안에서 `카메라`, `손쉬운 사용`에 HandMouse 허용

## 손동작
| 동작 | 기능 |
|---|---|
| 손바닥 펴고 움직이기 | 커서 이동 |
| 엄지+검지 집기 | 클릭 (집은 채로 움직이면 드래그, 두 번 = 더블클릭) |
| 엄지+중지 집기 | 오른쪽 클릭 |
| 검지+중지만 펴고 위아래 | 스크롤 (일정 거리 움직일 때마다 한 칸씩) |
| 주먹 | 일시정지 |
| 카메라 창에서 q / ESC | 종료 |

- 카메라 창의 **노란 네모** 안에서 손을 움직이면 커서가 화면 전체를 움직여요.
- 손이 카메라에서 멀어질수록 감도가 점점 올라가고, 가까워지면 다시 원래대로 돌아와요.

비상 정지: 실제 마우스를 화면 왼쪽 위 모서리로 밀기

## 개발자용
- Windows에서 직접 빌드: `build_windows.bat` 더블클릭 (Python·패키지 설치부터 exe·zip 생성까지 자동)
- 새 버전 배포: GitHub에서 새 Release를 발행(Publish)하면 GitHub Actions가 Windows·Mac 설치 파일을 만들어 그 Release에 자동으로 첨부합니다.
