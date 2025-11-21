#!/usr/bin/env python3
"""
简单的 vLLM translate 测试
测试 vLLM 是否能正常调用（不依赖 c2rust/crown）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import tomli
except ImportError:
    print("需要安装 tomli: pip install tomli")
    sys.exit(1)

try:
    from sactor.llm import llm_factory
except ImportError as e:
    print(f"无法导入 sactor.llm: {e}")
    print("可能需要激活虚拟环境: source .venv/bin/activate")
    sys.exit(1)


def test_vllm_translate():
    """测试 vLLM 是否能正常调用"""
    print("=" * 60)
    print("vLLM Translate 功能测试")
    print("=" * 60)
    print()
    
    # 读取配置
    config_file = "sactor.toml"
    if not os.path.exists(config_file):
        print(f"❌ 配置文件 {config_file} 不存在")
        return False
    
    try:
        with open(config_file, "rb") as f:
            config = tomli.load(f)
        print(f"✅ 配置文件读取成功: {config_file}")
    except Exception as e:
        print(f"❌ 无法读取配置文件: {e}")
        return False
    
    # 检查配置
    llm_type = config['general'].get('llm')
    print(f"📋 LLM 类型: {llm_type}")
    
    if llm_type != 'VLLM':
        print(f"⚠️  当前配置的 LLM 类型是: {llm_type}")
        print("   请设置 [general] llm = \"VLLM\"")
        return False
    
    if 'VLLM' not in config:
        print("❌ 配置文件中缺少 [VLLM] 部分")
        return False
    
    # 创建 LLM 实例
    try:
        print("\n🔧 创建 LLM 实例...")
        llm = llm_factory(config)
        print(f"✅ LLM 实例创建成功: {type(llm).__name__}")
    except Exception as e:
        print(f"❌ 无法创建 LLM 实例: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试一个简单的翻译任务
    print("\n🧪 测试翻译功能...")
    test_prompt = """请将以下 C 代码翻译成 Rust 代码：

```c
int add(int a, int b) {
    return a + b;
}
```

请只输出 Rust 代码，不要其他解释。"""
    
    try:
        print("📤 发送请求到 vLLM...")
        response = llm.query(test_prompt)
        
        if response:
            print("✅ 翻译成功!")
            print("\n📝 翻译结果:")
            print("-" * 60)
            print(response[:500])  # 只显示前500字符
            if len(response) > 500:
                print("...")
            print("-" * 60)
            
            # 检查是否包含 Rust 代码特征
            rust_keywords = ['fn ', 'pub ', '->', 'i32', 'usize']
            found_keywords = [kw for kw in rust_keywords if kw in response]
            if found_keywords:
                print(f"\n✅ 检测到 Rust 关键字: {', '.join(found_keywords)}")
            else:
                print("\n⚠️  未检测到明显的 Rust 代码特征")
            
            return True
        else:
            print("❌ 响应为空")
            return False
            
    except Exception as e:
        print(f"❌ 翻译失败: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 提示:")
        print("   1. 确认 vLLM 服务正在运行")
        print("   2. 检查 base_url 和 model 配置是否正确")
        print("   3. 运行: python3 test_vllm_standalone.py")
        return False


if __name__ == "__main__":
    success = test_vllm_translate()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过!")
        print("\n💡 下一步:")
        print("   1. 确保 c2rust 和 crown 工具已安装")
        print("   2. 运行完整翻译: sactor translate <c_file> <test_task.json> -r <result_dir> --type bin")
    else:
        print("❌ 测试失败!")
        sys.exit(1)

