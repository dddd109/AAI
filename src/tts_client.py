"""
TTS Client — 统一 TTS 接口
支持: api (skytnt/moe-tts 莲华原声) | local (v4 GPT-SoVITS) | mock
"""

import io
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

logger = logging.getLogger(__name__)


class TTSClient:
    """Text-to-Speech unified interface."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        self.tts_cfg = cfg["tts"]
        self.mode = self.tts_cfg["mode"]
        self.sample_rate = cfg["audio"].get("sample_rate", 44100)
        self._engine = None

    def synthesize(self, text: str) -> np.ndarray:
        """Convert text to audio waveform. Returns float32 numpy array."""
        if self.mode == "api":
            return self._api_synthesize(text)
        elif self.mode == "local_vits":
            return self._local_vits_synthesize(text)
        elif self.mode == "local":
            return self._local_synthesize(text)
        elif self.mode == "mock":
            return self._mock_synthesize(text)
        else:
            raise ValueError(f"Unknown TTS mode: {self.mode}. Valid: api, local, local_vits, mock")

    # ── Local VITS mode (fine-tuned 莲华 model, offline, <1s) ──

    def _local_vits_synthesize(self, text: str) -> np.ndarray:
        """
        Local VITS inference with fine-tuned 莲华 model.
        Requires: moe_tts_models/slot4/model.pth (454MB)
        Status: training on gdut GPU 2, not yet ready.
        """
        vits_cfg = self.tts_cfg.get("local_vits", {})
        model_path = vits_cfg.get("model_path", "./moe_tts_models/slot4/model.pth")
        config_path = vits_cfg.get("config_path", "./moe_tts_models/slot4/config.json")

        if not Path(model_path).exists():
            logger.warning("VITS model not found, falling back to API mode")
            return self._api_synthesize(text)

        try:
            import json, torch, commons
            sys.path.insert(0, str(Path(__file__).parent.parent / "moe_tts_models"))
            from models import SynthesizerTrn
            from text import text_to_sequence

            if not hasattr(self, "_vits_model"):
                with open(config_path) as f:
                    hps = json.load(f)
                model = SynthesizerTrn(
                    len(hps["symbols"]), hps["data"]["filter_length"] // 2 + 1,
                    hps["train"]["segment_size"] // hps["data"]["hop_length"],
                    n_speakers=hps["data"]["n_speakers"], **hps["model"],
                )
                ckpt = torch.load(model_path, map_location="cpu", weights_only=False)
                model.load_state_dict(ckpt["model"], strict=False)
                model = model.to("cuda").eval()
                self._vits_model = model
                self._vits_hps = hps
                self._vits_symbols = hps["symbols"]
                logger.info("VITS 莲华 model loaded")

            seq = text_to_sequence(text, self._vits_symbols, ["japanese_cleaners2"])
            if self._vits_hps["data"]["add_blank"]:
                seq = commons.intersperse(seq, 0)
            x = torch.LongTensor(seq).unsqueeze(0).cuda()
            x_len = torch.LongTensor([len(seq)]).cuda()
            sid = torch.LongTensor([0]).cuda()

            with torch.no_grad():
                audio = self._vits_model.infer(
                    x, x_len, sid=sid,
                    noise_scale=0.667, noise_scale_w=0.8, length_scale=1.0,
                )[0][0, 0].cpu().float().numpy()
            return audio
        except Exception as e:
            logger.error(f"VITS local inference failed: {e}")
            return self._api_synthesize(text)

    # ── API mode (skytnt/moe-tts, 莲华原声) ──

    def _api_synthesize(self, text: str) -> np.ndarray:
        """Use skytnt/moe-tts HF Space API. 莲华本人声音, ~5s延迟."""
        from src.tts_api import RengeTTS
        api_cfg = self.tts_cfg.get("api", {})
        character = api_cfg.get("character", "莲华")
        if not hasattr(self, "_api_tts"):
            self._api_tts = RengeTTS(character)
        return self._api_tts.synthesize(text)

    # ── Local mode (GPT-SoVITS v4, offline) ──

    def _local_synthesize(self, text: str) -> np.ndarray:
        """Local GPT-SoVITS v4 inference. Offline, ~50s on RTX 4060."""
        local_cfg = self.tts_cfg.get("local", {})
        model_path = Path(local_cfg.get("model_path", "./莲华模型"))

        try:
            self._ensure_engine_loaded(local_cfg)
            return self._run_inference(text)
        except Exception as e:
            logger.error(f"Local TTS failed: {e}")
            return self._mock_synthesize(text)

    def _ensure_engine_loaded(self, local_cfg: dict):
        if self._engine is not None:
            return

        gpt_sovits_root = Path(local_cfg.get("gpt_sovits_path", "./GPT-SoVITS")).resolve()
        if str(gpt_sovits_root) not in sys.path:
            sys.path.insert(0, str(gpt_sovits_root))

        try:
            from GPT_SoVITS.inference_webui import get_tts_wav
            self._get_tts_wav = get_tts_wav
            model_path = Path(local_cfg["model_path"]).resolve()
            self._gpt_path = str(model_path / local_cfg.get("gpt_weights", ""))
            self._sovits_path = str(model_path / local_cfg.get("sovits_weights", ""))
            self._ref_audio = self._find_ref_audio(model_path)
            self._ref_text = self._load_ref_text(model_path)
            self._engine = "loaded"
            logger.info("GPT-SoVITS engine loaded")
        except ImportError as e:
            logger.warning(f"GPT-SoVITS not installed: {e}")
            raise

    def _find_ref_audio(self, model_path: Path) -> str:
        for ext in (".wav", ".mp3", ".flac", ".ogg"):
            candidates = list(model_path.glob(f"*ref*{ext}")) + list(model_path.glob(f"*{ext}"))
            if candidates:
                return str(candidates[0])
        return ""

    def _load_ref_text(self, model_path: Path) -> str:
        txt_path = model_path / "ref_text.txt"
        if txt_path.exists():
            return txt_path.read_text(encoding="utf-8").strip()
        return ""

    def _run_inference(self, text: str) -> np.ndarray:
        try:
            sr, audio = self._get_tts_wav(
                ref_wav_path=self._ref_audio,
                prompt_text=self._ref_text,
                prompt_language="ja",
                text=text,
                text_language="ja",
                how_to_cut="不切",
                gpt_path=self._gpt_path,
                sovits_path=self._sovits_path,
                top_k=5, top_p=1.0, temperature=1.0,
            )
            return audio.astype(np.float32)
        except Exception as e:
            logger.error(f"Inference error: {e}")
            raise

    # ── Mock mode ──

    def _mock_synthesize(self, text: str) -> np.ndarray:
        """Sine-wave placeholder for testing."""
        duration = min(0.1 * len(text), 5.0)
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        freq = 220 + (hash(text) % 200)
        audio = 0.3 * np.sin(2 * np.pi * freq * t).astype(np.float32)
        fade = min(1000, len(audio) // 10)
        audio[:fade] *= np.linspace(0, 1, fade)
        audio[-fade:] *= np.linspace(1, 0, fade)
        return audio
