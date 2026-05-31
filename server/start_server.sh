#!/bin/bash
MODEL="$HOME/llm/qwen2.5-coder-32b-q4_k_m.gguf"
PORT=8080
GPU=1

CUDA_VISIBLE_DEVICES=$GPU $HOME/.conda/envs/py310/bin/python -m llama_cpp.server \
    --model "$MODEL" \
    --n_gpu_layers 99 \
    --n_ctx 32768 \
    --host 0.0.0.0 \
    --port $PORT \
    --chat_format chatml

echo "Server started on port $PORT"
