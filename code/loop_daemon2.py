"""挖掘机闭环本地端（轻量版）——只做四件事，尽量少占 CPU。
优化点：
  · 用 Win32 BitBlt 只拷窗口那一块（不再每次全屏 3840x1080 拷贝）
  · 抓图周期 1 秒（agent 读一次约 3 秒，再密没意义）
  · 只写一个 jpg + 三个小文本，不攒帧
  · 窗口位置每 30 秒才重新量一次
用法:
  python loop_daemon2.py [COM3]
产出:
  E:\\Cache\\cam\\live.jpg    最近一帧（左上角带 #帧号 秒数）
  E:\\Cache\\cam\\inbox.txt   用户新说的话（读了不会自动删，自己按行数记）
  E:\\Cache\\cam\\state.txt   帧号+秒数
消费:
  E:\\Cache\\cam\\cmd.txt     写一行就是一条串口指令（发完自动清空）
"""
import ctypes
import ctypes.wintypes
import os
import sys
import time

from PIL import Image, ImageDraw, ImageFont

CAM = r"E:\Cache\cam"
LIVE = os.path.join(CAM, "live.jpg")
STATE = os.path.join(CAM, "state.txt")
INBOX = os.path.join(CAM, "inbox.txt")
CMD = os.path.join(CAM, "cmd.txt")
USER_TXT = r"C:\Users\橘猫猫！\Desktop\对话输入.txt"

INTERVAL = 1.0
SCALE_W = 200
RELOCATE_EVERY = 30

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


def find_phone():
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


def grab(box):
    l, t, r, b = box
    w, h = r - l, b - t
    if w <= 0 or h <= 0:
        return None
    hdc = user32.GetDC(0)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    gdi32.BitBlt(mem, 0, 0, w, h, hdc, l, t, 0x00CC0020)
    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth = w
    bi.biHeight = -h
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(0, hdc)
    return Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")


def main() -> int:
    os.makedirs(CAM, exist_ok=True)
    port = sys.argv[1] if len(sys.argv) > 1 else None
    ser = None
    if port:
        import serial
        ser = serial.Serial(port, 115200, timeout=0)

    for p in (CMD, INBOX, STATE):
        if not os.path.exists(p):
            open(p, "a", encoding="utf-8").close()
    if os.path.exists(USER_TXT):
        open(USER_TXT, "w", encoding="utf-8").close()

    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 20)
    box = None
    last_locate = 0.0
    last_size = 0
    cmd_seen = 0
    t0 = time.time()
    i = 0
    print("daemon up, port =", port, flush=True)

    while True:
        i += 1
        el = time.time() - t0

        if box is None or el - last_locate > RELOCATE_EVERY:
            w = find_phone()
            last_locate = el
            if w is None:
                print("[no-window] 等 PHONE 窗口", flush=True)
                time.sleep(2)
                continue
            l, t, r, b = w
            box = (l + 2, t + 34, r - 2, min(b - 2, 1080))

        try:
            img = grab(box)
            if img is not None:
                h = int(img.height * SCALE_W / img.width)
                img = img.resize((SCALE_W, h), 3)
                # 变化检测：跟上一帧比，几乎一样就不写盘、不叫醒 agent
                small = img.convert("L")
                if prev_gray is not None and small.size == prev_gray.size:
                    diff = ImageChops.difference(small, prev_gray)
                    hist = diff.histogram()
                    total = sum(hist) or 1
                    changed = sum(hist[CHANGE_THRESHOLD:]) / total
                    prev_gray = small
                    if changed < CHANGE_MIN:
                        skipped += 1
                        state_line = f"#{i:04d} {el:6.1f}s SKIP diff={changed:.3f}"
                        if skipped % 10 == 0:
                            print(f"[skip] {skipped} 帧无变化", flush=True)
                        with open(STATE, "w", encoding="utf-8") as f:
                            f.write(state_line + "\n")
                        process_text_and_cmd()
                        time.sleep(INTERVAL)
                        continue
                prev_gray = small
                d = ImageDraw.Draw(img)
                d.rectangle([0, 0, SCALE_W, 24], fill="black")
                d.text((3, 1), f"#{i:04d} {el:6.1f}s", font=font, fill="yellow")
                img.save(LIVE, quality=75)
                CHANGED.append(1)
        except Exception as e:
            print(f"[grab-fail] {e}", flush=True)

        try:
            if os.path.exists(USER_TXT):
                sz = os.path.getsize(USER_TXT)
                if sz != last_size:
                    txt = open(USER_TXT, encoding="utf-8", errors="ignore").read().strip()
                    open(USER_TXT, "w", encoding="utf-8").close()
                    last_size = 0
                    if txt:
                        with open(INBOX, "a", encoding="utf-8") as f:
                            f.write(f"[{time.strftime('%H:%M:%S')}] {txt}\n")
                        print(f"[in] {txt}", flush=True)
        except Exception as e:
            print(f"[txt-fail] {e}", flush=True)

        try:
            lines = [x.strip() for x in open(CMD, encoding="utf-8") if x.strip()]
            if len(lines) > cmd_seen:
                for line in lines[cmd_seen:]:
                    if ser:
                        ser.write((line + "\n").encode("utf-8"))
                        ser.flush()
                    print(f"[cmd] {line}", flush=True)
                cmd_seen = len(lines)
                if cmd_seen >= 20:
                    open(CMD, "w", encoding="utf-8").close()
                    cmd_seen = 0
        except Exception as e:
            print(f"[cmd-fail] {e}", flush=True)

        try:
            with open(STATE, "w", encoding="utf-8") as f:
                f.write(f"{i} {el:.1f}\n")
        except Exception:
            pass

        time.sleep(INTERVAL)


if __name__ == "__main__":
    raise SystemExit(main())
