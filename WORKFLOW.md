# Phase 1 工作流程与问题总结

> 2026-05-27 ~ 2026-05-29 | 目标: 莲华 TTS 语音输出 → VITS 微调训练
>
> **GitHub**: https://github.com/dddd109/AAI
> **服务器**: `ssh gdut` → `~/vits_renge/` (训练中) | `~/anime-agent-infer/` (数据+模型)

---

## 时间线

```
Day 1 (05-27)
  13:00  启动 Phase 1，SSH 检查学校服务器 (3× Quadro RTX 8000 48GB)
  13:20  写 Phase 1 模块 (llm_client, tts_client, audio_io, subtitle, tool_executor)
  13:30  conda create 被限流 → 改用 Python 3.12 venv (--system-site-packages)
  13:40  Clone GPT-SoVITS，开始装依赖
  14:00  莲华 checkpoint 转换 (训练格式 → 推理格式 sovits_renge.pth)
  14:10  发现 v1/v2 架构不匹配 (362 missing keys)
  14:20  尝试下载预训练模型 — HF/hf-mirror/modelscope 全部阻塞
  14:40  学校服务器 curl hf-mirror → 6 秒下完，SCP 到本地
  14:50  逐层修复依赖冲突
  15:30  MRTE 维度不匹配 (512 vs 256) → 确认 v1/v2 架构级差异

  16:30  转向 v2 代码 + v2 预训练模型，修复 core_vq.py / kaldi mock
  17:00  v4 预训练模型全部匹配！但推理卡在 fast-langdetect
  17:30  修复 dist / VQ / transformers 等一连串问题
  17:55  v4 demo 成功！5.3s 日语语音输出

  18:40  发现 youzi_voice → skytnt/moe-tts API 有莲华本人声音
  19:00  调通 API: speaker=蓮華, fn_index=12 → 但实际是 DRACU-RIOT! slot
  19:05  找到正确 slot 4 (美少女万華鏡, 454MB, 6 角色含莲华)
  19:10  API 莲华语音测试通过，写 src/tts_api.py
  19:20  下载 moe_tts slot 4 模型 (454MB VITS) 备用本地推理

  19:30  整理项目、写 README/CLAUDE.md/WORKFLOW.md
  20:00  git 清理：.venv/ + 模型权重误提交 1.47GB → filter-branch → 48KB
  20:10  SSH key 配置，push 到 GitHub

Day 2 (05-28)
  补充: 清理学校服务器 ~/tts_models/ (3.1GB)

Day 3 (05-29)
  13:30  发现 美少女万華鏡5 语音包 D:\ボイス.7z (3516 个 ogg, 529MB)
  13:35  分析音频: 44.1kHz mono, 平均 3.5s/条, 总时长 ~12 分钟
  13:40  用 GARbro + filepack31 解包 game data8.pack
  13:45  解析 .s 脚本文件 (UTF-16LE, 全角%分隔符)
  13:50  提取 3501 条语音→文本配对 (99.6% 覆盖率!)

  14:00  配置学校服务器 py310 环境
  14:20  上传训练数据到 gdut
  14:30  尝试 GPT-SoVITS Stage 1 训练 → vocab 不匹配 (英文 phoneme 表)
  14:45  转向 VITS 微调方案 (skytnt/moe-tts slot 4)
  15:00  下载 VITS 代码, 上传 454MB 预训练模型
  15:10  VITS 模型加载 + 推理测试通过
  15:15  写 VITS 微调脚本, 修复 spectrogram/dtype/forward 等 bug
  15:25  VITS 微调训练启动! GPU 2, 100 epochs, ~30 min/epoch

  18:30  发现 D:/GAL 下全部 5 部万华镜游戏本体
  18:40  用 filepack31 解包游戏 4 data7/data8 (221 .s 文件)
  18:45  用 GARbro 解包游戏 1-3
  19:00  解析全部脚本: 5 种不同的 %voice_id% 格式
  19:15  提取全部音频: 19875 条 .ogg 文件
  19:30  按角色分类: 90 个角色, 音频↔文本配对完成
  19:40  莲华: 3670 条 (合并 reng + renk)

## 完整数据集

```
D:/GAL_unpack/dataset/
├── reng.csv          ★ 莲华 3670 条 (游戏1-5)
├── yuma.csv           覡夕摩 3074 条
├── yuri.csv           覡夕莉 2631 条
├── alic.csv           アリス 2537 条
├── doro.csv           ドロシー 2392 条
├── kiri.csv           キリエ 2255 条
└── ... 90 角色 19875 条总计
```

每行: `game, voice_id, audio_path, text`
```

