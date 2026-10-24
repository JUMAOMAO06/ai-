"""挖掘机串口控制（PC 侧）——多通道并发。
协议（行文本，ESP32 一行一条读；缺省值补 0）：
  C <行走 -100..100> <回转 -100..100> <臂 -100..100> <斗 -100..100> <毫秒>
      例: C 40 0 -20 15 400      # 前进 40%、回转不动、臂抬 20%、斗收 15%、持续 400ms
  S                              立刻全停
  ARM                            解锁
  P                              查状态
  兼容旧式: M <油门> <转向> <毫秒>  == C <油门> <转向> 0 0 <毫秒>
说明:
  · 每路单独标定：行走看位移，回转看角度，臂/斗看行程或角度
  · 板子必须做超时兜底：超过 <毫秒>+200ms 没收到下一条，全部归零
用法:
  python rover_ctl.py list
  python rover_ctl.py COM3 C 40 0 -20 15 400
  python rover_ctl.py COM3 S
"""
import sys
import time

import serial
from serial.tools import list_ports


def do_list() -> int:
    ports = list(list_ports.comports())
    if not ports:
        print("没有发现串口。检查 USB 线、驱动（CH340/CP210x）")
        return 1
    for p in ports:
        print(f"{p.device}  {p.description}  {p.hwid}")
    return 0


def clamp(v: int) -> int:
    return max(-100, min(100, v))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if sys.argv[1] == "list":
        return do_list()

    port = sys.argv[1]
    rest = sys.argv[2:]
    if not rest:
        print("缺指令")
        return 2

    cmd = rest[0].upper()
    if cmd == "C":
        if len(rest) < 5:
            print("用法: C <行走> <回转> <臂> <斗> <毫秒>")
            return 2
        walk = clamp(int(rest[1]))
        turn = clamp(int(rest[2]))
        arm = clamp(int(rest[3]))
        bucket = clamp(int(rest[4]))
        ms = max(1, min(5000, int(rest[5]) if len(rest) > 5 else 400))
        line = f"C {walk} {turn} {arm} {bucket} {ms}"
    elif cmd == "M":
        if len(rest) < 4:
            print("用法: M <油门> <转向> <毫秒>")
            return 2
        walk = clamp(int(rest[1]))
        turn = clamp(int(rest[2]))
        ms = max(1, min(5000, int(rest[3])))
        line = f"C {walk} {turn} 0 0 {ms}"
    else:
        line = " ".join(rest)

    with serial.Serial(port, 115200, timeout=2) as ser:
        time.sleep(0.2)
        ser.write((line.strip() + "\n").encode("utf-8"))
        ser.flush()
        time.sleep(0.05)
        try:
            back = ser.readline().decode("utf-8", "ignore").strip()
        except Exception:
            back = ""
        print(f">> {line}" + (f"   << {back}" if back else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
