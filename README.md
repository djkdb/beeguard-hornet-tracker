# BeeGuard Step 1 — 꿀벌·장수말벌·등검은말벌 탐지와 추적 (YOLOv8)

직접 수집하고 라벨링한 3개 부류 데이터셋으로 YOLOv8을 학습하고, 영상에서 벌과 말벌을 탐지·추적하며 이동 궤적과 말벌의 정지비행을 표시합니다. 양봉장 말벌 방어 시스템 **BeeGuard**의 첫 단계(데이터 구축과 모델 개발)입니다.

<!-- 03_track.ipynb 실행 후 results/demo.gif가 생기면 아래 줄이 보입니다 -->
![tracking demo](results/demo.gif)

> 결과 영상: [`videos/beeguard_tracking.mp4`](videos/beeguard_tracking.mp4) · 학습 모델: [`models/best.pt`](models/best.pt)

## 프로젝트 위치

| 단계 | 목표 | 상태 |
| --- | --- | --- |
| **Step 1. 데이터 구축 및 모델 개발** | PC 환경에서 탐지·추적 모델과 데이터셋 구축 | **이 저장소** |
| Step 2. 실내 테스트 (MVP) | 카메라 실시간 입력, Jetson 추론, 대시보드 | 예정 |
| Step 3. 야외 양봉장 설치 | 주야간·날씨 대응, 원격 알림 | 예정 |
| Step 4. 방어 시스템 | 탐지 → 추적 → 조준 → 대응 | 예정 |

## 부류

| 라벨 | 이름 | 역할 |
| --- | --- | --- |
| `giant_hornet` | 장수말벌 (*Vespa mandarinia*) | 탐지 대상 — 무리 지어 벌통을 공격 |
| `honeybee` | 꿀벌 (*Apis mellifera*) | 구분 대상 — 정상 활동 |
| `yellow_legged_hornet` | 등검은말벌 (*Vespa velutina nigrithorax*) | 탐지 대상 — 벌통 입구 앞에서 정지비행하며 사냥 |
| (박스 없음) | 꽃등에·쌍살벌·호박벌 등, 빈 배경 | hard negative — 비슷한 곤충의 오탐 방지 |

한국 양봉장의 두 주요 위협종을 꿀벌과 함께 구분합니다. 생김새가 제각각인 "기타 곤충"은 부류로 만들지 않고, 박스 없는 이미지로 학습에 넣어 오탐을 줄였습니다. 부류별 구별 기준은 [`docs/labeling_guide.md`](docs/labeling_guide.md)에 있습니다.

## 결과

<!-- 02_train.ipynb 실행 후 results/experiments.csv의 값으로 채우기 -->

테스트 세트 기준, Colab T4 GPU.

| 실험 | 모델 | 입력 크기 | Precision | Recall | mAP50 | mAP50-95 | FPS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| n640 | YOLOv8n | 640 | – | – | – | – | – |
| n960 | YOLOv8n | 960 | – | – | – | – | – |
| n1280 | YOLOv8n | 1280 | – | – | – | – | – |

- 학습 곡선과 혼동 행렬: [`results/`](results/)
- 입력 해상도별 객체 크기 분포: [`results/label_size_stats.csv`](results/label_size_stats.csv)
- 시간에 따른 탐지 수와 정지비행 구간: [`results/detection_timeline.png`](results/detection_timeline.png)

## 데이터셋

| 구분 | 수집 | 정제 후 | 라벨 박스 수 |
| --- | --- | --- | --- |
| honeybee | 2,013 | 432 | – |
| giant_hornet | 1,687 | 529 | – |
| yellow_legged_hornet | 1,787 | 385 | – |
| hard negative · 배경 | 1,803 · 293 | 152 · 38 | 0 (Null) |

