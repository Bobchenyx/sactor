#!/bin/bash

# vLLM 启动脚本
# 使用 Qwen 1.5B 模型

MODEL="${MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
PORT="${PORT:-8000}"
GPU_MEMORY_UTIL="${GPU_MEMORY_UTIL:-0.9}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"

echo "🚀 启动 vLLM 服务..."
echo "📦 模型: $MODEL"
echo "🔌 端口: $PORT"
echo "💾 GPU 内存使用率: $GPU_MEMORY_UTIL"
echo "📏 最大上下文长度: $MAX_MODEL_LEN"
echo ""

python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --port "$PORT" \
  --trust-remote-code \
  --gpu-memory-utilization "$GPU_MEMORY_UTIL" \
  --max-model-len "$MAX_MODEL_LEN"

