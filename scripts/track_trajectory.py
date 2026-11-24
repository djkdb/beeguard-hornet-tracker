#!/usr/bin/env python3
"""BeeGuard Step 1 — 탐지 + 추적 + 궤적 저장 + 정지비행(hovering) 표시.

사용 예:
    python scripts/track_trajectory.py --model models/best.pt \
        --source videos/clips/test.mp4 --out videos/beeguard_tracking.mp4 --imgsz 960

산출물:
    결과 영상            박스, 추적 ID, 최근 궤적, 말벌 정지비행(HOVER) 표시
    logs/tracks.csv      프레임별 객체 좌표와 이동 속도 (궤적 원자료)
    logs/detections.csv  대시보드 '최근 탐지 기록'과 같은 형식의 이벤트 로그
    logs/summary.json    부류별 고유 객체 수, 정지비행 이벤트 수, 부류가 바뀐 트랙 수

정지비행 판단:
    최근 window 초 동안 트랙 중심의 '순 이동 거리'를 몸길이(박스 긴 변)로 나눠
    초당 몸길이 단위 속도를 구한다. 이 값이 기준 이하인 상태가 min 초 이상 이어지면
    정지비행으로 본다. 벌통 입구 앞에서 좌우로 오가며 제자리에 머무는 사냥 행동은
    순 이동 거리가 작아서 잡히고, 곧게 드나드는 꿀벌은 잡히지 않는다.
    한계: 2D 영상만으로는 '앉아 있는 개체'와 '떠 있는 개체'를 구분하지 못한다.
"""
import argparse
import csv
import json
import math
import os
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta

import cv2
import numpy as np

HORNET_CLASSES = {"giant_hornet", "yellow_legged_hornet"}
KO_NAME = {"honeybee": "꿀벌", "giant_hornet": "장수말벌", "yellow_legged_hornet": "등검은말벌"}
BOX_COLORS = {"honeybee": (5, 183, 242), "giant_hornet": (70, 57, 230), "yellow_legged_hornet": (229, 93, 155)}  # BGR
TRAIL_COLORS = {  # BGR
    "honeybee": (0, 200, 255),
    "giant_hornet": (0, 0, 255),
    "yellow_legged_hornet": (255, 0, 200),
}


class HoverDetector:
    """트랙별 순 이동 속도(몸길이/초)로 정지비행 상태를 판단한다."""

    def __init__(self, fps, window_s=1.0, max_speed=1.0, min_duration_s=1.0):
        self.fps = fps
        self.window = max(2, int(round(fps * window_s)))
        self.max_speed = max_speed
        self.min_frames = max(1, int(round(fps * min_duration_s)))
        self.hist = defaultdict(lambda: deque(maxlen=self.window))
        self.slow_frames = defaultdict(int)
        self.active = set()

    def update(self, tid, cx, cy, body_len):
        """(속도, 정지비행 여부, 이번 프레임에 정지비행이 시작됐는지)를 돌려준다."""
        h = self.hist[tid]
        h.append((cx, cy, body_len))
        if len(h) < self.window:
            return float("nan"), False, False
        (x0, y0, _), (x1, y1, _) = h[0], h[-1]
        mean_len = sum(b for _, _, b in h) / len(h)
        secs = (len(h) - 1) / self.fps
        speed = math.hypot(x1 - x0, y1 - y0) / max(mean_len, 1e-6) / secs
        if speed <= self.max_speed:
            self.slow_frames[tid] += 1
        else:
            self.slow_frames[tid] = 0
            self.active.discard(tid)
        hovering = self.slow_frames[tid] >= self.min_frames
        started = hovering and tid not in self.active
        if started:
            self.active.add(tid)
        return speed, hovering, started


def fmt_time(base, t):
    if base is not None:
        return (base + timedelta(seconds=t)).strftime("%Y-%m-%d %H:%M:%S")
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="학습된 가중치 (예: models/best.pt)")
    ap.add_argument("--source", required=True, help="입력 영상 경로")
    ap.add_argument("--out", default="videos/beeguard_tracking.mp4", help="결과 영상 경로")
    ap.add_argument("--logs", default="logs", help="CSV·JSON 로그를 저장할 폴더")
    ap.add_argument("--imgsz", type=int, default=960, help="추론 입력 크기 (학습과 같게)")
    ap.add_argument("--conf", type=float, default=0.25, help="신뢰도 임계값")
    ap.add_argument("--tracker", default="bytetrack.yaml", help="bytetrack.yaml 또는 botsort.yaml")
    ap.add_argument("--trail", type=int, default=45, help="궤적으로 그릴 최근 프레임 수")
    ap.add_argument("--clean", action="store_true", help="꿀벌은 얇은 박스만, 말벌만 이름·ID 표시 (화면이 덜 복잡함)")
    ap.add_argument("--hover-window", type=float, default=1.0, help="속도 계산 구간(초)")
    ap.add_argument("--hover-speed", type=float, default=1.0, help="이 값(몸길이/초) 이하이면 느린 상태")
    ap.add_argument("--hover-min", type=float, default=1.0, help="느린 상태가 이 시간(초) 이상 이어지면 정지비행")
    ap.add_argument("--camera", default="카메라 1")
    ap.add_argument("--location", default="1번 벌통")
    ap.add_argument("--start-time", default=None,
                    help="영상 시작 시각 'YYYY-MM-DD HH:MM:SS' (없으면 영상 경과 시간으로 기록)")
    return ap.parse_args()


