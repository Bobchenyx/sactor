#!/usr/bin/env python3
"""
快速测试批量翻译脚本
"""

import os
import sys
import time

def main():
    print("🚀 开始快速测试批量翻译脚本")
    print("=" * 50)
    
    # 导入批量翻译脚本
    sys.path.append('/home/changdi/sactor')
    from batch_translate_correct import CorrectDataTranslator
    
    print("✅ 导入成功")
    
    # 创建翻译器
    translator = CorrectDataTranslator()
    print("✅ 翻译器创建成功")
    
    # 测试单个文件
    c_file = '/home/changdi/sactor-datasets/Project_CodeNet/raw_data/argv/s005765690.c'
    output_dir = '/tmp/quick_test_result'
    
    print(f"📁 测试文件: {os.path.basename(c_file)}")
    print(f"📁 输出目录: {output_dir}")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    print("🚀 开始翻译...")
    start_time = time.time()
    
    try:
        result = translator.translate_and_verify(c_file, output_dir)
        duration = time.time() - start_time
        
        print(f"\n📊 翻译结果:")
        print(f"   成功: {result['success']}")
        print(f"   验证: {result['verification']['overall'] if result['verification'] else False}")
        print(f"   测试用例数: {result['test_count']}")
        print(f"   使用预生成测试: {result.get('used_pregen', False)}")
        print(f"   耗时: {duration:.2f} 秒")
        
        if result['error']:
            print(f"   错误: {result['error']}")
        
        print(f"\n✅ 测试完成！")
        
    except Exception as e:
        print(f"❌ 翻译失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理
        if hasattr(translator, 'temp_dir') and os.path.exists(translator.temp_dir):
            import shutil
            shutil.rmtree(translator.temp_dir)

if __name__ == "__main__":
    main()
