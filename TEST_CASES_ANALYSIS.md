# 测试用例生成机制分析

## 🔍 **当前测试用例生成方式**

### **我们的脚本使用的测试用例生成**

**❌ 不是使用预生成的测试用例，而是动态生成：**

```python
def generate_correct_test_samples(self, c_file_path: str) -> List[Dict]:
    """生成正确的测试用例（包含期望输出）"""
    # 1. 编译 C 程序
    compile_result = subprocess.run(['gcc', c_file_path, '-o', test_binary])
    
    # 2. 运行 C 程序获取期望输出
    test_inputs = ["10", "5", "0", "1", "2"]
    for test_input in test_inputs:
        result = subprocess.run([test_binary, test_input])
        expected_output = result.stdout.strip()
        test_samples.append({
            "input": test_input,
            "output": expected_output  # ← 动态获取期望输出
        })
```

### **数据集中的预生成测试用例**

**✅ 存在预生成的测试用例，但格式不同：**

**位置**: `/home/changdi/sactor-datasets/TransCoder-IR-dataset/test_tasks/`

**格式**: 
```json
[
    {"command": "%t 0"},
    {"command": "%t 1"},
    {"command": "%t 2"},
    // ... 10个测试命令
]
```

**问题**:
1. **没有期望输出**: 只有命令，没有 `output` 字段
2. **文件不匹配**: 预生成的测试用例文件名与我们的 C 文件不匹配
3. **格式不兼容**: SACToR 需要 `{"input": "...", "output": "..."}` 格式

## 📊 **对比分析**

| 方面 | 预生成测试用例 | 我们的动态生成 |
|------|---------------|----------------|
| **期望输出** | ❌ 没有 | ✅ 动态获取 |
| **文件匹配** | ❌ 文件名不匹配 | ✅ 自动匹配 |
| **格式兼容** | ❌ 格式不兼容 | ✅ SACToR 兼容 |
| **准确性** | ❓ 未知 | ✅ 100% 准确 |
| **生成速度** | ✅ 快 | ❌ 需要编译运行 |

## 🔧 **为什么不能直接使用预生成的测试用例**

### **1. 格式不兼容**
```json
// 预生成的格式（不兼容）
{"command": "%t 0"}

// SACToR 需要的格式
{"input": "10", "output": "22.000000"}
```

### **2. 缺少期望输出**
- 预生成的测试用例只有命令，没有期望输出
- SACToR 验证需要比较实际输出和期望输出
- 没有期望输出就无法进行验证

### **3. 文件映射问题**
- 预生成的测试用例文件名与我们的 C 文件不匹配
- 例如：`s005765690.c` 没有对应的测试文件

## 💡 **改进建议**

### **方案1：修改脚本使用预生成测试用例（如果存在）**
```python
def generate_test_samples_optimized(self, c_file_path: str) -> List[Dict]:
    """优化的测试用例生成"""
    # 1. 尝试查找预生成的测试用例
    pre_generated = self._find_pre_generated_tests(c_file_path)
    if pre_generated:
        # 2. 转换为 SACToR 格式
        return self._convert_to_sactor_format(pre_generated)
    
    # 3. 回退到动态生成
    return self._generate_dynamically(c_file_path)
```

### **方案2：预生成 SACToR 兼容的测试用例**
```python
def pre_generate_all_tests(self):
    """为所有 C 文件预生成 SACToR 兼容的测试用例"""
    for c_file in all_c_files:
        test_samples = self._generate_dynamically(c_file)
        self._save_test_samples(c_file, test_samples)
```

## 🎯 **当前方案的优势**

### **✅ 动态生成的优点：**
1. **100% 准确**: 期望输出直接从 C 程序运行获取
2. **自动匹配**: 每个 C 文件都有对应的测试用例
3. **格式正确**: 直接生成 SACToR 需要的格式
4. **无需维护**: 不需要手动维护测试用例文件

### **⚠️ 动态生成的缺点：**
1. **速度较慢**: 需要编译和运行每个 C 程序
2. **依赖环境**: 需要 gcc 编译器
3. **可能失败**: 某些 C 程序可能无法编译或运行

## 📋 **总结**

**回答你的问题：不是，我们现在不是使用预生成的测试用例。**

**原因：**
1. ✅ **预生成的测试用例存在**，但格式不兼容
2. ✅ **我们的脚本动态生成**测试用例，包含正确的期望输出
3. ✅ **动态生成更准确**，因为期望输出直接从 C 程序获取
4. ✅ **虽然速度较慢**，但确保了测试的准确性

**这是为什么我们的脚本能够成功翻译的关键原因之一！**
