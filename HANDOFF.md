# 작업 인수인계 (제출 전 임시 문서, 제출 직전에 지워도 됨)

과제 마감: 2026-11-25 00:00 (KST), 23:50까지 제출 목표. 학번·이름 2022041067 이성준.
제출물: 결과보고서 PDF(`report/result_report.pdf`) + 이 GitHub 저장소 링크.

## 끝난 것
- 데이터 수집·정제(7,583 → 1,536장), Grounding DINO 자동 라벨, AI 검수(`labeling/corrections.json`), 분할
- 분할된 데이터셋: Google Drive `MyDrive/beeguard/dataset_split.zip` (333MB, 공유 링크
  https://drive.google.com/file/d/1MhwPtHR2vAcBEGcf_8BuSXW1lfU5jHLD/view , 제출 뒤 "제한됨"으로 되돌릴 것)
  Train 996 / Valid 284 / Test 143장, 박스 1,432개
- 보고서 초안 `report/report_draft.md`: 학습·추적 결과 칸(【 】)만 남음

## 남은 일 (순서대로)
1. 학습: Colab 무료 GPU는 사용량 제한으로 막힘. Claude Code 클라우드 세션(CPU 4코어)에서 학습함.
   - n320 (12 epoch, epoch당 약 52초) → 결과는 `models/best.pt`, `results/` 에 커밋됨 (커밋 메시지 확인)
   - n640 (20 epoch 예정, epoch당 약 3.5분) → 끝나면 n320과 비교해 더 나은 쪽을 best.pt로
2. 추적 영상: `notebooks/03_track.ipynb`와 같은 일을 로컬에서 실행
   ```bash
   # 클립 3개 내려받기 (URL은 03 노트북 셀 3 CLIP_SOURCES), 잘라 붙이기
   python scripts/video_tools.py cut --clip videos/clips/bees_mixkit_25173.mp4 0 5 \
       --clip videos/clips/giant_hornet_naturebox.webm 86 5 \
       --clip videos/clips/yellow_legged_hornet_ddfrelons.webm 160 5 --out videos/clips/test.mp4
   python scripts/track_trajectory.py --model models/best.pt --source videos/clips/test.mp4 \
       --out videos/beeguard_tracking_raw.mp4 --logs logs --imgsz 640 --conf 0.25 \
       --tracker bytetrack.yaml --hover-window 1.0 --hover-speed 1.0 --hover-min 1.0
   python scripts/video_tools.py h264 videos/beeguard_tracking_raw.mp4 videos/beeguard_tracking.mp4
   python scripts/video_tools.py gif videos/beeguard_tracking.mp4 results/demo.gif --width 640 --fps 10
   ```
   그래프는 03 노트북 셀 6 코드.
3. README 결과 표, 보고서 【 】 칸 채우기 (results/experiments.csv, results/test_confusion_counts.csv,
   results/failure_cases.jpg, logs/summary.json)
4. 보고서 PDF 만들기 → `report/result_report.pdf`, 이 파일(HANDOFF.md) 삭제

## 학습을 다른 곳에서 다시 해야 할 때
```bash
pip install ultralytics gdown
gdown "https://drive.google.com/file/d/1MhwPtHR2vAcBEGcf_8BuSXW1lfU5jHLD/view" -O dataset_split.zip
unzip dataset_split.zip -d dataset
python scripts/train_local.py --data dataset --run n320 --epochs 12 --patience 4   # CPU
python scripts/train_local.py --data dataset --run n640 --epochs 50                # GPU
```
`train_local.py`는 02 노트북 셀 3·5·6·7·8을 그대로 실행하고 models/best.pt, results/, train_outputs.zip을 만든다.
주의: 실행할 때마다 results/experiments.csv를 그 실행의 실험만으로 덮어쓴다. 두 실험을 따로 돌렸으면 표를 합칠 것.

## 진행 기록
- n320 학습 끝: test mAP50 0.731 / mAP50-95 0.484. models/best.pt, results/ 커밋됨 (results/experiments_n320.csv에 따로 보관)
- n320으로 추적 영상·GIF·그래프·logs 커밋됨 (꿀벌 구간에서 꿀벌 무리를 장수말벌로 묶는 문제 → 640 이상 입력이 필요)
- 보고서 1.4~1.7, 3.6~3.7 채움. 남은 【 】: n640 결과, 최종 모델 선택, n640 추적 결과
- PDF: `node scripts/report_pdf.js` → report/result_report.pdf (현재 n320 기준 판본이 커밋됨)
- n640 학습: 클라우드 세션 scratch 복사본에서 진행 중 (epoch당 약 3분, 20 epoch). 세션이 끊기면 n320 결과로 제출하거나 train_local.py로 다시 실행