## 最终 TTS 方案

| 方案 | 文件 | 声音 | 速度 | 联网 | 状态 |
|------|------|------|------|------|------|
| **API** | `src/tts_api.py` | 莲华本人 | ~5s | 需要 | 可用 |
| **本地 v4** | `demo_v4.py` | 通用女声 | ~50s | 不需要 | 可用 |
| **VITS 微调** | gdut 训练中 | 莲华本人 | <1s | 不需要 | 训练中 |
| v1 莲华权重 | `莲华模型/` | 莲华 | - | 不需要 | 架构不兼容 |

## 服务器地址

| 资源 | 路径 |
|------|------|
| GitHub | https://github.com/dddd109/AAI |
| 服务器 SSH | `ssh gdut` (10.200.168.108:22) |
| VITS 训练 | `~/vits_renge/` (GPU 2, 100 epochs) |
| 训练数据 | `~/anime-agent-infer/data/` |
| 预训练模型 | `~/anime-agent-infer/models/` |
| GPT-SoVITS | `~/GPT-SoVITS/` |
```

## 问题树

```
目标: 莲华语音输出
│
├─[1] 环境
│   ├─ conda HTTP 429 → venv (Python 3.12) ✓
│   └─ venv Python 3.9 → 换 base Python 3.12 ✓
│
├─[2] 依赖冲突
│   ├─ opencc 编译失败 → 跳过 (日文不需要)
│   ├─ fasttext 编译失败 → fasttext-wheel ✓
│   ├─ numpy 2.x vs torchmetrics → 降级 1.26.4 ✓
│   ├─ typing_extensions (4.9 vs 4.14+) → 升级 ✓
│   └─ transformers torch>=2.6 → monkey-patch ✓
│
├─[3] 模型下载
│   ├─ HF/hf-mirror/modelscope 均阻塞
│   └─ curl -x proxy 直接下载 → 慢但可用 ✓
│
├─[4] v1 莲华权重 (阻塞)
│   ├─ Checkpoint 格式转换 ✓
│   ├─ config 修复 (n_speakers, extra keys) ✓
│   └─ MRTE 维度不匹配 → v1/v2 架构差异，放弃
│
├─[5] v4 预训练模型 (成功)
│   ├─ s1v3.ckpt + s2Gv4.pth 全部匹配 ✓
│   ├─ core_vq.py dist 守卫 ✓
│   ├─ kaldi mock ✓
│   ├─ fast-langdetect 目录 + fasttext 模型下载 ✓
│   └─ demo_v4.py: 5.3s 日语语音 ✓
│
├─[6] skytnt/moe-tts API (莲华本人声音)
│   ├─ youzi_voice bot → API endpoint ✓
│   ├─ slot 12 不是美少女万華鏡 (是 DRACU-RIOT!)
│   ├─ slot 4 = 美少女万華鏡 (莲华+5 角色, VITS 454MB) ✓
│   └─ src/tts_api.py 完成 ✓
│
├─[7] Git 推不上去
│   ├─ .venv/ + 模型权重误提交 → 1.47GB 历史
│   ├─ git gc --prune=now → 48KB ✓
│   └─ SSH key → GitHub → push ✓
│
└─[8] 莲华训练数据提取 (Day 3)
    ├─ 语音包 D:\ボイス.7z → 3516 ogg, 12min ✓
    ├─ 识别游戏引擎: QLIE (FilePackVer3.0) ✓
    ├─ 解包工具: GARbro / filepack31 ✓
    ├─ 脚本编码: UTF-16LE, 全角%分隔符 ✓
    └─ 提取 3501 对 语音→文本 ✓
