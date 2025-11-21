# SACToR Batch API 优化方案

## 问题分析

### 当前调用模式

SACToR在翻译一个C文件时会进行**多次独立的LLM调用**：

```
翻译一个C文件的流程:
1. 翻译 enum        → LLM调用 1
2. 翻译 struct      → LLM调用 2
3. 翻译 function 1  → LLM调用 3
4. 翻译 function 2  → LLM调用 4
5. 翻译 function 3  → LLM调用 5
6. 验证 harness     → LLM调用 6
7. 修复错误         → LLM调用 7-N
...

总计: 平均 10-20 次独立调用
```

### 成本问题

每次独立调用的问题：
- ❌ 网络往返延迟（RTT）
- ❌ 每次都建立连接
- ❌ 无法利用批量折扣
- ❌ 串行处理速度慢

## Batch API 方案

### 方案1: OpenAI Batch API (异步批处理) ⭐

#### 特点
- ✅ **50% 成本折扣**
- ✅ 24小时内完成
- ✅ 适合大规模批量处理
- ⚠️ 异步处理，需要等待

#### 工作流程

```
1. 收集阶段 (1-2分钟)
   ↓ 收集所有待翻译的C文件
   ↓ 生成所有需要的prompts
   
2. 提交Batch (几秒)
   ↓ 创建JSONL文件
   ↓ 上传到API
   ↓ 获取batch_id
   
3. 等待处理 (几分钟到几小时)
   ↓ 轮询状态
   ↓ API后台批量处理
   
4. 获取结果 (几秒)
   ↓ 下载结果文件
   ↓ 解析JSONL
   ↓ 映射回原始请求
```

#### 成本对比

| 模式 | 500个文件 | 10,000个文件 |
|------|-----------|-------------|
| 普通API | $60.00 | $1,200.00 |
| **Batch API** | **$30.00** | **$600.00** |
| **节省** | **$30.00 (50%)** | **$600.00 (50%)** |

---

### 方案2: 自定义批量聚合 (同步优化)

#### 特点
- ✅ 立即处理
- ✅ 减少网络开销
- ⚠️ 无成本折扣
- ⚠️ 需要重构代码

#### 策略

**策略A: 同文件内批量翻译**

将一个C文件的多个函数合并到一个prompt中：

```python
# 当前方式（10次调用）
translate(function1) → result1
translate(function2) → result2
...
translate(function10) → result10

# 优化方式（1次调用）
translate([function1, function2, ..., function10]) → [result1, result2, ..., result10]
```

**优势**:
- 减少90%的API调用次数
- 更快的处理速度
- 减少网络往返

**策略B: 跨文件批量翻译**

将多个C文件的翻译合并：

```python
# 当前方式（500次调用）
for file in files:
    translate(file)

# 优化方式（1次调用）
translate_batch(files) → results
```

**风险**:
- Prompt可能过长
- 错误影响整批
- 难以调试

---

## 推荐方案: 混合方案 ⭐⭐⭐

### 策略

1. **小批量实时处理** (< 50个文件)
   - 使用普通API + Prompt Cache
   - 立即获得结果
   
2. **大批量离线处理** (> 50个文件)
   - 使用Batch API
   - 节省50%成本
   - 可以等待

### 实施方案

#### 阶段1: Batch API集成

创建 `batch_translate_with_batch_api.py`:

```python
import json
import time
from openai import OpenAI

class BatchAPITranslator:
    def __init__(self):
        self.client = OpenAI(
            api_key="sk-aaca0ccf722143a39ec3c6e38a0a4bc2",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        )
    
    def collect_translation_requests(self, c_files):
        """收集所有翻译请求"""
        requests = []
        
        for idx, c_file in enumerate(c_files):
            # 读取C代码
            with open(c_file, 'r') as f:
                c_code = f.read()
            
            # 创建请求
            request = {
                "custom_id": f"translate-{idx}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "qwen3-coder-plus",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a C to Rust translator...",
                            "cache_control": {"type": "ephemeral"}
                        },
                        {
                            "role": "user",
                            "content": f"Translate this C code to Rust:\n\n{c_code}"
                        }
                    ],
                    "temperature": 0.3
                }
            }
            requests.append(request)
        
        return requests
    
    def create_batch_file(self, requests, output_path):
        """创建JSONL格式的批处理文件"""
        with open(output_path, 'w') as f:
            for req in requests:
                f.write(json.dumps(req) + '\n')
    
    def submit_batch(self, batch_file_path):
        """提交批处理任务"""
        # 上传文件
        with open(batch_file_path, 'rb') as f:
            batch_file = self.client.files.create(
                file=f,
                purpose='batch'
            )
        
        # 创建批处理任务
        batch = self.client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h"
        )
        
        return batch.id
    
    def check_batch_status(self, batch_id):
        """检查批处理状态"""
        batch = self.client.batches.retrieve(batch_id)
        return batch.status, batch
    
    def retrieve_results(self, batch_id):
        """获取批处理结果"""
        batch = self.client.batches.retrieve(batch_id)
        
        if batch.status != "completed":
            raise Exception(f"Batch not completed: {batch.status}")
        
        # 下载结果文件
        result_file = self.client.files.content(batch.output_file_id)
        
        # 解析结果
        results = []
        for line in result_file.text.split('\n'):
            if line.strip():
                results.append(json.loads(line))
        
        return results
    
    def batch_translate(self, c_files):
        """批量翻译主函数"""
        print(f"🚀 开始批量翻译 {len(c_files)} 个文件")
        
        # 1. 收集请求
        print("📝 收集翻译请求...")
        requests = self.collect_translation_requests(c_files)
        
        # 2. 创建批处理文件
        batch_file = "/tmp/batch_translate_requests.jsonl"
        print(f"📄 创建批处理文件: {batch_file}")
        self.create_batch_file(requests, batch_file)
        
        # 3. 提交批处理
        print("⬆️  提交批处理任务...")
        batch_id = self.submit_batch(batch_file)
        print(f"✅ 批处理ID: {batch_id}")
        
        # 4. 轮询状态
        print("⏳ 等待处理完成...")
        while True:
            status, batch = self.check_batch_status(batch_id)
            print(f"   状态: {status}")
            
            if status == "completed":
                break
            elif status in ["failed", "expired", "cancelled"]:
                raise Exception(f"Batch failed with status: {status}")
            
            time.sleep(30)  # 每30秒检查一次
        
        # 5. 获取结果
        print("📥 下载结果...")
        results = self.retrieve_results(batch_id)
        
        print(f"✅ 完成！共 {len(results)} 个结果")
        return results
```

#### 阶段2: 智能路由

根据任务规模自动选择：

```python
def smart_translate(c_files, wait_for_batch=True):
    """智能选择翻译模式"""
    
    if len(c_files) < 50 or not wait_for_batch:
        # 小批量或需要立即结果：使用普通API
        print("📍 使用实时API模式")
        return realtime_translate(c_files)
    else:
        # 大批量：使用Batch API
        print("📍 使用Batch API模式（50%折扣）")
        return batch_api_translate(c_files)
```

---

## 详细实施计划

### 阶段1: 验证Batch API支持 (1天)

#### 任务
1. 确认Qwen是否支持OpenAI兼容的Batch API
2. 创建简单的测试脚本
3. 提交小批量测试（5-10个请求）

#### 验证脚本

```python
# test_batch_api.py
from openai import OpenAI

client = OpenAI(
    api_key="sk-aaca0ccf722143a39ec3c6e38a0a4bc2",
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)

# 尝试创建batch
try:
    # 创建测试JSONL
    with open('/tmp/test_batch.jsonl', 'w') as f:
        f.write(json.dumps({
            "custom_id": "test-1",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "qwen3-coder-plus",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        }) + '\n')
    
    # 上传文件
    with open('/tmp/test_batch.jsonl', 'rb') as f:
        batch_file = client.files.create(file=f, purpose='batch')
    
    # 创建batch
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )
    
    print(f"✅ Batch API支持！Batch ID: {batch.id}")
    
except Exception as e:
    print(f"❌ Batch API不支持: {e}")
```

### 阶段2: 设计批量聚合策略 (2天)

