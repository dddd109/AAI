# Anime-Agent-Infer 项目完整报告

> 2026-05-31 | 历时 4 天 | 莲华 TTS 桌面 Agent

---

## 1. 项目概述

以《美少女万華鏡5》莲华为看板娘的桌面 AI 助手。输入文本 → 莲华语音回复 + 双语字幕。

**当前可用功能**：
- 桌面悬浮窗 Agent（右下角，输入即对话）
- 莲华 TTS 语音（API 联网 + 本地推理）
- LLM 对话（DeepSeek/Claude/Ollama/自定义）
- 数据集 19,875 条（含莲华 3,670 条）
- VITS 微调训练中（epoch 193/200）

---

## 2. 文件清单

### 核心代码

| 文件 | 用途 | 状态 |
|------|------|------|
| `agent_gui.py` | 桌面 Agent 主程序 | ✅ 可用 |
| `test_agent.py` | CLI 测试工具 | ✅ 可用 |
| `demo_v4.py` | 本地 v4 TTS (离线) | ✅ 可用 |
| `upload_hf.py` | HuggingFace 数据集上传 | ✅ 可用 |
| `build_exe.bat` | 打包 EXE 脚本 | ⚠️ 需 PyInstaller |

### Phase 1 模块 (`src/`)

| 文件 | 用途 | 状态 |
|------|------|------|
| `src/tts_api.py` | skytnt/moe-tts API 客户端 | ✅ |
| `src/tts_client.py` | TTS 统一接口 (api/local/mock) | ✅ |
| `src/llm_client.py` | LLM API 客户端 | ✅ |
| `src/audio_io.py` | 录音+播放 | ✅ |
| `src/subtitle.py` | tkinter 字幕覆盖层 | ✅ |
| `src/tool_executor.py` | Claude Code CLI 执行 | ✅ |
| `src/main.py` | Agent 流水线 | ✅ |

### VITS 推理 (`vits_infer/`)

从 skytnt/moe-tts Space 下载的 VITS 推理代码（models.py, modules.py, commons.py 等）。

### 文档

| 文件 | 内容 |
|------|------|
| `README.md` | 项目概览 |
| `CLAUDE.md` | Claude Code 开发指南 |
| `GUIDE.md` | 新手指南 |
| `ARCHITECTURE.md` | 架构设计 |
| `WORKFLOW.md` | 工作流程与踩坑记录 |
| `PROJECT_REPORT.md` | 本文件 |

---

## 3. 模型状态矩阵

### 所有模型一览

| 文件 | 大小 | 类型 | 声音 | 可用？ | 原因 |
|------|------|------|------|:---:|------|
| `moe_tts_models/slot4/model.pth` | 455MB | VITS | 莲华 | ✅ | skytnt 预训练 |
| `moe_tts_models/slot4/config.json` | 2KB | config | - | ✅ | 配套 |
| `moe_tts_models/slot4/renge_ft_final.pth` | 152MB | VITS | 噪音 | ❌ | 训练坍缩 |
| `moe_tts_models/slot4/ft_e20.pth` | 341MB | VITS | 噪音 | ❌ | 训练坍缩 |
| `moe_tts_models/slot4/renge_ft_epoch10.pth` | 341MB | VITS | 噪音 | ❌ | 训练坍缩 |
| `莲华模型/G.莲华22240.pth` | 536MB | GPT-SoVITS v1 | - | ❌ | 架构不兼容 |
| `莲华模型/D.莲华222400.pth` | 561MB | GPT-SoVITS v1 | - | ❌ | 架构不兼容 |
| `莲华模型/sovits_renge.pth` | 139MB | GPT-SoVITS v1 | - | ❌ | 架构不兼容 |
| `moe_tts_models/slot4/sayashi_ft.pth` | 458MB | VITS | 噪音 | ❌ | 微调不足，仍需训练 |
| 服务器 sayashi 训练 | - | VITS | ? | ⏳ | E195/200, 需更多轮 |

### GPT-SoVITS v1 为什么不能用

莲华权重 `G/D.莲华.pth` 是用 GPT-SoVITS v1 (2023) 训练的，当前所有代码都是 v2/v3/v4。架构差异：

| | v1 | v2+ |
|---|----|-----|
| 文本编码 | `enc_p.proj` + `enc_p.enc_` | `enc_p.ssl_proj` + `enc_p.encoder_ssl` |
| 声纹 | `emb_g` 嵌入表 | `ref_enc` 参考编码 |
| SSL | 256-dim | 768-dim CNHubert |
| 推理 | 直接 | VQ 量化器 |

362 个 key 缺失，234 个不匹配。无法通过重命名解决。

---

## 4. 数据集详情

### 来源

从《美少女万華鏡》全系列 5 部游戏提取：

| 游戏 | 莲华 | 总语音 | 提取工具 |
|------|:---:|------:|------|
| 万华镜 1 | 51 | 2,383 | GARbro |
| 万华镜 2 | 32 | 3,285 | GARbro |
| 万华镜 3 | 55 | 6,266 | GARbro |
| 万华镜 4 | 71 | 7,520 | filepack31 + GARbro |
| 万华镜 5 | 3,501 | 3,516 | filepack31 |
| **合计** | **3,670** | **19,875** | |

### 提取流程

