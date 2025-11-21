# Qwen 缓存验证指南

## 问题：如何验证缓存是否生效？

由于SACToR运行在Docker中，我们需要通过实际的翻译任务来验证缓存效果。

## 方法1: 通过批量翻译观察 (推荐)

### 运行小规模测试

```bash
cd /home/changdi/sactor
python3 batch_generate_tests.py --sample-size 10 --workers 2 --num-tests 5
```

### 预期观察

如果显式缓存生效，你应该看到：

1. **处理速度**：
   - 第一个文件：正常速度（创建缓存）
   - 后续文件：稍快（命中缓存，减少了system message的计算）

2. **API响应**：
   - 查看SACToR的输出日志
   - 应该能看到 `cached_tokens` 字段（如果SACToR输出了这个信息）

## 方法2: 检查API使用统计

### Qwen API控制台

1. 登录 Alibaba Cloud DashScope控制台
2. 查看API使用统计
3. 观察：
   - Token使用量是否减少
   - 是否有缓存相关的统计信息

## 方法3: 修改SACToR代码输出缓存信息

如果想看到详细的缓存统计，需要修改 `qwen_llm.py` 来记录响应信息：

### 添加日志输出

在 `/home/changdi/sactor/sactor/llm/qwen_llm.py` 中：

```python
@override
def _query_impl_inner(self, prompt, model):
    # ... 现有代码 ...
    
    # 发送请求
    resp = self.client.chat.completions.create(...)
    
    # 🆕 添加缓存信息日志
    if hasattr(resp, 'usage') and hasattr(resp.usage, 'prompt_tokens_details'):
        details = resp.usage.prompt_tokens_details
        if hasattr(details, 'cached_tokens'):
            cached = details.cached_tokens
            if cached > 0:
                print(f"✅ Cache hit: {cached} tokens cached (10% cost)")
        if hasattr(details, 'cache_creation_input_tokens'):
            creation = details.cache_creation_input_tokens
            if creation > 0:
                print(f"📝 Cache created: {creation} tokens (125% cost)")
    
    return resp
```

## 方法4: 对比测试 (最准确)

### 步骤1: 禁用显式缓存

临时注释掉 `qwen_llm.py` 中的 `cache_control`：

```python
messages.append({
    "role": "system", 
    "content": self.system_msg,
    # "cache_control": {"type": "ephemeral"}  # 暂时注释掉
})
```

运行测试：
```bash
python3 batch_generate_tests.py --sample-size 20 --workers 3 --num-tests 5
```

记录：
- 总处理时间
- API成本（如果有统计）
- 成功率

### 步骤2: 启用显式缓存

取消注释 `cache_control`，再次运行相同的测试：

```bash
python3 batch_generate_tests.py --sample-size 20 --workers 3 --num-tests 5
```

### 步骤3: 对比结果

| 指标 | 无缓存 | 有缓存 | 改善 |
|------|--------|--------|------|
| 总时间 | ? | ? | ? |
| API成本 | ? | ? | ? |
| 成功率 | ? | ? | ? |

## 简单验证方法 (不需要修改代码)

### 直接运行批量翻译

```bash
cd /home/changdi/sactor
python3 batch_generate_tests.py --sample-size 50 --workers 5 --num-tests 8
```

### 观察性能指标

查看最终的统计信息：

```python
# 脚本会输出类似这样的统计
📊 测试用例生成结果:
处理文件数: 50
成功生成: 42
生成失败: 8
总测试用例数: 336
生成成功率: 84.0%
平均每个文件: 8.0 个测试用例
总处理时间: 1234.56 秒
平均处理时间: 24.69 秒/文件
```

### 预期改善

如果缓存生效（特别是在并行处理时）：

- ✅ 平均处理时间应该略有减少（5-10%）
- ✅ API成本会显著降低（system message部分节省90%）
- ✅ 性能更稳定（不依赖隐式缓存的不确定性）

## 理论验证

根据Qwen文档，显式缓存：

1. **保证命中**：5分钟内的请求如果system message相同，100%命中
2. **成本节省**：
   - 第一次：125% × system_message_tokens
   - 后续：10% × system_message_tokens
   - 节省：90% × system_message_tokens

3. **适用场景**：
   - ✅ 批量处理（你的场景）
   - ✅ 多轮对话
   - ✅ 重复的system message

## 实际应用建议

### 当前配置已经启用显式缓存

你的 `qwen_llm.py` 已经添加了 `cache_control`，现在：

1. **直接使用**：无需额外配置
2. **自动生效**：所有通过Docker运行的翻译都会使用显式缓存
3. **成本优化**：在批量处理时自动节省成本

### 最佳实践

1. **批量处理**：一次处理多个文件，保持在5分钟窗口内
2. **并行处理**：使用多线程/进程，共享缓存
3. **保持连续**：避免长时间暂停（>5分钟）导致缓存失效

### 监控建议

定期检查：
- Qwen API控制台的使用统计
- 总token使用量是否下降
- 平均处理时间是否改善

## 总结

✅ **缓存已启用**：修改已应用到 `qwen_llm.py`

✅ **自动工作**：无需额外操作，运行批量翻译即可

✅ **验证方法**：
1. 最简单：直接运行批量翻译，观察性能
2. 最准确：对比有无缓存的运行结果
3. 最详细：修改代码添加日志输出

🎯 **推荐**：直接运行你的批量翻译任务：

```bash
cd /home/changdi/sactor
python3 batch_generate_tests.py --sample-size 500 --workers 15 --num-tests 8
```

缓存会自动工作，你会在成本和性能上看到改善！

