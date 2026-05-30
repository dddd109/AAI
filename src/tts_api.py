"""
莲华 TTS API Client — calls skytnt-moe-tts HuggingFace Space.
Provides character-accurate voice synthesis without local GPU.
"""

import base64
import io
import json
import logging
import random
import time
from string import ascii_lowercase, digits
from typing import Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)

# Character registry: (speaker_name, fn_index, trigger_id)
CHARACTERS = {
    "莲华":   ("蓮華",   12, 85),
    "篝之雾枝": ("篝ノ霧枝", 12, 85),
    "沢渡雫":  ("沢渡雫",  12, 85),
    "亚璃子":  ("亜璃子",  12, 85),
    "灯露椎":  ("灯露椎",  12, 85),
    "覡夕莉":  ("覡夕莉",  12, 85),
    # Yuzusoft characters
    "绫地宁宁": ("綾地寧々", 0, 17),
    "因幡爱瑠": ("因幡めぐる", 0, 17),
    "朝武芳乃": ("朝武芳乃", 6, 51),
    "丛雨":    ("ムラサメ", 6, 51),
}


class RengeTTS:
    """莲华 character TTS via skytnt-moe-tts API."""

    API = "https://skytnt-moe-tts.hf.space"

    def __init__(self, character: str = "莲华", proxy: Optional[str] = "http://127.0.0.1:7897"):
        if character not in CHARACTERS:
            raise ValueError(f"Unknown character: {character}. Available: {list(CHARACTERS.keys())}")
        self.speaker, self.fn_index, self.trigger_id = CHARACTERS[character]
        self.proxy = proxy
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=120,
                follow_redirects=True,
                proxy=self.proxy,
            )
        return self._client

    def synthesize(self, text: str) -> np.ndarray:
        """Convert Japanese text to audio waveform. Returns float32 array."""
        wav_bytes = self._call_api(text)
        return self._decode_wav(wav_bytes)

    def _call_api(self, text: str) -> bytes:
        """Call the HuggingFace Space TTS API."""
        session_hash = "".join(random.choice(ascii_lowercase + digits) for _ in range(10))
        logger.info(f"TTS API: speaker={self.speaker}, text={text[:50]}...")

        # Join queue
        r = self.client.post(
            f"{self.API}/queue/join?__theme=light",
            json={
                "fn_index": self.fn_index,
                "data": [text, self.speaker, 1, False],
                "session_hash": session_hash,
                "event_data": None,
                "trigger_id": self.trigger_id,
            },
        )
        r.raise_for_status()

        # Poll for result
        r2 = self.client.get(f"{self.API}/queue/data?session_hash={session_hash}")
        r2.raise_for_status()

        data_url = None
        for line in r2.text.split("\n"):
            if not line.startswith("data: "):
                continue
            try:
                event = json.loads(line.replace("data: ", ""))
            except json.JSONDecodeError:
                continue

            msg = event.get("msg", "")
            if msg == "process_completed":
                output = event.get("output", {})
                if output.get("data"):
                    data_url = output["data"][1]["url"]
                    break
                else:
                    logger.error(f"API returned success=false: {json.dumps(output, ensure_ascii=False)[:200]}")
                    raise RuntimeError("TTS API returned no audio data")
            elif msg == "process_generating":
                logger.debug("TTS generating...")

        if not data_url:
            raise RuntimeError("No audio URL in API response")

        r3 = self.client.get(data_url)
        r3.raise_for_status()
        logger.info(f"TTS done: {len(r3.content)} bytes")
        return r3.content

    @staticmethod
    def _decode_wav(wav_bytes: bytes) -> np.ndarray:
        """Decode wav bytes to float32 numpy array."""
        import soundfile as sf
        audio, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        return audio

    def save(self, text: str, path: str):
        """Synthesize and save to wav file."""
        wav_bytes = self._call_api(text)
        with open(path, "wb") as f:
            f.write(wav_bytes)
        return path


def test():
    """Quick test."""
    tts = RengeTTS("莲华")
    audio = tts.synthesize("こんにちは、私は蓮華です。")
    print(f"Audio: {len(audio)} samples, max={audio.max():.2f}")

    import sounddevice as sd
    import soundfile as sf
    sd.play(audio, 22050)
    sd.wait()


if __name__ == "__main__":
    test()
