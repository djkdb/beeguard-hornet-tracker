#!/usr/bin/env python3
"""추적 영상 준비·공유용 도구 (ffmpeg 필요).

1) 여러 클립을 잘라 하나의 테스트 영상으로 잇기
    python scripts/video_tools.py cut --clip videos/clips/bees.mp4 3 5 \
        --clip videos/clips/hornet.mp4 10 5 --out videos/clips/test.mp4
    (--clip 경로 시작초 길이초, 여러 번 지정 가능. 해상도·fps를 맞춰 이어 붙임)

2) 결과 영상을 브라우저·GitHub에서 재생되는 H.264로 변환
    python scripts/video_tools.py h264 videos/beeguard_tracking.mp4 videos/beeguard_tracking_h264.mp4

3) README용 GIF 만들기
    python scripts/video_tools.py gif videos/beeguard_tracking_h264.mp4 results/demo.gif --width 640 --fps 10
"""
import argparse
import os
import shutil
import subprocess
import tempfile


def run(cmd):
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def need_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg가 필요합니다. Colab에는 기본으로 설치되어 있습니다.")


def cmd_cut(a):
    need_ffmpeg()
    vf = (f"scale={a.width}:{a.height}:force_original_aspect_ratio=decrease,"
          f"pad={a.width}:{a.height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={a.fps},format=yuv420p")
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, (path, start, dur) in enumerate(a.clip):
            out = os.path.join(tmp, f"part{i:02d}.mp4")
            run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(start), "-t", str(dur), "-i", path,
                 "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", out])
            parts.append(out)
        listfile = os.path.join(tmp, "list.txt")
        with open(listfile, "w") as f:
            f.writelines(f"file '{p}'\n" for p in parts)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", a.out])
    print("완성:", a.out)


def cmd_h264(a):
    need_ffmpeg()
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.src, "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-preset", "veryfast", "-crf", "20", "-movflags", "+faststart", "-an", a.dst])
    print("완성:", a.dst)


def cmd_gif(a):
    need_ffmpeg()
    vf = (f"fps={a.fps},scale={a.width}:-1:flags=lanczos,split[s0][s1];"
          "[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer")
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.src, "-vf", vf, a.dst])
    print("완성:", a.dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("cut", help="클립을 잘라 이어 붙이기")
    c.add_argument("--clip", nargs=3, action="append", required=True, metavar=("PATH", "START", "DUR"))
    c.add_argument("--out", required=True)
    c.add_argument("--width", type=int, default=1280)
    c.add_argument("--height", type=int, default=720)
    c.add_argument("--fps", type=int, default=30)
    c.set_defaults(func=cmd_cut)

    h = sub.add_parser("h264", help="H.264로 변환")
    h.add_argument("src")
    h.add_argument("dst")
    h.set_defaults(func=cmd_h264)

    g = sub.add_parser("gif", help="GIF 만들기")
    g.add_argument("src")
    g.add_argument("dst")
    g.add_argument("--width", type=int, default=640)
    g.add_argument("--fps", type=int, default=10)
    g.set_defaults(func=cmd_gif)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
