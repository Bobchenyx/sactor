# SACToR Prompt 优化方案

## 当前问题分析

### 1. **过多的重试次数**
- `max_translation_attempts = 20` - 每个翻译最多20次尝试
- `max_verifier_harness_attempts = 6` - 每个验证最多6次尝试
- `test_generator.max_attempts = 6` - 每个测试生成最多6次尝试

**问题**: 对于大多数简单程序，1-3次尝试就能成功，20次过于保守

### 2. **冗余的Prompt调用**
SACToR的翻译流程：
```
C代码 → 预处理 → 非惯用Rust翻译 → 编译测试 → 惯用Rust翻译 → 编译测试 → 验证
         ↓            ↓                ↓              ↓              ↓
       LLM调用      LLM调用          LLM调用        LLM调用        LLM调用
```

每个阶段都可能多次调用LLM，造成大量重复的system message和上下文。

### 3. **Qwen Prompt Cache未充分利用**
Qwen的prompt cache机制：
- 相同的system message会被缓存
- 相同的上下文前缀会被缓存
- **但每次新的翻译任务都会创建全新的对话**

## 优化策略

### **策略1: 减少最大尝试次数** ⭐⭐⭐⭐⭐

```toml
[general]
max_translation_attempts = 5  # 从20降到5
max_verifier_harness_attempts = 3  # 从6降到3

[test_generator]
max_attempts = 3  # 从6降到3
```

**预期效果**:
- 成功率略微下降（估计从72%降到65-70%）
- **Prompt调用减少60-75%**
- 平均处理时间减少50%

### **策略2: 优化System Message** ⭐⭐⭐⭐

**当前system message过于冗长**:
```toml
system_message = '''
You are an expert in translating code from C to Rust. You will take all information from the user as reference, and will output the translated code into the format that the user wants.
'''
```

**优化为更简洁的版本**:
```toml
system_message = '''
You are a C to Rust code translator. Output only the translated Rust code in the requested format.
'''
```

**预期效果**:
- 减少每次调用的输入token数量（约30%）
- 提高Qwen cache命中率

### **策略3: 启用Early Stopping** ⭐⭐⭐⭐

修改翻译器逻辑，当连续2次失败时提前终止：

```python
# 在translator.py中添加early stopping逻辑
consecutive_failures = 0
max_consecutive_failures = 2

for attempt in range(max_attempts):
    result = translate()
    if result.success:
        consecutive_failures = 0
        break
    else:
        consecutive_failures += 1
        if consecutive_failures >= max_consecutive_failures:
            # 提前终止，不再尝试
            break
```

**预期效果**:
- 对于无法翻译的程序快速失败
- 减少无效的重试次数

### **策略4: 批量处理优化** ⭐⭐⭐

对于测试生成阶段，可以批量生成测试用例：

```python
# 将多个C文件的测试生成合并为一个请求
# 但这需要修改SACToR核心代码，暂时不推荐
```

### **策略5: 调整温度参数** ⭐⭐⭐

```toml
[Qwen]
temperature = 0.3  # 从默认的1降到0.3，减少随机性
```

**预期效果**:
- 输出更加确定性，减少无效的变化
- 提高cache命中率
- 更快收敛到正确答案

## 推荐配置

### **激进优化版本（最快速度）**:
```toml
[general]
llm = "Qwen"
max_translation_attempts = 3  # 激进：只尝试3次
max_verifier_harness_attempts = 2  # 激进：只验证2次
timeout_seconds = 60
system_message = 'C to Rust translator. Output translated code only.'

[Qwen]
model = "qwen3-coder-plus-2025-09-23"
max_tokens = 8192
temperature = 0.2  # 低温度，更确定性

[test_generator]
max_attempts = 2  # 激进：只尝试2次
```

**预期**:
- 成功率: 60-65%
- Prompt减少: 80%
- 速度提升: 4-5倍

