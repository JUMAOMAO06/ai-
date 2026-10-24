"""挖掘机闭环的本地端：一条龙。
做四件事，全部在本地进程里，不让 agent 为它们各跑一次工具调用：
  1. 定时抓 PHONE 窗口 -> E:\\Cache\\cam\\live.jpg（缩到 200 宽）
  2. 盯 对话输入.txt 的大小，一变就把新增行写进 E:\\Cache\\cam\\inbox.txt 并清空该文件
  3. 盯 cmd.txt，有新行就通过串口发出去（没给端口就跳过，只记录）
  4. 把心跳写进 state.txt（帧号 / 时间），方便 agent 判断自己是否落后
用法:
  python loop_daemon.py [COM3]        # 不给端口就只抓图+收文本
"""
import ctypes
import ctypes.wintypes
import os
import sys
import time

from PIL import ImageDraw, ImageFont, ImageGrab

CAM = r"E:\Cache\cam"
LIVE = os.path.join(CAM, "live.jpg")
STATE = os.path.join(CAM, "state.txt")
INBOX = os.path.join(CAM, "inbox.txt")
CMD = os.path.join(CAM, "cmd.txt")
USER_TXT = r"C:\Users\橘猫猫！\Desktop\对话输入.txt"

INTERVAL = 0.5
SCALE_W = 200


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
    os.makedirs(CAM, exist_ok=True)
    port = sys.argv[1] if len(sys.argv) > 1 else None
    ser = None
    if port:
        import serial
        ser = serial.Serial(port, 115200, timeout=0)

    box0 = find_phone()
    if not box0:
        print("no PHONE window", flush=True)
        return 1
    l, t, r, b = box0
    box = (l + 2, t + 34, r - 2, min(b - 2, 1080))
    print("box", box, "port", port, flush=True)

    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)

    # 文本基线
    last_size = os.path.getsize(USER_TXT) if os.path.exists(USER_TXT) else 0
    if os.path.exists(USER_TXT):
        open(USER_TXT, "w", encoding="utf-8").close()
        last_size = 0
    cmd_seen = 0
    if not os.path.exists(CMD):
        open(CMD, "a", encoding="utf-8").close()
    if not os.path.exists(INBOX):
        open(INBOX, "a", encoding="utf-8").close()

    t0 = time.time()
    i = 0
    while True:
        i += 1
        el = time.time() - t0
        try:
            img = ImageGrab.grab(bbox=box)
            h = int(img.height * SCALE_W / img.width)
            img = img.resize((SCALE_W, h), 3)
            d = ImageDraw.Draw(img)
            d.rectangle([0, 0, SCALE_W, 26], fill="black")
            d.text((4, 2), f"#{i:04d} {el:6.1f}s", font=font, fill="yellow")
            img.save(LIVE, quality=78)
        except Exception as e:
            print(f"[grab-fail] {e}", flush=True)

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
                if cmd_seen > 50:
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
