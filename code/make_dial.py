"""生成 A4 (300dpi) 的角度刻度盘，打印出来给挖掘机/车当视觉量角器。
用法: python make_dial.py [输出路径=E:\\Cache\\cam\\dial_a4.png]
要点: 每 15° 一个刻度，每 30° 一个大数字；字体粗、对比高，方便图传糊了也能认。
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 2480, 3508          # A4 @300dpi
OUT = sys.argv[1] if len(sys.argv) > 1 else r"E:\Cache\cam\dial_a4.png"
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\ariblk.ttf",
    r"C:\Windows\Fonts\seguisb.ttf",
]

def load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main() -> int:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    R = 1000

    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline="black", width=8)
    d.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill="black")

    f_big = load_font(150)
    f_mid = load_font(90)

    for deg in range(0, 360, 5):
        # 屏幕上：0° 指正上方，顺时针增大
        a = math.radians(deg - 90)
        if deg % 30 == 0:
            inner, width = R - 130, 12
        elif deg % 15 == 0:
            inner, width = R - 90, 9
        else:
            inner, width = R - 45, 5
        x1, y1 = cx + inner * math.cos(a), cy + inner * math.sin(a)
        x2, y2 = cx + R * math.cos(a), cy + R * math.sin(a)
        d.line([x1, y1, x2, y2], fill="black", width=width)

    for deg in range(0, 360, 30):
        a = math.radians(deg - 90)
        f = f_big if deg % 90 == 0 else f_mid
        label = f"{deg}"
        tx = cx + (R - 260) * math.cos(a)
        ty = cy + (R - 260) * math.sin(a)
        bbox = d.textbbox((0, 0), label, font=f)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text((tx - tw / 2, ty - th / 2 - bbox[1]), label, font=f, fill="black")

    # 中心指南针：正上方一个粗箭头（0° 参考）
    d.polygon([(cx, cy - 300), (cx - 45, cy - 190), (cx + 45, cy - 190)], fill="black")

    img.save(OUT, dpi=(300, 300))
    print(OUT, img.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
