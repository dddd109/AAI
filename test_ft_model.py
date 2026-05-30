#!/usr/bin/env python3
"""Test the fine-tuned VITS 莲华 model locally."""

import sys, json, torch, os
from pathlib import Path

PROJECT = Path(__file__).parent
sys.path.insert(0, str(PROJECT / "vits_infer"))

import commons
from models import SynthesizerTrn
from text import text_to_sequence

# ── Config ──
MODEL_PATH = PROJECT / "moe_tts_models" / "slot4" / "renge_ft_final.pth"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Device: {DEVICE}")
print(f"Model: {MODEL_PATH}")

# Load
ckpt = torch.load(str(MODEL_PATH), map_location="cpu", weights_only=False)
hps = ckpt["hps"]
symbols = hps["symbols"]

model = SynthesizerTrn(
    len(symbols),
    hps["data"]["filter_length"] // 2 + 1,
    hps["train"]["segment_size"] // hps["data"]["hop_length"],
    n_speakers=hps["data"]["n_speakers"],
    **hps["model"],
)
model.load_state_dict(ckpt["model"], strict=False)
model = model.to(DEVICE).eval()
print(f"Model: {sum(p.numel() for p in model.parameters())/1e6:.1f}M params")
print(f"Speakers: {hps['data']['n_speakers']}")
print(f"Sample rate: {hps['data']['sampling_rate']} Hz")

# ── Synthesize ──
test_texts = [
    "こんにちは、私は蓮華です。よろしくお願いします。",
    "ふん…何か用か？",
    "マスター、そろそろ休んだらどうだ。",
    "おやすみなさい、また明日会いましょう。",
]

import soundfile as sf
import sounddevice as sd

for i, text in enumerate(test_texts):
    print(f"\n[{i+1}/4] {text[:50]}...")

    seq = text_to_sequence(text, symbols, hps["data"]["text_cleaners"])
    if hps["data"]["add_blank"]:
        seq = commons.intersperse(seq, 0)

    x = torch.LongTensor(seq).unsqueeze(0).to(DEVICE)
    x_len = torch.LongTensor([len(seq)]).to(DEVICE)
    sid = torch.LongTensor([0]).to(DEVICE)  # 莲华 = speaker 0

    with torch.no_grad():
        audio = model.infer(
            x, x_len, sid=sid,
            noise_scale=0.667, noise_scale_w=0.8, length_scale=1.0,
        )[0][0, 0].cpu().float().numpy()

    sr = hps["data"]["sampling_rate"]
    out = str(PROJECT / f"test_ft_{i+1}.wav")
    sf.write(out, audio, sr)
    print(f"  Saved: {out} ({len(audio)/sr:.1f}s)")

    # Play
    sd.play(audio, samplerate=sr)
    sd.wait()

print("\n✅ All tests complete! Check the wav files.")
