# 📚 CodeNet C→Rust 批量翻译指南

## 🎯 数据集概览

### 数据集1: test_4k_accept (第1-2个Accepted)
- **位置**: `/home/changdi/CodeNet/test_4k_accept`
- **题目数**: 3,265 个
- **C文件数**: 6,161 个
- **说明**: 每题选择前2个Accepted的C文件

### 数据集2: test_4k_accept_34 (第3-4个Accepted)
- **位置**: `/home/changdi/CodeNet/test_4k_accept_34`
- **题目数**: 2,639 个
- **C文件数**: 5,049 个
- **说明**: 每题选择第3-4个Accepted的C文件

### 测试JSON
- **位置**: `/home/changdi/sactor/generated_tests`
- **说明**: 两个数据集共享相同的测试JSON

---

## 🚀 翻译工具

### 工具1: 通用翻译脚本 (固定模型)
**文件**: `batch_translate_generic.py`

**特点**:
- ✅ 支持任意C文件数据集
- ✅ 参数化配置（C文件目录、JSON目录、输出目录）
- ✅ 可指定并发数和测试用例数
- ❌ 不支持自动模型切换（遇到配额错误会失败）

**基本用法**:
```bash
python3 batch_translate_generic.py \
    --c-files <C文件目录> \
    --json-files <JSON目录> \
    --output <输出目录> \
    --workers 4 \
    --num-tests 6
```

### 工具2: 自动模型切换翻译脚本
**文件**: `batch_translate_generic_auto_switch.py`

**特点**:
- ✅ 支持任意C文件数据集
- ✅ 参数化配置
- ✅ 自动检测配额错误
- ✅ 自动切换到备用模型
- ✅ 尝试所有可用模型直到成功

**基本用法**:
```bash
python3 batch_translate_generic_auto_switch.py \
    --c-files <C文件目录> \
    --json-files <JSON目录> \
    --output <输出目录> \
    --workers 10 \
    --num-tests 6
```

---

## 📋 使用示例

### 示例1: 翻译 test_4k_accept (第1-2批)

#### 使用固定模型:
```bash
cd /home/changdi/sactor

python3 batch_translate_generic.py \
    --c-files /home/changdi/CodeNet/test_4k_accept \
    --json-files /home/changdi/sactor/generated_tests \
    --output /home/changdi/sactor/translated_rust_4k \
    --workers 4 \
    --num-tests 6
```

#### 使用自动模型切换 (推荐):
```bash
cd /home/changdi/sactor

python3 batch_translate_generic_auto_switch.py \
    --c-files /home/changdi/CodeNet/test_4k_accept \
    --json-files /home/changdi/sactor/generated_tests \
    --output /home/changdi/sactor/translated_rust_4k \
    --workers 10 \
    --num-tests 6
```

### 示例2: 翻译 test_4k_accept_34 (第3-4批)

#### 使用固定模型:
```bash
cd /home/changdi/sactor

python3 batch_translate_generic.py \
    --c-files /home/changdi/CodeNet/test_4k_accept_34 \
    --json-files /home/changdi/sactor/generated_tests \
    --output /home/changdi/sactor/translated_rust_4k_34 \
    --workers 4 \
    --num-tests 6
```

#### 使用自动模型切换 (推荐):
```bash
cd /home/changdi/sactor

python3 batch_translate_generic_auto_switch.py \
    --c-files /home/changdi/CodeNet/test_4k_accept_34 \
    --json-files /home/changdi/sactor/generated_tests \
    --output /home/changdi/sactor/translated_rust_4k_34 \
    --workers 10 \
    --num-tests 8
```

---

## ⚙️ 参数说明

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--c-files` | C文件目录 | `/home/changdi/CodeNet/test_4k_accept` |
| `--json-files` | JSON测试文件目录 | `/home/changdi/sactor/generated_tests` |
| `--output` | 输出目录 | `/home/changdi/sactor/translated_rust_4k` |

### 可选参数

| 参数 | 说明 | 默认值 | 推荐值 |
|------|------|--------|--------|
| `--workers` | 并发数 | 4 | 4-10 |
| `--num-tests` | 测试用例数 | 6 | 6-10 |

**参数建议**:
- `workers`: 并发数越高，速度越快，但API调用也越频繁
  - 推荐: 4-10（根据API配额调整）
- `num-tests`: 测试用例数越多，验证越严格，但翻译时间越长
  - 推荐: 6-8（平衡验证质量和速度）

---

## 📊 输出结构

翻译后的文件结构:

```
translated_rust_4k/
├── p00000/
│   └── Rust/
│       ├── s123456789/
│       │   └── translated_code_unidiomatic/
│       │       └── combined.rs  ← 主要输出文件
│       └── s987654321/
│           └── translated_code_unidiomatic/
│               └── combined.rs
├── p00001/
│   └── Rust/
│       └── ...
└── ...
```

**关键文件**:
- `combined.rs`: 完整的翻译后的Rust代码
- 只生成 unidiomatic 版本（使用 `--unidiomatic-only` 标志）
- 每个C文件有独立的输出目录

---

## 🔄 自动模型切换逻辑

### 触发条件
当检测到以下错误时，自动切换模型:
- `Error code: 403` (权限错误)
- `Error code: 429` (请求频率限制)
- `rate limit` (频率限制)
- `quota exceeded` (配额用完)
- `AllocationQuota` (配额分配错误)
- `AccessDenied.Unpurchased` (模型未购买)

### 切换流程
1. 检测到配额错误
2. 停止当前翻译进程
3. 切换到下一个备用模型
4. 更新 `sactor.toml` 配置
5. 等待5秒后重启翻译
6. 重复直到成功或所有模型都尝试过

### 可用模型
模型列表定义在 `sactor.toml` 中的 `available_models` 数组:

```toml
available_models = [
    "qwen3-coder-flash",      # 当前使用
    "qwen3-coder-plus",       # 备用1
    "qwen-plus-latest",       # 备用2
    "qwen3-max",              # 备用3
    # ... 更多模型
]
```

**修改模型列表**:
1. 编辑 `/home/changdi/sactor/sactor.toml`
2. 修改 `available_models` 数组
3. 将优先级高的模型放在前面

---

## 📈 进度监控

### 查看翻译进度
```bash
# 统计已翻译的文件数
find /home/changdi/sactor/translated_rust_4k -name "combined.rs" | wc -l

