#!/usr/bin/env python3
"""AI 검수 결과(corrections.json)를 자동 라벨에 적용해 Roboflow 업로드용 zip을 만든다.

01b_auto_label.ipynb 셀 8과 같은 일을 로컬에서 한다 (Colab 없이).

사용 예:
    python scripts/apply_corrections.py --auto ~/Downloads/autolabel_roboflow.zip \
        --corrections labeling/corrections.json --out ~/Downloads/autolabel_reviewed.zip

corrections.json 형식 (박스 번호는 검수 시트에 표시된 원래 번호):
    {"파일이름(확장자 없이)": {"drop": true}
                              또는 {"delete": [1, 2], "relabel": {"0": "giant_hornet"}}}
"""
import argparse
import glob
import json
import os
import shutil
import tempfile
import zipfile

NAMES = ["giant_hornet", "honeybee", "yellow_legged_hornet"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auto", required=True, help="autolabel_roboflow.zip 또는 압축을 푼 폴더")
    ap.add_argument("--corrections", required=True)
    ap.add_argument("--out", required=True, help="만들 zip 경로 (예: autolabel_reviewed.zip)")
    a = ap.parse_args()

    work = tempfile.mkdtemp()
    rev = os.path.join(work, "reviewed")
    if os.path.isdir(a.auto):
        shutil.copytree(a.auto, rev)
    else:
        zipfile.ZipFile(a.auto).extractall(rev)
    lab_dir, img_dir = os.path.join(rev, "train", "labels"), os.path.join(rev, "train", "images")
    assert os.path.isdir(lab_dir), f"{lab_dir} 가 없습니다. 01b가 만든 autolabel zip이 맞는지 확인하세요."

    corr = json.load(open(a.corrections, encoding="utf-8"))
    st = dict(dropped=0, box_deleted=0, relabeled=0, missing=0)

    def drop(stem):
        os.remove(os.path.join(lab_dir, stem + ".txt"))
        for ip in glob.glob(os.path.join(img_dir, stem + ".*")):
            os.remove(ip)
        st["dropped"] += 1

    for stem, c in corr.items():
        lp = os.path.join(lab_dir, stem + ".txt")
        if not os.path.exists(lp):
            st["missing"] += 1
            continue
        if c.get("drop"):
            drop(stem)
            continue
        lines = [l.split() for l in open(lp) if l.strip()]
        for i, cls in c.get("relabel", {}).items():
            if int(i) < len(lines):
                lines[int(i)][0] = str(NAMES.index(cls))
                st["relabeled"] += 1
        dele = {int(i) for i in c.get("delete", []) if int(i) < len(lines)}
        st["box_deleted"] += len(dele)
        lines = [l for i, l in enumerate(lines) if i not in dele]
        if not lines:                       # 박스를 모두 지웠으면 대상이 없는 사진이므로 제외
            drop(stem)
            continue
        with open(lp, "w") as fp:
            fp.write("\n".join(" ".join(l) for l in lines) + "\n")

    n_img = len(glob.glob(os.path.join(img_dir, "*")))
    out = os.path.abspath(os.path.expanduser(a.out))
    shutil.make_archive(os.path.splitext(out)[0], "zip", rev)
    shutil.rmtree(work)
    print(st, f"→ 남은 사진 {n_img}장 (Null 포함), 저장: {out}")


if __name__ == "__main__":
    main()
