# Qwen API 使用指南

## 🚀 快速开始

### 1. 获取API密钥
- 访问 [阿里云DashScope](https://dashscope.aliyun.com/)
- 注册/登录阿里云账号
- 获取API密钥

### 2. 配置SACToR
修改 `sactor.toml` 文件：

```toml
[general]
llm = "Qwen"  # 改为使用Qwen

[Qwen]
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key = "你的实际API密钥"
model = "qwen-plus"  # 可选模型见下方
max_tokens = 8192
max_completion_tokens = 8192
# temperature = 1  # 可选，取消注释以设置
```

### 3. 运行翻译
```bash
python3 batch_translate_correct.py
```

## 📋 可用的Qwen模型

| 模型 | 描述 | 适用场景 |
|------|------|----------|
| `qwen-plus` | 平衡性能和成本 | 日常翻译任务 |
| `qwen-max` | 最强性能 | 复杂代码翻译 |
| `qwen-turbo` | 快速响应 | 简单快速翻译 |
| `qwen-long` | 长文本处理 | 大型文件翻译 |

## 🔧 技术细节

### API兼容性
- Qwen LLM使用OpenAI兼容的API接口
- 支持 `max_tokens` 和 `max_completion_tokens` 参数
- 自动处理temperature参数

### 输出目录
翻译结果会保存在：
```
/home/changdi/sactor/test_qwen_plus/  # 根据模型名称
```

### 日志文件
日志文件包含模型信息：
```
translation_log_2025-10-06_qwen_plus.json
translation_log_2025-10-06_qwen_plus.csv
```

## 🐛 故障排除

### 常见问题
1. **API密钥错误**: 检查密钥是否正确
2. **网络连接**: 确保可以访问阿里云API
3. **模型名称**: 确认模型名称拼写正确

### 调试方法
```bash
# 检查配置
python3 -c "
import toml
with open('sactor.toml', 'r') as f:
    config = toml.load(f)
print('Qwen配置:', config.get('Qwen', {}))
"
```

## 📊 成本对比

| 模型 | 输入价格 | 输出价格 | 备注 |
|------|----------|----------|------|
| qwen-plus | ¥0.008/1K tokens | ¥0.02/1K tokens | 推荐 |
| qwen-max | ¥0.02/1K tokens | ¥0.06/1K tokens | 高性能 |
| qwen-turbo | ¥0.003/1K tokens | ¥0.006/1K tokens | 经济型 |

*价格可能变动，请以官方最新价格为准*
