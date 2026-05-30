# Anime-Agent-Infer 新手指南

> 面向初学者 — 逐个文件解释 + 基础原理

---

## 这个项目是做什么的

把《美少女万華鏡5》中的角色 **莲华（蓮華 / Renge）** 做成一个桌面 AI 助手。

说一句话 → 莲华用日语语音回复 → 屏幕上显示双语字幕 → 如果你让它操作电脑，它还能执行系统命令。

```
你: "こんにちは" (你好)
  → AI 理解意图
  → 莲华的声线说: "ふん…何か用か？" (哼…有什么事？)
  → 屏幕显示: 日文 "ふん…何か用か？" + 中文 "哼…有什么事？"
```

---

## 文件地图

### 配置文件

| 文件 | 作用 | 你需要改什么 |
|------|------|-------------|
| `config.yaml` | 整个项目的设置中心 | API key、TTS 模式、音频设备 |
| `character_card.txt` | 莲华的人设描述（日语） | 如果想改变莲华的性格可以改这里 |
| `requirements.txt` | Python 包依赖列表 | 一般不用改 |
| `.gitignore` | 告诉 git 哪些文件不上传 | 模型权重、venv、临时文件 |

### 核心代码 (`src/`)

| 文件 | 作用 | 原理 |
|------|------|------|
| `src/main.py` | **入口文件**，把各个模块串起来 | 收到输入 → LLM → TTS → 播放 → 字幕 → 工具执行 |
| `src/llm_client.py` | 调用大模型 API | 把 `character_card.txt` 作为系统提示发给 DeepSeek，让它扮演莲华 |
| `src/tts_api.py` | 莲华语音合成（联网） | 调用 HuggingFace 上的 TTS 服务，返回 wav 音频 |
| `src/tts_client.py` | TTS 统一接口 | 根据 `config.yaml` 的设置选择用 API 还是本地模型 |
| `src/audio_io.py` | 录音和播放 | 用 sounddevice 库操作麦克风和扬声器 |
| `src/subtitle.py` | 双语字幕窗口 | tkinter 半透明置顶窗口，日文白字+中文灰字 |
| `src/tool_executor.py` | 执行系统命令 | 调用 Claude Code CLI，沙盒模式防误操作 |

### Demo 脚本

| 文件 | 作用 | 运行命令 |
|------|------|---------|
| `demo_v4.py` | 本地 TTS（离线，通用日语女声） | `.venv/Scripts/python.exe demo_v4.py --text "こんにちは"` |
| `quick_demo.py` | 测试 SoVITS 模型能否加载 | `.venv/Scripts/python.exe quick_demo.py` |
| `convert_ckpt.py` | 转换模型格式 | `.venv/Scripts/python.exe convert_ckpt.py` |
| `run_demo.py` | 完整 TTS 流水线测试 | `.venv/Scripts/python.exe run_demo.py` |

### 文档

| 文件 | 内容 |
|------|------|
| `README.md` | 项目概览和快速开始 |
| `CLAUDE.md` | 给 Claude Code 看的开发备忘录 |
| `ARCHITECTURE.md` | 系统架构设计文档 |
| `WORKFLOW.md` | 完整开发过程记录（踩坑日志） |
| `GUIDE.md` | 本文件 — 新手指南 |

### 数据目录（不在 git 中）

| 目录 | 内容 |
|------|------|
| `莲华模型/` | 莲华 v1 GPT-SoVITS 权重（不兼容当前代码） |
| `moe_tts_models/` | skytnt/moe-tts slot 4 VITS 模型（454MB） |
| `GPT-SoVITS/` | GPT-SoVITS 开源代码（git clone 获取） |
| `.venv/` | Python 虚拟环境 |

---

## 基础原理

### 1. 大语言模型 (LLM) 是怎么扮演莲华的

```
System Prompt (character_card.txt)
  ↓ 告诉 AI "你是莲华，用这个格式回答"
用户消息 "こんにちは"
  ↓
DeepSeek API
  ↓ 返回 JSON
{
  "jp_text": "ふん…何か用か？",
  "zh_text": "哼…有什么事？",
  "tool_call": "",
  "emotion": "neutral"
}
```

**关键技巧**: 在 System Prompt 中强制要求输出 JSON 格式，这样程序可以直接解析，不需要从自然语言中提取信息。

### 2. TTS 是怎么合成莲华声音的

#### API 模式（推荐，需要联网）

```
日语文本 → skytnt/moe-tts HuggingFace Space
  → VITS 模型 (预先用莲华语音训练好的)
  → wav 音频（22050Hz）
```

