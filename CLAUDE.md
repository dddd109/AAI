# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Anime-Agent-Infer is a three-node heterogeneous agent system featuring "莲华" (Renge) from 美少女万华镜5. Architecture: cloud LLM brain (Node A) → school-server GPT-SoVITS TTS throat (Node B) → local C++/CUDA engine (Node C). Currently in Phase 1 (Python MVP).

## Key architectural decisions

- Three heterogeneous nodes across network boundaries: Cloud API (DeepSeek/Claude), school K8s GPU cluster (Quadro RTX 8000 ×3), local Windows PC (RTX 4060 8GB).
- LLM outputs structured JSON: `{jp_text, zh_text, tool_call, emotion}`.
- TTS is GPT-SoVITS with fine-tuned 莲华 voice weights. **The weights are v1 format** (`enc_p.proj` + `enc_p.enc_` + `emb_g`), but the cloned repo (`GPT-SoVITS/`) is v2/v3/v4 (SSL-based architecture with `enc_p.ssl_proj` + `enc_p.encoder_ssl`). This architecture mismatch blocks full inference.
- School server network: campus blocks UDP → Cloudflare Tunnel (TCP/HTTPS 443) for exposing TTS API. SSH via `gdut` alias.
- Phase 2 will use custom CUDA kernels compiled with nvcc 13.2 targeting sm_89 (Ada) and sm_75 (Turing).

## Python environment

```bash
# Primary: torch conda env (Python 3.9, torch 2.3.1+cu118)
C:/Users/AD/.conda/envs/torch/python.exe script.py
C:/Users/AD/.conda/envs/torch/python.exe -m pip install <package>

# Fallback: base conda (Python 3.12.7)
D:/program/anaconda3/python.exe script.py

# Proxy for external downloads
export HTTP_PROXY=http://127.0.0.1:7897
export HTTPS_PROXY=http://127.0.0.1:7897
```

⚠️ Do NOT use `.venv/` — deleted.

## Key scripts (Phase 1)

| Script | Purpose | Status |
|--------|---------|--------|
| **`src/tts_api.py`** | **莲华 TTS via skytnt-moe-tts HF Space — real character voice, ~3-6s** | **Works** |
| `demo_v4.py` | v4 local TTS (GPT-SoVITS pretrained, generic voice, 48s) | Works |
| `src/main.py` | Full agent pipeline (LLM → TTS → Audio → Subtitle → Tool) | Ready |
| `src/llm_client.py` | DeepSeek/Claude API with 莲华 character card | Works (needs API key) |

### Run TTS

```bash
# 莲华 voice via API (fast, accurate character voice)
.venv/Scripts/python.exe -c "
from src.tts_api import RengeTTS
tts = RengeTTS('莲华')
tts.save('こんにちは', 'hello.wav')
"

# Or use the TTS client (reads config.yaml mode)
.venv/Scripts/python.exe -c "
from src.tts_client import TTSClient
t = TTSClient('config.yaml')
t.mode = 'api'
audio = t.synthesize('こんにちは')
"

# Local v4 TTS (offline, generic voice)
.venv/Scripts/python.exe demo_v4.py --text "こんにちは"
```

### yozu_voice / skytnt-moe-tts API

The repo `SonderXiaoming/youzi_voice` wraps the HuggingFace Space `skytnt-moe-tts` which hosts character TTS models. Key API details:

- Endpoint: `https://skytnt-moe-tts.hf.space/queue/join`
- Method: POST JSON with session_hash, poll GET for result
- 莲华 params: speaker="蓮華", fn_index=12, trigger_id=85
- Output: wav bytes, 22050Hz, ~5KB/s of speech
- Latency: 3-6s per request via HuggingFace Space (queued)

### VITS fine-tuning (gdut GPU 2, training in progress)

- **Code**: `~/vits_renge/train_v2.py` (Space-compatible VITS training)
- **Data**: 3670 莲华 pairs (games 1-5), 22050Hz WAV
- **Pretrained**: `renge_vits.pth` (454MB, skytnt/moe-tts slot 4)
- **Output**: `~/vits_renge/output_v2/` (checkpoints every 20 epochs)
- **Monitor**: `ssh gdut "tail -f ~/vits_renge/train_v2.log"`
- **Key fix**: enc_q expects spectrogram [B, C, T] not raw audio [B, T]; librosa mel() needs keyword args on v0.10+

