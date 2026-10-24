"""常驻的"嘴"：监听 say.txt，每出现新行就 TTS 播出来。
用法: python say_loop.py
  往 E:\Cache\cam\say.txt 里追加一行，就会念出来。
  每行格式: 文本            (格式 "角色|文本" 也兼容，只念文本部分)
"""
import io
import os
import queue
import sys
import threading
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import sounddevice as sd
import torch
from qwen_tts import Qwen3TTSModel

MODEL = r"E:\qwen-tts\models\Qwen3-TTS-12Hz-1.7B-CustomVoice"
SAY = r"E:\Cache\cam\say.txt"
SPEAKER = os.environ.get("SPEAKER", "Vivian")
INSTRUCT = os.environ.get("INSTRUCT", "语速稍快，节奏紧凑，像在实时汇报")
SR = 24000

say_q: "queue.Queue[str]" = queue.Queue()


def split_short(text: str, limit: int = 24):
    parts, cur = [], ""
    for ch in text:
        cur += ch
        if ch in "。！？!?，,；;" and len(cur) >= limit:
            parts.append(cur)
            cur = ""
    if cur.strip():
        parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def speaker_thread(model):
    while True:
        text = say_q.get()
        if text is None:
            break
        try:
            for piece in split_short(text):
                wavs, sr = model.generate_custom_voice(
                    text=piece, speaker=SPEAKER, instruct=INSTRUCT
                )
                wav = wavs[0]
                if isinstance(wav, torch.Tensor):
                    wav = wav.detach().float().cpu().numpy()
                wav = np.asarray(wav, dtype=np.float32).reshape(-1)
                # 句尾补 0.2 秒的"气"，不然收得太短促
                wav = np.concatenate([wav, np.zeros(int(sr * 0.2), dtype=np.float32)])
                sd.play(wav, sr)
                sd.wait()
            print(f"[say] {text}", flush=True)
        except Exception as e:
            print(f"[say-fail] {e}", flush=True)


def main() -> int:
    os.makedirs(os.path.dirname(SAY), exist_ok=True)
    if not os.path.exists(SAY):
        open(SAY, "a", encoding="utf-8").close()

    model = Qwen3TTSModel.from_pretrained(MODEL, device_map="cuda:0", dtype=torch.bfloat16)
    print("# 嘴就绪", flush=True)

    t = threading.Thread(target=speaker_thread, args=(model,), daemon=True)
    t.start()

    seen = 0
    while True:
        try:
            with open(SAY, encoding="utf-8") as f:
                lines = [l.rstrip("\n") for l in f if l.strip()]
        except Exception:
            lines = []
        if len(lines) > seen:
            batch = lines[seen:]
            for line in batch:
                text = line.split("|", 1)[-1].strip()
                if text:
                    say_q.put(text)
            seen = len(lines)
            # 念完这一批就把它们从文件里删掉，别一直堆着
            try:
                rest = lines[len(batch):]
                with open(SAY, "w", encoding="utf-8") as f:
                    if rest:
                        f.write("\n".join(rest) + "\n")
                seen = len(rest)
            except Exception as e:
                print(f"[trim-fail] {e}", flush=True)
        time.sleep(0.3)


if __name__ == "__main__":
    raise SystemExit(main())
