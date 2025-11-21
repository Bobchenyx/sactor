# vLLM 快速开始指南

## 🚀 快速开始（3 步）

### 步骤 1: 安装 vLLM

```bash
pip install vllm
```

### 步骤 2: 启动 vLLM 服务

```bash
# 使用 Qwen 1.5B 模型（推荐用于测试）
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --port 8000 \
  --trust-remote-code
```

或者使用提供的脚本：

```bash
./start_vllm.sh
```

### 步骤 3: 配置 SACToR

编辑 `sactor.toml`：

```toml
[general]
llm = "VLLM"

[VLLM]
base_url = "http://localhost:8000/v1"
api_key = "EMPTY"
model = "Qwen/Qwen2.5-1.5B-Instruct"
max_tokens = 8192
temperature = 0.7
```

## ✅ 验证安装

运行测试脚本：

```bash
python3 test_vllm.py
```

或者手动测试：

```bash
curl http://localhost:8000/v1/models
```

## 📝 使用示例

### 单文件翻译

```bash
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
    --workers 4
```

## 🔧 常见问题

**Q: vLLM 服务启动失败？**  
A: 确保已安装 vLLM 和所需的依赖（CUDA、PyTorch 等）

**Q: 连接被拒绝？**  
A: 检查端口是否正确，确认 vLLM 服务正在运行

**Q: GPU 内存不足？**  
A: 使用更小的模型或降低 `gpu-memory-utilization` 参数

**Q: 模型下载慢？**  
A: 首次使用需要从 HuggingFace 下载模型，可以设置镜像或使用代理

## 📚 更多信息

查看 [VLLM_USAGE.md](./VLLM_USAGE.md) 获取详细文档。