def main():
    args = parse_args()
    from ultralytics import YOLO  # 무거운 import는 인자 확인 뒤에

    model = YOLO(args.model)
    names = model.names

    cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        raise SystemExit(f"영상을 열 수 없습니다: {args.source}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    os.makedirs(args.logs, exist_ok=True)
    writer = cv2.VideoWriter(args.out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    base = datetime.strptime(args.start_time, "%Y-%m-%d %H:%M:%S") if args.start_time else None
    hover = HoverDetector(fps, args.hover_window, args.hover_speed, args.hover_min)
    trails = defaultdict(lambda: deque(maxlen=args.trail))
    class_votes = defaultdict(Counter)
    hover_events = Counter()

    tracks_f = open(os.path.join(args.logs, "tracks.csv"), "w", newline="", encoding="utf-8-sig")
    events_f = open(os.path.join(args.logs, "detections.csv"), "w", newline="", encoding="utf-8-sig")
    tw, ew = csv.writer(tracks_f), csv.writer(events_f)
    tw.writerow(["frame", "time_s", "track_id", "class", "conf", "cx", "cy", "w", "h", "speed_bl_s", "hovering"])
    ew.writerow(["time", "event", "class", "confidence", "camera", "location", "status", "track_id"])

    frame_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = frame_idx / fps
        res = model.track(frame, persist=True, imgsz=args.imgsz, conf=args.conf,
                          tracker=args.tracker, verbose=False)[0]
        canvas = frame.copy() if args.clean else res.plot(line_width=2)
        if args.clean and res.boxes is not None and len(res.boxes):
            bid = res.boxes.id.int().cpu().tolist() if res.boxes.id is not None else [None] * len(res.boxes)
            for (x0, y0, x1, y1), c, tid in zip(res.boxes.xyxy.cpu().numpy().astype(int), res.boxes.cls.int().cpu().tolist(), bid):
                nm = names[int(c)]
                col = BOX_COLORS.get(nm, (255, 255, 255))
                cv2.rectangle(canvas, (x0, y0), (x1, y1), col, 1 if nm == "honeybee" else 3, cv2.LINE_AA)
                if nm in HORNET_CLASSES:
                    txt = f"{nm.replace('_', ' ')} #{tid}" if tid is not None else nm.replace('_', ' ')
                    (tw_, th_), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(canvas, (x0, y0 - th_ - 8), (x0 + tw_ + 6, y0), col, -1)
                    cv2.putText(canvas, txt, (x0 + 3, y0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        if res.boxes is not None and res.boxes.id is not None:
            xywh = res.boxes.xywh.cpu().numpy()
            ids = res.boxes.id.int().cpu().tolist()
            clss = res.boxes.cls.int().cpu().tolist()
            confs = res.boxes.conf.cpu().tolist()
            for (cx, cy, bw, bh), tid, c, cf in zip(xywh, ids, clss, confs):
                name = names[int(c)]
                is_hornet = name in HORNET_CLASSES
                first_seen = tid not in class_votes
                class_votes[tid][name] += 1
                trails[tid].append((int(cx), int(cy)))
                speed, hovering, started = hover.update(tid, float(cx), float(cy), float(max(bw, bh)))

                if first_seen:
                    ew.writerow([fmt_time(base, t), f"{KO_NAME.get(name, name)} 탐지", name, f"{cf:.2f}",
                                 args.camera, args.location, "주의" if is_hornet else "정상", tid])
                if started and is_hornet:
                    hover_events[name] += 1
                    ew.writerow([fmt_time(base, t), f"{KO_NAME.get(name, name)} 정지비행", name, f"{cf:.2f}",
                                 args.camera, args.location, "경고", tid])

                tw.writerow([frame_idx, f"{t:.3f}", tid, name, f"{cf:.3f}", f"{cx:.1f}", f"{cy:.1f}",
                             f"{bw:.1f}", f"{bh:.1f}", "" if math.isnan(speed) else f"{speed:.2f}", int(hovering)])

                pts = np.array(trails[tid], np.int32).reshape(-1, 1, 2)
                if len(pts) > 1:
                    cv2.polylines(canvas, [pts], False, TRAIL_COLORS.get(name, (255, 255, 255)), 2)
                if hovering and is_hornet:
                    cv2.putText(canvas, "HOVER", (int(cx - bw / 2), int(cy + bh / 2 + 20)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

        writer.write(canvas)
        frame_idx += 1

    cap.release()
    writer.release()
    tracks_f.close()
    events_f.close()

    majority = {tid: votes.most_common(1)[0][0] for tid, votes in class_votes.items()}
    summary = {
        "source": args.source,
        "frames": frame_idx,
        "fps": round(fps, 2),
        "duration_s": round(frame_idx / fps, 2),
        "unique_tracks_by_class": dict(Counter(majority.values())),
        "hover_events_by_class": dict(hover_events),
        "tracks_with_class_switch": sum(1 for v in class_votes.values() if len(v) > 1),
        "settings": {k: getattr(args, k) for k in ("imgsz", "conf", "tracker", "hover_window", "hover_speed", "hover_min")},
    }
    with open(os.path.join(args.logs, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"결과 영상: {args.out}")


if __name__ == "__main__":
    main()
