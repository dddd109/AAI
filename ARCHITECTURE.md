# Anime-Agent-Infer 项目架构总结

> 最后更新: 2026-05-29

---

## 1. 项目目的和功能

**Anime-Agent-Infer** 是一个高性能跨设备二次元桌面智能体系统。以《美少女万華鏡5》角色 **莲华（蓮華 / Renge）** 为看板娘，实现：

- **语音交互**: 用户输入文本 → 莲华用日语语音回复
- **双语字幕**: 日语语音 + 中文字幕同步显示
- **系统自动化**: 通过 Claude Code CLI 执行本地系统操作
- **LLM 对话**: 云端大模型注入莲华角色卡，输出结构化 JSON

最终目标是三节点异构部署：云端 LLM 做大脑、学校 GPU 服务器做 TTS 喉咙、本地 C++/CUDA 做高性能推理躯干。

---

## 2. 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| **LLM** | DeepSeek-V3 / Claude API | OpenAI 兼容协议，HTTP POST，JSON 输出 |
| **TTS (API)** | skytnt/moe-tts (HuggingFace Space) | VITS 多角色模型，莲华 speaker_id=0, slot=4 |
| **TTS (本地)** | GPT-SoVITS v4 | DiT-based 语音合成，~50s/句，离线可用 |
| **TTS (训练)** | GPT-SoVITS v2/v3, VITS | 莲华 v1 权重不兼容，改用 v4 预训练 + API |
| **音频 I/O** | sounddevice, soundfile | 麦克风录音 + 音频播放，44.1kHz |
| **字幕** | tkinter | always-on-top 半透明窗口，日文+中文 |
| **工具执行** | subprocess → Claude Code CLI | 沙盒模式，异步 fire-and-forget |
| **Python** | 3.12.7 (venv) | torch 2.5.1+cu121, transformers 4.57 |
| **GPU (本地)** | RTX 4060 Laptop 8GB | Ada Lovelace, CC 8.9 |
| **GPU (训练)** | Quadro RTX 8000 ×3 48GB | Turing, SM 7.5, CUDA 12.4 |
| **游戏数据提取** | GARbro + filepack31 | QLIE (FilePackVer3.0) 解包, UTF-16LE 脚本解析 |

---

## 3. 目录结构

```
Anime-Agent-Infer/
│
├── README.md                 # 项目说明与快速开始
├── README_old.md             # 原始项目愿景 (Phase 1-3 规划)
├── CLAUDE.md                 # Claude Code 开发指南
├── ARCHITECTURE.md           # 本文件 — 架构总结
├── WORKFLOW.md               # 完整工作流程与踩坑记录
│
├── config.yaml               # 全局配置 (LLM/TTS/Audio/Tool)
├── requirements.txt          # Python 依赖
├── character_card.txt        # 莲华角色卡 System Prompt
│
├── src/                      # Phase 1 核心源码
│   ├── main.py               # 主流水线 & 交互 REPL
│   ├── llm_client.py         # LLM API (DeepSeek/Claude)
│   ├── tts_api.py            # 莲华 TTS API (skytnt/moe-tts)
│   ├── tts_client.py         # TTS 统一接口 (api/local/remote/mock)
│   ├── audio_io.py           # 麦克风录音 & 音频播放
│   ├── subtitle.py           # tkinter 双语字幕覆盖层
│   └── tool_executor.py      # Claude Code CLI 沙盒执行
│
├── demo_v4.py                # 本地 GPT-SoVITS v4 TTS demo
├── convert_ckpt.py           # 训练 ckpt → 推理格式转换
├── quick_demo.py             # SoVITS 声纹测试 (随机输入)
├── test_model_load.py        # 模型加载 & GPU 推理验证
├── download_pretrained.py    # 预训练模型下载
│
├── .venv/                    # Python 3.12 venv (gitignored)
├── GPT-SoVITS/               # GPT-SoVITS 代码 (gitignored)
├── 莲华模型/                  # 莲华 v1 权重 (gitignored)
└── moe_tts_models/           # skytnt/moe-tts slot4 (gitignored)
```

### 学校服务器 (gdut)

```
~/GPT-SoVITS/                 # GPT-SoVITS 代码 + 依赖
  GPT_SoVITS/pretrained_models/
    gsv-v2final-pretrained/     GPT 149MB + SoVITS 102MB
    chinese-roberta-wwm-ext-large/  BERT 1.3GB
    chinese-hubert-base/            CNHuBERT 361MB

~/renge_data/
    audio/                     3516 OGG 莲华语音 (529MB)
    wavs/                      3516 WAV 16kHz 莲华语音
    train.txt                  3133 行训练数据
    val.txt                    348 行验证数据
    preprocess.py              统一预处理脚本
```

---

## 4. 核心模块与关系

