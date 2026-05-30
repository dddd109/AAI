#!/usr/bin/env python3
"""
Anime-Agent-Infer Phase 1 MVP — Main Pipeline
=============================================
Orchestrates: Text Input → LLM Brain → TTS Voice → Subtitle → Tool Execute

Usage:
    D:/program/anaconda3/python.exe -m src.main          # Interactive session
    D:/program/anaconda3/python.exe -m src.main --once "こんにちは"  # Single query
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

import yaml

from .llm_client import LLMClient
from .tts_client import TTSClient
from .audio_io import AudioPlayer, AudioRecorder
from .subtitle import SubtitleOverlay
from .tool_executor import ToolExecutor

# Ensure src/ is importable when run as module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def setup_logging(config_path: str = "config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    log_cfg = cfg.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO"))
    log_file = log_cfg.get("file", "./logs/agent.log")
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


class AnimeAgent:
    """Main agent pipeline coordinating LLM, TTS, Audio, and Tools."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.log = logging.getLogger(__name__)

        self.log.info("Initializing Anime-Agent-Infer Phase 1 MVP...")
        self.llm = LLMClient(config_path)
        self.tts = TTSClient(config_path)
        self.player = AudioPlayer(config_path)
        self.recorder = AudioRecorder(config_path)
        self.tool = ToolExecutor(config_path)
        self.subtitle: SubtitleOverlay | None = None
        self.running = False

    def start(self, show_subtitle: bool = True):
        """Start the agent (subtitle window if GUI available)."""
        if show_subtitle:
            try:
                self.subtitle = SubtitleOverlay()
                self.subtitle.start()
                self.log.info("Subtitle overlay started")
            except Exception as e:
                self.log.warning(f"Subtitle not available (headless?): {e}")
                self.subtitle = None
        self.running = True

    def stop(self):
        """Clean shutdown."""
        self.running = False
        if self.subtitle:
            self.subtitle.close()
        self.log.info("Agent stopped")

    def process_text(self, user_text: str) -> dict:
        """Full pipeline: text in → LLM → TTS → play + subtitle → tool.

        Returns the parsed LLM response dict.
        """
        if not user_text.strip():
            return {}

        t_start = time.time()

        # 1. LLM: Get character response
        self.log.info(f"User: {user_text[:80]}...")
        response = self.llm.chat(user_text)

        jp_text = response.get("jp_text", "")
        zh_text = response.get("zh_text", "")
        emotion = response.get("emotion", "neutral")
        tool_call = response.get("tool_call", "")

        self.log.info(f"Renge [{emotion}]: {jp_text[:80]}...")

        # 2. Subtitle: Show both languages
        if self.subtitle:
            self.subtitle.show(jp_text, zh_text, emotion)

        # 3. TTS + Playback: Speak Japanese text
        if jp_text:
            audio = self.tts.synthesize(jp_text)
            self.player.play(audio, blocking=True)

        # 4. Tool execution (async — fire and forget)
        if tool_call and tool_call.strip():
            self.log.info(f"Tool call: {tool_call[:120]}")
            self.tool.execute(tool_call, on_complete=self._on_tool_complete)

        elapsed = time.time() - t_start
        self.log.info(f"Pipeline completed in {elapsed:.2f}s")

        return response

    def process_voice(self) -> dict:
        """Record from mic and process through the pipeline."""
        print("Recording... (speak now, auto-stop on silence)")
        self.recorder.start()
        time.sleep(0.3)  # Brief visual feedback

        while self.recorder._recording:
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(0.2)
        print()

        audio = self.recorder.stop()
        if len(audio) == 0:
            print("No audio recorded.")
            return {}

        # Placeholder: For MVP, skip ASR and use a text prompt
        # In production, add Whisper/ASR here
        print(f"Recorded {len(audio) / self.recorder.sample_rate:.1f}s of audio")
        user_text = input("Text (manual input, ASR not yet integrated): ")
        return self.process_text(user_text)

    def _on_tool_complete(self, result: str):
        """Callback when async tool execution finishes."""
        self.log.info(f"Tool result: {result[:200]}")
        if self.subtitle:
            brief = result[:200] + ("..." if len(result) > 200 else "")
            self.subtitle.show(
                jp_text="ツール実行完了だ。結果を見ろ",
                zh_text=f"[Tool] {brief}",
                emotion="neutral",
            )

    def interactive_loop(self):
        """REPL for text-based interaction."""
        print("=" * 60)
        print("  蓮華 (Renge) Anime Agent — Phase 1 MVP")
        print("  Type 'quit' to exit, 'voice' for mic input")
        print("=" * 60)

        self.start()

        try:
            while self.running:
                try:
                    user_input = input("\nYou: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break

                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "q"):
                    break
                if user_input.lower() == "voice":
                    self.process_voice()
                else:
                    self.process_text(user_input)
        finally:
            self.stop()
            print("\nまたな。")

    def once(self, text: str):
        """Run a single query and exit."""
        self.start()
        self.process_text(text)
        self.stop()


def main():
    parser = argparse.ArgumentParser(description="Anime-Agent-Infer Phase 1 MVP")
    parser.add_argument("--once", type=str, help="Single query mode")
    parser.add_argument("--config", type=str, default="config.yaml")
    parser.add_argument("--no-subtitle", action="store_true", help="Disable subtitle overlay")
    args = parser.parse_args()

    setup_logging(args.config)

    agent = AnimeAgent(args.config)

    # Graceful shutdown on Ctrl+C
    signal.signal(signal.SIGINT, lambda *_: agent.stop())

    if args.once:
        agent.once(args.once)
    else:
        agent.interactive_loop()


if __name__ == "__main__":
    main()
