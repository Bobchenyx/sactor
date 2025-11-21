# 📚 CodeNet 全量 Accepted C → Rust 翻译指南

## 🎯 功能概述

这个工具可以翻译 **整个 CodeNet 数据集中所有 Accepted 的 C 文件**，支持：

- ✅ **断点续传**: 中断后可以从上次停止的地方继续
- ✅ **进度记录**: 自动保存翻译进度到文件
- ✅ **增量翻译**: 跳过已完成的文件
- ✅ **安全中断**: Ctrl+C 中断不会丢失进度
- ✅ **详细日志**: 记录所有翻译活动

---

## 📊 数据规模

根据之前的统计：

| 项目 | 数量 |
|------|------|
| CodeNet 总题目 | 4,054 个 |
| C 语言提交总数 | 754,058 个 |
| **Accepted C 提交** | **313,360 个** |
| 已有测试 JSON | ~1,561 个题目 |

**预计翻译目标**: 
- 有 JSON 的 Accepted C 文件: ~78,000 个
- 全部 Accepted C 文件: 313,360 个

---

## 🚀 快速开始

### 方法1: 使用快速启动脚本（推荐）

```bash
cd /home/changdi/sactor

# 使用默认配置 (并发10, 测试6)
./start_translate_all_accepted.sh

# 自定义并发数
./start_translate_all_accepted.sh 20

# 自定义并发和测试数
./start_translate_all_accepted.sh 15 8
```

### 方法2: 直接使用 Python 脚本

```bash
cd /home/changdi/sactor

# 首次运行
python3 translate_all_codenet_accepted.py --workers 10

# 断点续传（默认）
python3 translate_all_codenet_accepted.py --resume --workers 10

# 从头开始（忽略之前的进度）
python3 translate_all_codenet_accepted.py --no-resume --workers 10
```

---

## ⚙️ 参数说明

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--workers` | 并发数 | 10 |
| `--num-tests` | 测试用例数 | 6 |
| `--resume` | 启用断点续传 | True |
| `--no-resume` | 禁用断点续传，从头开始 | - |

### 使用示例

```bash
# 低并发，适合测试
python3 translate_all_codenet_accepted.py --workers 3 --num-tests 4

# 中等并发（推荐）
python3 translate_all_codenet_accepted.py --workers 10 --num-tests 6

# 高并发，快速完成
python3 translate_all_codenet_accepted.py --workers 20 --num-tests 8

# 重新开始翻译
python3 translate_all_codenet_accepted.py --no-resume --workers 10
```

---

## 📁 文件和目录

### 输入文件

| 文件/目录 | 说明 |
|-----------|------|
| `/home/changdi/CodeNet/Project_CodeNet/data/` | CodeNet C 源文件 |
| `/home/changdi/CodeNet/Project_CodeNet/metadata/` | Metadata CSV 文件 |
| `/home/changdi/sactor/generated_tests/` | 测试 JSON 文件 |

### 输出文件

| 文件/目录 | 说明 |
|-----------|------|
| `/home/changdi/sactor/translated_rust_all_accepted/` | 翻译后的 Rust 文件 |
| `/home/changdi/sactor/translation_progress.json` | 进度文件 |
| `/home/changdi/sactor/translation_log.txt` | 详细日志 |

### 输出目录结构

```
translated_rust_all_accepted/
├── p00000/
│   └── Rust/
│       ├── s000000001/
│       │   └── translated_code_unidiomatic/
│       │       └── combined.rs
│       ├── s000000002/
│       │   └── translated_code_unidiomatic/
│       │       └── combined.rs
│       └── ...
├── p00001/
│   └── Rust/
│       └── ...
└── ...
```

---

## 🔄 断点续传机制

### 工作原理

1. **进度记录**: 每翻译10个文件自动保存一次进度
2. **任务检查**: 启动时检查所有已完成的任务
3. **自动跳过**: 跳过已存在的 `combined.rs` 文件
4. **安全中断**: Ctrl+C 中断时保存进度

### 进度文件格式

```json
{
  "completed": [
    "p00000/s000000001",
    "p00000/s000000002",
    ...
  ],
  "failed": [
    "p00123/s999999999"
  ],
  "last_update": "2025-10-28T12:34:56",
  "statistics": {
    "total_completed": 1234,
    "total_failed": 56,
    "total_skipped": 789
  }
}
```

### 使用断点续传

```bash
# 1. 启动翻译
./start_translate_all_accepted.sh 10

# 2. 按 Ctrl+C 中断
# ⚠️  收到中断信号，正在保存进度...
# ✅ 进度已保存

# 3. 重新启动（自动从上次停止的地方继续）
./start_translate_all_accepted.sh 10

# 输出会显示:
# ✅ 加载进度文件: 1234 个已完成
```

---

## 📊 进度监控

### 实时查看翻译进度

```bash
# 统计已翻译文件数
find /home/changdi/sactor/translated_rust_all_accepted -name "combined.rs" | wc -l

# 实时监控（每10秒刷新）
watch -n 10 'find /home/changdi/sactor/translated_rust_all_accepted -name "combined.rs" | wc -l'

# 查看最新翻译的10个文件
find /home/changdi/sactor/translated_rust_all_accepted -name "combined.rs" -type f -printf '%T@ %p\n' | sort -n | tail -10

# 查看目录大小
du -sh /home/changdi/sactor/translated_rust_all_accepted
```

### 查看进度文件

```bash
# 查看进度统计
cat /home/changdi/sactor/translation_progress.json | python3 -m json.tool | head -30

# 查看最近的日志
tail -50 /home/changdi/sactor/translation_log.txt