```
┌─────────────────────────────────────────────────────────┐
│                      config.yaml                         │
│  (LLM API key, TTS mode, audio device, tool settings)   │
└──────────────────────┬──────────────────────────────────┘
                       │ 读取配置
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    src/main.py                           │
│                  Agent 主流水线                           │
│  Input → LLM → [Subtitle + TTS + Audio] → Tool          │
└──┬──────────┬──────────┬──────────┬─────────────────────┘
   │          │          │          │
   ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐
│LLM   │ │TTS   │ │Audio │ │Tool      │
│Client│ │Client│ │I/O   │ │Executor  │
└──┬───┘ └──┬───┘ └──────┘ └────┬─────┘
   │        │                    │
   │        ├── tts_api.py       │
   │        │   (RengeTTS)       │
   │        │   → skytnt/moe-tts │
   │        │                    │
   │        └── demo_v4.py       │
   │            (本地 v4 TTS)     │
   │                             │
   ▼                             ▼
┌──────────────────┐    ┌────────────────┐
│ DeepSeek/Claude  │    │ Claude Code    │
│ API              │    │ CLI subprocess │
│ (cloud)          │    │ (local)        │
└──────────────────┘    └────────────────┘
```

### 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| **LLMClient** | `src/llm_client.py` | 调用 DeepSeek/Claude API，注入莲华角色卡，解析 JSON 响应 `{jp_text, zh_text, tool_call, emotion}`，含离线 fallback |
| **RengeTTS** | `src/tts_api.py` | 调用 skytnt/moe-tts HF Space API，POST 队列 → 轮询 → 下载 wav。支持 100+ 角色，莲华 speaker="蓮華", fn_index=12, trigger_id=85 |
| **TTSClient** | `src/tts_client.py` | 统一 TTS 接口，支持 api / local / remote / mock 四种模式，读取 config.yaml 切换 |
| **AudioRecorder** | `src/audio_io.py` | 麦克风录音，沉默自动停止 (1.6s 阈值)，sounddevice InputStream |
| **AudioPlayer** | `src/audio_io.py` | 音频播放，sounddevice.play()，支持阻塞/非阻塞 |
| **SubtitleOverlay** | `src/subtitle.py` | tkinter 半透明置顶窗口，日文+中文+情绪颜色 |
| **ToolExecutor** | `src/tool_executor.py` | `claude -p "<instruction>"` 子进程，沙盒模式，120s 超时 |

### character_card.txt

莲华角色卡 System Prompt，强制 LLM 输出结构化 JSON：
```json
{"jp_text": "日本語セリフ", "zh_text": "中文字幕", "tool_call": "系统命令(可选)", "emotion": "neutral/happy/angry/sad/surprised/teasing"}
```

---

## 5. 数据流向

### 主交互流

```
用户文本输入
    │
    ▼
┌─────────────┐
│  LLMClient   │  POST DeepSeek API (30s timeout, httpx + proxy)
│  .chat()     │  System Prompt: character_card.txt
└──────┬──────┘
    │  JSON {jp_text, zh_text, tool_call, emotion}
    ▼
┌──────────────────────────────────────────────┐
│              Main Pipeline                    │
│                                              │
│  ┌──────────────┐  ┌───────────┐  ┌───────┐ │
│  │ Subtitle      │  │ TTS       │  │ Tool  │ │
│  │ (zh_text,     │  │ (jp_text  │  │ (异步) │ │
│  │  emotion)     │  │  → wav)   │  │       │ │
│  └──────────────┘  └─────┬─────┘  └───────┘ │
│                          │                   │
│                   ┌──────▼──────┐            │
│                   │ AudioPlayer │            │
│                   │ .play(wav)  │            │
│                   └─────────────┘            │
└──────────────────────────────────────────────┘
```

### TTS 数据流 (API 模式)

```
jp_text
  → RengeTTS.synthesize()
    → POST https://skytnt-moe-tts.hf.space/queue/join
      {fn_index: 12, data: [text, "蓮華", 1, False], session_hash}
    → GET /queue/data?session_hash=xxx  (SSE 轮询)
    → event: process_completed → data[1].url
    → GET {audio_url} → wav bytes
    → soundfile → float32 numpy array
```

### TTS 数据流 (本地 v4 模式, demo_v4.py)

```
text
  → TTS_Config("custom": {version: "v4", t2s_weights, vits_weights})
  → TTS.__init__()
    → init_t2s_weights(s1v3.ckpt)
    → init_vits_weights(s2Gv4.pth)
    → init_bert_weights(chinese-roberta)
    → init_cnhuhbert_weights(chinese-hubert)
    → init_vocoder(BigVGAN vocoder.pth)
  → tts.run({text, text_lang: "ja", ref_audio_path, ...})
    → text_preprocessor → phonemes + BERT
    → GPT model → semantic tokens (1500 steps)
    → SoVITS → mel spectrogram
    → BigVGAN → wav (48kHz)
  → soundfile.write()
```

### 训练数据流 (学校服务器)

