# 服务器端代码 (gdut)

运行在学校 K8s GPU 集群节点 `gpu-108` (10.200.168.108) 上。

## 文件

| 文件 | 用途 | 路径 |
|------|------|------|
| `train_genonly.py` | VITS generator-only 微调脚本 | `~/vits_finetune/` |
| `renge.json` | VITS 训练配置 (41 音素, 6 说话人) | `~/vits_finetune/configs/` |
| `lazy_server.py` | LLM 懒加载代理 — 按需启动/空闲释放 | `~/llm/` |
| `start_server.sh` | LLM 手动启动脚本 (已弃用，用 lazy_server 替代) | `~/llm/` |

## 服务器目录结构

```
~/vits_finetune/
├── train_genonly.py    # 训练脚本
├── configs/
│   └── renge.json      # 训练配置
├── filelists/
│   └── renge_train.txt # 训练数据列表 (3670 条)
├── checkpoints/
│   └── G_0.pth         # skytnt 预训练模型 (455MB)
└── output_gen/
    └── ft_e*.pth       # 微调 checkpoint

~/llm/
├── lazy_server.py          # 懒加载代理 :8081
├── server_manager.sh       # 备用管理脚本
└── qwen2.5-coder-32b-q4_k_m.gguf  # 模型文件 (18GB, gitignored)
```

## 部署

```bash
# 训练
cd ~/vits_finetune
CUDA_VISIBLE_DEVICES=2 setsid ~/.conda/envs/py310/bin/python train_genonly.py > train_gen.log 2>&1 & disown

# LLM 懒加载
nohup env CUDA_VISIBLE_DEVICES=1 python3 ~/llm/lazy_server.py > ~/llm/lazy.log 2>&1 & disown

# 监控
nvidia-smi
grep 'E[0-9]*: avg' ~/vits_finetune/train_gen.log | tail -5
```
