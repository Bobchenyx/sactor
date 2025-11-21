#!/usr/bin/env python3
"""
验证Qwen显式缓存是否正常工作
"""

import json
from openai import OpenAI

def test_explicit_cache():
    """测试显式缓存功能"""
    
    print("="*80)
    print("🧪 Qwen 显式缓存验证")
    print("="*80)
    
    # 初始化客户端
    client = OpenAI(
        api_key="sk-aaca0ccf722143a39ec3c6e38a0a4bc2",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )
    
    system_message = "You are an expert in translating code from C to Rust. You will take all information from the user as reference, and will output the translated code into the format that the user wants."
    
    # 第一次请求 - 创建缓存
    print("\n📝 第一次请求 (创建缓存)...")
    messages1 = [
        {
            "role": "system",
            "content": system_message,
            "cache_control": {"type": "ephemeral"}  # 启用显式缓存
        },
        {
            "role": "user",
            "content": "Translate this C code to Rust: int add(int a, int b) { return a + b; }"
        }
    ]
    
    response1 = client.chat.completions.create(
        model="qwen3-coder-plus-2025-09-23",
        messages=messages1,
        temperature=0.3
    )
    
    print(f"\n✅ 第一次请求完成")
    print(f"Response: {response1.choices[0].message.content[:100]}...")
    print(f"\n📊 Token 使用情况:")
    print(f"  - Prompt tokens: {response1.usage.prompt_tokens}")
    print(f"  - Completion tokens: {response1.usage.completion_tokens}")
    
    # 检查是否创建了缓存
    if hasattr(response1.usage, 'prompt_tokens_details'):
        details = response1.usage.prompt_tokens_details
        if hasattr(details, 'cache_creation_input_tokens'):
            print(f"  - Cache creation tokens: {details.cache_creation_input_tokens} (按125%计费)")
        if hasattr(details, 'cached_tokens'):
            print(f"  - Cached tokens: {details.cached_tokens} (按10%计费)")
    
    # 第二次请求 - 应该命中缓存
    print("\n\n📝 第二次请求 (应该命中缓存)...")
    messages2 = [
        {
            "role": "system",
            "content": system_message,  # 相同的system message
            "cache_control": {"type": "ephemeral"}
        },
        {
            "role": "user",
            "content": "Translate this C code to Rust: int sub(int a, int b) { return a - b; }"
        }
    ]
    
    response2 = client.chat.completions.create(
        model="qwen3-coder-plus-2025-09-23",
        messages=messages2,
        temperature=0.3
    )
    
    print(f"\n✅ 第二次请求完成")
    print(f"Response: {response2.choices[0].message.content[:100]}...")
    print(f"\n📊 Token 使用情况:")
    print(f"  - Prompt tokens: {response2.usage.prompt_tokens}")
    print(f"  - Completion tokens: {response2.usage.completion_tokens}")
    
    # 检查缓存命中
    cache_hit = False
    if hasattr(response2.usage, 'prompt_tokens_details'):
        details = response2.usage.prompt_tokens_details
        if hasattr(details, 'cached_tokens'):
            cached = details.cached_tokens
            print(f"  - Cached tokens: {cached} (按10%计费) ✅")
            if cached > 0:
                cache_hit = True
        if hasattr(details, 'cache_creation_input_tokens'):
            print(f"  - Cache creation tokens: {details.cache_creation_input_tokens}")
    
    print("\n" + "="*80)
    if cache_hit:
        print("🎉 成功！显式缓存正常工作")
        print("="*80)
        print("\n💡 说明:")
        print("  - 第一次请求创建了缓存")
        print("  - 第二次请求成功命中缓存")
        print("  - System message 部分只需按10%计费")
        print("  - 5分钟内的后续请求都会命中这个缓存")
    else:
        print("⚠️  缓存未命中")
        print("="*80)
        print("\n可能的原因:")
        print("  - System message tokens < 1024 (显式缓存最小要求)")
        print("  - API可能需要一些时间来建立缓存")
        print("  - 模型可能不支持显式缓存")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    try:
        test_explicit_cache()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

