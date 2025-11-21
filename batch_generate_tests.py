#!/usr/bin/env python3
"""
使用SACToR批量生成测试用例
"""

import os
import subprocess
import json
import time
import random
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class BatchTestGenerator:
    def __init__(self, max_workers: int = 4, num_tests_per_file: int = 10, process_all: bool = True):
        from datetime import datetime
        
        # CodeNet 原始数据目录
        self.codenet_data_dir = "/home/changdi/CodeNet/new-data"
        
        # 输出目录：保持与输入相同的结构
        self.output_base_dir = "/home/changdi/sactor/generated_tests"
        os.makedirs(self.output_base_dir, exist_ok=True)
        
        self.max_workers = max_workers
        self.num_tests_per_file = num_tests_per_file
        self.process_all = process_all
        self.lock = threading.Lock()  # 用于线程安全的计数器更新
        
        # 统计计数器（用于计算准确率）
        self.success_count = 0
        self.total_count = 0
        
        # 创建日志目录
        log_dir = os.path.join(self.output_base_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建 CSV 日志文件
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_log_file = os.path.join(log_dir, f"generation_log_{date_str}.csv")
        with open(self.csv_log_file, 'w') as f:
            f.write("timestamp,problem_dir,c_file,c_file_path,success,processing_time,test_count,success_rate,error\n")
        
        print("=" * 80)
        print("🎯 批量测试用例生成器配置")
        print("=" * 80)
        print(f"📁 数据集来源: {self.codenet_data_dir}")
        print(f"   - 数据集类型: CodeNet new-data")
        print(f"   - 目录结构: {self.codenet_data_dir}/p*/C/*.c")
        print(f"📁 输出基础目录: {self.output_base_dir}")
        print(f"   - 输出结构: {self.output_base_dir}/p*/C/xxx.c.json")
        print(f"🔧 并行处理线程数: {self.max_workers}")
        print(f"📝 每个文件生成测试数: {self.num_tests_per_file}")
        print(f"🎯 处理模式: {'所有文件' if self.process_all else '随机采样'}")
        print(f"📝 CSV 日志文件: {self.csv_log_file}")
        print("=" * 80)
    
    def is_valid_c_file(self, file_path: str) -> bool:
        """检查文件是否是有效的 C 文件（而非 C++）"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(10000)  # 读取更多内容来检查
                
                # C++ 特征关键词
                cpp_indicators = [
                    '#include <iostream>',
                    '#include <string>',
                    '#include <vector>',
                    '#include <algorithm>',
                    'using namespace std',
                    'std::',
                    'cout',
                    'cin',
                    'endl',
                    'class ',
                    'template<',
                    'namespace '
                ]
                
                for indicator in cpp_indicators:
                    if indicator in content:
                        return False
                
                # 基本语法检查：花括号匹配
                open_braces = content.count('{')
                close_braces = content.count('}')
                if open_braces != close_braces:
                    return False
                
                # 检查是否有 main 函数
                if 'main' not in content:
                    return False
                
                # 检查文件大小（太小可能不完整，太大可能有问题）
                if len(content) < 50 or len(content) > 50000:
                    return False
                
                return True
        except Exception:
            return False
    
    def collect_all_c_files(self) -> List[str]:
        """收集每个问题的第一个有效 C 文件
        
        策略：
        - 每个问题（problem）只选择第一个有效的C文件
        - 如果该问题已有JSON（至少1个），跳过整个问题
        """
        print(f"🔍 扫描 CodeNet 问题目录...")
        
        # 获取所有问题目录（p*）
        selected_c_files = []
        skipped_invalid = 0
        skipped_has_json = 0
        
        problem_dirs = sorted([item for item in os.listdir(self.codenet_data_dir) 
                              if os.path.isdir(os.path.join(self.codenet_data_dir, item)) and item.startswith('p')])
        
        print(f"   找到 {len(problem_dirs)} 个问题目录")
        
        for idx, problem_dir_name in enumerate(problem_dirs):
            problem_dir = os.path.join(self.codenet_data_dir, problem_dir_name)
            c_dir = os.path.join(problem_dir, 'C')
            
            if not os.path.exists(c_dir):
                continue
            
            # 检查输出目录是否已有JSON
            output_problem_dir = os.path.join(self.output_base_dir, problem_dir_name, 'C')
            if os.path.exists(output_problem_dir):
                # 检查是否有任何 .json 文件
                existing_jsons = [f for f in os.listdir(output_problem_dir) if f.endswith('.json')]
                if existing_jsons:
                    skipped_has_json += 1
                    if (idx + 1) % 100 == 0:
                        print(f"   进度: {idx + 1}/{len(problem_dirs)} 目录, ⏭️  跳过 {problem_dir_name} (已有JSON)")
                    continue
            
            # 获取该目录下的所有C文件，按名字排序
            c_files = sorted([os.path.join(c_dir, f) for f in os.listdir(c_dir) if f.endswith('.c')])
            
            # 找到第一个有效的C文件
            found_valid = False
            for c_file in c_files:
                if self.is_valid_c_file(c_file):
                    selected_c_files.append(c_file)
                    found_valid = True
                    break  # 只取第一个有效的
                else:
                    skipped_invalid += 1
            
            if not found_valid and len(c_files) > 0:
                # 该问题的所有C文件都无效
                pass
            
            # 每处理100个目录打印一次进度
            if (idx + 1) % 100 == 0:
                print(f"   进度: {idx + 1}/{len(problem_dirs)} 目录, 已选择 {len(selected_c_files)} 个问题")
        
        print(f"\n📊 统计:")
        print(f"   ✅ 选择了 {len(selected_c_files)} 个问题的第一个有效C文件")
        print(f"   ⏭️  跳过 {skipped_has_json} 个问题（已有JSON）")
        print(f"   ❌ 跳过 {skipped_invalid} 个无效文件（C++/语法错误/不完整）")
        return selected_c_files
    
    def generate_test_for_file(self, c_file_path: str, num_tests: int = 10) -> Dict:
        """为单个C文件生成测试用例"""
        c_filename = os.path.basename(c_file_path)
        
        # 提取问题目录名（例如 p00000）
        # c_file_path格式: /home/changdi/CodeNet/new-data/p00000/C/xxx.c
        parts = c_file_path.split(os.sep)
        problem_dir = None
        for i, part in enumerate(parts):
            if part.startswith('p') and len(part) == 6 and i+1 < len(parts) and parts[i+1] == 'C':
                problem_dir = part
                break
        
        if not problem_dir:
            print(f"⚠️  无法从路径提取问题目录: {c_file_path}")
            problem_dir = "unknown"
        
        # 创建输出目录：保持与输入相同的结构
        # 输出结构: /home/changdi/sactor/generated_tests/p00000/C/xxx.c.json
        output_problem_dir = os.path.join(self.output_base_dir, problem_dir, 'C')
        os.makedirs(output_problem_dir, exist_ok=True)
        
        # 输出文件路径
        output_test_samples = os.path.join(output_problem_dir, f"{c_filename}.json")
        
        # 注意：跳过逻辑已经在 collect_all_c_files() 中处理了
        # 这里不需要再检查，因为能到这里的文件都是需要生成的
        
        # 构建Docker命令 - 只生成 test_samples.json
        c_file_dir = os.path.dirname(c_file_path)
        output_filename = os.path.basename(output_test_samples)
        
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{c_file_dir}:/data/c_files",
            "-v", f"/home/changdi/sactor/sactor.toml:/app/sactor.toml",
            "-v", f"{output_problem_dir}:/app/output",
            "sactor", "generate-tests",
            f"/data/c_files/{c_filename}",
            str(num_tests),
            "--type", "bin",
            "--feed-as-stdin",  # CodeNet programs use stdin
            "--out-test-sample-path", f"/app/output/{output_filename}"
        ]
        
        print(f"\n🚀 生成测试用例: {c_filename}")
        print(f"   📂 C文件: {c_file_path}")
        print(f"   📁 问题目录: {problem_dir}")
        print(f"   💾 输出: {output_test_samples}")
        print(f"   🎲 测试数量: {num_tests}")
        print(f"\n▶️  开始生成...\n")
        print("=" * 80)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd, 
                timeout=120,
                capture_output=True,
                text=True
            )  # 2分钟timeout
            
            processing_time = time.time() - start_time
            print("=" * 80)
            print(f"\n⏱️  生成耗时: {processing_time:.2f} 秒")
            
            # 打印详细的错误输出（特别是API配额错误）
            if result.stderr:
                stderr_lower = result.stderr.lower()
                # 检测各种错误类型
                if '403' in result.stderr or '429' in result.stderr:
                    print("\n" + "!"*80)
                    print("🚫 API配额错误 (403/429):")
                    print("!"*80)
                    # 提取关键错误信息
                    for line in result.stderr.split('\n'):
                        if any(keyword in line.lower() for keyword in ['error', 'quota', '403', '429', 'permission', 'rate limit']):
                            print(f"   {line}")
                    print("!"*80 + "\n")
                elif 'ratelimiterror' in stderr_lower or 'rate limit' in stderr_lower:
                    print("\n" + "!"*80)
                    print("⏱️  速率限制错误:")
                    print("!"*80)
                    for line in result.stderr.split('\n'):
                        if 'rate' in line.lower() or 'limit' in line.lower():
                            print(f"   {line}")
                    print("!"*80 + "\n")
                elif 'permissiondeniederror' in stderr_lower:
                    print("\n" + "!"*80)
                    print("🔒 权限拒绝错误:")
                    print("!"*80)
                    for line in result.stderr.split('\n'):
                        if 'permission' in line.lower():
                            print(f"   {line}")
                    print("!"*80 + "\n")
                elif 'insufficient_quota' in stderr_lower or 'quota' in stderr_lower:
                    print("\n" + "!"*80)
                    print("💰 配额不足错误:")
                    print("!"*80)
                    for line in result.stderr.split('\n'):
                        if 'quota' in line.lower():
                            print(f"   {line}")
                    print("!"*80 + "\n")
                elif 'error' in stderr_lower:
                    # 其他错误也显示
                    print("\n" + "⚠️  检测到错误信息:")
                    for line in result.stderr.split('\n')[-20:]:  # 只显示最后20行
                        if line.strip():
                            print(f"   {line}")
            
            if result.returncode == 0:
                # 检查输出文件是否生成
                if os.path.exists(output_test_samples):
                    with open(output_test_samples, 'r') as f:
                        test_samples = json.load(f)
                    
                    return {
                        "success": True,
                        "c_file": c_filename,
                        "c_file_path": c_file_path,
                        "problem_dir": problem_dir,
                        "test_count": len(test_samples),
                        "processing_time": processing_time,
                        "output_file": output_test_samples
                    }
                else:
                    print(f"\n⚠️  输出文件未生成: {output_test_samples}")
                    
                    # 显示stderr以了解为什么没有生成文件
                    if result.stderr:
                        print("\n📋 错误输出 (可能的原因):")
                        print("-"*80)
                        for line in result.stderr.split('\n')[-30:]:
                            if line.strip():
                                print(f"   {line}")
                        print("-"*80)
                    
                    return {
                        "success": False,
                        "error": f"Output file not generated: {output_test_samples}",
                        "processing_time": processing_time,
                        "c_file": c_filename,
                        "c_file_path": c_file_path,
                        "problem_dir": problem_dir
                    }
            else:
                # 提取详细错误信息
                error_msg = f"Docker command failed with return code: {result.returncode}"
                
                print(f"\n" + "="*80)
                print(f"❌ 失败: {error_msg}")
                print("="*80)
                
                if result.stderr:
                    print("\n📋 完整错误输出 (stderr):")
                    print("-"*80)
                    # 显示最后50行stderr（通常包含所有重要信息）
                    stderr_lines = result.stderr.split('\n')
                    for line in stderr_lines[-50:]:
                        if line.strip():
                            print(f"   {line}")
                    print("-"*80)
                    
                    # 提取关键错误行保存到返回结果
                    error_lines = []
                    for line in result.stderr.split('\n'):
                        if any(keyword in line.lower() for keyword in ['error', 'exception', 'failed', 'quota', '403', '429', 'traceback']):
                            error_lines.append(line.strip())
                    if error_lines:
                        error_msg += f"\n关键错误: {' | '.join(error_lines[:5])}"
                
                if result.stdout:
                    print("\n📋 标准输出 (stdout) 最后20行:")
                    print("-"*80)
                    stdout_lines = result.stdout.split('\n')
                    for line in stdout_lines[-20:]:
                        if line.strip():
                            print(f"   {line}")
                    print("-"*80)
                
                print()
                
                return {
                    "success": False,
                    "error": error_msg,
                    "processing_time": processing_time,
                    "c_file": c_filename,
                    "c_file_path": c_file_path,
                    "problem_dir": problem_dir
                }
                
        except subprocess.TimeoutExpired as e:
            print(f"\n⏱️  生成超时！测试生成时间超过 2 分钟")
            return {
                "success": False,
                "error": "Timeout (2 minutes)",
                "processing_time": 120,
                "c_file": os.path.basename(c_file_path),
                "c_file_path": c_file_path,
                "problem_dir": problem_dir
            }
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            print(f"\n💥 发生异常: {error_msg}")
            
            # 打印堆栈跟踪
            import traceback
            traceback_str = traceback.format_exc()
            print(f"堆栈跟踪:\n{traceback_str}")
            
            return {
                "success": False,
                "error": error_msg,
                "processing_time": time.time() - start_time,
                "c_file": c_filename,
                "c_file_path": c_file_path,
                "problem_dir": problem_dir
            }
    
    def batch_generate_tests(self) -> Dict:
        """批量生成测试用例 - 并行版本（处理所有C文件）"""
        # 收集所有C文件
        all_c_files = self.collect_all_c_files()
        
        print(f"\n📊 将要处理 {len(all_c_files)} 个C文件")
        
        results = {
            'total': len(all_c_files),
            'success': 0,
            'failed': 0,
            'skipped': 0,  # 跳过的文件数量
            'total_tests_generated': 0,
            'total_processing_time': 0,
            'details': [],
            'start_time': time.time()
        }
        
        processed_count = 0
        
        # 使用线程池进行并行处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.generate_test_for_file, c_file_path, self.num_tests_per_file): c_file_path 
                for c_file_path in all_c_files
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                c_file_path = future_to_file[future]
                processed_count += 1
                
                try:
                    result = future.result()
                    
                    # 线程安全地更新结果
                    with self.lock:
                        if result['success']:
                            results['success'] += 1
                            results['total_tests_generated'] += result.get('test_count', result.get('num_tests', 0))
                            
                            # 检查是否是跳过的文件
                            if result.get('skipped', False):
                                results['skipped'] += 1
                                success_rate = (results['success'] / processed_count * 100)
                                print(f"\n⏭️  ===== [{processed_count}/{len(all_c_files)}] {os.path.basename(c_file_path)}: 已跳过 (已有 {result.get('num_tests', 0)} 个测试) | 成功率: {success_rate:.1f}% =====\n")
                            else:
                                success_rate = (results['success'] / processed_count * 100)
                                print(f"\n✅ ===== [{processed_count}/{len(all_c_files)}] {os.path.basename(c_file_path)}: 成功生成 {result.get('test_count', 0)} 个测试用例 | 成功率: {success_rate:.1f}% =====\n")
                        else:
                            results['failed'] += 1
                            success_rate = (results['success'] / processed_count * 100)
                            error_msg = result.get('error', 'Unknown error')
                            print(f"\n❌ ===== [{processed_count}/{len(all_c_files)}] {os.path.basename(c_file_path)}: 失败 | 成功率: {success_rate:.1f}% =====")
                            print(f"   错误: {error_msg}\n")
                        
                        results['total_processing_time'] += result['processing_time']
                        results['details'].append(result)
                        
                        # 实时保存到 CSV
                        self._log_result_to_csv(result)
                        
                        # 每处理5个文件保存一次进度
                        if processed_count % 5 == 0:
                            self._save_progress(results, processed_count)
                            
                except Exception as e:
                    with self.lock:
                        results['failed'] += 1
                        success_rate = (results['success'] / processed_count * 100)
                        print(f"\n❌ ===== [{processed_count}/{len(all_c_files)}] {os.path.basename(c_file_path)}: 异常 | 成功率: {success_rate:.1f}% =====")
                        print(f"   💥 Exception: {str(e)}")
                        import traceback
                        print(f"   堆栈跟踪:\n{traceback.format_exc()}\n")
                        
                        error_result = {
                            'success': False,
                            'error': f"Exception in worker: {str(e)}",
                            'c_file': os.path.basename(c_file_path),
                            'processing_time': 0,
                            'test_count': 0
                        }
                        results['details'].append(error_result)
                        
                        # 保存到 CSV
                        self._log_result_to_csv(error_result)
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        # 计算平均值
        if results['total'] > 0:
            results['avg_processing_time'] = results['total_processing_time'] / results['total']
            results['avg_tests_per_file'] = results['total_tests_generated'] / results['success'] if results['success'] > 0 else 0
        
        return results
    
    def _log_result_to_csv(self, result: Dict):
        """将单个结果实时保存到 CSV（包含准确率）"""
        try:
            from datetime import datetime
            with self.lock:
                # 更新计数器
                self.total_count += 1
                if result.get('success', False):
                    self.success_count += 1
                
                # 计算当前准确率
                success_rate = (self.success_count / self.total_count * 100) if self.total_count > 0 else 0
                
                timestamp = datetime.now().isoformat()
                problem_dir = result.get('problem_dir', 'unknown')
                c_file = result.get('c_file', 'unknown')
                c_file_path = result.get('c_file_path', '')
                success = result.get('success', False)
                processing_time = result.get('processing_time', 0)
                test_count = result.get('test_count', 0)
                error = str(result.get('error', '')).replace(',', ';').replace('\n', ' ')[:200]
                
                csv_line = f"{timestamp},{problem_dir},{c_file},{c_file_path},{success},{processing_time:.2f},{test_count},{success_rate:.2f},{error}\n"
                
                with open(self.csv_log_file, 'a') as f:
                    f.write(csv_line)
                    f.flush()  # 强制刷新到磁盘
                
                # 调试信息
                print(f"   📊 CSV已保存: {c_file} | 准确率: {success_rate:.1f}%")
        except Exception as e:
            print(f"⚠️ CSV 日志保存失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_progress(self, results: Dict, processed_count: int):
        """保存进度"""
        progress_file = os.path.join(self.output_base_dir, "logs", f"progress_{processed_count}.json")
        with open(progress_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 进度已保存: {processed_count}/{results['total']} 文件")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SACToR 批量测试用例生成器（处理所有C文件）')
    parser.add_argument('--workers', type=int, default=15, help='并行处理的线程数（默认：15）')
    parser.add_argument('--num-tests', type=int, default=8, help='每个文件生成的测试用例数量（默认：8）')
    args = parser.parse_args()
    
    print("🚀 SACToR 批量测试用例生成器 (处理所有C文件)")
    print("=" * 60)
    print(f"🔧 配置: ")
    print(f"   - 处理模式: 所有C文件")
    print(f"   - 并行线程数: {args.workers}")
    print(f"   - 每个文件测试数: {args.num_tests}")
    print("=" * 60)
    
    generator = BatchTestGenerator(
        max_workers=args.workers, 
        num_tests_per_file=args.num_tests,
        process_all=True
    )
    
    try:
        # 批量生成测试用例
        results = generator.batch_generate_tests()
        
        # 输出结果统计
        print(f"\n📊 批量测试生成结果:")
        print(f"=" * 60)
        print(f"📁 文件处理:")
        print(f"   - 处理文件数: {results['total']}")
        print(f"   - 生成成功: {results['success']} (其中跳过: {results.get('skipped', 0)})")
        print(f"   - 生成失败: {results['failed']}")
        print(f"   - 成功率: {results['success']/results['total']*100:.1f}%")
        print(f"\n🧪 测试用例:")
        print(f"   - 总测试用例数: {results['total_tests_generated']}")
        print(f"   - 平均每文件: {results['avg_tests_per_file']:.1f} 个")
        print(f"\n⏱️  处理时间:")
        print(f"   - 总处理时间: {results['duration']:.2f} 秒 ({results['duration']/60:.1f} 分钟)")
        print(f"   - 平均每文件: {results['avg_processing_time']:.2f} 秒")
        if results['success'] > 0:
            print(f"   - 平均每成功: {results['total_processing_time']/results['success']:.2f} 秒")
        print(f"\n💰 API 成本: (测试生成通常需要 API 调用)")
        print(f"   - 预估调用次数: ~{results['success'] * 2} 次")  # 估算
        print(f"=" * 60)
        
        # 显示配置影响
        print(f"\n💡 配置汇总:")
        print(f"   - 每个文件请求生成: {args.num_tests} 个测试")
        print(f"   - 实际平均生成: {results['avg_tests_per_file']:.1f} 个测试")
        print(f"   - 并行线程数: {args.workers}")
        if results['duration'] > 0:
            throughput = results['total'] / (results['duration'] / 60)
            print(f"   - 处理吞吐量: {throughput:.1f} 个文件/分钟")
        
        # 保存详细结果
        results_file = os.path.join(generator.output_base_dir, "logs", "generation_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 详细结果已保存到:")
        print(f"   JSON: {results_file}")
        print(f"   CSV:  {generator.csv_log_file}")
        print(f"📁 生成的测试用例保存在: {generator.output_base_dir}")
        print(f"   结构: {generator.output_base_dir}/p*/C/*.c.json")
        
        return results
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()