```
游戏 GameData/*.pack → GARbro/filepack31 解包 → .s 脚本(UTF-16LE/SJIS)
→ 正则 %voice_id% → 语音↔文本配对 → CSV (game,voice_id,audio_path,text)
```

### HuggingFace

[daffae/biman-voice-dataset](https://huggingface.co/datasets/daffae/biman-voice-dataset) — 23,073 文件，88 CSV + 22,984 OGG

---

## 5. 服务器 (gdut)

### 硬件

- 3× Quadro RTX 8000 48GB (Turing, SM 7.5)
- Xeon Silver 4216 64 核, 114GB RAM, 2.1TB 磁盘
- CUDA 12.4, Python 3.10, torch 2.6
- K8s 集群节点, Docker 已安装(stu001 无权限)

### 项目目录

```
~/vits_finetune/       # VITS 微调（运行中）
~/vits_renge/           # 之前的训练尝试
~/anime-agent-infer/    # 训练数据 + 模型
~/GPT-SoVITS/           # GPT-SoVITS 代码
```

### 训练命令

```bash
ssh gdut
cd ~/vits_finetune
# 监控: tail -f train.log
# 重启: pkill train_ms; nohup ~/.conda/envs/py310/bin/python train_ms.py -c configs/renge.json -m checkpoints > train.log 2>&1 &
```

---

## 6. 本地环境

### Python

| 环境 | Python | torch | CUDA | 用途 |
|------|--------|-------|------|------|
| torch conda | 3.9.23 | 2.3.1+cu118 | ✅ | **Agent 运行** |
| base conda | 3.12.7 | 2.9.1+cpu | ❌ | 备用 |

```bash
# 运行 Agent（必须用 torch env）
C:/Users/AD/.conda/envs/torch/python.exe agent_gui.py

# 安装包
C:/Users/AD/.conda/envs/torch/python.exe -m pip install <包> --proxy=http://127.0.0.1:7897
```

### GPU

- RTX 4060 Laptop 8GB (Ada, CC 8.9, 24 SMs)
- CUDA Toolkit 13.2, 驱动 580.88
- Clash 代理: 127.0.0.1:7897

---

## 7. TTS 方案对比

| 方案 | 声音 | 速度 | 联网 | 状态 |
|------|------|------|:---:|:---:|
| API (skytnt/moe-tts) | 莲华 | ~5s | 需要 | ✅ |
| 本地 VITS 原版 | 莲华 | <1s | 不需要 | ✅ |
| 本地 VITS 微调 | ? | <1s | 不需要 | ⏳ |
| 本地 v4 GPT-SoVITS | 通用女声 | ~50s | 不需要 | ✅ |
| 莲华 v1 权重 | - | - | - | ❌ |

---

## 8. 训练历程

| # | 方案 | 数据 | 结果 | 失败原因 |
|---|------|------|:---:|------|
| 1 | GPT-SoVITS s1 | 3501 | ❌ | 英文 phoneme 表，日文不兼容 |
| 2 | 自写 VITS 训练 | 3501 | ❌ | spectrogram 维度 bug，模型坍缩 |
| 3 | 自写 VITS (LR 2e-4) | 3670 | ❌ | loss 不降，model collapse |
| 4 | SayaSS 方案 | 3670 | ⏳ | 进行中 E193/200 |

### 当前训练配置（方案 4）

- **代码**: [SayaSS/vits-finetuning](https://github.com/SayaSS/vits-finetuning)
- **预训练**: sayashi's G_0.pth (804 说话人, 日语)
- **数据**: 3670 条莲华 (游戏1-5), 22050Hz WAV
- **参数**: batch=4, lr=2e-4, epochs=200, speaker_id=0
- **GPU**: gdut GPU 2, ~1.9 it/s
- **Checkpoints**: `~/drive/MyDrive/vits-finetune/checkpoints/G_*.pth`

---

## 10. LLM 服务器部署（进行中）

目标：在学校服务器部署大模型，作为莲华 Agent 和 Claude Code 的后端。

- **框架**: llama-cpp-python (已安装) → 计划换 Ollama（自动显存释放+多卡切分）
- **模型**: Qwen-2.5-Coder-32B-Instruct GGUF Q4_K_M (~19GB, 下载中)
- **GPU**: 双卡 1+2 (96GB), 单卡模式 1 卡 (48GB)
- **端口**: 8080, OpenAI 兼容 API
- **用途**: Agent 对话 + 代码辅助 + 后续微调莲华人设

### Claude Code 集成

计划用服务器 LLM 替代 Anthropic API 调用，节省 token 费用。需要：
- 本地代理层将 OpenAI API 转为 Anthropic API 格式
- 或直接让 Claude Code 用自定义 endpoint

## 11. 已知问题

1. **莲华 v1 权重不可用** — 架构不兼容，无修复计划
2. **VITS 训练难收敛** — 前 3 次尝试全部失败，第 4 次等待结果
3. **数据集只有文本无音频的游戏 1-2** — 游戏 1: 51 条莲华但有 2405 个 OGG；游戏 2: 32 条有 3285 个 OGG
4. **torch env 是 Python 3.9** — x_transformers 等新包不兼容
5. **Conda 代理问题** — 之前设置的代理导致 conda 卡死，已清除
