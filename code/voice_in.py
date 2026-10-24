"""语音输入通道：一直听着，一句话说完就自动转写，落成 txt 给 agent 读。
用法:
  python voice_in.py [输出目录=E:\\Cache\\voice] [模型=small]
产物:
  <输出目录>\\inbox.md      —— 追加式，一行一句（读完别删，靠行号或偏移区分）
  <输出目录>\\last.wav      —— 最近一句的原始音频
说明:
  · VAD 断句：连续 0.8 秒没声音就算一句结束；单句最短 0.3 秒、最长 15 秒
  · 首次运行会加载 whisper 模型（已经下载过就快）
"""
import os
import queue
import sys
import time
import wave

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

RATE = 16000
FRAME_MS = 30
FRAME = RATE * FRAME_MS // 1000


def write_wav(path: str, pcm: np.ndarray) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.astype(np.int16).tobytes())


def main() -> int:
    outdir = sys.argv[1] if len(sys.argv) > 1 else r"E:\Cache\voice"
    size = sys.argv[2] if len(sys.argv) > 2 else "small"
    os.makedirs(outdir, exist_ok=True)
    inbox = os.path.join(outdir, "inbox.md")
    last_wav = os.path.join(outdir, "last.wav")

    vad = webrtcvad.Vad(2)
    q: "queue.Queue[bytes]" = queue.Queue()

    def cb(indata, frames, t, status):
        q.put(bytes(indata))

    print(f"# 监听中 -> {outdir}  模型 {size}", flush=True)
    model = WhisperModel(size, device="cpu", compute_type="int8")
    print("# 模型就绪", flush=True)

    with sd.RawInputStream(samplerate=RATE, blocksize=FRAME, dtype="int16",
                           channels=1, callback=cb):
        buf = []
        voiced = 0
        silence = 0
        speaking = False
        total = 0
        silent_limit = int(0.8 * 1000 / FRAME_MS)
        min_frames = int(0.3 * 1000 / FRAME_MS)
        max_frames = int(15.0 * 1000 / FRAME_MS)
        while True:
            chunk = q.get()
            if len(chunk) < FRAME * 2:
                continue
            is_speech = vad.is_speech(chunk, RATE)
            buf.append(chunk)
            total += 1
            if is_speech:
                speaking = True
                silence = 0
                voiced += 1
            elif speaking:
                silence += 1
            if speaking and (silence >= silent_limit or total >= max_frames):
                if voiced >= min_frames:
                    pcm = b"".join(buf[-total:])
                    write_wav(last_wav, np.frombuffer(pcm, dtype=np.int16))
                    segs, _ = model.transcribe(last_wav, language="zh", vad_filter=False)
                    text = " ".join(s.text.strip() for s in segs).strip()
                    if text:
                        stamp = time.strftime("%H:%M:%S")
                        with open(inbox, "a", encoding="utf-8") as f:
                            f.write(f"- [{stamp}] {text}\n")
                        print(f"[{stamp}] {text}", flush=True)
                buf = []
                voiced = 0
                silence = 0
                speaking = False
                total = 0
            if total > max_frames * 2:
                buf = buf[-max_frames:]
                total = len(buf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
