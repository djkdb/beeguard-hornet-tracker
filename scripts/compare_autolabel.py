#!/usr/bin/env python3
"""자동 라벨(Grounding DINO)과 검수를 마친 최종 라벨(Roboflow 내보내기)을 비교한다.

"자동 박스가 얼마나 맞았고, 사람이 무엇을 얼마나 고쳤는지"를 숫자로 보여 주기 위한 스크립트.
두 라벨의 박스를 IoU로 짝지은 뒤 다음을 센다.
- 맞음: IoU >= 0.5이고 클래스도 같음
- 클래스 수정: 위치는 맞는데(IoU >= 0.5) 클래스가 바뀜
- 위치 수정: 짝은 맞지만 IoU < 0.9 (사람이 박스를 줄이거나 옮김)
- 삭제: 자동 박스 중 최종 라벨에 짝이 없음 (둥지·다른 곤충·중복 박스 등)
- 추가: 최종 박스 중 자동 라벨에 짝이 없음 (자동이 놓친 개체)
정밀도 = 맞음 / 자동 박스 수, 재현율 = 맞음 / 최종 박스 수

사용 예:
    python scripts/compare_autolabel.py --auto /content/autolabel --final /content/dataset \
        --manual /content/needs_manual --csv results/autolabel_eval.csv

  --auto    01b_auto_label.ipynb가 만든 폴더 (train/labels, data.yaml)
  --final   Roboflow에서 YOLOv8 형식으로 내보내 압축을 푼 폴더 (train·valid·test/labels, data.yaml)
  --manual  (선택) 자동 박스를 하나도 못 찾아 손으로 라벨링한 사진 폴더 (needs_manual)

주의: Roboflow 전처리에서 Resize를 "Fit within"(비율 유지, 여백 없음)이나 끄기로 했을 때만
정규화 좌표가 그대로 유지되어 비교가 정확하다. "Stretch"나 검은 여백이 들어가는 설정이면 IoU가 틀어진다.
"""
import argparse
import csv
import glob
import os
import re

import yaml

RF_SUFFIX = re.compile(r"_(jpe?g|png|webp|bmp)\.rf\.[0-9a-f]+$", re.I)


def names_of(root):
    d = yaml.safe_load(open(os.path.join(root, "data.yaml"), encoding="utf-8"))
    n = d["names"]
    return n if isinstance(n, list) else [n[k] for k in sorted(n)]


def original_stem(path):
    """Roboflow가 붙인 '_jpg.rf.<해시>'를 떼어 원래 파일 이름을 되찾는다."""
    return RF_SUFFIX.sub("", os.path.splitext(os.path.basename(path))[0])


def read_labels(root, names):
    """{원래 파일 이름: [(클래스 이름, cx, cy, w, h), ...]}"""
    out = {}
    for lp in glob.glob(os.path.join(root, "*", "labels", "*.txt")):
        boxes = []
        for line in open(lp, encoding="utf-8"):
            p = line.split()
            if len(p) >= 5:
                boxes.append((names[int(p[0])], *map(float, p[1:5])))
        out[original_stem(lp)] = boxes
    return out


def iou(a, b):
    ax0, ay0, ax1, ay1 = a[1] - a[3] / 2, a[2] - a[4] / 2, a[1] + a[3] / 2, a[2] + a[4] / 2
    bx0, by0, bx1, by1 = b[1] - b[3] / 2, b[2] - b[4] / 2, b[1] + b[3] / 2, b[2] + b[4] / 2
    iw, ih = max(0.0, min(ax1, bx1) - max(ax0, bx0)), max(0.0, min(ay1, by1) - max(ay0, by0))
    inter = iw * ih
    union = a[3] * a[4] + b[3] * b[4] - inter
    return inter / union if union > 0 else 0.0


