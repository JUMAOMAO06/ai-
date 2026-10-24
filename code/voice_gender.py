"""判断一段音频里说话人的性别倾向（按基频中位数，分段输出）。
用法: python voice_gender.py <音频> [窗口秒=6]
注意: 这是声学估计，不是鉴定；童声、假声、变声器都会误判。
"""
import sys

import librosa
import numpy as np


def classify(med: float) -> str:
    if med < 145:
        return "偏男声"
    if med < 175:
        return "偏低/中性"
    return "偏女声"


def main() -> int:
    path = sys.argv[1]
    win = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    y, sr = librosa.load(path, sr=16000, mono=True)
    total = len(y) / sr
    rows = []
    t = 0.0
    while t < total:
        seg = y[int(t * sr):int((t + win) * sr)]
        if len(seg) < sr:
            break
        f0, _, _ = librosa.pyin(seg, fmin=70, fmax=400, sr=sr, frame_length=1024)
        vals = f0[~np.isnan(f0)]
        if len(vals) >= 10:
            med = float(np.median(vals))
            rows.append((t, med, classify(med), float(np.percentile(vals, 90))))
        else:
            rows.append((t, 0.0, "无浊音", 0.0))
        t += win
    for start, med, label, p90 in rows:
        if med:
            print(f"[{start:6.1f}-{start + win:6.1f}] 基频中位 {med:6.1f}Hz  p90 {p90:6.1f}Hz  {label}")
        else:
            print(f"[{start:6.1f}-{start + win:6.1f}] （这一段没有稳定的浊音）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
