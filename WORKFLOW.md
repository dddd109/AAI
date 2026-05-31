# Phase 1 工作流程与问题总结

> 2026-05-27 ~ 2026-05-31 | 目标: 莲华 TTS 语音 → VITS 微调 → LLM 部署 → Agent GUI
>
> **GitHub**: https://github.com/dddd109/AAI
> **服务器**: `ssh gdut` (10.200.168.108:22)

---

## 当前架构

```
┌─ 本地 Windows ─────────────────────┐
│  agent_gui.py   (tkinter 悬浮窗)     │
│  ├─ LLM  ── SSH隧道 ──→ gdut GPU1  │
│  ├─ TTS  ── API / 本地VITS         │
│  └─ Audio 播放 + 双语字幕            │
│                                     │
│  proxy_server.py (Flask :8787)      │
│  └─ Anthropic→OpenAI 翻译 (备用)     │
└─────────────────────────────────────┘
         │ SSH: localhost:8080 → gdut:8081
         │
┌─ 学校服务器 gdut ───────────────────┐
│  GPU 0: 他人使用 (~31GB)            │
│  GPU 1: LLM 懒加载 (Qwen-32B, 29GB) │
│  GPU 2: VITS 训练 (~2.8GB)          │
│                                     │
│  lazy_server.py :8081               │
│  └─ 按需启动 llama.cpp → 5分钟空闲  │
│     自动卸载 GPU                     │
│                                     │
│  vits_finetune/ (tmux session)      │
│  ├─ train_genonly.py                │
│  └─ 3303 条, segment=16384 (0.75s)  │
│      batch=2, ~3.6it/s, 300 epochs  │
└─────────────────────────────────────┘
```

---

## 时间线

### Day 1-2 (05-27 ~ 05-28): 环境搭建 + 游戏数据提取

- Phase 1 模块编写 (llm_client, tts_client, audio_io, subtitle, tool_executor)
- GPT-SoVITS v1/v2 架构差异分析 → 放弃 v1 莲华权重
- skytnt/moe-tts API 发现 → 莲华本人语音可用
- 5 部万华镜游戏数据提取 → 19,875 条语音+文本 (莲华 3,670 条)
- 数据集上传 HuggingFace: `daffae/biman-voice-dataset`

### Day 3 (05-29): VITS 训练尝试

- 多次 VITS 训练尝试失败: GPT-SoVITS phoneme 不兼容、spectrogram 维度 bug、模型坍缩
- 最终采用 SayaSS vits-finetuning 方案 + skytnt 预训练模型

### Day 4 (05-30): Agent GUI + LLM 部署

- agent_gui.py 桌面悬浮窗完成
- 服务器部署 Qwen-2.5-Coder-32B GGUF (Q4_K_M, 18GB)
- SSH 隧道 + Flask 代理 → Agent GUI / Claude Code 可连
- 发现 VITS 训练数据解析 bug 并修复

### Day 5 (05-31): 训练修复 + 懒加载 + 完善

- **关键发现**: 训练音频未归一化 (int16 范围 → 需要 `a / 32768`)
- **数据解析 bug**: `split('|', 1)` → 文本含 `0|` 前缀
- **Duration 问题**: segment_size=8192 (0.37s) 太短，长句硬塞导致语速 3x 加速 → 改为 16384 (0.75s) + 随机裁剪
- 修复后 loss 从 ~260 降到 ~17 (正常范围)
- 实现 LLM 懒加载: 有请求时启动，5分钟无请求自动释放 GPU
- 角色卡升级: 基于萌娘百科详细人设，1745 字日文系统提示
- GUI 添加推理计时器
- LLM provider 添加 "学校服务器 Qwen-32B" 一键选项
- **训练改为 tmux 运行**，SSH 断开不中断

### Day 6 (06-01): 稳定性改进

- 服务器代码同步到 GitHub (`server/` 目录)
- 尝试 Ollama (需 sudo, 放弃) → 改用自建 lazy_server.py
- SSH 隧道简化: 移除自动 LocalForward，按需使用 `ssh -f -N gdut-tunnel`
- 训练适配: segment_size 增大避免 duration 压缩，随机裁剪增加多样性

---

## TTS 方案矩阵

| 方案 | 声音 | 速度 | 联网 | 状态 |
|------|------|:---:|:---:|:---:|
| **API** (skytnt/moe-tts) | 莲华本人 | ~3-5s | 需要 | ✅ 可用 |
| **本地 VITS 原版** (slot 4) | 莲华本人 | <1s | 不需要 | ✅ 可用 |
| **VITS 微调** (gdut GPU2) | 莲华(增强) | <1s | 不需要 | ⏳ 训练中 E8, loss 17↓ |
| **本地 v4** (GPT-SoVITS) | 通用女声 | ~50s | 不需要 | ✅ 可用 |
| v1 莲华权重 | 莲华 | - | - | ❌ 架构不兼容 |

