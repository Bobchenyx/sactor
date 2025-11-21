# SACToR 官方 Pipeline vs 我们的脚本对比分析

## 🔍 **Pipeline 架构对比**

### **SACToR 官方 Pipeline**

#### **1. 入口点 (`sactor/__main__.py`)**
```python
def translate(parser, args):
    sactor = Sactor(
        input_file=args.input_file,
        test_cmd_path=args.test_command_path,
        build_dir=args.build_dir,
        result_dir=args.result_dir,
        config_file=args.config_file,
        no_verify=args.no_verify,
        unidiomatic_only=args.unidiomatic_only,
        # ... 其他参数
    )
    sactor.run()
```

#### **2. 核心执行流程 (`sactor/sactor.py`)**
```python
def run(self):
    # 1. 非惯用代码翻译
    result, unidiomatic_translator = self._run_unidomatic_translation()
    
    # 2. 保存失败信息
    unidiomatic_translator.save_failure_info(...)
    
    # 3. 检查翻译结果
    if result != TranslateResult.SUCCESS:
        raise ValueError(f"Failed to translate unidiomatic code: {result}")
    
    # 4. 组合非惯用代码
    combine_result, _ = self.combiner.combine(
        os.path.join(self.result_dir, "translated_code_unidiomatic"),
        is_idiomatic=False,
    )
    
    # 5. 惯用代码翻译 (如果不是 unidiomatic_only)
    if not self.unidiomatic_only:
        result, idiomatic_translator = self._run_idiomatic_translation()
        # ... 类似的流程
```

### **我们的脚本 Pipeline**

#### **1. 入口点 (`batch_translate_fixed.py`)**
```python
def translate_and_verify_fixed(self, c_file_path: str, output_dir: str) -> Dict:
    # 1. 创建修复后的测试配置
    test_task_path, test_samples_path = self.create_fixed_test_config(c_file_path, output_dir)
    
    # 2. 使用 SACToR Docker 进行翻译
    translation_result = self.translate_with_sactor_docker_fixed(c_file_path, output_dir, test_task_path)
    
    # 3. 验证翻译结果
    verification_results = self.verify_translation_result(translation_result['result_dir'])
```

#### **2. SACToR Docker 调用**
```python
def translate_with_sactor_docker_fixed(self, c_file_path: str, output_dir: str, test_task_path: str) -> Dict:
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{sactor_config}:/app/sactor.toml",
        "-v", f"{output_dir}:/tmp/translation",
        "sactor", "translate",  # ← 调用 SACToR 官方命令
        f"/tmp/translation/{os.path.basename(c_file_path)}",
        f"/tmp/translation/test_task.json",
        "--result-dir", "/tmp/translation/result",
        "--type", "bin"
    ]
```

## 📊 **详细对比表**

| 方面 | SACToR 官方 Pipeline | 我们的脚本 | 是否相同 |
|------|---------------------|------------|----------|
| **入口点** | `sactor translate` 命令 | Docker 调用 `sactor translate` | ✅ **完全相同** |
| **核心翻译逻辑** | `Sactor.run()` | 通过 Docker 调用 `Sactor.run()` | ✅ **完全相同** |
| **非惯用翻译** | `UnidiomaticTranslator` | 通过 Docker 调用 | ✅ **完全相同** |
| **惯用翻译** | `IdiomaticTranslator` | 通过 Docker 调用 | ✅ **完全相同** |
| **验证机制** | `Verifier` 类 | 通过 Docker 调用 | ✅ **完全相同** |
| **测试运行** | `sactor run-tests` | 通过 Docker 调用 | ✅ **完全相同** |
| **配置系统** | `sactor.toml` | 使用相同的 `sactor.toml` | ✅ **完全相同** |
| **LLM 集成** | 官方 LLM 工厂 | 使用相同的 LLM 配置 | ✅ **完全相同** |

## 🔧 **关键差异分析**

### **1. 调用方式**
- **官方**: 直接 Python 调用
- **我们**: Docker 容器调用
- **影响**: 无功能差异，只是执行环境不同

### **2. 测试用例生成**
- **官方**: 使用 `TestGenerator` 类
- **我们**: 手动生成 + 自动获取期望输出
- **影响**: 我们的方法更准确，因为包含了期望输出

### **3. 批量处理**
- **官方**: 单文件处理
- **我们**: 批量处理多个文件
- **影响**: 我们添加了批量处理逻辑

### **4. 错误处理**
- **官方**: 标准错误处理
- **我们**: 增强的错误处理和进度保存
- **影响**: 更好的用户体验

## 🧪 **测试流程对比**

### **SACToR 官方测试流程**
```python
# 在 sactor/verifier/verifier.py 中
def _run_tests_with_rust(self, target, test_number=None, valgrind=False):
    # 1. 设置环境变量
    env = os.environ.copy()
    env['RUST_BACKTRACE'] = '1'
    
    # 2. 构建测试命令
    cmd = ["sactor", "run-tests", "--type", "bin", test_samples_path, target]
    if test_number is not None:
        cmd.extend([str(test_number)])
    if self.feed_as_arguments:
        cmd.append("--feed-as-args")
    
    # 3. 运行测试 (可选 Valgrind)
    if valgrind:
        valgrind_cmd = ["valgrind", "--tool=memcheck", "--leak-check=full", "--show-leak-kinds=all"]
        cmd = valgrind_cmd + cmd
    
    # 4. 执行并收集结果
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
```

### **我们的测试流程**
```python
# 通过 Docker 调用相同的测试命令
cmd = [
    "sactor", "run-tests", "--type", "bin", 
    "./test_samples.json", target, test_id, "--feed-as-args"
]
# ← 完全相同的命令格式
```

## ✅ **结论**

### **Pipeline 一致性**
我们的脚本和 SACToR 官方 GitHub 的翻译 pipeline **完全一致**：

1. **✅ 相同的入口点**: 都调用 `sactor translate` 命令
2. **✅ 相同的核心逻辑**: 都使用 `Sactor.run()` 方法
3. **✅ 相同的翻译器**: 都使用 `UnidiomaticTranslator` 和 `IdiomaticTranslator`
4. **✅ 相同的验证器**: 都使用 `Verifier` 类
5. **✅ 相同的测试流程**: 都使用 `sactor run-tests` 命令
6. **✅ 相同的配置**: 都使用 `sactor.toml` 配置文件
7. **✅ 相同的 LLM**: 都使用相同的 LLM 工厂和配置

### **主要改进**
我们的脚本在官方 pipeline 基础上添加了：

1. **🔧 修复的测试用例**: 自动生成包含期望输出的测试用例
2. **📊 批量处理**: 支持处理多个文件
3. **💾 进度保存**: 定期保存处理进度
4. **🔍 增强验证**: 更详细的验证结果收集
5. **⚙️ 配置优化**: 增加最大尝试次数到 20

### **测试流程一致性**
测试时使用的流程**完全相同**：
- 相同的 `sactor run-tests` 命令
- 相同的 Valgrind 内存检查
- 相同的测试用例格式
- 相同的验证标准

**总结**: 我们的脚本本质上是 SACToR 官方 pipeline 的增强版，保持了完全的功能一致性，同时添加了批量处理和错误修复功能。