**原理**: VITS（Variational Inference Text-to-Speech）是一个端到端模型：
- **文本编码器**: 把"こんにちは"转成音素序列（ko-n-ni-chi-wa）
- **时长预测器**: 决定每个音素念多久
- **Flow 模型**: 把音素特征映射到频谱特征
- **HiFi-GAN 解码器**: 把频谱转成音频波形
- **说话人嵌入**: 一个 256 维的向量，代表莲华的声线特征

整个过程在 GPU 上一次前向传播完成，不需要中间步骤。

#### 本地模式（离线，v4 GPT-SoVITS）

```
日语文本
  → GPT 模型 (文本→语义 token，~1500步)
  → SoVITS 模型 (语义 token→梅尔频谱)
  → BigVGAN vocoder (频谱→音频 48kHz)
```

比 VITS 慢 50 倍，但不需要联网。

### 3. 音频是怎么录和播的

```python
# 录音
import sounddevice as sd
audio = sd.rec(5 * 44100, samplerate=44100, channels=1)  # 5秒, 44.1kHz

# 播放
sd.play(audio, samplerate=44100)
sd.wait()  # 等播放完
```

静音检测：连续 1.6 秒音量低于阈值 → 自动停止录音。

### 4. 字幕窗口是怎么做到的

tkinter 创建无边框窗口：
- `overrideredirect(True)` → 没有标题栏
- `attributes("-topmost", True)` → 永远在最上面
- `attributes("-alpha", 0.85)` → 85% 不透明度
- 深蓝背景 + 日文白色粗体 + 中文灰色 + 情绪彩色

### 5. 工具执行是怎么实现的

```
LLM 返回:
  "tool_call": "把桌面文件按类型整理到文件夹"

  → subprocess: claude -p "把桌面文件按类型整理到文件夹"
  → Claude Code CLI 执行
  → 结果返回给 Agent
```

**安全机制**: `config.yaml` 中 `tool.sandbox_mode: true` 时，只打印命令不执行。

---

## 从游戏提取训练数据

本项目的莲华语音数据是从《美少女万華鏡5》游戏文件中提取的：

```
游戏安装目录
  └── GameData/data8.pack      ← QLIE 加密压缩包
        ↓ filepack31.exe unpack
      scenario/本編/*.s         ← UTF-16LE 脚本文件
        ↓ 正则解析 ％rengNNNN％
      reng0001.ogg ↔ "「……馬鹿」"  ← 3516 对语音↔文本
```

**工具链**:
- **GARbro**: 识别 QLIE (FilePackVer3.0) 格式
- **filepack31.exe**: 解包/封包 .pack 文件
- **Python**: 解析 .s 脚本（UTF-16LE 编码，全角 ％ 分隔符）

---

## 快速上手

```bash
# 1. 桌面 Agent（推荐）
.venv/Scripts/python.exe agent_gui.py
# 右下角悬浮窗，输入即对话。点击 ⚙ 配置 LLM API Key。

# 2. 直接 TTS
.venv/Scripts/python.exe -c "from src.tts_api import RengeTTS; RengeTTS('莲华').save('こんにちは','h.wav')"

# 3. 打包 EXE
build_exe.bat
# → dist/RengeAgent.exe 可直接运行

# 4. 离线测试（无 API）
.venv/Scripts/python.exe test_agent.py --text "こんにちは"
```

### 设置面板说明

点击悬浮窗右上角 ⚙ 齿轮：

| 标签页 | 功能 |
|--------|------|
| **LLM** | 提供商选择：DeepSeek / Claude / OpenAI / **Ollama(本地)** / 自定义 API。配 API Key + Model |
| **角色卡** | 可编辑 System Prompt，支持自定义人设（默认莲华） |
| **TTS** | API(skytnt/moe-tts) / 本地 VITS 模型路径 |
| **音频** | 0~100% 音量滑块 |

设置自动保存到 `agent_settings.json`。

---

## 常见问题

**Q: 为什么 API 模式比本地模式快那么多？**
A: API 用的是 VITS 单阶段模型（文本直接生成音频），本地模式是 GPT-SoVITS 两阶段（先语义 token 再合成）。VITS 一次推理，GPT-SoVITS 需要 1500 步自回归生成。

**Q: 莲华的 v1 权重为什么不能用？**
A: 你的 `G.莲华22240.pth` 是用 GPT-SoVITS v1 训练的，但当前代码是 v2/v3/v4。v1 用嵌入表查声纹，v2 用参考音频提取声纹，架构完全不同。详见 `WORKFLOW.md`。

**Q: 训练需要多少数据？**
A: GPT-SoVITS 建议 5-30 分钟。你的 3516 条莲华语音（~12 分钟）刚好够。VITS 微调需要更少，几百条就能看到效果。
