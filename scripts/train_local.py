"""02_train.ipynb의 학습·평가·분석(셀 3, 5, 6, 7, 8)을 Colab 없이 내 PC에서 그대로 실행합니다.

노트북 셀의 코드를 읽어 와서 실행하므로, 결과 파일은 Colab에서 돌린 것과 같습니다.
  - models/best.pt, results/experiments.csv, results/<실험>/ (학습 곡선, 혼동 행렬)
  - results/test_confusion_counts.csv, results/failure_cases.csv, results/failure_cases.jpg
  - train_outputs.zip (위 파일 묶음, 저장소 폴더에 생성)

사용법 (저장소 폴더에서):
    python scripts/train_local.py --data C:/beeguard/dataset --run n640 --epochs 50
    python scripts/train_local.py --data ~/beeguard/dataset --run n320 --epochs 12 --patience 4   # GPU가 없을 때
"""
import argparse
import json
import os
import sys
import zipfile

KEYS = ["셀 3:", "셀 5:", "셀 6:", "셀 7:", "셀 8:"]


def load_cells(repo):
    nb = json.load(open(os.path.join(repo, "notebooks", "02_train.ipynb"), encoding="utf-8"))
    cells = {}
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        src = c["source"] if isinstance(c["source"], str) else "".join(c["source"])
        first = src.split("\n", 1)[0]
        for k in KEYS:
            if k in first:
                cells[k] = src
    missing = [k for k in KEYS if k not in cells]
    if missing:
        sys.exit(f"02_train.ipynb에서 셀을 찾지 못했습니다: {missing}")
    return cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dataset_split.zip을 푼 폴더 (data.yaml, train/valid/test가 있는 곳)")
    ap.add_argument("--run", nargs="+", default=["n640"], help="돌릴 실험 이름 (02 노트북 셀 5의 EXPERIMENTS)")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--patience", type=int, default=10)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ds = os.path.abspath(os.path.expanduser(a.data)).replace("\\", "/")
    if not os.path.exists(os.path.join(ds, "data.yaml")):
        sys.exit(f"{ds}/data.yaml이 없습니다. dataset_split.zip을 푼 폴더를 --data로 주세요.")
    cells = load_cells(repo)
    cells["셀 3:"] = cells["셀 3:"].replace('DS = "/content/dataset"', f"DS = {ds!r}")
    cells["셀 8:"] = cells["셀 8:"].replace("from IPython.display import display", "display = print")

    g = {"__name__": "__notebook__", "os": os, "REPO": repo, "PROJECT": os.path.join(repo, "runs")}
    os.makedirs(g["PROJECT"], exist_ok=True)
    exec(cells["셀 3:"], g)
    exec(cells["셀 5:"], g)
    unknown = [r for r in a.run if r not in g["EXPERIMENTS"]]
    if unknown:
        sys.exit(f"없는 실험 이름: {unknown}. 고를 수 있는 것: {list(g['EXPERIMENTS'])}")
    g["EPOCHS"], g["PATIENCE"], g["RUN"] = a.epochs, a.patience, a.run
    print(f"실험 {a.run}, epochs {a.epochs}, patience {a.patience}")
    for k in ["셀 6:", "셀 7:", "셀 8:"]:
        print(f"\n===== {k} 실행 =====")
        exec(cells[k], g)

    out = os.path.join(repo, "train_outputs.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(repo, "models", "best.pt"), "models/best.pt")
        for root, _, fs in os.walk(os.path.join(repo, "results")):
            for f in fs:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, repo))
    print(f"\n완료: {out} ({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":   # Windows에서 데이터 로더가 프로세스를 새로 띄울 때 학습이 다시 시작되지 않도록
    main()