---

## LLM 方案

| 方案 | 模型 | 显存 | 速度 | 状态 |
|------|------|:---:|:---:|:---:|
| **学校服务器** | Qwen-2.5-Coder-32B | 29GB | ~2-5s | ✅ 懒加载 |
| DeepSeek API | deepseek-chat | - | ~2s | ✅ 需 key |
| Claude API | claude-3-opus | - | ~3s | ✅ 需 key |
| Claude Code 代理 | Qwen-32B (via proxy) | - | ~2-5s | ⚠️ 需启动代理 |

### LLM 服务器连接方式

```
Agent GUI: 设置→LLM→选择 "🏫 学校服务器 Qwen-32B" → 自动连 localhost:8080/v1

Claude Code (需代理):
  1. 开终端: ssh -f -N gdut-tunnel
  2. 开另一个: C:/Users/AD/.conda/envs/torch/python.exe proxy_server.py 8787
  3. 设置环境: ANTHROPIC_BASE_URL=http://localhost:8787 ANTHROPIC_API_KEY=not-needed claude
```

---

## VITS 微调技术细节

### 训练配置

| 参数 | 值 |
|------|------|
| 代码 | `~/vits_finetune/train_genonly.py` (generator-only, 无判别器) |
| 基模型 | skytnt slot 4 model.pth (455MB, 6 角色, 41 音素) |
| 数据 | 3,303 条莲华 (游戏1-5), 22050Hz WAV |
| 参数 | batch=2, lr=2e-4, AdamW, ExponentialLR(0.999875), 300 epochs |
| Segment | 16384 样本 (0.75s), 随机裁剪 |
| GPU | GPU 2 (Quadro RTX 8000 48GB), ~3.6 it/s, ~7.5min/epoch |
| 进程管理 | **tmux** (session: `vits`), SSH 断开不中断 |
| Checkpoint | 每 30 epoch 保存到 `output_gen/ft_e30.pth` |

### 发现并修复的关键 Bug

| # | Bug | 症状 | 修复 |
|---|-----|------|------|
| 1 | `split('|', 1)` 只切 2 段 | 文本包含 `0|` 前缀 → 模型学垃圾数据 | `split('|', 2)` 取 parts[0] 和 parts[2] |
| 2 | 音频未归一化 | int16 范围(±30000)喂给期望[-1,1]的模型 → loss ~260 且不收敛 | `a = a / hps["data"]["max_wav_value"]` |
| 3 | spectrogram 维度 bug | decoder 输出 [B,1,T] 直接算 mel → 维度不对 | `yh_spec = spectrogram_torch(y_hat.squeeze(1))` |
| 4 | 多进程冲突 | `nohup` 被 SSH 断连杀死 | 改用 `setsid` + `disown` |

### Loss 变化

```
修复前 (bug 1+2): E1=260, E50=229 (降得很慢)
修复后: E1=21, E2=19.4, E5=17.4, E8=17.5 (正常下降)
```

---

## 服务器资源

| 资源 | 路径 |
|------|------|
| GitHub | https://github.com/dddd109/AAI |
| 服务器 SSH | `ssh gdut` (10.200.168.108:22) |
| VITS 训练 | `~/vits_finetune/` — `train_genonly.py` (GPU 2) |
| 训练输出 | `~/vits_finetune/output_gen/ft_e{30,60,90...}.pth` |
| LLM 模型 | `~/llm/qwen2.5-coder-32b-q4_k_m.gguf` (18GB) |
| LLM 懒加载 | `~/llm/lazy_server.py` (:8081 → 自动管理 llama.cpp) |
| 训练数据 | `~/anime-agent-infer/data/reng_wavs/` |
| 预训练模型 | `~/vits_finetune/checkpoints/G_0.pth` (skytnt 原版) |

### 监控命令

```bash
# 训练进度 (tmux)
ssh gdut "tmux capture-pane -t vits -p | grep 'E[0-9]*: avg'"

# 实时查看训练
ssh gdut -t tmux attach -t vits
# (Ctrl+B D 退出但不中断训练)

# GPU 状态
ssh gdut "nvidia-smi --query-gpu=index,memory.used --format=csv,noheader"

# LLM 服务器日志
ssh gdut "tail -10 ~/llm/lazy.log"

# 下载最新 checkpoint
scp gdut:~/vits_finetune/output_gen/ft_e30.pth moe_tts_models/slot4/
```

