#!/usr/bin/env python3
"""
测试哪些 Qwen 模型真正可用
"""
import openai
import time

# 配置
base_url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
api_key = "sk-2eb7b7ad4e5a4a63b34aef5f1eba03ee"

client = openai.OpenAI(
    api_key=api_key,
    base_url=base_url
)

# 要测试的模型列表
models_to_test = [
    # Coder系列
    "qwen3-coder-flash",
    "qwen3-coder-plus",
    "qwen-coder-turbo",
    
    # Flagship系列
    "qwen-max",
    "qwen-max-latest",
    "qwen3-max",
    
    # Plus系列
    "qwen-plus",
    "qwen-plus-latest",
    
    # Flash系列
    "qwen-flash",
    "qwen-turbo",
    
    # 基础系列
    "qwen3-32b",
    "qwen3-14b",
    "qwen3-8b",
    "qwen3-4b",
    "qwen3-1.7b",
    "qwen3-0.6b",
    
    # Translation
    "qwen-mt-plus",
    "qwen-mt-turbo",
]

print("="*80)
print("🔍 测试 Qwen 模型可用性")
print("="*80)
print(f"API Key: {api_key[:10]}...")
print(f"Base URL: {base_url}")
print(f"测试模型数: {len(models_to_test)}")
print("="*80)
print()

available_models = []
unavailable_models = []

for idx, model in enumerate(models_to_test, 1):
    print(f"[{idx}/{len(models_to_test)}] 测试 {model}...", end=" ", flush=True)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            extra_body={"enable_thinking": False}
        )
        print(f"✅ 可用")
        available_models.append(model)
    except openai.PermissionDeniedError as e:
        error_msg = str(e)
        if "Unpurchased" in error_msg or "AccessDenied" in error_msg:
            print(f"❌ 未购买/未开通")
        else:
            print(f"❌ 权限错误: {error_msg[:50]}")
        unavailable_models.append((model, "未购买"))
    except openai.RateLimitError as e:
        print(f"⚠️  配额限制")
        unavailable_models.append((model, "配额限制"))
    except Exception as e:
        print(f"❌ 错误: {type(e).__name__}: {str(e)[:50]}")
        unavailable_models.append((model, str(type(e).__name__)))
    
    # 避免请求过快
    time.sleep(1)

print()
print("="*80)
print("📊 测试结果")
print("="*80)
print(f"\n✅ 可用模型 ({len(available_models)} 个):")
for model in available_models:
    print(f"   - {model}")

print(f"\n❌ 不可用模型 ({len(unavailable_models)} 个):")
for model, reason in unavailable_models:
    print(f"   - {model} ({reason})")

print()
print("="*80)
print("💡 建议配置")
print("="*80)
if available_models:
    print("\n将以下可用模型添加到 sactor.toml 的 available_models 列表:")
    print("available_models = [")
    for model in available_models:
        print(f'    "{model}",')
    print("]")
else:
    print("⚠️  没有找到任何可用模型！请检查 API Key 或联系服务提供商。")

print("="*80)
