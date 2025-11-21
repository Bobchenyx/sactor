# vLLM 集成总结文档 (2024-11-17)

## 📋 目录

1. [功能概述](#功能概述)
2. [实现内容](#实现内容)
3. [配置说明](#配置说明)
4. [使用方法](#使用方法)
5. [测试验证](#测试验证)
6. [故障排除](#故障排除)
7. [技术细节](#技术细节)

---

## 🎯 功能概述

### 主要功能

SACToR 现已支持使用 **vLLM** 本地部署的模型进行 C→Rust 代码翻译，替代原有的 API 模型调用。

### 核心优势

- ✅ **完全本地运行**：数据不上传，隐私有保障
- ✅ **无 API 费用**：本地部署，无调用成本
- ✅ **无配额限制**：不受 API 配额限制
- ✅ **OpenAI 兼容**：使用 OpenAI 兼容的 API 接口
- ✅ **灵活配置**：支持自定义端口、模型、参数等

### 适用场景

- 大规模代码翻译任务
- 需要数据隐私保护的场景
- 希望降低 API 调用成本的场景
- 需要长时间运行的翻译任务

---

## 📦 实现内容

### 1. 核心实现文件

#### `sactor/llm/vllm_llm.py`
- **功能**：vLLM LLM 包装器实现
- **特点**：
  - 实现 OpenAI 兼容 API 接口
  - 正确处理 Python 3.9+ 兼容性（override 装饰器）
  - 支持自定义 base_url、model、temperature 等参数
  - 完整的错误处理

#### `sactor/llm/__init__.py`
- **功能**：LLM 工厂函数更新
- **修改**：
  - 添加 VLLMLLM 导入
  - 在 `llm_factory()` 中添加 "VLLM" case
  - 更新 `__all__` 列表

### 2. 配置文件

#### `sactor.default.toml` / `sactor.toml`
- **新增配置段**：`[VLLM]`
- **配置项**：
  ```toml
  [VLLM]
  base_url = "http://localhost:8000/v1"
  api_key = "EMPTY"
  model = "Qwen/Qwen2.5-1.5B-Instruct"
  max_tokens = 2048
  temperature = 0.7
  ```

### 3. 工具脚本

#### `start_vllm.sh`
- **功能**：快速启动 vLLM 服务
- **用法**：
  ```bash
  ./start_vllm.sh
  # 或自定义参数
  MODEL=Qwen/Qwen2.5-7B-Instruct PORT=8001 ./start_vllm.sh
  ```

#### `test_vllm_standalone.py`
- **功能**：独立测试 vLLM 连接（不依赖整个项目）
- **用法**：
  ```bash
  python3 test_vllm_standalone.py
  ```

#### `test_vllm_translate_simple.py`
- **功能**：测试 vLLM 翻译功能（不依赖 c2rust/crown）
- **用法**：
  ```bash
  python3 test_vllm_translate_simple.py
  ```

### 4. 文档文件

- `VLLM_USAGE.md` - 完整使用文档
- `VLLM_QUICKSTART.md` - 快速开始指南
- `VLLM_INTEGRATION_SUMMARY.md` - 集成总结

---

## ⚙️ 配置说明

### 1. 基本配置

编辑 `sactor.toml`：

```toml
[general]
llm = "VLLM"  # 设置为 VLLM

[VLLM]
base_url = "http://localhost:8000/v1"
api_key = "EMPTY"
model = "Qwen/Qwen2.5-1.5B-Instruct"
max_tokens = 2048
temperature = 0.7
```

### 2. 配置参数说明

| 参数 | 说明 | 默认值 | 备注 |
|------|------|--------|------|
| `base_url` | vLLM 服务地址 | `http://localhost:8000/v1` | 必须包含 `/v1` |
| `api_key` | API 密钥 | `EMPTY` | vLLM 不需要真实密钥 |
| `model` | 模型名称 | `Qwen/Qwen2.5-1.5B-Instruct` | 需与 vLLM 服务启动时一致 |
| `max_tokens` | 最大生成 token 数 | `2048` | 需小于模型最大上下文长度 |
| `temperature` | 生成温度 | `0.7` | 控制随机性 |

### 3. 模型选择建议

| 模型 | 大小 | 内存需求 | 适用场景 |
|------|------|----------|----------|
| Qwen/Qwen2.5-1.5B-Instruct | 1.5B | ~4GB VRAM | 测试、快速验证 |
| Qwen/Qwen2.5-7B-Instruct | 7B | ~16GB VRAM | 生产环境、高质量翻译 |
| Qwen/Qwen2.5-14B-Instruct | 14B | ~32GB VRAM | 复杂代码翻译 |

**注意**：`max_tokens` 需要根据模型的最大上下文长度调整：
- 1.5B: 4096 tokens → max_tokens ≤ 2048
- 7B: 8192 tokens → max_tokens ≤ 4096
- 14B: 16384 tokens → max_tokens ≤ 8192

---

## 🚀 使用方法

### 步骤 1: 安装 vLLM

```bash
# 使用 pip 安装
pip install vllm

# 或使用 conda
conda install -c conda-forge vllm
```

### 步骤 2: 启动 vLLM 服务

#### 方法 1: 使用启动脚本（推荐）

```bash
cd /home/changdi/sactor
./start_vllm.sh
```

#### 方法 2: 手动启动

```bash
# 使用 Qwen 1.5B 模型（测试用）
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --port 8000 \
  --trust-remote-code

# 使用 Qwen 7B 模型（生产用）
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --port 8000 \
  --trust-remote-code \
  --gpu-memory-utilization 0.9
```

#### 方法 3: 自定义端口

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --port 8001 \
  --trust-remote-code
```

**注意**：如果使用自定义端口，需要在 `sactor.toml` 中修改 `base_url`。

### 步骤 3: 配置 SACToR

编辑 `sactor.toml`：

```toml
[general]
llm = "VLLM"

[VLLM]
base_url = "http://localhost:8000/v1"
api_key = "EMPTY"
model = "Qwen/Qwen2.5-1.5B-Instruct"
max_tokens = 2048
temperature = 0.7
```

### 步骤 4: 验证连接

```bash
# 方法 1: 使用独立测试脚本（推荐）
python3 test_vllm_standalone.py

# 方法 2: 使用简单翻译测试
source .venv/bin/activate
python3 test_vllm_translate_simple.py

# 方法 3: 手动测试 API
curl http://localhost:8000/v1/models
```

### 步骤 5: 运行翻译

#### 单文件翻译

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行翻译
sactor translate \
  /path/to/file.c \
  /path/to/test_task.json \
  -r /path/to/result \
  --type bin
```

#### 批量翻译

```bash
python3 batch_translate_generic.py \
    --c-files /path/to/c_files \
    --json-files /path/to/json_files \
    --output /path/to/output \
    --workers 4 \
    --num-tests 6
```

---

## ✅ 测试验证

### 测试 1: 连接测试

```bash
python3 test_vllm_standalone.py
```

**预期输出**：
```
✅ 成功连接到 vLLM 服务
   可用模型数: 1
   - Qwen/Qwen2.5-1.5B-Instruct
✅ 查询成功!
```

### 测试 2: 翻译功能测试

```bash
source .venv/bin/activate
python3 test_vllm_translate_simple.py
```

**预期输出**：
```
✅ LLM 实例创建成功: VLLMLLM
✅ 翻译成功!
✅ 检测到 Rust 关键字: fn , ->, i32
```

### 测试 3: 完整翻译测试

```bash
source .venv/bin/activate
cd tests/c_examples/atoi
sactor translate atoi.c test_task/test_task.json -r result_vllm --type bin
```

**预期结果**：
- 生成 `result_vllm/translated_code_unidiomatic/combined.rs`
- 生成 `result_vllm/translated_code_idiomatic/combined.rs`
- 编译和测试通过

---

## 🔧 故障排除

### 问题 1: 连接失败

**症状**：
```
Connection error.
❌ 无法列出模型
```

**解决方案**：
1. 检查 vLLM 服务是否运行：
   ```bash
   ps aux | grep vllm
   curl http://localhost:8000/v1/models
   ```

2. 检查端口是否正确：
   ```bash
   netstat -tuln | grep 8000
   ```

3. 确认 `base_url` 配置正确（必须包含 `/v1`）

### 问题 2: 模型加载失败

**症状**：
```
Model not found
Failed to load model
```

**解决方案**：
1. 确认模型名称正确（与 HuggingFace 上的名称一致）
2. 首次使用需要下载模型，确保网络连接正常
3. 检查磁盘空间是否充足

### 问题 3: max_tokens 错误

**症状**：
```
Error code: 400 - 'max_tokens' is too large: 8192
```

**解决方案**：
1. 检查模型的最大上下文长度：
   ```bash
   curl http://localhost:8000/v1/models | grep max_model_len
   ```

2. 调整 `max_tokens` 配置：
   ```toml
   [VLLM]
   max_tokens = 2048  # 小于模型最大上下文长度的一半
   ```

### 问题 4: GPU 内存不足

**症状**：
```
CUDA out of memory
```

**解决方案**：
1. 降低 GPU 内存使用率：
   ```bash
   python -m vllm.entrypoints.openai.api_server \
     --model Qwen/Qwen2.5-1.5B-Instruct \
     --gpu-memory-utilization 0.7
   ```

2. 使用更小的模型
3. 减少 `max-model-len` 参数

### 问题 5: 翻译质量差

**可能原因**：
- 模型太小（1.5B 可能不够）
- temperature 设置不合适
- max_tokens 太小导致截断

**解决方案**：
1. 使用更大的模型（7B 或更大）
2. 调整 temperature（0.5-0.9）
3. 增加 max_tokens（在模型限制内）

---

## 🔍 技术细节

### 调用流程

```
sactor.toml (llm = "VLLM")
    ↓
llm_factory(config)
    ↓
检查 llm = "VLLM"
    ↓
创建 VLLMLLM 实例
    ↓
llm.query(prompt)
    ↓
VLLMLLM._query_impl()
    ↓
OpenAI 客户端 (base_url=http://localhost:8000/v1)
    ↓
vLLM 服务 API
    ↓
返回翻译结果
```

### 关键代码位置

1. **LLM 工厂函数**：`sactor/llm/__init__.py:40-41`
   ```python
   case "VLLM":
       return VLLMLLM(config, encoding=encoding, system_msg=system_message)
   ```

2. **VLLM 实现**：`sactor/llm/vllm_llm.py:70`
   ```python
   resp = self.client.chat.completions.create(
       model=model,
       messages=messages,
       temperature=temperature,
       max_tokens=max_tokens,
   )
   ```

3. **Sactor 初始化**：`sactor/sactor.py:93`
   ```python
   self.llm = llm_factory(self.config)
   ```

### 兼容性说明

- **Python 版本**：支持 Python 3.9+
- **vLLM 版本**：建议使用最新版本
- **OpenAI 客户端**：使用 `openai` 库的 OpenAI 兼容接口

### 性能优化建议

1. **GPU 设置**：
   - 使用 `--gpu-memory-utilization 0.9` 最大化 GPU 使用
   - 多 GPU 使用 `--tensor-parallel-size 2`

2. **并发设置**：
   - 批量翻译时，`--workers` 建议设置为 4-10
   - 根据 GPU 内存调整并发数

3. **模型选择**：
   - 测试：1.5B（快速）
   - 生产：7B+（质量）

---

## 📝 常用命令速查

### vLLM 服务管理

```bash
# 启动服务
./start_vllm.sh

# 启动服务（自定义模型）
MODEL=Qwen/Qwen2.5-7B-Instruct ./start_vllm.sh

# 检查服务状态
curl http://localhost:8000/v1/models

# 停止服务
pkill -f vllm
```

### SACToR 翻译命令

```bash
# 激活环境
source .venv/bin/activate

# 单文件翻译
sactor translate file.c test_task.json -r result --type bin

# 批量翻译
python3 batch_translate_generic.py \
    --c-files /path/to/c_files \
    --json-files /path/to/json_files \
    --output /path/to/output \
    --workers 4
```

### 测试命令

```bash
# 连接测试
python3 test_vllm_standalone.py

# 翻译功能测试
python3 test_vllm_translate_simple.py

# 完整翻译测试
sactor translate tests/c_examples/atoi/atoi.c \
    tests/c_examples/atoi/test_task/test_task.json \
    -r tests/c_examples/atoi/result_vllm \
    --type bin
```

---

## 📚 相关文档

- `VLLM_USAGE.md` - 详细使用文档
- `VLLM_QUICKSTART.md` - 快速开始指南
- `README.md` - 项目主文档
- `TRANSLATION_GUIDE.md` - 翻译指南

---

## 🎉 总结

vLLM 集成已完成并通过测试，主要特点：

- ✅ **完全集成**：无缝替代 API 模型
- ✅ **配置简单**：只需修改 `sactor.toml`
- ✅ **测试完善**：提供多个测试脚本
- ✅ **文档齐全**：包含完整的使用文档

**下一步**：
1. 根据需求选择合适的模型
2. 启动 vLLM 服务
3. 配置 `sactor.toml`
4. 开始翻译！

---

**文档版本**：v1.0  
**更新日期**：2024-11-17  
**作者**：SACToR Team

