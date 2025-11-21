#!/usr/bin/env python3
import openai
import time

client = openai.OpenAI(
    api_key="sk-2eb7b7ad4e5a4a63b34aef5f1eba03ee",
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)

# 可能免费或有试用的模型
free_models = [
    "qwen-turbo",
    "qwen-long",
    "qwen1.5-72b-chat",
    "qwen1.5-32b-chat", 
    "qwen1.5-14b-chat",
    "qwen1.5-7b-chat",
    "qwen2.5-72b-instruct",
    "qwen2.5-32b-instruct",
    "qwen2.5-14b-instruct",
    "qwen2.5-7b-instruct",
    "qwen2.5-coder-32b-instruct",
    "qwen2.5-coder-7b-instruct",
]

print("="*80)
print("🔍 测试可能免费/可用的基础模型")
print("="*80)

available = []
for model in free_models:
    print(f"测试 {model}...", end=" ", flush=True)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            extra_body={"enable_thinking": False}
        )
        print(f"✅ 可用!")
        available.append(model)
    except openai.PermissionDeniedError as e:
        if "Unpurchased" in str(e):
            print(f"❌ 未购买")
        else:
            print(f"❌ 权限错误")
    except openai.NotFoundError:
        print(f"❌ 模型不存在")
    except Exception as e:
        print(f"❌ {type(e).__name__}: {str(e)[:40]}")
    time.sleep(0.5)

print("\n" + "="*80)
if available:
    print(f"✅ 找到 {len(available)} 个可用模型:")
    for m in available:
        print(f"   - {m}")
    print("\n💡 建议在 sactor.toml 中使用:")
    print(f'   model = "{available[0]}"')
else:
    print("❌ 没有找到任何可用模型")
    print("\n请：")
    print("1. 登录阿里云控制台开通模型权限")
    print("2. 或联系阿里云客服确认可用的免费模型")
print("="*80)