```

## 最终 TTS 方案

| 方案 | 文件 | 声音 | 速度 | 状态 |
|------|------|------|------|------|
| **API** | `src/tts_api.py` | 莲华本人 | ~5s | 可用 |
| **本地 v4** | `demo_v4.py` | 通用女声 | ~50s | 可用 |
| v1 莲华权重 | `莲华模型/` | 莲华 | - | 架构不兼容 |
| **莲华训练** | 数据就绪 | 莲华本人 | 待训练 | 3501 对 |

---

## Day 3 详解：游戏语音数据提取

### 数据来源

- **游戏**: 美少女万華鏡5 - 理と迷宮の少女 (ωstar, 2020)
- **语音包**: `D:\ボイス.7z` (511MB 压缩, 529MB 解压)
- **文件**: `reng0001.ogg` ~ `reng3516.ogg` (3516 个文件)
- **格式**: OGG Vorbis, 44100Hz, mono, 平均 3.5s/条, 总时长 ~12 分钟
- **游戏本体**: `D:\GAL\美少女万华镜5-理与迷宫的少女\`

### 工具链

| 工具 | 版本/来源 | 用途 | 原理 |
|------|----------|------|------|
| **GARbro** | [morkt/GARbro](https://github.com/morkt/GARbro) v1.5.44 | 识别游戏资源格式 | 通过文件头签名匹配已知引擎格式，本游戏使用 QLIE (FilePackVer3.0) |
| **filepack31.exe** | 汉化补丁中的工具 | 解包/封包 .pack 文件 | QLIE 引擎专用 CLI 工具：`filepack31 unpack <in.pack> <out_dir>` |
| **7za.exe** | 汉化补丁附带 | 分卷解压 | 汉化补丁分发时使用 7z 分卷 |
| **Python** | venv 3.12 | 解析 .s 脚本文件 | 读取 UTF-16LE 编码，正则匹配全角 `%rengNNNN%` 标记 |

### 解包流程

```
美少女万華鏡5 游戏目录
├── GameData/
│   ├── data0.pack ~ data9.pack    ← QLIE 封包格式
│   └── System/
│
1. 识别格式
   GARbro 读取 data8.pack 文件头 → 识别为 "FilePackVer3.0" (QLIE 引擎)
   
2. 解包
   filepack31.exe unpack data8.pack ./output/
   → 输出 scenario/ 目录，含 .s 脚本文件
   
3. 解析脚本
   .s 文件 = UTF-16LE 编码的文本
   对话行格式:
      【蓮華】        ← 角色名标记
      ％reng0105％    ← 语音文件引用（全角％ U+FF05）
      「……」         ← 下一行是对话文本
```

### .s 脚本文件格式

```python
# 编码: UTF-16 Little Endian
# 行分隔: \r (CR)
# 语音引用: ％rengNNNN％ (全角百分号 U+FF05)

# 实际解析逻辑
with open('scenario/本編/k01_01.s', 'rb') as f:
    text = f.read().decode('utf-16-le')
    for i, line in enumerate(text.split('\n')):
        m = re.search(r'％reng(\d{4})％', line)
        if m:
            voice_id = f'reng{m.group(1)}'   # e.g. reng0105
            dialogue = lines[i + 1].strip()   # 下一行是台词
