"""0.7 秒一张，覆盖写 live.jpg，跑 60 秒。agent 反复读 live.jpg 即看到最新画面。"""
import ctypes
import ctypes.wintypes
import time

from PIL import ImageGrab

OUT = r"E:\Cache\cam\live.jpg"
DURATION = 60
INTERVAL = 0.7
SCALE_W = 280


def find_phone():
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, _):
        n = user32.GetWindowTextLengthW(h)
        if n:
            b = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, b, n + 1)
            if "PHONE" in b.value and user32.IsWindowVisible(h):
                r = ctypes.wintypes.RECT()
                user32.GetWindowRect(h, ctypes.byref(r))
                found.append((r.left, r.top, r.right, r.bottom))
        return True

    user32.EnumWindows(cb, 0)
    return found[0] if found else None


def main() -> int:
    box0 = find_phone()
    if not box0:
        print("no PHONE window")
        return 1
    l, t, r, b = box0
    box = (l + 2, t + 34, r - 2, min(b - 2, 1080))
    print("box", box, flush=True)
    t0 = time.time()
    i = 0
    while time.time() - t0 < DURATION:
        i += 1
        img = ImageGrab.grab(bbox=box)
        h = int(img.height * SCALE_W / img.width)
        img.resize((SCALE_W, h), 3).save(OUT, quality=75)
        print(i, round(time.time() - t0, 2), flush=True)
        time.sleep(INTERVAL)
    print("done", i)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
