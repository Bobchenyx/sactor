# SACToR翻译过程中的API Prompt总结

## 概述
SACToR是一个将C代码翻译为Rust代码的工具，它使用大语言模型(LLM)进行代码翻译。本文档总结了SACToR在翻译过程中使用的所有API prompt模板。

## 系统配置

### 基础配置 (sactor.toml)
```toml
[general]
llm = "OpenAI" # 可选: OpenAI, AzureOpenAI, DeepSeek, Anthropic, Google, Ollama
max_translation_attempts = 20
max_verifier_harness_attempts = 6
timeout_seconds = 60
system_message = '''
You are an expert in translating code from C to Rust. You will take all information from the user as reference, and will output the translated code into the format that the user wants.
'''
```

### API价格配置 (2025年最新)
- **GPT-4o价格**:
  - Input: $2.50 per 1M tokens = $0.0025 per 1K tokens
  - Output: $10.00 per 1M tokens = $0.01 per 1K tokens

## 翻译流程和Prompt模板

### 阶段1: 非惯用翻译 (Unidiomatic Translation)

#### 1.1 枚举翻译
```
Translate the following C enum to Rust. Try to keep the **equivalence** as much as possible.
`libc` will be included as the **only** dependency you can use. To keep the equivalence, you can use `unsafe` if you want.
The enum is:
```c
{code_of_enum}
```

Output the translated enum into this format (wrap with the following tags):
----ENUM----
```rust
// Your translated enum here
```
----END ENUM----
```

#### 1.2 结构体翻译
```
Translate the following C struct to Rust. Try to keep the **equivalence** as much as possible.
`libc` will be included as the **only** dependency you can use. To keep the equivalence, you can use `unsafe` if you want.
The struct is:
```c
{code_of_struct}
```

Output the translated struct into this format (wrap with the following tags):
----STRUCT----
```rust
// Your translated struct here
```
----END STRUCT----
```

#### 1.3 全局变量翻译
```
Translate the following C global variable to Rust. Try to keep the **equivalence** as much as possible.
`libc` will be included as the **only** dependency you can use. To keep the equivalence, you can use `unsafe` if you want.
The global variable is:
```c
{code_of_global_var}
```

Output the translated global variable into this format (wrap with the following tags):
----GLOBAL VAR----
```rust
// Your translated global variable here
```
----END GLOBAL VAR----
```

#### 1.4 函数翻译
```
Translate the following C function to Rust. Try to keep the **equivalence** as much as possible.
`libc` will be included as the **only** dependency you can use. To keep the equivalence, you can use `unsafe` if you want.
Your solution should only have **one** function, if you need to create help function, define the help function inside the function you translate.
The function is:
```c
{code_of_function}
```

[包含依赖的结构体、全局变量、枚举等]

Output the translated function into this format (wrap with the following tags):
----FUNCTION----
```rust
// Your translated function here
```
----END FUNCTION----
```

**特殊处理 - main函数:**
```
The function is the `main` function, which is the entry point of the program. The function signature should be: `pub fn main() -> ()`.
For `return 0;`, you can directly `return;` in Rust or ignore it if it's the last statement.
For other return values, you can use `std::process::exit()` to return the value.
For `argc` and `argv`, you can use `std::env::args()` to get the arguments.
```

### 阶段2: 惯用翻译 (Idiomatic Translation)

#### 2.1 枚举惯用翻译
```
Translate the following unidiomatic Rust enum to idiomatic Rust. Try to avoid using raw pointers in the translation of the enum.
The enum is:
```rust
{unidiomatic_enum_code}
```
If you think the enum is already idiomatic, you can directly copy the code to the output format.

Output the translated enum into this format (wrap with the following tags):
----ENUM----
```rust
// Your translated enum here
```
----END ENUM----
```

#### 2.2 结构体惯用翻译
```
Translate the following Rust struct to idiomatic Rust. Try to avoid using raw pointers in the translation of the struct.
The struct is:
```rust
{unidiomatic_struct_code}
```
If you think the struct is already idiomatic, you can directly copy the code to the output format.

Output the translated struct into this format (wrap with the following tags):
----STRUCT----
```rust
// Your translated struct here
```
----END STRUCT----
```

#### 2.3 函数惯用翻译
```
Translate the following unidiomatic Rust function into idiomatic Rust.
The function is:
```rust
{unidiomatic_function_code}
```
If you think the function is already idiomatic, you can directly copy the code to the output format.

Output the translated function into this format (wrap with the following tags):
----FUNCTION----
```rust
// Your translated function here
```
----END FUNCTION----
```

### 阶段3: 验证器 (Verifier) Prompt

#### 3.1 测试生成器
```
Generate the harness for the function {function_name}_idiomatic
The function signature is:
```rust
{function_signature}
```

Output the harness into this format (wrap with the following tags):
----HARNESS----
```rust
// Your harness here
```
----END HARNESS----
```