# 查看最近翻译的文件
find /home/changdi/sactor/translated_rust_4k -name "combined.rs" -type f -printf '%T@ %p\n' | sort -n | tail -10
```

### 查看翻译日志
翻译过程会实时输出进度信息:
```
🔄 开始翻译: p00001/s123456789
   C文件: /home/changdi/CodeNet/test_4k_accept/p00001/C/s123456789.c
   JSON: /home/changdi/sactor/generated_tests/p00001/C/xxx.json
   输出: /home/changdi/sactor/translated_rust_4k/p00001/Rust/s123456789

✅ [1/1561] p00001/s123456789 - 翻译成功
```

---

## 🛠️ 故障排除

### 问题1: 配额错误
**症状**: 看到 `Error code: 403` 或 `quota exceeded`

**解决方案**:
1. 使用自动模型切换脚本 (`batch_translate_generic_auto_switch.py`)
2. 或者登录阿里云控制台，启用/购买更多模型
3. 或者等待配额重置（通常每天重置）

### 问题2: Docker错误
**症状**: `docker: command not found` 或权限错误

**解决方案**:
```bash
# 检查Docker是否运行
sudo systemctl start docker

# 检查SACToR镜像是否存在
docker images | grep sactor

# 如果不存在，重新构建
cd /home/changdi/sactor
docker build -t sactor .
```

### 问题3: 翻译失败
**症状**: 输出文件未生成或太小 (<100字节)

**可能原因**:
1. C代码语法错误
2. 测试用例失败
3. LLM生成的代码质量差

**解决方案**:
1. 查看详细的错误日志
2. 手动检查C文件是否有效
3. 增加 `max_translation_attempts` (在 `sactor.toml` 中)

### 问题4: 进程卡住
**症状**: 长时间没有输出

**解决方案**:
1. 按 `Ctrl+C` 中断
2. 检查是否有Docker进程残留: `docker ps`
3. 清理残留进程: `docker stop <container_id>`
4. 重新启动翻译

---

## 💡 最佳实践

### 1. 分批翻译
- 先完成 `test_4k_accept` (第1-2批)
- 再开始 `test_4k_accept_34` (第3-4批)
- 避免同时运行多个翻译任务

### 2. 合理设置并发
- 开始时使用较低的并发数 (4-6)
- API稳定后可以提高到 10
- 监控API配额使用情况

### 3. 定期检查进度
- 每小时检查一次翻译文件数
- 确保进度正常推进
- 及时发现和解决问题

### 4. 备份重要文件
- 定期备份 `sactor.toml`
- 备份已翻译的Rust文件
- 避免意外数据丢失

### 5. 监控资源使用
```bash
# 查看磁盘使用
du -sh /home/changdi/sactor/translated_rust_4k*

# 查看内存使用
free -h

# 查看Docker资源
docker stats
```

---

## 📞 快速参考

### 常用命令
```bash
# 翻译第1-2批 (推荐用法)
python3 -u batch_translate_generic_auto_switch.py \
    --c-files /home/changdi/CodeNet/test_4k_accept \
    --json-files /home/changdi/sactor/generated_tests \
    --output /home/changdi/sactor/translated_rust_4k \
    --workers 10

# 翻译第3-4批 (推荐用法)
python3 -u batch_translate_generic_auto_switch.py \
    --c-files /home/changdi/CodeNet/test_4k_accept_34 \
    --json-files /home/changdi/sactor/generated_tests \
    --output /home/changdi/sactor/translated_rust_4k_34 \
    --workers 10

# 查看进度
find /home/changdi/sactor/translated_rust_4k -name "combined.rs" | wc -l

# 查看配置
cat /home/changdi/sactor/sactor.toml | grep "model = "
```

---

## 🎓 总结

### 数据规模
- **总C文件**: 11,210 个
- **预计有JSON**: ~2,803 个 (25%)
- **翻译目标**: 11,210 个Rust文件

### 推荐流程
1. ✅ 使用 `batch_translate_generic_auto_switch.py`
2. ✅ 先翻译 test_4k_accept
3. ✅ 再翻译 test_4k_accept_34
4. ✅ 定期监控进度
5. ✅ 备份重要文件

### 关键文件
- **翻译脚本**: `batch_translate_generic.py`, `batch_translate_generic_auto_switch.py`
- **配置文件**: `sactor.toml`
- **输出目录**: `translated_rust_4k/`, `translated_rust_4k_34/`
- **测试JSON**: `generated_tests/`

---

**祝翻译顺利！** 🎉

