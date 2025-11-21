#!/usr/bin/env python3
import openai
import time

base_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# 测试不同的API keys
api_keys = [
    ("Key1", "sk-2eb7b7ad4e5a4a63b34aef5f1eba03ee"),
    ("Key2", "sk-95af377202264ba187d4863af3ce7eb4"),
]

# 简单的模型列表
test_models = ["qwen-turbo", "qwen-plus", "qwen-max", "qwen3-14b", "qwen3-4b"]

print("="*80)
print("🔍 测试不同 API Key 的模型权限")
print("="*80)

for key_name, api_key in api_keys:
    print(f"\n📋 测试 {key_name}: {api_key[:10]}...")
    print("-"*80)
    
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    available = []
    
    for model in test_models:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
                extra_body={"enable_thinking": False}
            )
            print(f"   ✅ {model}")
            available.append(model)
        except openai.PermissionDeniedError:
            print(f"   ❌ {model} (未购买)")
        except Exception as e:
            print(f"   ❌ {model} ({type(e).__name__})")
        time.sleep(0.5)
    
    print(f"\n   结果: {len(available)}/{len(test_models)} 可用")
    if available:
        print(f"   可用模型: {', '.join(available)}")

print("\n" + "="*80)
