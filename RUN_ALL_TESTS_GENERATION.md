# 处理所有C文件并按文件夹结构保存

## 修改说明

已修改 `batch_generate_tests.py`，现在会：

1. ✅ **处理所有C文件**（不是随机采样）
2. ✅ **按文件夹结构保存**：保持与输入相同的目录结构
3. ✅ **一一对应**：C文件名和测试JSON文件名完全对应

## 目录结构

### 输入结构
```
/home/changdi/CodeNet/new-data/
├── p00000/
│   └── C/
│       ├── s015231140.c
│       ├── s052253756.c
│       └── ...
├── p00001/
│   └── C/
│       └── ...
└── ...
```

### 输出结构
```
/home/changdi/sactor/generated_tests/
├── p00000/
│   └── C/
│       ├── s015231140.c.json  ← 对应 s015231140.c
│       ├── s052253756.c.json  ← 对应 s052253756.c
│       └── ...
├── p00001/
│   └── C/
│       └── ...
├── logs/
│   ├── generation_log_YYYYMMDD_HHMMSS.csv
│   ├── generation_results.json
│   └── progress_*.json
└── ...
```

## 运行方法

### 基本运行
```bash
cd /home/changdi/sactor
python3 batch_generate_tests.py --workers 15 --num-tests 8
```

### 参数说明

- `--workers 15`: 使用15个并行线程
- `--num-tests 8`: 每个C文件生成8个测试用例

### 预计处理时间

- 总C文件数：约 66,809 个
- 并行线程数：15
- 平均处理时间：30秒/文件
- **预计总时间**：约 37 小时

### 断点续传

脚本会：
- ✅ 每处理5个文件保存一次进度
- ✅ 实时保存CSV日志
- ✅ 跳过已存在的测试JSON文件（如果重新运行）

## 日志文件

### CSV日志
```csv
timestamp,problem_dir,c_file,c_file_path,success,processing_time,test_count,success_rate,error
2025-10-19T...,p00000,s015231140.c,/path/to/file,True,25.3,8,85.2,
```

### JSON结果
```json
{
  "total": 66809,
  "success": 54000,
  "failed": 12809,
  "success_rate": 80.8,
  ...
}
```

## 优势

1. ✅ **完整覆盖**：处理所有C文件
2. ✅ **结构清晰**：按问题目录组织
3. ✅ **一一对应**：文件名匹配
4. ✅ **易于查找**：p00000/C/xxx.c → p00000/C/xxx.c.json
5. ✅ **并行处理**：15线程加速
6. ✅ **实时日志**：CSV记录每个文件的处理情况

## 注意事项

1. **磁盘空间**：预计需要约 5-10GB 空间
2. **网络稳定**：长时间运行，确保网络稳定
3. **API配额**：检查Qwen API配额是否足够
4. **中断恢复**：可以随时Ctrl+C中断，重新运行会跳过已处理的文件

## 查看进度

### 实时查看日志
```bash
tail -f /home/changdi/sactor/generated_tests/logs/generation_log_*.csv
```

### 统计已完成数量
```bash
find /home/changdi/sactor/generated_tests -name "*.json" | wc -l
```

### 查看成功率
```bash
tail -1 /home/changdi/sactor/generated_tests/logs/generation_log_*.csv | cut -d',' -f8
```

## 完成后

所有测试JSON文件将保存在:
```
/home/changdi/sactor/generated_tests/p*/C/*.c.json
```

可以直接用于后续的翻译任务！