```

### 识别引擎格式的方法

1. 看 DLL 目录 — `wuvorbis.dll` (OGG 解码器) 暗示 QLIE/CatSystem2 引擎
2. 看 .pack 文件头 — `81 3f 3c 19 ...` 是 QLIE 加密特征
3. GARbro 内置 300+ 引擎签名库，自动匹配

### 提取结果

| 指标 | 值 |
|------|------|
| 语音文件 | 3516 个 OGG |
| 成功配对 | **3501 条** (99.6%) |
| 总文本量 | ~93,000 字 |
| 输出文件 | `D:\GAL_unpack\renge_transcripts.csv` |
| 格式 | `reng0001.ogg,「……」` (CSV UTF-8 BOM) |
| 文本长度 | min=3, max=100, avg=27 字 |
| 未配对 | 15 个 (可能是系统音效/无台词语音) |

### 为什么会有 15 条未配对

- 游戏脚本中某些语音引用使用了不同的命名格式
- 可能有语音文件在 data8.pack 以外的其他 pack 中
- 可能是呼吸声/语气音等无台词语音

---

## 架构发现

### 莲华 v1 权重 vs GPT-SoVITS v2 代码

不是 key 重命名能解决的差异：

| | v1 (莲华权重) | v2 (当前代码) |
|---|---|---|
| 文本编码 | `enc_p.proj` + `enc_p.enc_` (6 层) | `enc_p.ssl_proj` + `enc_p.encoder_ssl` + `enc_p.encoder_text` |
| 声纹 | `emb_g` 嵌入表 | `ref_enc` (mel 参考编码) |
| SSL | 无 (256-dim gin) | 768-dim CNHubert |
| 量化 | 无 | VQ ResidualVectorQuantizer |
| 注意力 | 自注意力 | MRTE 交叉注意力 (512-dim) |

### skytnt/moe-tts 模型结构

HuggingFace Space，21 个模型槽位，每个是独立的多说话人 VITS：

- **Slot 4: 美少女万華鏡** — 莲华 + 篝之雾枝 + 沢渡雫 + 亚璃子 + 灯露椎 + 覡夕莉 (454MB)
- Slot 0: 柚子社 (サノバウィッチ/千恋万花/RIDDLE JOKER)
- Slot 15: Voistock (2891 个角色)
- 推理: `model.infer(text_tokens, lengths, sid=speaker_id)`

### QLIE 引擎 (FilePackVer3.0)

美少女万華鏡系列使用的视觉小说引擎。.pack 文件是 QLIE 格式的加密压缩包，包含：
- 图片 (`.png` / `.webp`)
- 音频 (`.ogg` - 语音, `.wav` - 效果音)
- 脚本 (`.s` - UTF-16LE 编码的游戏逻辑/对话)
- 字体、配置文件等

解包工具 `filepack31.exe` 的工作原理：
1. 读取 `pack_keyfile_*.key` 获取解密密钥
2. 解密文件索引表
3. 逐文件解压输出到目标目录
4. 反向操作 `enpack` 可将修改后的文件重新封包

## 代理设置速查

```bash
# curl
curl -x http://127.0.0.1:7897 <url>

# git
git config --global http.proxy http://127.0.0.1:7897

# pip
pip install --proxy http://127.0.0.1:7897 <package>

# Python httpx
httpx.Client(proxy="http://127.0.0.1:7897")
```

## 可用脚本

| 脚本 | 命令 | 结果 |
|------|------|------|
| **tts_api** | `.venv/Scripts/python.exe -c "from src.tts_api import RengeTTS; RengeTTS('莲华').save('こんにちは', 'h.wav')"` | 莲华语音 wav |
| **demo_v4** | `.venv/Scripts/python.exe demo_v4.py --text "こんにちは"` | 本地 v4 TTS |
| quick_demo | `.venv/Scripts/python.exe quick_demo.py` | SoVITS 声纹测试 |
| convert_ckpt | `.venv/Scripts/python.exe convert_ckpt.py` | 训练→推理格式 |
| main | `.venv/Scripts/python.exe -m src.main` | Agent 交互 REPL |

## 数据文件

| 文件 | 说明 |
|------|------|
| `D:/ボイス/` | 3516 个 OGG 莲华语音 (529MB) |
| `D:/GAL_unpack/renge_transcripts.csv` | 3501 对 语音→文本 (CSV UTF-8) |
| `D:/GAL_unpack/data8/scenario/` | 游戏脚本文件 (.s, UTF-16LE) |
