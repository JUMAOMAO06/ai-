"""0.5 秒一张，跑 180 秒，只截左侧 PHONE 窗口区域，存 jpg + 时间戳。"""
import csv
import os
import time

from PIL import ImageGrab

OUT = r"E:\Cache\cam\loop"
BOX = (0, 0, 420, 620)
DURATION = 180
INTERVAL = 0.5


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".jpg"):
            os.remove(os.path.join(OUT, f))

    rows = []
    t0 = time.time()
    i = 0
    while time.time() - t0 < DURATION:
        i += 1
        img = ImageGrab.grab(bbox=BOX)
        name = f"f_{i:04d}.jpg"
        img.save(os.path.join(OUT, name), quality=85)
        rows.append((i, time.strftime("%H:%M:%S"), name))
        time.sleep(INTERVAL)

    with open(os.path.join(OUT, "frames.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "time", "file"])
        w.writerows(rows)
    print(f"done frames={i}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
