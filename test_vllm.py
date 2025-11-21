#!/usr/bin/env python3
"""
测试 vLLM 集成
验证 vLLM 服务是否正常工作
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import tomli
except ImportError:
    print("错误: 需要安装 tomli")
    print("运行: pip install tomli")
    sys.exit(1)

try:
    from sactor.llm import llm_factory
except ImportError as e:
    print(f"错误: 无法导入 sactor.llm: {e}")
    sys.exit(1)


def test_vllm_connection():
    """测试 vLLM 连接"""
    print("🔍 测试 vLLM 连接...")
    
    # 读取配置
    config_file = "sactor.toml"
    if not os.path.exists(config_file):
        config_file = "sactor.default.toml"
        print(f"⚠️  未找到 sactor.toml，使用 {config_file}")
    
    try:
        with open(config_file, "rb") as f:
            config = tomli.load(f)
    except Exception as e:
        print(f"❌ 无法读取配置文件 {config_file}: {e}")
        return False
    
    # 检查配置
    if config['general'].get('llm') != 'VLLM':
        print(f"⚠️  配置中的 LLM 类型是: {config['general'].get('llm')}")
        print("   请设置 [general] llm = \"VLLM\"")
        return False
    
    if 'VLLM' not in config:
        print("❌ 配置文件中缺少 [VLLM] 部分")
        return False
    
    vllm_config = config['VLLM']
    print(f"✅ 配置读取成功")
    print(f"   base_url: {vllm_config.get('base_url', 'N/A')}")
    print(f"   model: {vllm_config.get('model', 'N/A')}")
    
    # 创建 LLM 实例
    try:
        llm = llm_factory(config)
        print(f"✅ LLM 实例创建成功: {type(llm).__name__}")
    except Exception as e:
        print(f"❌ 无法创建 LLM 实例: {e}")
        return False
    
    # 测试查询
    print("\n🧪 测试查询...")
    test_prompt = "请用一句话介绍 Rust 编程语言。"
    
    try:
        response = llm.query(test_prompt)
        print(f"✅ 查询成功!")
        print(f"📝 响应: {response[:200]}...")
        return True
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        print("\n💡 提示:")
        print("   1. 确认 vLLM 服务正在运行")
        print("   2. 检查 base_url 是否正确")
        print("   3. 运行: curl http://localhost:8000/v1/models")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("vLLM 集成测试")
    print("=" * 60)
    print()
    
    success = test_vllm_connection()
    
    print()
    print("=" * 60)
    if success:
        print("✅ 测试通过!")
    else:
        print("❌ 测试失败!")
        sys.exit(1)

