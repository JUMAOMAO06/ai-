"""图传抓帧：定时从 rtsp/mjpeg/http 流里抓一帧，只留最新那张。
用法:
  python cam_grab.py <url> [间隔秒=3] [输出目录=E:\\Cache\\cam] [取几张=0]
    url 例: rtsp://192.168.4.1:8554/video  http://192.168.4.1:8080/?action=stream
    取几张=0 表示一直跑；>0 表示抓这么多张就退出。
读图时读 <输出目录>\\latest.jpg 即可。
"""
import os
import subprocess
import sys
import time

FFMPEG = r"E:\sd\ffmpeg\bin\ffmpeg.exe"


def grab(url: str, out: str) -> bool:
    tmp = out + ".tmp.jpg"
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-rtsp_transport", "tcp", "-i", url,
        "-frames:v", "1", "-q:v", "3", tmp,
    ]
    try:
        subprocess.run(cmd, timeout=20, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return False
    if os.path.exists(tmp) and os.path.getsize(tmp) > 1024:
        os.replace(tmp, out)
        return True
    return False


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python cam_grab.py <url> [间隔秒] [输出目录] [取几张]")
        return 2
    url = sys.argv[1]
    every = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    outdir = sys.argv[3] if len(sys.argv) > 3 else r"E:\Cache\cam"
    count = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    os.makedirs(outdir, exist_ok=True)
    latest = os.path.join(outdir, "latest.jpg")
    done = 0
    while True:
        ok = grab(url, latest)
        stamp = time.strftime("%H:%M:%S")
        print(f"[{stamp}] {'OK' if ok else 'FAIL'} -> {latest}", flush=True)
        done += 1
        if count and done >= count:
            break
        time.sleep(max(0.5, every))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
