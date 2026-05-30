"""
LLM Client — calls DeepSeek/Claude API with "莲华" character card.
Returns structured JSON: {jp_text, zh_text, tool_call, emotion}
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import httpx
import yaml
from openai import OpenAI

logger = logging.getLogger(__name__)

# Fallback responses when API is unreachable (offline mode)
_FALLBACKS = [
    {"jp_text": "ふん…APIが繋がらないみたいだ。後で試せよな", "zh_text": "哼…API好像连不上。你晚点再试吧。", "tool_call": "", "emotion": "sad"},
    {"jp_text": "おい、ネットワークを確認しろってんだ。私じゃどうにもならん", "zh_text": "喂，你去检查一下网络。我是没办法的。", "tool_call": "", "emotion": "angry"},
    {"jp_text": "…退屈だ。早くなんとかしろ", "zh_text": "…好无聊。快想想办法。", "tool_call": "", "emotion": "neutral"},
]
_fallback_idx = 0


class LLMClient:
    """Structured JSON LLM client for the 莲华 character agent."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        self.llm_cfg = cfg["llm"]
        self.provider = self.llm_cfg["provider"]

        card_path = Path(cfg["character"].get("card_file", "character_card.txt"))
        self.system_prompt = card_path.read_text(encoding="utf-8") if card_path.exists() else ""

        self.client = OpenAI(
            api_key=self.llm_cfg["api_key"],
            base_url=self.llm_cfg["api_base"],
            timeout=30.0,
            http_client=httpx.Client(
                proxy="http://127.0.0.1:7897",
                transport=httpx.HTTPTransport(retries=2),
            ),
        )

    def chat(self, user_text: str) -> dict:
        """Send user text, return parsed JSON response from the character."""
        try:
            response = self.client.chat.completions.create(
                model=self.llm_cfg["model"],
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_text},
                ],
                max_tokens=self.llm_cfg.get("max_tokens", 512),
                temperature=self.llm_cfg.get("temperature", 0.7),
            )
            raw = response.choices[0].message.content.strip()
            return self._parse(raw)

        except Exception as e:
            logger.warning(f"LLM API failed: {e}. Using fallback response.")
            return self._fallback(user_text)

    def _parse(self, raw: str) -> dict:
        """Extract JSON from LLM output, tolerating markdown fences."""
        # Try direct JSON parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from ```json ... ``` code block
        m = re.search(r"```(?:json)?\s*\n?([\s\S]*?)```", raw)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding JSON object by braces
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse LLM output as JSON: {raw[:200]}")
        return {
            "jp_text": "…出力がおかしいな。JSONが壊れてる",
            "zh_text": "…输出有问题。JSON坏了。",
            "tool_call": "",
            "emotion": "sad",
        }

    def _fallback(self, user_text: str) -> dict:
        """Offline fallback — cycle through canned responses."""
        global _fallback_idx
        resp = _FALLBACKS[_fallback_idx % len(_FALLBACKS)]
        _fallback_idx += 1
        return resp
