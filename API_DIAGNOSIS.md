# 🔴 API 诊断报告

## 问题确认

经过全面测试，**所有模型都无法使用**，包括：
- ❌ 35个备用模型列表中的所有模型
- ❌ 基础免费模型（qwen-turbo等）
- ❌ 旧版本模型（qwen1.5系列）
- ❌ 新版本模型（qwen2.5系列）

## 错误原因

```
Error code: 403 - AccessDenied.Unpurchased
Message: Access to model denied. Please make sure you are eligible 
         for using the model.
```

这**不是配额问题**，而是**权限问题**：
- ✅ API Key 有效（认证通过）
- ✅ 有配额余额
- ❌ 没有模型使用权限

## 阿里云通义千问的计费模式

阿里云通义千问采用"模型独立授权"模式：
1. 每个模型需要单独开通使用权限
2. 即使账户有余额，也需要对每个模型授权
3. 不同模型有不同的计费方式：
   - 免费试用（通常有次数限制）
   - 按量付费（需要先开通）
   - 包年包月（企业套餐）

## 必须执行的操作

### 步骤1: 登录控制台

访问：https://dashscope.console.aliyun.com/

### 步骤2: 查看可用模型

在控制台中找到：
- **模型广场** 或 **API管理**
- 查看哪些模型显示为"已开通"或"可试用"

### 步骤3: 开通模型权限

选择你需要的模型并开通：

**推荐开通顺序**（按成本从低到高）：

1. **qwen-turbo** - 基础模型，成本最低
   - 适合大批量翻译
   - 质量中等

2. **qwen-plus** - 增强模型，平衡性价比
   - 性能和成本平衡
   - 适合一般任务

3. **qwen3-coder-flash** - 代码专用快速模型
   - 专门优化代码任务
   - 成本较低

4. **qwen3-coder-plus** - 代码专用高级模型
   - 代码质量最高
   - 成本较高

### 步骤4: 记录可用模型

开通后，记录下模型的**准确名称**（API中使用的名称）

### 步骤5: 更新配置

编辑 `/home/changdi/sactor/sactor.toml`：

```toml
[Qwen]
model = "你开通的模型名称"  # 例如 "qwen-turbo"

available_models = [
    "你开通的模型1",
    "你开通的模型2",
    # ... 只保留已开通的模型
]
```

## 临时解决方案

如果无法立即开通模型，可以考虑：

### 方案A: 使用其他LLM服务

修改 `sactor.toml` 使用其他已有的 API：

```toml
[general]
llm = "OpenAI"  # 或 "DeepSeek" 或 "Anthropic"

[OpenAI]
api_key = "你的OpenAI key"
model = "gpt-4o-mini"  # 或其他可用模型
```

### 方案B: 申请免费试用

1. 查看是否有新用户试用活动
2. 申请模型测试权限
3. 联系客服申请临时额度

## 验证脚本

开通模型后，运行以下命令验证：

```bash
cd /home/changdi/sactor
docker run --rm --entrypoint python3 -v /home/changdi/sactor:/work sactor /work/test_qwen_models.py
```

## 联系支持

阿里云通义千问支持：
- 工单系统：阿里云控制台 -> 工单管理
- 客服热线：95187
- 文档中心：https://help.aliyun.com/zh/dashscope/

需要询问的问题：
1. 我的API Key为什么无法使用任何模型？
2. 如何开通模型使用权限？
3. 是否有免费试用的模型可以使用？
4. 我的账户类型是否支持这些模型？

---

**生成时间**: $(date)
**测试的API Key**: sk-2eb7b7ad4e5a4a63b34aef5f1eba03ee (前10位)
**测试的模型数**: 30+ 个
**可用模型数**: 0 个
