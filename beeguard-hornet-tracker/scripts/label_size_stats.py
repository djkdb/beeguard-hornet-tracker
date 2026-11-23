#!/usr/bin/env python3
"""YOLO 라벨로 '입력 해상도별 객체 크기'를 계산한다 (작은 객체 분석용).

YOLO는 이미지의 긴 변을 imgsz로 줄여서 학습·추론한다. 그래서 같은 꿀벌도
imgsz가 작을수록 픽셀 크기가 작아진다. 이 스크립트는 각 객체의 긴 변이
imgsz별로 몇 픽셀이 되는지 구해, 크기 구간별 개수를 표로 보여 준다.
YOLOv8의 가장 촘촘한 탐지 격자(P3)는 8픽셀 간격이므로 8픽셀 미만은 특히 어렵다.

사용 예:
    python scripts/label_size_stats.py --root /content/dataset --imgsz 640 960 1280 \
        --names giant_hornet honeybee yellow_legged_hornet --csv results/label_size_stats.csv
"""
import argparse
import csv
import glob
import os
from collections import defaultdict

from PIL import Image

BINS = [(0, 8, "<8px"), (8, 16, "8-16px"), (16, 32, "16-32px"), (32, 1e9, ">=32px")]
IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def find_image(label_path):
    stem = os.path.splitext(os.path.basename(label_path))[0]
    img_dir = os.path.join(os.path.dirname(os.path.dirname(label_path)), "images")
    for ext in IMG_EXTS:
        p = os.path.join(img_dir, stem + ext)
        if os.path.exists(p):
            return p
    return None


def collect(root):
    """(class_id, 객체 긴 변의 원본 픽셀 길이, 이미지 긴 변) 목록."""
    rows = []
    for lp in glob.glob(os.path.join(root, "*", "labels", "*.txt")):
        ip = find_image(lp)
        if ip is None:
            continue
        with Image.open(ip) as im:
            iw, ih = im.size
        with open(lp) as f:
            for line in f:
                parts = line.split()
                if len(parts) < 5:
                    continue
                c, _, _, w, h = int(parts[0]), *map(float, parts[1:5])
                rows.append((c, max(w * iw, h * ih), max(iw, ih)))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="train/valid/test 폴더가 있는 데이터셋 경로")
    ap.add_argument("--imgsz", type=int, nargs="+", default=[640, 960, 1280])
    ap.add_argument("--names", nargs="*", default=None, help="부류 이름 (data.yaml 순서)")
    ap.add_argument("--csv", default=None, help="결과를 저장할 CSV 경로")
    a = ap.parse_args()

    rows = collect(a.root)
    if not rows:
        raise SystemExit("라벨을 찾지 못했습니다. --root 경로를 확인하세요.")
    max_long = max(r[2] for r in rows)
    over = [s for s in a.imgsz if s > max_long]
    if over:
        print(f"[주의] 데이터셋 이미지의 긴 변이 최대 {max_long}px입니다. imgsz {over}는 확대(업샘플링)일 뿐"
              " 정보가 늘지 않습니다. Roboflow 내보내기에서 Resize 설정을 확인하세요.\n")

    table = []
    for s in a.imgsz:
        counts = defaultdict(lambda: [0] * len(BINS))
        for c, obj_px, img_long in rows:
            px = obj_px * s / img_long  # YOLO처럼 이미지 긴 변을 imgsz에 맞춤 (작은 이미지는 확대됨)
            for i, (lo, hi, _) in enumerate(BINS):
                if lo <= px < hi:
                    counts[c][i] += 1
                    break
        for c in sorted(counts):
            name = a.names[c] if a.names and c < len(a.names) else str(c)
            total = sum(counts[c])
            table.append([s, name, total] + counts[c] + [f"{counts[c][0] / total:.1%}"])

    header = ["imgsz", "class", "objects"] + [b[2] for b in BINS] + ["share_<8px"]
    widths = [max(len(str(r[i])) for r in [header] + table) for i in range(len(header))]
    for r in [header] + table:
        print("  ".join(str(v).rjust(w) for v, w in zip(r, widths)))

    if a.csv:
        os.makedirs(os.path.dirname(os.path.abspath(a.csv)), exist_ok=True)
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows([header] + table)
        print("저장:", a.csv)


if __name__ == "__main__":
    main()
