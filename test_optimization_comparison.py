#!/usr/bin/env python3
"""
测试优化前后的性能对比
"""

import os
import json
import time
import subprocess
from datetime import datetime

def run_test_batch(config_file: str, sample_size: int = 20, workers: int = 5, num_tests: int = 8):
    """运行一批测试并收集统计数据"""
    
    print(f"\n{'='*80}")
    print(f"🧪 测试配置: {config_file}")
    print(f"{'='*80}")
    
    # 备份当前配置
    subprocess.run(["cp", "/home/changdi/sactor/sactor.toml", "/tmp/sactor.toml.backup"])
    
    # 应用测试配置
    subprocess.run(["cp", config_file, "/home/changdi/sactor/sactor.toml"])
    
    # 运行测试
    start_time = time.time()
    
    cmd = [
        "python3", "batch_generate_tests.py",
        "--sample-size", str(sample_size),
        "--workers", str(workers),
        "--num-tests", str(num_tests)
    ]
    
    print(f"🚀 运行命令: {' '.join(cmd)}\n")
    
    result = subprocess.run(
        cmd,
        cwd="/home/changdi/sactor",
        capture_output=True,
        text=True
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    # 恢复原配置
    subprocess.run(["cp", "/tmp/sactor.toml.backup", "/home/changdi/sactor/sactor.toml"])
    
    # 解析结果
    # 查找最新的test_generation目录
    test_dirs = [d for d in os.listdir("/home/changdi/sactor") if d.startswith("test_generation_")]
    if test_dirs:
        test_dirs.sort(reverse=True)
        latest_dir = os.path.join("/home/changdi/sactor", test_dirs[0])
        result_file = os.path.join(latest_dir, "test_generation_results.json")
        
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                results = json.load(f)
            
            return {
                "config": config_file,
                "duration": duration,
                "total": results.get("total", 0),
                "success": results.get("success", 0),
                "failed": results.get("failed", 0),
                "success_rate": results.get("success", 0) / results.get("total", 1) * 100,
                "total_tests": results.get("total_tests_generated", 0),
                "avg_time": results.get("avg_processing_time", 0),
                "output_dir": latest_dir
            }
    
    return {
        "config": config_file,
        "duration": duration,
        "error": "No results found"
    }

def main():
    """主函数"""
    
    print("\n" + "="*80)
    print("🎯 SACToR 优化效果对比测试")
    print("="*80)
    
    # 测试参数
    sample_size = 20  # 测试20个文件
    workers = 5       # 5个并行线程
    num_tests = 8     # 每个文件8个测试
    
    print(f"\n📊 测试参数:")
    print(f"   - 样本数量: {sample_size}")
    print(f"   - 并行线程: {workers}")
    print(f"   - 测试数量: {num_tests}")
    
    # 配置文件列表
    configs = [
        ("/home/changdi/sactor/sactor.toml.before_optimization", "优化前（原配置）"),
        ("/home/changdi/sactor/sactor.toml", "优化后（平衡版）"),
    ]
    
    results = []
    
    for config_file, label in configs:
        if not os.path.exists(config_file):
            print(f"\n⚠️  配置文件不存在: {config_file}")
            continue
        
        print(f"\n{'='*80}")
        print(f"🧪 测试 {label}")
        print(f"{'='*80}")
        
        result = run_test_batch(config_file, sample_size, workers, num_tests)
        result["label"] = label
        results.append(result)
        
        print(f"\n✅ {label} 完成")
        print(f"   - 总时长: {result.get('duration', 0):.2f} 秒")
        print(f"   - 成功率: {result.get('success_rate', 0):.1f}%")
        print(f"   - 平均时间: {result.get('avg_time', 0):.2f} 秒/文件")
    
    # 生成对比报告
    print("\n" + "="*80)
    print("📊 性能对比报告")
    print("="*80)
    
    if len(results) >= 2:
        before = results[0]
        after = results[1]
        
        print(f"\n{'指标':<20} {'优化前':<20} {'优化后':<20} {'变化':<20}")
        print("-" * 80)
        
        # 总时长
        duration_change = (after['duration'] - before['duration']) / before['duration'] * 100
        print(f"{'总时长 (秒)':<20} {before['duration']:>19.2f} {after['duration']:>19.2f} {duration_change:>18.1f}%")
        
        # 成功率
        success_rate_change = after['success_rate'] - before['success_rate']
        print(f"{'成功率 (%)':<20} {before['success_rate']:>19.1f} {after['success_rate']:>19.1f} {success_rate_change:>18.1f}%")
        
        # 平均时间
        avg_time_change = (after['avg_time'] - before['avg_time']) / before['avg_time'] * 100
        print(f"{'平均时间 (秒)':<20} {before['avg_time']:>19.2f} {after['avg_time']:>19.2f} {avg_time_change:>18.1f}%")
        
        # 成功数量
        print(f"{'成功数量':<20} {before['success']:>19d} {after['success']:>19d} {after['success'] - before['success']:>19d}")
        
        # 失败数量
        print(f"{'失败数量':<20} {before['failed']:>19d} {after['failed']:>19d} {after['failed'] - before['failed']:>19d}")
        
        print("\n" + "="*80)
        print("💡 结论:")
        print("="*80)
        
        if duration_change < 0:
            print(f"✅ 速度提升: {abs(duration_change):.1f}%")
        else:
            print(f"⚠️  速度下降: {duration_change:.1f}%")
        
        if success_rate_change >= 0:
            print(f"✅ 成功率提升: {success_rate_change:.1f}%")
        elif success_rate_change > -5:
            print(f"⚠️  成功率略微下降: {abs(success_rate_change):.1f}%（可接受范围）")
        else:
            print(f"❌ 成功率显著下降: {abs(success_rate_change):.1f}%")
        
        # 估算Token节省
        # 假设每次尝试使用2000 tokens
        before_attempts = before['total'] * 20  # 原max_translation_attempts=20
        after_attempts = after['total'] * 5    # 新max_translation_attempts=5
        token_savings = (before_attempts - after_attempts) / before_attempts * 100
        
        print(f"💰 预估Token节省: {token_savings:.1f}%")
        print(f"💰 预估API成本节省: {token_savings:.1f}%")
    
    # 保存报告
    report_file = f"/home/changdi/sactor/optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "test_params": {
                "sample_size": sample_size,
                "workers": workers,
                "num_tests": num_tests
            },
            "results": results,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n📄 详细报告已保存到: {report_file}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()