## Critical known issues

### 1. 莲华 v1 weights incompatible with current code

The 莲华 SoVITS weights (`G.莲华22240.pth`, `sovits_renge.pth`) are v1 format. The cloned `GPT-SoVITS/` is the latest v2/v3/v4 code. Key differences:

| | v1 (our weights) | v2 (current code) |
|---|---|---|
| Text encoder | `enc_p.proj` + `enc_p.enc_` (6 layers) | `enc_p.ssl_proj` + `enc_p.encoder_ssl` + `enc_p.encoder_text` |
| Speaker | `emb_g` embedding table | `ref_enc` (from mel spectrogram) |
| SSL dimension | N/A (256-dim gin) | 768-dim SSL from CNHuBERT |
| Semantic tokens | Direct from GPT | VQ-quantized with residual vector quantizer |

~200 weights missing, ~200 unexpected. MRTE attention fails with tensor dimension mismatch (512 vs 256).

**Possible solutions:**
- Find GPT-SoVITS v1 commit and checkout that code version
- Use v2 pretrained SoVITS (`s2G2333k.pth`) for a working demo (won't be 莲华 voice)
- Retrain with v2 codebase using the same 莲华 dataset

### 2. transformers torch>=2.6 requirement

transformers >=4.57 requires torch >=2.6 for `torch.load` security. Workaround: monkey-patch `transformers.modeling_utils.load_state_dict`. Torch 2.5.1 is used because CUDA 12.1 wheels don't go beyond 2.5.1; CUDA 12.6 download times out.

### 3. torch.distributed in single-GPU inference

GPT-SoVITS code calls `dist.get_rank()`, `dist.broadcast()` during VQ codebook init. Fix applied in `GPT-SoVITS/GPT_SoVITS/module/core_vq.py` lines 165-170: added `not dist.is_available() or not dist.is_initialized()` guard.

### 4. opencc build failure

`opencc` (Chinese text conversion) can't compile from source on Windows. Not needed for Japanese TTS. `ToJyutping`, `g2pk2`, `ko_pron`, `python_mecab_ko` also skipped (Cantonese/Korean only).

### 5. Model files location

All pretrained models are stored locally under project directory:
- `GPT-SoVITS/GPT_SoVITS/pretrained_models/` — GPT + SoVITS v4 + BERT + CNHuBERT
- `moe_tts_models/slot4/` — 莲华 VITS model (from skytnt/moe-tts)

These are gitignored. If models are lost, re-download from HF-Mirror via proxy:
```bash
curl -x http://127.0.0.1:7897 -L -o <path> <hf-mirror-url>
```

### 6. CUDA toolkit vs PyTorch CUDA

System has CUDA Toolkit v13.2 (`nvcc`). PyTorch uses bundled CUDA 12.1 runtime. They don't interact — custom CUDA kernels (Phase 2) must be compiled with nvcc 13.2 targeting the right architecture, then loaded via PyBind11 separately from PyTorch's CUDA ops.

## Conda note

Creating new conda environments is blocked (repo.anaconda.com rate-limits). Use the existing `torch` conda env (`C:/Users/AD/.conda/envs/torch/`) or create Python `venv` from `D:/program/anaconda3/python.exe`.

## Git

```bash
# Remote uses SSH (not HTTPS, which had timeout issues)
git remote set-url origin git@github.com:dddd109/AAI.git

# SSH key already authorized with GitHub
ssh -T git@github.com  # Should show: Hi dddd109!
```

## Hardware

| | Local | School Server (gpu-108) |
|---|---|---|
| GPU | RTX 4060 Laptop 8GB (Ada, CC 8.9) | Quadro RTX 8000 ×3 48GB (Turing, SM 7.5) |
| CPU | i7-13650HX | Xeon Silver 4216 64-core |
| RAM | 24GB DDR5 | 114GB DDR4 ECC |
| CUDA | Toolkit 13.2, PyTorch 12.1 | Driver 550.135, CUDA 12.4 |
| OS | Windows 11 | Ubuntu 22.04 K8s cluster |
| Access | — | `ssh gdut` (stu001@10.200.168.108) |