#### 方案A: 函数级别批量

```python
def translate_functions_batch(functions):
    """一次性翻译多个函数"""
    prompt = "Translate these C functions to Rust:\n\n"
    for i, func in enumerate(functions):
        prompt += f"=== Function {i+1} ===\n{func}\n\n"
    
    response = llm.query(prompt)
    
    # 解析多个函数的结果
    return parse_multiple_functions(response)
```

**优势**: 简单，易于实现
**劣势**: Prompt可能过长

#### 方案B: 使用Batch API

**优势**: 50%成本节省
**劣势**: 异步，需要等待

### 阶段3: 实现与测试 (3-5天)

1. 实现Batch API封装
2. 修改SACToR翻译流程
3. 添加智能路由逻辑
4. 测试小规模（10个文件）
5. 测试大规模（500个文件）

### 阶段4: 性能对比 (1天)

对比三种模式：

| 模式 | 100个文件 | 成本 | 时间 | 成功率 |
|------|-----------|------|------|--------|
| 当前方式 | - | $12 | 5小时 | 72% |
| +Prompt Cache | - | $4 | 5小时 | 72% |
| +Batch API | - | $2 | 30分钟+2小时 | 72% |

---

## 注意事项

### 1. Qwen Batch API可用性

**需要确认**:
- ✅ Qwen是否支持OpenAI兼容的Batch API
- ✅ 是否有50%折扣
- ✅ 处理时间限制

**如果不支持**: 使用方案2（自定义批量聚合）

### 2. 错误处理

```python
# Batch API的错误处理
for result in batch_results:
    if result.get('error'):
        print(f"请求 {result['custom_id']} 失败: {result['error']}")
        # 回退到普通API
        retry_with_realtime_api(result['custom_id'])
```

### 3. 调试困难

Batch API的调试更困难：
- 异步处理，无法实时看到结果
- 错误信息可能不够详细
- 建议：先用小批量测试

---

## 成本收益分析

### 场景1: 处理500个C文件

| 项目 | 当前 | +Cache | +Batch API | 节省 |
|------|------|--------|------------|------|
| System message | $0.75 | $0.075 | $0.038 | 95% |
| User prompt | $59.25 | $59.25 | $29.63 | 50% |
| **总计** | **$60** | **$59.33** | **$29.67** | **51%** |

### 场景2: 处理10,000个文件

| 项目 | 当前 | +Cache | +Batch API | 节省 |
|------|------|--------|------------|------|
| System message | $15 | $1.5 | $0.75 | 95% |
| User prompt | $1,185 | $1,185 | $592.5 | 50% |
| **总计** | **$1,200** | **$1,186.5** | **$593.25** | **51%** |

**总节省**: **Prompt Cache (90%) + Batch API (50%) = ~51%综合节省**

---

## 下一步行动

### 立即可做

1. ✅ **验证Batch API支持**
   ```bash
   cd /home/changdi/sactor
   python3 test_batch_api.py
   ```

2. ✅ **创建Batch API封装**
   - 实现请求收集
   - 实现JSONL生成
   - 实现结果解析

3. ✅ **小规模测试**
   - 10个文件
   - 验证正确性
   - 对比成本

### 后续优化

1. **智能路由**: 根据任务量自动选择模式
2. **并行处理**: Batch API + 多线程上传
3. **增量更新**: 只翻译修改的文件

---

## 总结

### 推荐方案

**混合方案**: Prompt Cache + Batch API

1. **Prompt Cache** (已实施): 节省90% system message成本
2. **Batch API** (待实施): 节省50%总体成本

**综合优势**:
- ✅ 最大成本节省（~51%）
- ✅ 灵活性高（可选实时或批量）
- ✅ 向后兼容

**第一步**: 验证Qwen是否支持Batch API
**第二步**: 实现Batch API封装
**第三步**: 集成到现有流程

---

## 参考资源

- [OpenAI Batch API文档](https://platform.openai.com/docs/guides/batch)
- [Alibaba Cloud Model Studio](https://help.aliyun.com/zh/model-studio/)
- 当前实现: `/home/changdi/sactor/sactor/llm/qwen_llm.py`