#### 3.2 结构体转换器
```
There are two structs: {struct_name} and C{struct_name}, the {struct_name} is the idiomatic translation of Rust code from C, the struct is
```rust
{idiomatic_struct_code}
```
The C{struct_name} is the unidiomatic translation of Rust code from C, the struct is
```rust
{unidiomatic_struct_code}
```

Output the two transformation functions into this format (wrap with the following tags):
----TRANSFORM----
```rust
// Your transformation functions here
```
----END TRANSFORM----
```

#### 3.3 函数转换器
```
This is the idiomatic translation of Rust code from C, the function signature is
```rust
{idiomatic_signature};
```
This is the unidiomatic translation of Rust code from C, the function signature is
```rust
{unidiomatic_signature};
```

{unidiomatic_signature_renamed} {{
    // TODO: Add code here to Convert the input to the idiomatic format
    let result = {idiomatic_signature_replaced}; // Call the idiomatic function
    // TODO: Add code here to Convert the result back to the original format
    // {convert_back_prompt}
}}
```
remove all the TODOs and replace them with the necessary code.

Output the translated function into this format (wrap with the following tags):
----FUNCTION----
```rust
// Your translated function here
```
----END FUNCTION----
```

## 错误处理和重试机制

### 编译错误处理
```
Lastly, the function is translated as:
```rust
{error_translation}
```
It failed to compile with the following error message:
```
{error_message}
```
Analyzing the error messages, think about the possible reasons, and try to avoid this error.
```

### 测试错误处理
```
Lastly, the function is translated as:
```rust
{error_translation}
```
It failed the following tests:
{test_results}
```

## 特殊处理规则

### 1. 保留关键字处理
```
As the function name `{function_name}` is a reserved keyword in Rust, you need to add a '_' at the end of the function name.
```

### 2. 依赖管理
- **结构体依赖**: 自动包含已翻译的结构体
- **全局变量依赖**: 自动包含已翻译的全局变量
- **枚举依赖**: 自动包含已翻译的枚举
- **函数依赖**: 自动包含已翻译的函数

### 3. 类型别名处理
```
The function uses the following type aliases, which are defined as:
```c
{type_aliases}
```
```

### 4. stdio处理
```
The function uses some of the following stdio file descriptors: {stdio_list}. Which will be included as
```rust
{stdio_code}
```
You should **NOT** include them in your translation, as the system will automatically include them.
```

## 输出格式要求

所有翻译结果都必须用特定的标签包装：

| 组件类型 | 开始标签 | 结束标签 |
|---------|---------|---------|
| 函数 | `----FUNCTION----` | `----END FUNCTION----` |
| 结构体 | `----STRUCT----` | `----END STRUCT----` |
| 枚举 | `----ENUM----` | `----END ENUM----` |
| 全局变量 | `----GLOBAL VAR----` | `----END GLOBAL VAR----` |
| 测试harness | `----HARNESS----` | `----END HARNESS----` |
| 转换函数 | `----TRANSFORM----` | `----END TRANSFORM----` |

## 翻译统计 (基于实际运行数据)

### 总体统计
- **总记录数**: 161
- **Success=True**: 115 (71.4%)
- **Success=False**: 46 (28.6%)

### 成功翻译统计
- **平均处理时间**: 92.26 秒
- **平均尝试次数**: 3.08 次
- **平均API成本**: $0.0431
- **总API成本**: $4.9557

### 失败翻译统计
- **平均处理时间**: 484.45 秒
- **平均尝试次数**: 15.22 次
- **平均API成本**: $0.3568
- **总API成本**: $16.4141

### 失败原因分析
- **超时失败**: 35 次
- **其他错误**: 11 次

### 总体成本
- **总API成本**: $21.3698
- **平均每文件API成本**: $0.1327

## 配置参数

### 重试机制
- `max_translation_attempts = 20`: 最大翻译尝试次数
- `max_verifier_harness_attempts = 6`: 最大验证器尝试次数
- `timeout_seconds = 60`: 执行超时时间

### 模型配置
- **默认模型**: GPT-4o
- **最大token数**: 8192
- **编码方式**: o200k_base

## 总结

SACToR使用结构化的prompt设计，通过三个阶段完成C到Rust的翻译：
1. **非惯用翻译**: 保持C代码的等价性，使用unsafe代码
2. **惯用翻译**: 将非惯用Rust代码转换为惯用Rust代码
3. **验证**: 生成测试用例并验证翻译结果的正确性

每个阶段都有详细的错误处理和重试机制，确保翻译的准确性和鲁棒性。

---
*文档生成时间: 2025-09-30*
*基于SACToR v1.0代码分析*
