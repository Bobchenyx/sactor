#!/usr/bin/env python3
"""
测试Qwen是否支持OpenAI兼容的Batch API
"""

import json
import time
from openai import OpenAI

def test_batch_api_support():
    """测试Batch API支持"""
    
    print("="*80)
    print("🧪 测试Qwen Batch API支持")
    print("="*80)
    
    # 初始化客户端
    client = OpenAI(
        api_key="sk-aaca0ccf722143a39ec3c6e38a0a4bc2",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )
    
    print("\n📝 步骤1: 创建测试JSONL文件...")
    
    # 创建测试请求
    test_requests = [
        {
            "custom_id": "test-translate-1",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "qwen3-coder-plus",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a C to Rust translator.",
                        "cache_control": {"type": "ephemeral"}
                    },
                    {
                        "role": "user",
                        "content": "Translate this C code to Rust: int add(int a, int b) { return a + b; }"
                    }
                ],
                "temperature": 0.3
            }
        },
        {
            "custom_id": "test-translate-2",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "qwen3-coder-plus",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a C to Rust translator.",
                        "cache_control": {"type": "ephemeral"}
                    },
                    {
                        "role": "user",
                        "content": "Translate this C code to Rust: int sub(int a, int b) { return a - b; }"
                    }
                ],
                "temperature": 0.3
            }
        }
    ]
    
    # 保存为JSONL
    batch_file_path = "/tmp/test_batch_qwen.jsonl"
    with open(batch_file_path, 'w') as f:
        for req in test_requests:
            f.write(json.dumps(req) + '\n')
    
    print(f"✅ 创建完成: {batch_file_path}")
    print(f"   包含 {len(test_requests)} 个请求")
    
    try:
        print("\n📤 步骤2: 上传批处理文件...")
        
        # 尝试上传文件
        with open(batch_file_path, 'rb') as f:
            batch_file = client.files.create(
                file=f,
                purpose='batch'
            )
        
        print(f"✅ 文件上传成功！File ID: {batch_file.id}")
        
        print("\n🚀 步骤3: 创建批处理任务...")
        
        # 尝试创建batch
        batch = client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h"
        )
        
        print(f"✅ 批处理任务创建成功！")
        print(f"   Batch ID: {batch.id}")
        print(f"   状态: {batch.status}")
        print(f"   创建时间: {batch.created_at}")
        
        print("\n⏳ 步骤4: 监控批处理状态...")
        
        # 监控状态
        max_checks = 60  # 最多检查60次（30分钟）
        for i in range(max_checks):
            time.sleep(30)  # 每30秒检查一次
            
            batch_status = client.batches.retrieve(batch.id)
            print(f"   [{i+1}/{max_checks}] 状态: {batch_status.status}")
            
            if batch_status.status == "completed":
                print("\n✅ 批处理完成！")
                
                # 下载结果
                print("\n📥 步骤5: 下载结果...")
                result_file = client.files.content(batch_status.output_file_id)
                
                # 解析结果
                results = []
                for line in result_file.text.split('\n'):
                    if line.strip():
                        results.append(json.loads(line))
                
                print(f"✅ 获取 {len(results)} 个结果")
                
                # 显示结果
                print("\n📊 翻译结果:")
                for result in results:
                    custom_id = result.get('custom_id', 'unknown')
                    if 'response' in result:
                        content = result['response']['body']['choices'][0]['message']['content']
                        print(f"\n{custom_id}:")
                        print(f"  {content[:200]}...")
                    elif 'error' in result:
                        print(f"\n{custom_id}: ❌ {result['error']}")
                
                print("\n" + "="*80)
                print("🎉 Qwen支持Batch API！")
                print("="*80)
                print("\n💰 成本优势:")
                print("   - 普通API: 100% 成本")
                print("   - Batch API: 50% 成本")
                print("   - 节省: 50%")
                print("\n⏱️  处理时间:")
                print(f"   - 实际等待: {(i+1) * 30} 秒")
                print("   - 但可以批量提交后去做其他事情")
                
                return True
                
            elif batch_status.status in ["failed", "expired", "cancelled"]:
                print(f"\n❌ 批处理失败: {batch_status.status}")
                if hasattr(batch_status, 'errors'):
                    print(f"   错误信息: {batch_status.errors}")
                return False
        
        print("\n⏰ 超时：批处理30分钟内未完成")
        print("   这可能是正常的，大批量任务可能需要更长时间")
        return None
        
    except AttributeError as e:
        print(f"\n❌ Batch API不支持: {e}")
        print("\n💡 这意味着Qwen的OpenAI兼容模式可能不支持Batch API")
        print("   可以考虑使用其他优化方案:")
        print("   1. ✅ Prompt Cache (已实施)")
        print("   2. 函数级别批量聚合")
        print("   3. 并行调用优化")
        return False
        
    except Exception as e:
        print(f"\n❌ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_batch_api_support()
    
    if result is True:
        print("\n✅ 下一步: 实现Batch API集成到SACToR")
    elif result is False:
        print("\n⚠️  下一步: 使用替代优化方案")
    else:
        print("\n⏰ 批处理仍在运行中，请稍后检查")

