"""
Audio I/O — microphone recording and audio playback.
Uses sounddevice for cross-platform low-latency audio.
"""

import logging
import threading
import time
from collections import deque
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf
import yaml

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Non-blocking microphone recorder with silence auto-stop."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        audio_cfg = cfg["audio"]
        self.sample_rate = audio_cfg.get("sample_rate", 44100)
        self.device = audio_cfg.get("input_device")
        self.max_duration = audio_cfg.get("record_duration", 5)
        self.silence_threshold = audio_cfg.get("silence_threshold", 0.01)

        self._buffer: deque = deque()
        self._recording = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start recording in background thread."""
        if self._recording:
            return
        self._buffer.clear()
        self._recording = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self) -> np.ndarray:
        """Stop recording and return the concatenated audio."""
        self._recording = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        if not self._buffer:
            return np.array([], dtype=np.float32)

        audio = np.concatenate(list(self._buffer), axis=0)
        self._buffer.clear()
        return audio

    def _record_loop(self):
        """Continuously record chunks, stop on silence or max duration."""
        chunk_duration = 0.2
        chunk_size = int(self.sample_rate * chunk_duration)
        total_samples = 0
        max_samples = int(self.sample_rate * self.max_duration)
        silent_chunks = 0

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                device=self.device,
                dtype="float32",
                blocksize=chunk_size,
            ) as stream:
                while self._recording:
                    data, _ = stream.read(chunk_size)
                    self._buffer.append(data.copy())

                    total_samples += chunk_size
                    rms = float(np.sqrt(np.mean(data**2)))

                    if rms < self.silence_threshold:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0

                    if silent_chunks >= 8:  # 1.6s silence -> stop
                        logger.debug("Silence detected, stopping recording")
                        break
                    if total_samples >= max_samples:
                        logger.debug("Max duration reached, stopping recording")
                        break
        except Exception as e:
            logger.error(f"Recording error: {e}")

        self._recording = False


class AudioPlayer:
    """Play audio waveforms with optional non-blocking playback."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        audio_cfg = cfg["audio"]
        self.sample_rate = audio_cfg.get("sample_rate", 44100)
        self.device = audio_cfg.get("output_device")

    def play(self, audio: np.ndarray, blocking: bool = True):
        """Play audio waveform. Set blocking=False for async playback."""
        if len(audio) == 0:
            return
        # Ensure float32 in [-1, 1]
        audio = np.clip(audio.astype(np.float32), -1.0, 1.0)
        sd.play(audio, samplerate=self.sample_rate, device=self.device)
        if blocking:
            sd.wait()

    def play_file(self, filepath: str, blocking: bool = True):
        """Load and play a wav file."""
        audio, sr = sf.read(filepath, dtype="float32")
        if sr != self.sample_rate:
            from scipy.signal import resample
            audio = resample(audio, int(len(audio) * self.sample_rate / sr))
        self.play(audio, blocking=blocking)

    def stop(self):
        """Stop any ongoing playback."""
        sd.stop()