# 实时跟踪日志
tail -f /home/changdi/sactor/translation_log.txt
```

### 分析进度

```bash
# 统计成功、失败、跳过的数量
cat /home/changdi/sactor/translation_progress.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
stats = data.get('statistics', {})
print(f\"成功: {stats.get('total_completed', 0)}\")
print(f\"失败: {stats.get('total_failed', 0)}\")
print(f\"跳过: {stats.get('total_skipped', 0)}\")
"
```

---

## 🛠️ 进度管理

### 查看当前进度

```bash
# 查看进度文件
cat /home/changdi/sactor/translation_progress.json

# 统计已完成数量
python3 -c "
import json
with open('/home/changdi/sactor/translation_progress.json') as f:
    data = json.load(f)
    print(f'已完成: {len(data.get(\"completed\", []))} 个')
"
```

### 重置进度（从头开始）

```bash
# 方法1: 删除进度文件
rm /home/changdi/sactor/translation_progress.json

# 方法2: 使用 --no-resume 参数
python3 translate_all_codenet_accepted.py --no-resume --workers 10

# 方法3: 删除输出目录和进度文件
rm -rf /home/changdi/sactor/translated_rust_all_accepted
rm /home/changdi/sactor/translation_progress.json
```

### 清理失败的任务

如果想重新翻译失败的任务：

```bash
# 1. 编辑进度文件，删除 failed 列表
# 2. 或者手动删除对应的输出文件
# 3. 重新运行脚本
```

---

## 💡 使用建议

### 推荐配置

| 场景 | 并发数 | 测试数 | 说明 |
|------|--------|--------|------|
| 初次测试 | 3 | 3 | 测试脚本是否正常工作 |
| 日常使用 | 10 | 6 | 平衡速度和质量 |
| 夜间运行 | 15-20 | 8 | 无人值守，加快进度 |
| API 有限 | 5 | 4 | 节约 API 配额 |

### 最佳实践

1. **分阶段运行**:
   - 先用小并发测试（workers=3）
   - 确认正常后提高并发（workers=10-20）

2. **定期检查**:
   - 每小时检查一次进度
   - 查看日志文件是否有异常

3. **备份进度**:
   ```bash
   # 定期备份进度文件
   cp translation_progress.json translation_progress.backup.json
   ```

4. **监控资源**:
   ```bash
   # 查看 CPU 和内存使用
   htop
   
   # 查看磁盘空间
   df -h
   
   # 查看 Docker 容器
   docker ps
   ```

5. **分批翻译**:
   - 如果任务太多，可以考虑分批
   - 例如先翻译有 JSON 的文件
   - 再翻译没有 JSON 的文件

---

## 🔍 故障排除

### 问题1: 脚本中断后进度丢失

**解决方案**: 
- 确保使用 `--resume` 参数（默认启用）
- 检查 `translation_progress.json` 是否存在

### 问题2: 翻译速度很慢

**解决方案**:
- 增加并发数: `--workers 20`
- 减少测试数: `--num-tests 4`
- 检查 API 配额是否充足

### 问题3: 大量翻译失败

**解决方案**:
- 查看日志: `tail -100 translation_log.txt`
- 检查常见错误模式
- 考虑调整 `max_translation_attempts`

### 问题4: 磁盘空间不足

**解决方案**:
```bash
# 查看磁盘使用
df -h

# 清理 Docker 临时文件
docker system prune -a

# 删除旧的翻译结果
rm -rf /home/changdi/sactor/translated_rust_4k
```

### 问题5: 内存占用过高

**解决方案**:
- 降低并发数: `--workers 5`
- 清理 Docker 容器: `docker system prune`

---

## 📈 预估时间

### 基于当前进度估算

假设：
- 平均翻译速度: 0.5 个/秒（workers=10）
- 有 JSON 的文件: ~78,000 个

```
预计时间 = 78,000 / 0.5 / 3600 = 43 小时
```

实际时间取决于：
- 并发数
- API 响应速度
- 网络状况
- 测试用例数量

---

## 🎓 高级用法

### 只翻译特定范围的题目

修改脚本中的 `collect_all_accepted_c_files` 方法，添加过滤条件：

```python
for metadata_file in metadata_files:
    problem_id = metadata_file.replace('.csv', '')
    
    # 只翻译 p00000 到 p00999
    if not (problem_id >= 'p00000' and problem_id <= 'p00999'):
        continue
    
    # ... 其余代码
```

### 并行运行多个实例

可以同时运行多个脚本实例，只要：
1. 使用不同的输出目录
2. 处理不同范围的题目
3. 注意 API 配额限制

---

## 📞 快速参考

### 常用命令

```bash
# 启动翻译（默认配置）
./start_translate_all_accepted.sh

# 启动翻译（高并发）
./start_translate_all_accepted.sh 20 8

# 查看进度
find /home/changdi/sactor/translated_rust_all_accepted -name "combined.rs" | wc -l

# 查看日志
tail -f /home/changdi/sactor/translation_log.txt

# 查看进度文件
cat /home/changdi/sactor/translation_progress.json

# 重置进度
rm /home/changdi/sactor/translation_progress.json
```

---

## ✅ 总结

这个工具设计用于大规模、长时间运行的翻译任务：

- **可靠性**: 断点续传，不怕中断
- **可监控**: 详细的进度和日志
- **灵活性**: 可调整并发和测试参数
- **易用性**: 一键启动，自动管理

适合：
- ✅ 翻译整个 CodeNet 数据集
- ✅ 无人值守长时间运行
- ✅ 分阶段、分批次翻译
- ✅ 需要完整进度记录的场景

---

**祝翻译顺利！** 🎉

