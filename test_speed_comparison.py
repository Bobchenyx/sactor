#!/usr/bin/env python3
"""
速度对比测试脚本
测试不同超时设置下的翻译速度
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

def test_single_file_speed(c_file_path: str, timeout: int, test_name: str) -> Dict:
    """测试单个文件的翻译速度"""
    print(f"\n🧪 测试 {test_name}: 超时 {timeout}秒")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix=f'sactor_test_{timeout}_')
    
    try:
        # 复制测试文件
        test_c_file = os.path.join(temp_dir, os.path.basename(c_file_path))
        shutil.copy2(c_file_path, test_c_file)
        
        # 创建测试用例
        test_samples = [
            {"input": "10", "output": "30"},
            {"input": "5", "output": "6"},
            {"input": "0", "output": "0"}
        ]
        
        test_samples_path = os.path.join(temp_dir, "test_samples.json")
        with open(test_samples_path, 'w') as f:
            json.dump(test_samples, f, indent=2)
        
        # 创建测试任务
        test_task = []
        for i in range(len(test_samples)):
            test_task.append({
                "command": f"sactor run-tests --type bin ./test_samples.json %t {i} --feed-as-args",
                "test_id": i
            })
        
        test_task_path = os.path.join(temp_dir, "test_task.json")
        with open(test_task_path, 'w') as f:
            json.dump(test_task, f, indent=2)
        
        # 运行 SACToR Docker 翻译
        sactor_config = "/home/changdi/sactor/sactor.toml"
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{sactor_config}:/app/sactor.toml",
            "-v", f"{temp_dir}:/tmp/translation",
            "sactor", "translate",
            f"/tmp/translation/{os.path.basename(c_file_path)}",
            f"/tmp/translation/test_task.json",
            "--result-dir", "/tmp/translation/result",
            "--type", "bin"
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        duration = time.time() - start_time
        
        success = result.returncode == 0
        
        print(f"   结果: {'✅ 成功' if success else '❌ 失败'}")
        print(f"   时间: {duration:.2f} 秒")
        
        return {
            'test_name': test_name,
            'timeout': timeout,
            'success': success,
            'duration': duration,
            'error': result.stderr[:200] if not success else None
        }
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"   结果: ⏰ 超时")
        print(f"   时间: {duration:.2f} 秒")
        
        return {
            'test_name': test_name,
            'timeout': timeout,
            'success': False,
            'duration': duration,
            'error': f"超时 ({timeout}秒)"
        }
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"   结果: ❌ 错误")
        print(f"   时间: {duration:.2f} 秒")
        
        return {
            'test_name': test_name,
            'timeout': timeout,
            'success': False,
            'duration': duration,
            'error': str(e)
        }
        
    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def main():
    """主函数"""
    print("🚀 SACToR 速度对比测试")
    print("==================================================")
    
    # 使用测试文件
    test_c_file = "/home/changdi/sactor/test_case_demo.c"
    
    if not os.path.exists(test_c_file):
        print(f"❌ 测试文件不存在: {test_c_file}")
        return
    
    print(f"📁 测试文件: {os.path.basename(test_c_file)}")
    
    # 测试不同的超时设置
    test_configs = [
        {"timeout": 60, "name": "超快速 (60秒)"},
        {"timeout": 120, "name": "快速 (120秒)"},
        {"timeout": 300, "name": "标准 (300秒)"},
        {"timeout": 600, "name": "保守 (600秒)"}
    ]
    
    results = []
    
    for config in test_configs:
        result = test_single_file_speed(
            test_c_file, 
            config["timeout"], 
            config["name"]
        )
        results.append(result)
        
        # 等待一下再测试下一个
        time.sleep(2)
    
    # 输出结果统计
    print(f"\n📊 速度对比结果:")
    print("=" * 80)
    print(f"{'测试名称':<15} {'超时设置':<10} {'结果':<8} {'时间(秒)':<10} {'备注'}")
    print("=" * 80)
    
    for result in results:
        status = "✅ 成功" if result['success'] else "❌ 失败"
        timeout_str = f"{result['timeout']}秒"
        duration_str = f"{result['duration']:.2f}"
        note = result['error'][:30] + "..." if result['error'] and len(result['error']) > 30 else (result['error'] or "")
        
        print(f"{result['test_name']:<15} {timeout_str:<10} {status:<8} {duration_str:<10} {note}")
    
    # 找出最快成功的配置
    successful_results = [r for r in results if r['success']]
    if successful_results:
        fastest = min(successful_results, key=lambda x: x['duration'])
        print(f"\n🏆 最快成功配置: {fastest['test_name']} ({fastest['duration']:.2f}秒)")
    
    # 保存结果
    results_file = "/tmp/sactor_speed_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 详细结果已保存到: {results_file}")
    
    return results

if __name__ == "__main__":
    main()
