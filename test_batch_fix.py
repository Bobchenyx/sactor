#!/usr/bin/env python3
"""
测试批量脚本修复效果的脚本
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import time

def test_single_file_with_fixed_batch():
    """测试修复后的批量脚本处理单个文件"""
    print("🧪 测试修复后的批量脚本")
    
    # 导入修复后的翻译器
    sys.path.append('/home/changdi/sactor')
    from batch_translate_correct import CorrectDataTranslator
    
    # 创建翻译器
    translator = CorrectDataTranslator()
    
    # 测试文件
    c_file = '/home/changdi/sactor-datasets/Project_CodeNet/raw_data/argv/s005765690.c'
    output_dir = '/tmp/test_single_batch_fix'
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📁 测试文件: {os.path.basename(c_file)}")
    print(f"📁 输出目录: {output_dir}")
    
    try:
        # 翻译和验证
        start_time = time.time()
        result = translator.translate_and_verify(c_file, output_dir)
        duration = time.time() - start_time
        
        print(f"\n📊 测试结果:")
        print(f"   成功: {result['success']}")
        print(f"   验证: {result['verification']['overall'] if result['verification'] else False}")
        print(f"   测试用例数: {result['test_count']}")
        print(f"   使用预生成测试: {result.get('used_pregen', False)}")
        print(f"   耗时: {duration:.2f} 秒")
        
        if result['error']:
            print(f"   错误: {result['error']}")
        
        # 检查生成的文件
        print(f"\n📁 生成的文件:")
        if os.path.exists(output_dir):
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    print(f"   {file_path}")
        
        return result
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None
    
    finally:
        # 清理临时目录
        if hasattr(translator, 'temp_dir') and os.path.exists(translator.temp_dir):
            shutil.rmtree(translator.temp_dir)

def main():
    """主函数"""
    print("🚀 批量脚本修复效果测试")
    print("==================================================")
    
    # 测试修复后的批量脚本
    result = test_single_file_with_fixed_batch()
    
    if result and result['success']:
        print(f"\n✅ 修复成功！批量脚本现在可以正常工作了")
        print(f"🎯 建议使用以下脚本进行批量翻译:")
        print(f"   - 标准版本: python3 batch_translate_correct.py")
        print(f"   - 优化版本: python3 batch_translate_optimized.py")
        print(f"   - 超快速版本: python3 batch_translate_ultra_fast.py")
    else:
        print(f"\n❌ 修复失败，需要进一步调试")

if __name__ == "__main__":
    main()
