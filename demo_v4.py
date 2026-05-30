#!/usr/bin/env python3
"""GPT-SoVITS v4 TTS Demo — Clean pretrained models, no v1 compatibility baggage."""

import os, sys
from pathlib import Path

PROJECT = Path(__file__).parent
GPT_SOVITS = PROJECT / "GPT-SoVITS"
PRETRAINED = GPT_SOVITS / "GPT_SoVITS" / "pretrained_models"

sys.path.insert(0, str(GPT_SOVITS))
sys.path.insert(0, str(GPT_SOVITS / "GPT_SoVITS"))
sys.path.insert(0, str(GPT_SOVITS / "GPT_SoVITS" / "eres2net"))

os.chdir(str(GPT_SOVITS))  # TTS expects cwd = GPT-SoVITS root

# Output to project root
OUTPUT_DIR = str(PROJECT)

# Monkey-patch transformers for torch 2.5
import torch
import transformers.modeling_utils as _mu
_mu.load_state_dict = lambda ckpt_files, **kw: torch.load(
    ckpt_files[0] if isinstance(ckpt_files, list) else ckpt_files,
    map_location="cpu", weights_only=False,
)


def main():
    from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config

    # Create dummy reference for API requirement
    import numpy as np
    import soundfile as sf
    ref_wav = "ref_dummy.wav"
    if not os.path.exists(ref_wav):
        sf.write(ref_wav, np.random.randn(int(16000 * 5)) * 0.001, 16000)
        with open("ref_text.txt", "w") as f:
            f.write("こんにちは")

    config = TTS_Config({
        "custom": {
            "device": "cuda",
            "is_half": True,
            "version": "v4",
            "t2s_weights_path": str(PRETRAINED / "s1v3.ckpt"),
            "vits_weights_path": str(PRETRAINED / "gsv-v4-pretrained" / "s2Gv4.pth"),
            "bert_base_path": str(PRETRAINED / "chinese-roberta-wwm-ext-large"),
            "cnhuhbert_base_path": str(PRETRAINED / "chinese-hubert-base"),
        }
    })

    print("Loading v4 models (GPT + SoVITS + BERT + CNHuBERT + BigVGAN)...")
    tts = TTS(config)
    print("TTS engine ready!")

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="こんにちは、今日もいい天気ですね。")
    parser.add_argument("--output", default="v4_demo.wav")
    parser.add_argument("--no-play", action="store_true")
    args = parser.parse_args()

    print(f"\nSynthesizing: '{args.text}'")
    gen = tts.run({
        "text": args.text,
        "text_lang": "ja",
        "ref_audio_path": ref_wav,
        "prompt_text": "こんにちは",
        "prompt_lang": "ja",
        "top_k": 5, "top_p": 1.0, "temperature": 1.0,
        "text_split_method": "cut0", "batch_size": 1,
        "speed_factor": 1.0, "streaming_mode": False,
    })

    result = None
    for step in gen:
        result = step
        if isinstance(result, tuple) and len(result) == 2:
            sr, audio = result
            print(f"\r  {len(audio)/sr:.1f}s...", end="", flush=True)

    if result is None:
        print("ERROR: no output")
        return

    sr, audio = result
    output_path = os.path.join(OUTPUT_DIR, args.output)
    sf.write(output_path, audio, sr)
    print(f"\rSaved: {output_path} ({len(audio)/sr:.1f}s, {sr}Hz)")

    if not args.no_play:
        import sounddevice as sd
        print("Playing...")
        sd.play(audio, sr)
        sd.wait()


if __name__ == "__main__":
    main()
