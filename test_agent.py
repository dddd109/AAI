#!/usr/bin/env python3
"""
莲华 Agent 体验测试 — 文本输入 → 莲华语音回复 + 字幕

用法:
    .venv/Scripts/python.exe test_agent.py
    .venv/Scripts/python.exe test_agent.py --text "こんにちは"
    .venv/Scripts/python.exe test_agent.py --no-subtitle
"""

import argparse, sys, time, threading, json, random
from pathlib import Path

PROJECT = Path(__file__).parent
sys.path.insert(0, str(PROJECT / "src"))

# ── 模拟 LLM 回复（无 API key 也能用）──
FALLBACKS = [
    {
        "jp_text": "ふん…呼んだか？用があるならさっさと言え",
        "zh_text": "哼…你叫我？有事就快说",
        "emotion": "neutral",
    },
    {
        "jp_text": "こんにちは。今日はいい天気だな…別に嬉しくないけど",
        "zh_text": "你好。今天天气不错…不过我并不高兴",
        "emotion": "teasing",
    },
    {
        "jp_text": "何を見てるんだ？私の顔に何かついてるか？",
        "zh_text": "你在看什么？我脸上有东西吗？",
        "emotion": "angry",
    },
    {
        "jp_text": "マスター、そろそろ休んだらどうだ。無理すると後で後悔するぞ",
        "zh_text": "主人，差不多该休息了吧。硬撑的话回头会后悔的哦",
        "emotion": "sad",
    },
    {
        "jp_text": "あら、私に話しかけるなんて珍しいな。どうした？",
        "zh_text": "哎呀，居然会找我说话，真少见。怎么了？",
        "emotion": "surprised",
    },
    {
        "jp_text": "ふふ…なかなか面白いことを言うじゃないか",
        "zh_text": "呵呵…你说的话还挺有意思的嘛",
        "emotion": "happy",
    },
]


def call_llm(text: str) -> dict:
    """Try real LLM, fall back to canned responses."""
    try:
        import yaml
        with open("config.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        from llm_client import LLMClient
        llm = LLMClient("config.yaml")
        return llm.chat(text)
    except Exception:
        pass

    # Fallback: pick a response based on text content
    idx = hash(text) % len(FALLBACKS)
    return FALLBACKS[idx]


def show_subtitle(jp_text: str, zh_text: str, emotion: str):
    """Try tkinter subtitle, fall back to console."""
    try:
        import tkinter as tk

        root = tk.Tk()
        root.title("莲华")
        root.geometry("800x140+560+680")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.88)
        root.configure(bg="#1a1a2e")

        colors = {
            "neutral": "#FFFFFF", "happy": "#FFD700", "angry": "#FF6B6B",
            "sad": "#87CEEB", "surprised": "#FFA500", "teasing": "#FF69B4",
        }
        color = colors.get(emotion, "#FFFFFF")

        frame = tk.Frame(root, bg="#1a1a2e", padx=20, pady=10)
        frame.pack(fill="both", expand=True)

        jp = tk.Label(frame, text=jp_text, font=("Yu Gothic", 20, "bold"),
                       fg=color, bg="#1a1a2e", anchor="w", wraplength=760)
        jp.pack(fill="x", pady=(5, 2))

        zh = tk.Label(frame, text=zh_text, font=("Microsoft YaHei", 16),
                       fg="#CCCCCC", bg="#1a1a2e", anchor="w", wraplength=760)
        zh.pack(fill="x", pady=(2, 2))

        em = tk.Label(frame, text=f"[{emotion}]", font=("Consolas", 10),
                       fg="#888888", bg="#1a1a2e", anchor="e")
        em.pack(fill="x")

        # Auto-close after 5 seconds
        root.after(5000, root.destroy)
        root.mainloop()
    except Exception:
        print(f"\n  莲华 [{emotion}]: {jp_text}")
        print(f"  字幕: {zh_text}")


def synthesize_and_play(text: str, mode: str = "api"):
    """TTS + playback. mode: 'api' (莲华原声, 联网) | 'mock' (测试用)"""
    import traceback
    try:
        if mode == "api":
            from tts_api import RengeTTS
            tts = RengeTTS("莲华")
            audio = tts.synthesize(text)
            # API returns 22050Hz — use that exact rate for playback
            sample_rate = 22050
        else:
            from tts_client import TTSClient
            tts = TTSClient("config.yaml")
            tts.mode = mode
            audio = tts.synthesize(text)
            import yaml
            with open("config.yaml", "r", encoding="utf-8") as f:
                sample_rate = yaml.safe_load(f)["audio"].get("sample_rate", 44100)

        print(f"  音频: {len(audio)} 采样点, {len(audio)/sample_rate:.1f}s")

        import sounddevice as sd
        sd.play(audio, samplerate=sample_rate)
        sd.wait()  # 等播放完，防止终端关闭
        return True
    except Exception as e:
        print(f"  ✗ TTS 失败 ({mode}): {e}")
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="莲华 Agent 体验测试")
    parser.add_argument("--text", type=str, help="直接输入文本测试")
    parser.add_argument("--no-subtitle", action="store_true")
    parser.add_argument("--tts-mode", choices=["api", "mock"], default="api",
                        help="TTS 模式: api=莲华原声(联网), mock=测试音(离线)")
    args = parser.parse_args()

    mode_labels = {"api": "莲华原声 (skytnt/moe-tts API)", "mock": "测试音 (正弦波)"}
    print("=" * 50)
    print("  蓮華 (Renge) Agent 体验测试")
    print(f"  TTS: {mode_labels[args.tts_mode]}")
    print("=" * 50)

    # LLM
    user_text = args.text or input("\n You: ").strip()
    if not user_text:
        user_text = "こんにちは"

    print(f"\n 用户: {user_text}")
    print(" 思考中...", end="\r")

    t0 = time.time()
    resp = call_llm(user_text)
    jp_text = resp.get("jp_text", "")
    zh_text = resp.get("zh_text", "")
    emotion = resp.get("emotion", "neutral")

    elapsed = time.time() - t0
    print(f" 莲华 [{emotion}]: {jp_text}  ({elapsed:.1f}s)")

    # Subtitle (non-blocking)
    if not args.no_subtitle:
        t_sub = threading.Thread(target=show_subtitle, args=(jp_text, zh_text, emotion), daemon=True)
        t_sub.start()
        time.sleep(0.3)

    # TTS + Play (retry once on failure, waits for playback to finish)
    print(" 语音合成中...", end="\r")
    ok = synthesize_and_play(jp_text, mode=args.tts_mode)
    if not ok and args.tts_mode == "api":
        print("  重试中...", end="\r")
        time.sleep(1)
        ok = synthesize_and_play(jp_text, mode=args.tts_mode)

    print(f"\n{'='*50}")
    print("测试完成！")
    if not args.no_subtitle:
        print("(字幕窗口 5 秒后自动关闭)")
        time.sleep(5)


if __name__ == "__main__":
    main()
