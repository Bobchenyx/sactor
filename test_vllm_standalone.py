#!/usr/bin/env python3
"""
独立的 vLLM 测试脚本
不依赖整个项目，只测试 vLLM 连接和基本功能
"""

import sys
import os
import json

def test_vllm_connection():
    """测试 vLLM 连接"""
    print("=" * 60)
    print("vLLM 连接测试（独立模式）")
    print("=" * 60)
    print()
    
    # 测试 OpenAI 客户端（vLLM 使用 OpenAI 兼容 API）
    try:
        from openai import OpenAI
        print("✅ OpenAI 客户端导入成功")
    except ImportError as e:
        print(f"❌ 无法导入 OpenAI 客户端: {e}")
        print("   请运行: pip install openai")
        return False
    
    # 测试配置
    base_url = "http://localhost:8000/v1"
    api_key = "EMPTY"
    model = "Qwen/Qwen2.5-1.5B-Instruct"
    
    print(f"🔌 连接地址: {base_url}")
    print(f"📦 模型: {model}")
    print()
    
    # 创建客户端
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        print("✅ OpenAI 客户端创建成功")
    except Exception as e:
        print(f"❌ 无法创建客户端: {e}")
        return False
    
    # 测试列出模型
    print("\n📋 测试: 列出可用模型...")
    try:
        models = client.models.list()
        print(f"✅ 成功连接到 vLLM 服务")
        print(f"   可用模型数: {len(models.data)}")
        for m in models.data:
            print(f"   - {m.id}")
    except Exception as e:
        print(f"❌ 无法列出模型: {e}")
        print("\n💡 提示:")
        print("   1. 确认 vLLM 服务正在运行")
        print("   2. 运行: python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-1.5B-Instruct --port 8000 --trust-remote-code")
        print("   3. 或运行: ./start_vllm.sh")
        return False
    
    # 测试简单查询
    print("\n🧪 测试: 简单查询...")
    test_prompt = "请用一句话介绍 Rust 编程语言。"
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": test_prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        if response.choices and response.choices[0].message.content:
            result = response.choices[0].message.content
            print(f"✅ 查询成功!")
            print(f"📝 响应: {result[:200]}...")
            return True
        else:
            print("❌ 响应为空")
            return False
            
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        print("\n💡 可能的原因:")
        print("   1. vLLM 服务未启动")
        print("   2. 模型名称不匹配")
        print("   3. 端口配置错误")
        return False


def test_config_file():
    """测试配置文件"""
    print("\n" + "=" * 60)
    print("配置文件测试")
    print("=" * 60)
    print()
    
    config_files = ["sactor.toml", "sactor.default.toml"]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"📄 找到配置文件: {config_file}")
            try:
                import tomli
                with open(config_file, "rb") as f:
                    config = tomli.load(f)
                
                if 'VLLM' in config:
                    print(f"✅ {config_file} 包含 [VLLM] 配置")
                    vllm_config = config['VLLM']
                    print(f"   base_url: {vllm_config.get('base_url', 'N/A')}")
                    print(f"   model: {vllm_config.get('model', 'N/A')}")
                else:
                    print(f"⚠️  {config_file} 不包含 [VLLM] 配置")
                    
            except ImportError:
                print("⚠️  需要 tomli 库来读取配置文件")
            except Exception as e:
                print(f"⚠️  读取配置文件失败: {e}")
            break
    else:
        print("⚠️  未找到配置文件")


if __name__ == "__main__":
    # 测试配置
    test_config_file()
    
    # 测试连接
    success = test_vllm_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过!")
        print("\n💡 下一步:")
        print("   1. 配置 sactor.toml:")
        print("      [general]")
        print("      llm = \"VLLM\"")
        print("   2. 运行翻译命令")
    else:
        print("❌ 测试失败!")
        print("\n💡 请检查:")
        print("   1. vLLM 服务是否运行")
        print("   2. 端口是否正确（默认8000）")
        print("   3. 模型是否已加载")
        sys.exit(1)

