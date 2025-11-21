#!/usr/bin/env python3
"""
监控测试生成进度
"""

import os
import json
import time
from datetime import datetime

def monitor_progress():
    """监控测试生成进度"""
    output_dir = "/home/changdi/sactor/random_test_results"
    logs_dir = os.path.join(output_dir, "logs")
    
    print("🔍 监控测试生成进度...")
    print(f"📁 输出目录: {output_dir}")
    
    # 查找最新的进度文件
    progress_files = []
    if os.path.exists(logs_dir):
        for file in os.listdir(logs_dir):
            if file.startswith("progress_") and file.endswith(".json"):
                progress_files.append(file)
    
    if not progress_files:
        print("❌ 未找到进度文件")
        return
    
    # 按文件名排序，获取最新的
    progress_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
    latest_progress = progress_files[-1]
    
    progress_file = os.path.join(logs_dir, latest_progress)
    
    try:
        with open(progress_file, 'r') as f:
            progress = json.load(f)
        
        print(f"\n📊 当前进度 (文件: {latest_progress}):")
        print(f"🤖 使用模型: {progress.get('llm_provider', 'Unknown')} - {progress.get('model_name', 'Unknown')}")
        print(f"📁 总文件数: {progress.get('total_files', 0)}")
        print(f"✅ 成功: {progress.get('success', 0)}")
        print(f"❌ 失败: {progress.get('failed', 0)}")
        print(f"📈 总测试用例: {progress.get('total_tests_generated', 0)}")
        print(f"⏱️ 总处理时间: {progress.get('total_processing_time', 0):.2f} 秒")
        print(f"🔢 总API调用: {progress.get('total_api_calls', 0)}")
        print(f"💰 总API成本: ${progress.get('total_api_cost', 0):.4f}")
        
        if progress.get('total_files', 0) > 0:
            success_rate = progress.get('success', 0) / progress.get('total_files', 1) * 100
            print(f"📊 成功率: {success_rate:.1f}%")
        
        # 显示程序类型统计
        program_types = progress.get('program_types', {})
        if program_types:
            print(f"\n📈 程序类型统计:")
            for ptype, count in program_types.items():
                print(f"  {ptype}: {count} 个文件")
        
        # 显示最近的错误
        details = progress.get('details', [])
        if details:
            recent_failures = [d for d in details[-5:] if not d.get('success', False)]
            if recent_failures:
                print(f"\n❌ 最近失败的文件:")
                for failure in recent_failures:
                    print(f"  {failure.get('c_file', 'Unknown')}: {failure.get('error', 'Unknown error')[:100]}...")
        
    except Exception as e:
        print(f"❌ 读取进度文件失败: {e}")

def check_output_files():
    """检查生成的测试文件"""
    output_dir = "/home/changdi/sactor/random_test_results"
    test_samples_dir = os.path.join(output_dir, "test_samples")
    
    if not os.path.exists(test_samples_dir):
        print("❌ 测试样本目录不存在")
        return
    
    test_files = [f for f in os.listdir(test_samples_dir) if f.endswith('_test_samples.json')]
    
    print(f"\n📁 已生成的测试文件: {len(test_files)} 个")
    
    if test_files:
        # 显示最新的几个文件
        test_files.sort(key=lambda x: os.path.getmtime(os.path.join(test_samples_dir, x)), reverse=True)
        print("📋 最新的测试文件:")
        for i, file in enumerate(test_files[:5]):
            file_path = os.path.join(test_samples_dir, file)
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            size = os.path.getsize(file_path)
            print(f"  {i+1}. {file} ({size} bytes, {mtime.strftime('%H:%M:%S')})")

if __name__ == "__main__":
    print("🚀 测试生成进度监控")
    print("=" * 50)
    
    monitor_progress()
    check_output_files()
    
    print(f"\n⏰ 监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