- **수집**: 여러 경로에서 부류별로 크롤링 — iNaturalist·GBIF(학명, 야외 관찰 사진), Wikimedia Commons·Openverse(학명·영문명), 네이버(한국어), Bing·DuckDuckGo(영문명), Baidu(중국어). 이미지마다 출처·라이선스·작성자를 기록
- **자동 정제**: 깨진 파일, 짧은 변 320px 미만, 극단적 가로세로 비율, 지각 해시 기반 중복 제거 (경로 간 중복은 관찰 사진 쪽을 남김)
- **수작업 검수**: 일러스트, 표본, 말벌주, 전투기 사진, 다른 말벌 종 제거
- **라벨링**: Grounding DINO로 초기 박스 생성 → 박스 번호를 붙인 시트로 AI(Claude) 검수 (사진 91장 제외, 박스 144개 삭제, 클래스 29개 수정) → 부류별 Train/Valid/Test = 70/20/10. 사람의 박스 미세 조정은 거치지 않았습니다(한계 참고)

공개 데이터셋은 쓰지 않았습니다. 크롤링한 이미지는 저작권 문제로 저장소에 올리지 않으며, 이미지별 출처 URL은 `sources.csv`로 따로 보관합니다.

## 방법

1. [`notebooks/01_collect_and_clean.ipynb`](notebooks/01_collect_and_clean.ipynb) — 크롤링, 자동 정제, 번호 붙은 미리보기로 검수, 출처 기록
2. [`notebooks/01b_auto_label.ipynb`](notebooks/01b_auto_label.ipynb) — Grounding DINO(zero-shot)로 초기 박스 생성(클래스는 폴더 기준), 번호 붙은 검수 시트 → 수정 목록 적용, Train/Valid/Test 분할
3. (선택) Roboflow — [라벨링 가이드](docs/labeling_guide.md)에 따라 박스를 더 다듬고 YOLOv8 형식으로 내보내기
4. [`notebooks/02_train.ipynb`](notebooks/02_train.ipynb) — 사전학습 가중치에서 전이학습, 비교 실험, 테스트 세트 평가
5. [`notebooks/03_track.ipynb`](notebooks/03_track.ipynb) — 추적 영상, 궤적 로그, 정지비행 표시, 그래프

02 노트북에 준비된 비교 실험입니다. 이번 제출에서는 입력 크기 비교만 돌렸습니다.

| 비교 실험 | 확인하려는 것 |
| --- | --- |
| 입력 크기 640 · 960 · 1280 | 작은 객체(꿀벌)에 해상도가 주는 영향과 속도 대가 |
| YOLOv8n vs YOLOv8s | 모델 크기의 영향 |
| 색상 증강 hsv_h 0.015 vs 0.1 | 색이 핵심 단서인 종 구분에서 색상 증강이 해가 되는지 |
| 기본 헤드 vs P2 헤드 | 4픽셀 간격 격자를 더하면 작은 객체가 나아지는지 |

## 추적과 궤적

[`scripts/track_trajectory.py`](scripts/track_trajectory.py)는 ByteTrack으로 객체를 추적하고 다음을 저장합니다.

| 파일 | 내용 |
| --- | --- |
| `logs/tracks.csv` | 프레임별 추적 ID, 부류, 중심 좌표, 박스 크기, 이동 속도, 정지비행 여부 |
| `logs/detections.csv` | 대시보드 '최근 탐지 기록' 형식의 이벤트 (새 객체 등장, 말벌 정지비행 시작) |
| `logs/summary.json` | 부류별 고유 객체 수, 정지비행 이벤트 수, 부류가 바뀐 트랙 수 |

**정지비행 판단**: 최근 1초 동안 트랙 중심의 순 이동 거리를 몸길이(박스 긴 변)로 나눈 속도가 초당 1몸길이 이하인 상태가 1초 이상 이어지면 정지비행으로 표시합니다. 말벌이 벌통 입구 앞에서 제자리에 머무는 사냥 행동을 잡기 위한 규칙이며, 기준값은 실행 인자로 바꿀 수 있습니다. 2D 영상만으로는 앉아 있는 개체와 떠 있는 개체를 구분하지 못한다는 한계가 있습니다.

## 저장소 구조

