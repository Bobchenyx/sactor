
git# vLLM 使用指南

## 简介

vLLM 是一个高性能的 LLM 推理和服务引擎，提供 OpenAI 兼容的 API 接口。SACToR 现在支持使用 vLLM 本地部署的模型进行 C→Rust 翻译。

## 安装 vLLM

```bash
# 使用 pip 安装
pip install vllm

# 或者使用 conda
conda install -c conda-forge vllm
```

## 启动 vLLM 服务

### 使用 Qwen 1.5B 模型

```bash
# 启动 vLLM 服务（默认端口 8000）
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --port 8000 \
  --trust-remote-code
```

### 其他常用参数

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --port 8000 \
  --trust-remote-code \
  --tensor-parallel-size 1 \      # GPU 并行数
  --max-model-len 4096 \          # 最大上下文长度
  --gpu-memory-utilization 0.9    # GPU 内存使用率
```

### 使用自定义端口

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --port 8001 \
  --trust-remote-code
```

## 配置 SACToR

### 1. 编辑配置文件

编辑 `sactor.toml`（如果不存在，从 `sactor.default.toml` 复制）：

```toml
[general]
llm = "VLLM"  # 使用 vLLM
max_translation_attempts = 6
timeout_seconds = 60

[VLLM]
base_url = "http://localhost:8000/v1"  # vLLM 服务地址
api_key = "EMPTY"  # vLLM 不需要真实的 API key
model = "Qwen/Qwen2.5-1.5B-Instruct"  # 模型名称（与启动时一致）
max_tokens = 8192
temperature = 0.7
```

### 2. 验证连接

测试 vLLM 服务是否正常运行：

```bash
curl http://localhost:8000/v1/models
```

应该返回类似：

```json
{
  "data": [
    {
      "id": "Qwen/Qwen2.5-1.5B-Instruct",
      "object": "model",
      "created": 1234567890,
      "owned_by": "vllm"
    }
  ]
}
```

## 使用示例

### 单文件翻译

```bash
# 确保 vLLM 服务正在运行
# 然后运行翻译命令
sactor translate \
  /path/to/file.c \
  /path/to/test_task.json \
  -r /path/to/result \
  --type bin
```

### 批量翻译

```bash
python3 batch_translate_generic.py \
    --c-files /path/to/c_files \
    --json-files /path/to/json_files \
    --output /path/to/output \
    --workers 4 \
    --num-tests 6
```

## 支持的模型

vLLM 支持多种模型，包括：

- **Qwen 系列**: `Qwen/Qwen2.5-1.5B-Instruct`, `Qwen/Qwen2.5-7B-Instruct` 等
- **Llama 系列**: `meta-llama/Llama-2-7b-chat-hf` 等
- **其他 HuggingFace 模型**: 任何兼容的模型

查看 vLLM 文档获取完整列表：https://docs.vllm.ai/

## 性能优化

### GPU 内存优化

如果遇到 GPU 内存不足：

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --port 8000 \
  --trust-remote-code \
  --gpu-memory-utilization 0.8 \  # 降低内存使用率
  --max-model-len 2048            # 减少最大上下文长度
```

### 多 GPU 支持

如果有多个 GPU：

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --port 8000 \
  --trust-remote-code \
  --tensor-parallel-size 2  # 使用 2 个 GPU
```

### CPU 模式（不推荐，速度很慢）

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --port 8000 \
  --trust-remote-code \
  --device cpu
```

## 故障排除

### 问题1: 连接失败

**错误**: `Connection refused` 或 `Failed to connect`

**解决方案**:
1. 确认 vLLM 服务正在运行：`ps aux | grep vllm`
2. 检查端口是否正确：`netstat -tuln | grep 8000`
3. 确认 `base_url` 配置正确

### 问题2: 模型加载失败

**错误**: `Model not found` 或 `Failed to load model`

**解决方案**:
1. 确认模型名称正确（与 HuggingFace 上的名称一致）
2. 首次使用需要下载模型，确保网络连接正常
3. 检查是否有足够的磁盘空间

### 问题3: GPU 内存不足

**错误**: `CUDA out of memory`

**解决方案**:
1. 降低 `gpu-memory-utilization`（如 0.7）
2. 减少 `max-model-len`
3. 使用更小的模型
4. 使用多 GPU 并行（`tensor-parallel-size`）

### 问题4: 响应速度慢

**可能原因**:
- 模型太大
- GPU 性能不足
- 上下文长度设置过大

**解决方案**:
1. 使用更小的模型（如 1.5B）
2. 减少 `max_tokens` 配置
3. 优化 GPU 设置

## 与 API 模型的对比

| 特性 | vLLM | API 模型 |
|------|------|----------|
| 成本 | 免费（本地运行） | 按使用量付费 |
| 速度 | 取决于硬件 | 通常较快 |
| 隐私 | 完全本地，数据不上传 | 数据发送到云端 |
| 配置 | 需要 GPU 和模型下载 | 只需 API key |
| 配额 | 无限制 | 受 API 配额限制 |

## 推荐配置

### 开发/测试环境
- **模型**: Qwen/Qwen2.5-1.5B-Instruct（小模型，速度快）
- **GPU**: 至少 4GB VRAM
- **并发**: workers=2-4

### 生产环境
- **模型**: Qwen/Qwen2.5-7B-Instruct 或更大（质量更好）
- **GPU**: 至少 16GB VRAM
- **并发**: workers=4-10

## 快速启动脚本

创建一个 `start_vllm.sh` 脚本：

```bash
#!/bin/bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --port 8000 \
  --trust-remote-code \
  --gpu-memory-utilization 0.9
```

使用：

```bash
chmod +x start_vllm.sh
./start_vllm.sh
```

## 总结

使用 vLLM 的优势：
- ✅ 完全本地运行，数据隐私有保障
- ✅ 无 API 调用费用
- ✅ 无配额限制
- ✅ 可以自定义模型和参数

注意事项：
- ⚠️ 需要 GPU 支持（推荐）
- ⚠️ 首次使用需要下载模型
- ⚠️ 需要一定的系统资源