---

## 游戏数据提取

### 数据来源

| 游戏 | 莲华 | 总语音 | 工具 |
|------|:---:|------:|------|
| 万华镜 1 | 51 | 2,383 | GARbro |
| 万华镜 2 | 32 | 3,285 | GARbro |
| 万华镜 3 | 55 | 6,266 | GARbro |
| 万华镜 4 | 71 | 7,520 | filepack31 + GARbro |
| 万华镜 5 | 3,501 | 3,516 | filepack31 |
| **合计** | **3,670** | **19,875** | |

### 提取流程

```
游戏 GameData/*.pack → GARbro/filepack31 解包 → .s 脚本 (UTF-16LE)
→ 正则 %voice_id% → 语音↔文本配对 → CSV
```

### 数据集

- HuggingFace: [daffae/biman-voice-dataset](https://huggingface.co/datasets/daffae/biman-voice-dataset)
- 23,073 文件 (88 CSV + 22,984 OGG)

---

## 代理设置速查

```bash
# curl
curl -x http://127.0.0.1:7897 <url>

# git
git config --global http.proxy http://127.0.0.1:7897

# pip
C:/Users/AD/.conda/envs/torch/python.exe -m pip install --proxy http://127.0.0.1:7897 <package>

# Python httpx
httpx.Client(proxy="http://127.0.0.1:7897")
```

---

## 项目文件清单

```
Anime-Agent-Infer/
├── agent_gui.py              ★ 桌面 Agent (tkinter 悬浮窗)
├── proxy_server.py           ★ Anthropic→OpenAI 翻译代理
├── start_server.bat          ★ 一键启动 SSH 隧道 + 代理
├── test_agent.py             CLI 测试
├── demo_v4.py                本地 GPT-SoVITS v4 TTS
├── upload_hf.py              HF 数据集上传
├── build_exe.bat             PyInstaller 打包
│
├── config.yaml               全局配置
├── agent_settings.json       GUI 运行时配置 (自动生成)
├── character_card.txt        旧角色卡 (已被 agent_gui.py 内置版替代)
│
├── src/                      Phase 1 模块
│   ├── tts_api.py            莲华 TTS API 客户端
│   ├── tts_client.py         TTS 统一接口 (api/local/mock)
│   ├── llm_client.py         LLM API 客户端
│   ├── audio_io.py           录音+播放
│   ├── subtitle.py           tkinter 字幕覆盖层
│   ├── tool_executor.py      Claude Code CLI 沙盒
│   └── main.py               Agent 流水线
│
├── vits_infer/               VITS 推理代码 (从 skytnt Space)
├── moe_tts_models/           VITS 模型 (gitignored)
│   └── slot4/
│       ├── model.pth         455MB 原版 skytnt 模型
│       ├── config.json       6 说话人配置
│       └── ft_e*.pth         微调 checkpoint
│
├── README.md                 ★ 项目概览
├── CLAUDE.md                 ★ Claude Code 开发指南
├── ARCHITECTURE.md           架构设计
├── WORKFLOW.md               本文件 (工作流程)
├── PROJECT_REPORT.md         项目完整报告
└── GUIDE.md                  新手指南
```

---

## GPT-SoVITS v1 为什么不能用

| | v1 (莲华权重) | v2+ (当前代码) |
|---|---|---|
| 文本编码 | `enc_p.proj` + `enc_p.enc_` (6层) | `enc_p.ssl_proj` + `enc_p.encoder_ssl` |
| 声纹 | `emb_g` 嵌入表 | `ref_enc` (mel 参考编码) |
| SSL | 无 (256-dim gin) | 768-dim CNHubert |
| 推理 | 直接 | VQ 残差量化器 |

362 keys missing, 234 unexpected — 无法通过重命名修复。

---

## 本地环境

| | 本地 | 服务器 (gdut) |
|---|---|---|
| GPU | RTX 4060 Laptop 8GB (Ada) | Quadro RTX 8000 ×3 48GB (Turing) |
| CPU | i7-13650HX | Xeon Silver 4216 64-core |
| Python | 3.9 (torch conda) | 3.10 (py310 conda) |
| CUDA | Toolkit 13.2 / PyTorch 12.1 | Driver 550.135 / CUDA 12.4 |
| 代理 | Clash 127.0.0.1:7897 | — |
| 路径 | `C:/Users/AD/.conda/envs/torch/` | `~/.conda/envs/py310/` |