```
beeguard-hornet-tracker/
├── dataset/data.yaml          # 부류 정의 (이미지는 미포함)
├── docs/labeling_guide.md     # 부류 구별 기준, 박스 규칙, Roboflow 설정
├── notebooks/                 # 01 수집·정제 → 01b 자동 라벨링 → 02 학습·실험 → 03 추적
├── scripts/
│   ├── track_trajectory.py    # 탐지·추적·궤적·정지비행·로그
│   ├── label_size_stats.py    # 입력 해상도별 객체 크기 분석
│   ├── video_tools.py         # 클립 이어 붙이기, H.264 변환, GIF
│   └── compare_autolabel.py   # 자동 라벨 vs 검수 후 최종 라벨 비교 (정밀도·재현율·수정량)
├── models/best.pt             # 최종 학습 모델
├── results/                   # 실험표, 학습 곡선, 혼동 행렬, 그래프, GIF
├── videos/beeguard_tracking.mp4
├── logs/                      # 추적 로그
└── report/                    # 결과보고서 (초안: report/report_draft.md)
```

## 재현 방법

1. Colab에서 노트북을 열고 런타임을 T4 GPU로 바꿉니다.
2. `01` → `01b` → `02` → `03` 순서로 실행합니다. 노트북 사이의 파일은 Google Drive `MyDrive/beeguard/`로 주고받습니다. 각 노트북 첫 셀의 `REPO_URL`을 본인 저장소 주소로 바꿉니다.
3. 로컬 실행 시: `pip install -r requirements.txt` 후 스크립트를 직접 실행합니다.

```bash
python scripts/track_trajectory.py --model models/best.pt --source videos/clips/test.mp4 \
    --out videos/beeguard_tracking_raw.mp4 --imgsz 960
python scripts/video_tools.py h264 videos/beeguard_tracking_raw.mp4 videos/beeguard_tracking.mp4
```

## 한계와 다음 단계

- 라벨은 AI 검수까지만 거쳤습니다. 박스 크기 조정이 필요한 17장과 자동 박스가 없던 22장은 사람이 직접 고치지 못했습니다.
- 웹 이미지는 접사가 많아, 벌이 작게 찍히는 실제 양봉장 영상과 차이가 있습니다. Step 2에서 고정 카메라로 현장 데이터를 모아 보완합니다.
- 추적 영상은 공개 클립을 이어 붙인 것이라 실제 벌통 입구 환경을 그대로 대표하지는 않습니다.
- 다음 단계: Jetson에서의 실시간 추론, 타일링(SAHI)을 이용한 고해상도 추론, 대시보드 연동

## 출처

**영상 클립** (03_track.ipynb가 자동으로 내려받아 5초씩 이어 붙임)

| 클립 | 출처 | 작성자 | 라이선스 |
| --- | --- | --- | --- |
| 꿀벌 · 0:00–0:05 | [Mixkit: Bees at the entrance of the beehive](https://mixkit.co/free-stock-video/bees-at-the-entrance-of-the-beehive-25173/) | azgek | Mixkit Stock Video Free License |
| 장수말벌 · 1:26–1:31 | [Wikimedia Commons: Japanese giant hornet.webm](https://commons.wikimedia.org/wiki/File:Japanese_giant_hornet.webm) | The Nature Box | CC BY-SA 3.0 |
| 등검은말벌 · 2:40–2:45 | [Wikimedia Commons: Un frelon COINCE son DARD dans ma GoPro.webm](https://commons.wikimedia.org/wiki/File:Un_frelon_COINCE_son_DARD_dans_ma_GoPro.webm) | DD Frelons | CC BY 3.0 |

**관련 연구**

- Jeon, M.-S. et al. (2023). Deep learning-based portable image analysis system for real-time detection of *Vespa velutina*. *Applied Sciences, 13*(13), 7414.
- O'Shea-Wheller, T. A. et al. (2024). VespAI: A deep learning-based system for the detection of invasive hornets. *Communications Biology*. https://doi.org/10.1038/s42003-024-05979-z
- Hall, H. et al. (2025). Remote and automated detection of Asian hornets at an apiary, using spectral features of their hovering flight sounds. *Computers and Electronics in Agriculture, 235*, 110307.
- Ultralytics YOLOv8: https://github.com/ultralytics/ultralytics

## 라이선스

코드는 [MIT License](LICENSE)를 따릅니다. 학습 이미지는 포함하지 않습니다. 결과 영상은 CC BY-SA 3.0 클립을 포함하므로 같은 CC BY-SA 3.0으로 공개합니다(원본 클립 출처는 위 표 참고).