### **平衡优化版本（推荐）** ⭐:
```toml
[general]
llm = "Qwen"
max_translation_attempts = 5  # 平衡：5次尝试
max_verifier_harness_attempts = 3  # 平衡：3次验证
timeout_seconds = 60
system_message = 'You are a C to Rust code translator. Output only the translated Rust code in the requested format.'

[Qwen]
model = "qwen3-coder-plus-2025-09-23"
max_tokens = 8192
temperature = 0.3  # 中等温度

[test_generator]
max_attempts = 3  # 平衡：3次尝试
```

**预期**:
- 成功率: 65-70%
- Prompt减少: 70%
- 速度提升: 3倍

### **保守优化版本（最稳定）**:
```toml
[general]
llm = "Qwen"
max_translation_attempts = 8  # 保守：8次尝试
max_verifier_harness_attempts = 4  # 保守：4次验证
timeout_seconds = 60
system_message = 'You are an expert in translating code from C to Rust. Output the translated code in the requested format.'

[Qwen]
model = "qwen3-coder-plus-2025-09-23"
max_tokens = 8192
temperature = 0.5  # 中高温度

[test_generator]
max_attempts = 4  # 保守：4次尝试
```

**预期**:
- 成功率: 70-72%（接近当前）
- Prompt减少: 50%
- 速度提升: 2倍

## 实施步骤

### **步骤1: 备份当前配置**
```bash
cp /home/changdi/sactor/sactor.toml /home/changdi/sactor/sactor.toml.before_optimization
```

### **步骤2: 应用优化配置**
选择上述三种配置之一，更新 `sactor.toml`

### **步骤3: 小规模测试**
```bash
cd /home/changdi/sactor
python3 batch_generate_tests.py --sample-size 50 --workers 5 --num-tests 8
```

### **步骤4: 对比效果**
- 成功率
- 平均处理时间
- Token使用量
- API成本

### **步骤5: 调整参数**
根据测试结果微调参数

## Token使用量估算

### 当前配置（未优化）:
```
平均每个C文件:
- 翻译尝试: 10次 × 2000 tokens = 20,000 tokens
- 验证尝试: 4次 × 1000 tokens = 4,000 tokens
- 测试生成: 3次 × 1500 tokens = 4,500 tokens
总计: ~28,500 tokens/文件
```

### 平衡优化后:
```
平均每个C文件:
- 翻译尝试: 3次 × 2000 tokens = 6,000 tokens
- 验证尝试: 2次 × 1000 tokens = 2,000 tokens
- 测试生成: 2次 × 1500 tokens = 3,000 tokens
总计: ~11,000 tokens/文件
```

**减少: 61.4%**

### 激进优化后:
```
平均每个C文件:
- 翻译尝试: 2次 × 2000 tokens = 4,000 tokens
- 验证尝试: 1次 × 1000 tokens = 1,000 tokens
- 测试生成: 1次 × 1500 tokens = 1,500 tokens
总计: ~6,500 tokens/文件
```

**减少: 77.2%**

## Qwen Prompt Cache原理

Qwen的cache机制会缓存：
1. **System Message** - 如果相同会完全复用
2. **对话历史的公共前缀** - 相同的上下文会被缓存
3. **有效期**: 5分钟内的重复请求

**优化建议**:
- 保持system message简短且一致
- 减少每次请求中的变化部分
- 在5分钟内完成相关的批次处理

## 监控指标

优化后需要监控：
1. **成功率**: 应保持在60%以上
2. **平均尝试次数**: 应降低到2-4次
3. **平均处理时间**: 应减少50%以上
4. **Token使用量**: 应减少60%以上
5. **API成本**: 应线性减少

## 回滚方案

如果优化效果不佳：
```bash
cp /home/changdi/sactor/sactor.toml.before_optimization /home/changdi/sactor/sactor.toml
```

## 总结

**推荐采用"平衡优化版本"**:
- ✅ 兼顾成功率和速度
- ✅ Token使用量减少70%
- ✅ 处理速度提升3倍
- ✅ 风险可控