def match(auto, final, thr):
    """IoU가 큰 쌍부터 하나씩 짝짓는다 (클래스는 따지지 않음). [(i, j, iou)]"""
    pairs = sorted(((iou(a, f), i, j) for i, a in enumerate(auto) for j, f in enumerate(final)), reverse=True)
    used_a, used_f, out = set(), set(), []
    for v, i, j in pairs:
        if v < thr:
            break
        if i not in used_a and j not in used_f:
            used_a.add(i); used_f.add(j); out.append((i, j, v))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auto", required=True)
    ap.add_argument("--final", required=True)
    ap.add_argument("--manual", default=None)
    ap.add_argument("--iou", type=float, default=0.5, help="같은 개체로 볼 IoU 기준")
    ap.add_argument("--edit-iou", type=float, default=0.9, help="이보다 낮으면 '위치 수정'으로 셈")
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()

    auto = read_labels(a.auto, names_of(a.auto))
    final_names = names_of(a.final)
    final = read_labels(a.final, final_names)
    manual = set()
    if a.manual:
        manual = {os.path.splitext(f)[0] for f in os.listdir(a.manual)}
        for stem in manual:
            auto.setdefault(stem, [])          # 자동이 박스를 하나도 못 낸 사진

    classes = sorted({b[0] for v in list(auto.values()) + list(final.values()) for b in v} | set(final_names))
    st = {c: dict(auto=0, final=0, correct=0, cls_changed=0, moved=0, deleted=0, added=0, iou_sum=0.0, n_match=0) for c in classes}
    img = dict(compared=0, removed_in_review=0, only_in_final=0, null_kept=0, null_changed=0, untouched=0)

    for stem, ab in auto.items():
        if stem not in final:
            img["removed_in_review"] += 1
            continue
        fb = final[stem]
        img["compared"] += 1
        if not ab and stem not in manual:     # 자동 단계에서 Null로 넣은 사진
            img["null_kept" if not fb else "null_changed"] += 1
        for b in ab:
            st[b[0]]["auto"] += 1
        for b in fb:
            st[b[0]]["final"] += 1
        pairs = match(ab, fb, a.iou)
        touched = len(pairs) != len(ab) or len(pairs) != len(fb)
        for i, j, v in pairs:
            c = fb[j][0]
            st[c]["n_match"] += 1; st[c]["iou_sum"] += v
            if ab[i][0] == c:
                st[c]["correct"] += 1
            else:
                st[c]["cls_changed"] += 1; touched = True
            if v < a.edit_iou:
                st[c]["moved"] += 1; touched = True
        mi, mj = {i for i, _, _ in pairs}, {j for _, j, _ in pairs}
        for i, b in enumerate(ab):
            if i not in mi:
                st[b[0]]["deleted"] += 1
        for j, b in enumerate(fb):
            if j not in mj:
                st[b[0]]["added"] += 1
        img["untouched"] += (not touched and bool(ab))
    img["only_in_final"] = len(set(final) - set(auto))

    rows = []
    tot = {k: 0 for k in ["auto", "final", "correct", "cls_changed", "moved", "deleted", "added", "n_match"]}
    tot_iou = 0.0
    for c in classes:
        s = st[c]
        for k in tot:
            tot[k] += s[k]
        tot_iou += s["iou_sum"]
        rows.append([c, s["auto"], s["final"], s["correct"], s["cls_changed"], s["moved"], s["deleted"], s["added"],
                     s["correct"] / s["auto"] if s["auto"] else float("nan"),
                     s["correct"] / s["final"] if s["final"] else float("nan"),
                     s["iou_sum"] / s["n_match"] if s["n_match"] else float("nan")])
    rows.append(["전체", tot["auto"], tot["final"], tot["correct"], tot["cls_changed"], tot["moved"], tot["deleted"], tot["added"],
                 tot["correct"] / tot["auto"] if tot["auto"] else float("nan"),
                 tot["correct"] / tot["final"] if tot["final"] else float("nan"),
                 tot_iou / tot["n_match"] if tot["n_match"] else float("nan")])
    head = ["클래스", "자동 박스", "최종 박스", "맞음", "클래스 수정", "위치 수정", "삭제", "추가", "정밀도", "재현율", "평균 IoU"]

    print("| " + " | ".join(head) + " |")
    print("|" + " --- |" * len(head))
    for r in rows:
        print("| " + " | ".join(f"{x:.3f}" if isinstance(x, float) else str(x) for x in r) + " |")
    print()
    print(f"비교한 사진 {img['compared']}장 | 검수에서 뺀 사진 {img['removed_in_review']}장 | "
          f"손대지 않은 사진 {img['untouched']}장 | 자동 단계 Null 유지 {img['null_kept']}장 / 박스가 생김 {img['null_changed']}장 | "
          f"최종에만 있는 사진 {img['only_in_final']}장")
    print(f"(IoU 기준 {a.iou}, 위치 수정 기준 IoU < {a.edit_iou}. 손 라벨링 사진은 자동 박스 0개로 계산)")

    if a.csv:
        os.makedirs(os.path.dirname(os.path.abspath(a.csv)), exist_ok=True)
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as fp:
            wr = csv.writer(fp)
            wr.writerow(head)
            wr.writerows([[f"{x:.4f}" if isinstance(x, float) else x for x in r] for r in rows])
            wr.writerow([])
            wr.writerow(["사진 통계"] + [f"{k}={v}" for k, v in img.items()])
        print("저장:", a.csv)


if __name__ == "__main__":
    main()
