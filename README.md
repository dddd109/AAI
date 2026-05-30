# Anime-Agent-Infer

高性能跨设备二次元桌面智能体 — 以《美少女万華鏡5》莲华为看板娘。

**架构**: 云端 LLM 大脑 + TTS 语音 + 本地 C++/CUDA 引擎 + Claude Code 系统自动化。

## 快速开始

```bash
# 1. 环境
.venv/Scripts/python.exe --version  # Python 3.12 + torch 2.5.1+cu121

# 2. 桌面 Agent（推荐）— 右下角悬浮窗，输入即对话
.venv/Scripts/python.exe agent_gui.py

# 3. 命令行测试
.venv/Scripts/python.exe test_agent.py --text "こんにちは"

# 4. 直接 TTS
.venv/Scripts/python.exe -c "from src.tts_api import RengeTTS; RengeTTS('莲华').save('こんにちは', 'h.wav')"
```

## 项目文件

```
Anime-Agent-Infer/
├── README.md                 # 本文件
├── README_old.md             # 原始项目愿景（中文，Phase 1-3 规划）
├── CLAUDE.md                 # Claude Code 开发指南
├── ARCHITECTURE.md           # 系统架构与设计文档
├── WORKFLOW.md               # Phase 1 工作流程与踩坑记录
│
├── config.yaml               # 全局配置（LLM / TTS / Audio / Tool）
├── requirements.txt          # Python 依赖
├── character_card.txt        # 莲华角色卡 System Prompt（日文）
│
├── src/                      # Phase 1 源码
│   ├── main.py               # 主流水线 & 交互 REPL
│   ├── llm_client.py         # LLM API 客户端（DeepSeek / Claude）
│   ├── tts_api.py            # 莲华 TTS API 客户端（skytnt/moe-tts）
│   ├── tts_client.py         # TTS 统一客户端（api / local / remote / mock）
│   ├── audio_io.py           # 麦克风录音 & 音频播放
│   ├── subtitle.py           # 双语字幕覆盖层（tkinter）
│   └── tool_executor.py      # Claude Code CLI 沙盒执行
│
├── agent_gui.py              # ★ 桌面 Agent（右下角悬浮窗）
├── test_agent.py             # CLI 测试工具
├── test_ft_model.py          # 微调模型本地推理测试
├── demo_v4.py                # 本地 GPT-SoVITS v4 TTS
├── upload_hf.py              # HuggingFace 数据集上传
│
├── vits_infer/               # VITS 推理代码（从 skytnt Space）
├── 莲华模型/                  # 莲华 GPT-SoVITS v1 权重（gitignored）
└── moe_tts_models/           # VITS 预训练+微调模型（gitignored）
```

## TTS 方案对比

| 方案 | 声音 | 速度 | 联网 | 状态 |
|------|------|------|------|------|
| **API (skytnt/moe-tts)** | 莲华本人 | ~3s | 需要 | 可用 |
| **本地 VITS 原始模型** | 莲华本人 | <1s | 不需要 | 可用 |
| **本地 VITS 微调** | 莲华（增强） | <1s | 不需要 | 训练中 (gdut GPU2) |
| **本地 v4** | 通用日语女声 | ~48s | 不需要 | 可用 |

## 训练数据

从《美少女万華鏡》全系列 5 部提取：莲华 3,670 条，全部角色 19,875 条。
详见 `PROJECT_REPORT.md` 和 `WORKFLOW.md`。

## 完整项目报告

见 [PROJECT_REPORT.md](PROJECT_REPORT.md) — 包含所有文件、模型状态、训练历程、服务器详情。

## 关键已知问题

1. **莲华 v1 权重与当前 GPT-SoVITS v2/v3/v4 代码不兼容** — 网络结构差异（v1: `emb_g` + `enc_p.proj`, v2: SSL + `encoder_ssl`），362 个 key 无法匹配
2. **GPT-SoVITS 预训练模型下载** — 本地慢（~20KB/s），需通过学校服务器 SCP（~20MB/s）：`ssh gdut`
3. **transformers torch>=2.6 检查** — 用 monkey-patch 绕过（`demo_v4.py` 中已处理）
4. **torch.distributed 单 GPU** — `core_vq.py` 需加 `is_initialized()` 守卫（已修改）

## 环境

| | 本地 | 服务器  |
|---|---|---|
| GPU | RTX 4060 Laptop 8GB | Quadro RTX 8000 ×3 48GB |
| Python | 3.12.7 (venv) | 3.10.12 |
| CUDA | Toolkit 13.2 / PyTorch 12.1 | Driver 550.135 / CUDA 12.4 |
| 代理 | Clash 127.0.0.1:7897 | — |

## 训练数据

从《美少女万華鏡》全系列 5 部游戏提取：
- **莲华**: 3,670 条语音+文本 (含游戏1-5全部出场)
- **全部角色**: 19,875 条, 90 个角色
- 格式: OGG 44.1kHz mono, CSV 配对

## 相关链接

- 数据集: [HuggingFace](https://huggingface.co/datasets/daffae/biman-voice-dataset)
- TTS API: [skytnt/moe-tts](https://huggingface.co/spaces/skytnt/moe-tts) — VITS 多角色 TTS（含莲华）
- 角色配音插件: [SonderXiaoming/youzi_voice](https://github.com/SonderXiaoming/youzi_voice)
- GPT-SoVITS: [RVC-Boss/GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
- 莲华模型训练者: [Francis-Komizu](https://github.com/Francis-Komizu/)