```
美少女万華鏡5 GameData/
  data8.pack (QLIE FilePackVer3.0)
    → filepack31.exe unpack → .s 脚本文件 (UTF-16LE)
      → Python 正则 ％reng\d{4}％ → 台词文本
        → reng0001.ogg ↔ "「……」"
          → CSV → train.txt (wav_path|speaker|lang|text)
            → GPT-SoVITS Stage 1 (GPT 微调)
            → GPT-SoVITS Stage 2 (SoVITS 微调)
```

---

## 6. API 接口列表

### TTS API (skytnt/moe-tts)

| 端点 | 方法 | 说明 |
|------|------|------|
| `https://skytnt-moe-tts.hf.space/queue/join` | POST | 提交 TTS 任务 |
| `https://skytnt-moe-tts.hf.space/queue/data?session_hash={hash}` | GET (SSE) | 轮询结果 |

**请求参数**:
```json
{
    "fn_index": 12,
    "data": ["こんにちは", "蓮華", 1, false],
    "session_hash": "abc123",
    "trigger_id": 85
}
```

**响应**: wav bytes (22050Hz, mono)

### 莲华角色 API 映射 (from youzi_voice)

| 游戏 | fn_index | trigger_id |
|------|----------|------------|
| 柚子 (Yuzusoft) | 0 | 17 |
| 常轨脱离 | 3 | 34 |
| **美少女万華鏡** | **12** | **85** |
| 缘之空 | 9 | 68 |
| galgame | 21 | 136 |
| 零之使魔 | 24 | 153 |
| TOLOVE | 30 | 187 |

### LLM API

| 端点 | 说明 |
|------|------|
| `https://api.deepseek.com/v1/chat/completions` | DeepSeek-V3 (默认) |
| `https://api.anthropic.com/v1/messages` | Claude (备选) |

### 内部模块接口

```python
# TTS
tts = RengeTTS('莲华')
audio = tts.synthesize("こんにちは")        # → np.ndarray
tts.save("こんにちは", "output.wav")        # → file

# TTS Client (统一接口)
tts = TTSClient('config.yaml')
tts.mode = 'api'            # api | local | mock
audio = tts.synthesize(text)

# LLM
llm = LLMClient('config.yaml')
resp = llm.chat("こんにちは")  # → dict {jp_text, zh_text, tool_call, emotion}

# Audio
player = AudioPlayer('config.yaml')
player.play(audio, blocking=True)

# Tool
tool = ToolExecutor('config.yaml')
tool.execute("整理桌面文件", on_complete=callback)  # async
```

---

## 7. 部署方式

### 本地 (Node C)

```bash
# 环境
python -m venv .venv --system-site-packages
.venv/Scripts/pip install -r requirements.txt

# 运行 Agent
.venv/Scripts/python.exe -m src.main
# 或单次查询
.venv/Scripts/python.exe -m src.main --once "こんにちは"

# 配置 config.yaml
# - llm.api_key: DeepSeek API key
# - tts.mode: "api" (推荐) 或 "local"
```

### 学校服务器 (Node B) — 训练

```bash
ssh gdut
# 环境: ~/.conda/envs/py310 (Python 3.10, torch 2.6+cu124)
# 数据: ~/renge_data/ (3516 WAV + filelists)
# 模型: ~/GPT-SoVITS/GPT_SoVITS/pretrained_models/

# 预处理
cd ~/GPT-SoVITS/GPT_SoVITS
CUDA_VISIBLE_DEVICES=2 PYTHONPATH=.:.. \
  ~/.conda/envs/py310/bin/python ~/renge_data/preprocess.py

# Stage 1 训练 (GPT)
CUDA_VISIBLE_DEVICES=2 PYTHONPATH=.:.. \
  ~/.conda/envs/py310/bin/python s1_train.py --config_file configs/s1longer.yaml

# Stage 2 训练 (SoVITS)
CUDA_VISIBLE_DEVICES=2 PYTHONPATH=.:.. \
  ~/.conda/envs/py310/bin/python s2_train_v3.py --config_file configs/s2v3.yaml
```

### 生产部署 (目标架构)

```
┌──────────────────────────────────────────────────────┐
│  Node A: 云端 (DeepSeek/Claude API)                   │
│  通过代理 127.0.0.1:7897 出站                         │
└──────────────────┬───────────────────────────────────┘
                   │ JSON {jp_text, zh_text, tool_call}
                   ▼
┌──────────────────────────────────────────────────────┐
│  Node C: 本地 Windows PC (RTX 4060 8GB)               │
│  Python Agent + 字幕 + 音频播放 + Claude Code CLI     │
└──────────────────┬───────────────────────────────────┘
                   │ jp_text (TTS 请求)
                   ▼
┌──────────────────────────────────────────────────────┐
│  Node B: 学校服务器 gpu-108                           │
│  3× Quadro RTX 8000, K8s 集群                        │
│  训练后部署 TTS API (FastAPI + GPT-SoVITS/VITS)       │
│  Cloudflare Tunnel (HTTPS 443) → 公网                 │
└──────────────────────────────────────────────────────┘
```
