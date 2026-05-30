# 项目名称：Anime-Agent-Infer (高性能跨设备二次元桌面智能体推理部署系统)

## 1. 项目愿景与定位

本项目旨在构建一个低延迟、高性能、跨物理设备的桌面智能体（以《美少女万华镜5》角色“莲华”为看板娘人设）。系统拒绝依赖臃肿的 Python 深度学习框架，采用前沿的“云端大脑 + 私有算力嘴巴 + 本地高性能 C++/CUDA 躯干”的异构微服务架构，并深度集成本地系统自动化执行能力（如 Claude Code/CLI 命令行调用）。

## 2. 系统拓扑架构 (Topology Architecture)

系统由三个核心物理节点跨网络协同工作：

* **节点 A：云端认知大脑（Cognitive Brain）**
  * **底层支撑**：接入大语言模型（如 DeepSeek-V3/Claude API）。
  * **核心机制**：通过 System Prompt 注入“莲华”的傲娇、毒舌角色卡。强制输出严格的 JSON 结构化数据：`{"jp_text": "日文语音文本", "zh_text": "中文字幕文本", "tool_call": "本地系统执行指令(可选)"}`。
* **节点 B：内网私有语音服务器（TTS Core）**
  * **部署环境**：学校服务器（Quadro RTX 8000 显卡，Turing 架构）。
  * **核心技术**：部署基于 PyTorch/TensorRT 优化的 GPT-SoVITS 语音合成服务，使用《美少女万华镜5》官方莲华原声数据集微调。
  * **网络穿透**：由于校园网封禁 UDP，该节点不使用 P2P/Tailscale，而是通过 **Cloudflare Tunnels (基于 TCP/HTTPS 443 出站隧道)** 将本地 FastAPI 服务安全暴露至公网。
* **节点 C：本地控制端与高性能计算引擎（Local Client & Compute Engine）**
  * **物理设备**：本地 PC（GeForce 显卡）。
  * **核心底座**：采用 **纯 C++ 与 CMake** 构建的高性能前向推理引擎。
  * **底层优化 (CUDA Moat)**：
    * 对模型的核心算子（如矩阵乘法 MatMul、Softmax）进行手写 CUDA 算子重构，并使用 **Nsight Compute** 进行显存带宽和寄存器利用率优化。
    * 在 C++ 层面设计高效的内存池（Memory Pool）和零拷贝（Zero-Copy）数据流，杜绝 CPU 与 GPU 之间不必要的数据拷贝开销。
    * 通过 **PyBind11** 将底层 CUDA 优化库无缝向 Python/C++ 业务逻辑层提供高吞吐接口。
  * **交互逻辑**：本地录音/输入 -> 异步调用节点 A 接口 -> 渲染双语字幕（展示 `zh_text`） -> 异步调用节点 B API 流式传输 `.wav` 语音并播放（播放 `jp_text` 语音） -> 若触发 `tool_call` 则在本地沙盒静默启动 **Claude Code** 代理执行系统任务。

## 3. 开发阶段规划 (Development Phases)

* **Phase 1**：使用 Python 快速跑通全链路 MVP（最小可行性产品），验证 Cloudflare Tunnel 穿透与 JSON 双语输出管道。
* **Phase 2**：在本地 C++ 环境中读取并重构算子，编写自定义 CUDA Kernel 进行特征计算与 NMS/MatMul 性能压榨。
* **Phase 3**：用 Nsight Compute 对 Turing 架构（学校）和 Ampere/Ada 架构（本地）进行针对性指令级调优。
