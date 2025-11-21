
#!/usr/bin/env python3
import sys
from openai import OpenAI

print("="*60)
print("测试Qwen是否支持Batch API")
print("="*60)

try:
    client = OpenAI(
        api_key='sk-aaca0ccf722143a39ec3c6e38a0a4bc2',
        base_url='https://dashscope-intl.aliyuncs.com/compatible-mode/v1'
    )
    print("✅ OpenAI客户端创建成功")
    
    # 检查batches属性
    has_batches = hasattr(client, 'batches')
    print(f"client.batches存在: {has_batches}")
    
    if has_batches:
        print("\n尝试调用batches.list()...")
        try:
            result = client.batches.list(limit=1)
            print(f"✅ Batch API可用! 结果: {result}")
        except Exception as e:
            print(f"❌ Batch API调用失败: {type(e).__name__}")
            print(f"   错误: {e}")
    else:
        print("\n❌ Qwen不支持OpenAI兼容的Batch API")
        print("   Qwen可能使用不同的批处理API")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("="*60)

