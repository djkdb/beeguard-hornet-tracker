"""추적 로그(logs/tracks.csv)를 후처리해서 결과 영상을 다시 그린다.

1. 트랙 길이 필터: 전체 프레임 수가 --min-len 미만인 짧은 트랙은 그리지 않는다 (한두 프레임 깜박이는 오탐 제거).
2. 트랙 다수결: 트랙마다 프레임별 종 판정을 모아 가장 많이 나온 종 하나로 표시한다.

트랙 전체를 본 뒤에 판단하므로 오프라인 후처리다. 실시간으로 쓰려면 "N프레임 이상 이어진 트랙만 표시"와
"지금까지의 누적 다수결"처럼 약간 늦게 판단하는 방식으로 바꿔야 한다.

사용법:
    python scripts/render_tracks.py --source videos/clips/test.mp4 --tracks logs/tracks.csv --out out.mp4
"""
import argparse
import csv
from collections import Counter, defaultdict, deque

import cv2
import numpy as np

COLORS = {"honeybee": (5, 183, 242), "giant_hornet": (70, 57, 230), "yellow_legged_hornet": (229, 93, 155)}  # BGR
HORNETS = {"giant_hornet", "yellow_legged_hornet"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--tracks", default="logs/tracks.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-len", type=int, default=10, help="이보다 짧은 트랙은 그리지 않음 (프레임 수)")
    ap.add_argument("--trail", type=int, default=45)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.tracks, encoding="utf-8-sig")))
    votes, length = defaultdict(Counter), Counter()
    by_frame = defaultdict(list)
    for r in rows:
        votes[r["track_id"]][r["class"]] += 1
        length[r["track_id"]] += 1
        by_frame[int(r["frame"])].append(r)
    major = {t: v.most_common(1)[0][0] for t, v in votes.items()}
    keep = {t for t, n in length.items() if n >= a.min_len}
    print(f"트랙 {len(length)}개 중 {len(keep)}개 표시, 다수결로 종이 바뀐 행 "
          f"{sum(1 for r in rows if r['track_id'] in keep and r['class'] != major[r['track_id']])}개")

    cap = cv2.VideoCapture(a.source)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    trails = defaultdict(lambda: deque(maxlen=a.trail))
    f = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        for r in by_frame.get(f, []):
            t = r["track_id"]
            if t not in keep:
                continue
            nm = major[t]
            col = COLORS.get(nm, (255, 255, 255))
            cx, cy, bw, bh = (float(r[k]) for k in ("cx", "cy", "w", "h"))
            x0, y0, x1, y1 = int(cx - bw / 2), int(cy - bh / 2), int(cx + bw / 2), int(cy + bh / 2)
            trails[t].append((int(cx), int(cy)))
            pts = np.array(trails[t], np.int32).reshape(-1, 1, 2)
            if len(pts) > 1:
                cv2.polylines(img, [pts], False, col, 2, cv2.LINE_AA)
            cv2.rectangle(img, (x0, y0), (x1, y1), col, 1 if nm == "honeybee" else 3, cv2.LINE_AA)
            if nm in HORNETS:
                txt = f"{nm.replace('_', ' ')} #{t}"
                (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(img, (x0, y0 - th - 8), (x0 + tw + 6, y0), col, -1)
                cv2.putText(img, txt, (x0 + 3, y0 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
                if r.get("hovering") == "1":
                    cv2.putText(img, "HOVER", (x0, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
        out.write(img)
        f += 1
    out.release()
    print("저장:", a.out)


if __name__ == "__main__":
    main()
