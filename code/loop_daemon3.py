"""挖掘机闭环本地端 v3：抓图 + 帧差过滤 + 收文本 + 发指令。
设计目标：不叫醒 agent 的部分全在本地做掉。
  · BitBlt 只拷窗口那一块（0.015 秒）
  · 帧差 < 1.5% 变化像素 -> 判定"没动"，不写 live.jpg，只更新 state.txt
  · 对话输入.txt 有变化 -> 追加到 inbox.txt 并清空原文件
  · cmd.txt 有新行 -> 走串口发出去（没端口就只打印）
用法: python loop_daemon3.py [COM3]
"""
import ctypes
import ctypes.wintypes
import os
import sys
import time

from PIL import Image, ImageChops, ImageDraw, ImageFont

CAM = r"E:\Cache\cam"
LIVE = os.path.join(CAM, "live.jpg")
STATE = os.path.join(CAM, "state.txt")
INBOX = os.path.join(CAM, "inbox.txt")
CMD = os.path.join(CAM, "cmd.txt")
USER_TXT = r"C:\Users\橘猫猫！\Desktop\对话输入.txt"

INTERVAL = 1.0
SCALE_W = 200
RELOCATE_EVERY = 30
CHANGE_MIN = 0.015      # 变化像素占比低于它就当没动
BLACK_LEVEL = 24        # 单像素亮度差超过它才算"变了"

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
    last_locate = -999.0
    prev_gray = None
    last_size = 0
    cmd_seen = 0
    skipped = 0
    saved = 0
    t0 = time.time()
    i = 0
    print("daemon v3 up, port =", port, flush=True)

    while True:
        i += 1
        el = time.time() - t0

        if box is None or el - last_locate > RELOCATE_EVERY:
            w = find_phone()
            last_locate = el
            if w is None:
                if i % 20 == 1:
                    print("[no-window] 等 PHONE 窗口", flush=True)
                time.sleep(2)
                continue
            l, t, r, b = w
            box = (l + 2, t + 34, r - 2, min(b - 2, 1080))
            prev_gray = None

        raw = None
        try:
            raw = grab(box)
        except Exception as e:
            print(f"[grab-fail] {e}", flush=True)

        if raw is not None:
            h = int(raw.height * SCALE_W / raw.width)
            small = raw.resize((SCALE_W, h), 3)
            gray = small.convert("L")
            moved = True
            ratio = 1.0
            if prev_gray is not None and gray.size == prev_gray.size:
                diff = ImageChops.difference(gray, prev_gray)
                hist = diff.histogram()
                total = sum(hist) or 1
                ratio = sum(hist[BLACK_LEVEL:]) / total
                moved = ratio >= CHANGE_MIN
            prev_gray = gray

            if moved:
                saved += 1
                d = ImageDraw.Draw(small)
                d.rectangle([0, 0, SCALE_W, 24], fill="black")
                d.text((3, 1), f"#{i:04d} {el:6.1f}s", font=font, fill="yellow")
                small.save(LIVE, quality=75)
            else:
                skipped += 1

            try:
                with open(STATE, "w", encoding="utf-8") as f:
                    f.write(f"#{i:04d} {el:6.1f}s {'MOVED' if moved else 'SAME'} "
                            f"diff={ratio:.3f} saved={saved} skipped={skipped}\n")
            except Exception:
                pass

        # 用户文本
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

        # 指令
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

        time.sleep(INTERVAL)


if __name__ == "__main__":
    raise SystemExit(main())
