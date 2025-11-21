#!/usr/bin/env python3
"""
为没有预生成测试用例的C程序生成测试用例
输出到独立目录，避免与现有翻译结果干扰
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import time
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

class MissingTestGenerator:
    def __init__(self, output_base_dir: str):
        self.output_base_dir = output_base_dir
        self.raw_data_dir = "/home/changdi/sactor-datasets/Project_CodeNet/raw_data"
        self.test_data_dir = "/home/changdi/sactor-datasets/Project_CodeNet/generated_tests"
        self.temp_dir = tempfile.mkdtemp(prefix='missing_test_gen_')
        
        # 创建输出目录
        os.makedirs(output_base_dir, exist_ok=True)
        os.makedirs(os.path.join(output_base_dir, "logs"), exist_ok=True)
        
        print(f"📁 输出目录: {output_base_dir}")
    
    def __del__(self):
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def find_corresponding_test(self, c_file_path: str) -> Optional[str]:
        """检查是否有对应的预生成测试用例"""
        c_filename = os.path.basename(c_file_path)
        test_filename = c_filename + ".json"
        
        if "argv" in c_file_path:
            test_path = os.path.join(self.test_data_dir, "argv", test_filename)
        elif "scanf" in c_file_path:
            test_path = os.path.join(self.test_data_dir, "scanf", test_filename)
        else:
            return None
        
        return test_path if os.path.exists(test_path) else None
    
    def analyze_c_program(self, c_file_path: str) -> Dict[str, Any]:
        """分析C程序，确定输入类型和参数"""
        try:
            with open(c_file_path, 'r') as f:
                content = f.read()
            
            analysis = {
                'has_argv': False,
                'has_scanf': False,
                'argv_params': [],
                'scanf_params': [],
                'program_type': 'unknown',
                'content_length': len(content)
            }
            
            # 检查命令行参数
            if 'argv[' in content and 'argc' in content:
                analysis['has_argv'] = True
                analysis['program_type'] = 'argv'
                
                # 分析参数类型
                lines = content.split('\n')
                for line in lines:
                    if 'argv[' in line:
                        if 'atoi' in line:
                            analysis['argv_params'].append('int')
                        elif 'atof' in line or 'strtod' in line:
                            analysis['argv_params'].append('float')
                        elif 'atol' in line:
                            analysis['argv_params'].append('long')
                        else:
                            analysis['argv_params'].append('string')
            
            # 检查scanf输入
            if 'scanf(' in content:
                analysis['has_scanf'] = True
                analysis['program_type'] = 'scanf'
                
                # 分析scanf格式
                scanf_patterns = re.findall(r'scanf\s*\(\s*["\']([^"\']+)["\']', content)
                for pattern in scanf_patterns:
                    if '%d' in pattern or '%i' in pattern:
                        analysis['scanf_params'].append('int')
                    elif '%f' in pattern or '%lf' in pattern or '%g' in pattern:
                        analysis['scanf_params'].append('float')
                    elif '%s' in pattern:
                        analysis['scanf_params'].append('string')
                    elif '%c' in pattern:
                        analysis['scanf_params'].append('char')
                    else:
                        analysis['scanf_params'].append('unknown')
            
            return analysis
            
        except Exception as e:
            print(f"❌ 分析C程序失败: {e}")
            return {'program_type': 'unknown', 'content_length': 0}
    
    def generate_smart_test_inputs(self, analysis: Dict[str, Any], num_tests: int = 10) -> List[Dict[str, str]]:
        """智能生成测试输入"""
        test_cases = []
        
        if analysis['program_type'] == 'argv':
            # 为argv程序生成测试用例
            for i in range(num_tests):
                test_input = []
                
                for param_type in analysis['argv_params']:
                    if param_type == 'int':
                        # 生成有意义的整数测试用例
                        if i == 0:
                            test_input.append('0')  # 边界值
                        elif i == 1:
                            test_input.append('1')  # 最小值
                        elif i == 2:
                            test_input.append('10')  # 小值
                        elif i == 3:
                            test_input.append('100')  # 中等值
                        elif i == 4:
                            test_input.append('-1')  # 负值
                        else:
                            # 生成一些特殊的测试值
                            special_values = [5, 15, 20, 25, 30, 50, 75, 99]
                            if i-5 < len(special_values):
                                test_input.append(str(special_values[i-5]))
                            else:
                                test_input.append(str(random.randint(1, 100)))
                    elif param_type == 'float':
                        if i == 0:
                            test_input.append('0.0')
                        elif i == 1:
                            test_input.append('1.5')
                        elif i == 2:
                            test_input.append('-1.5')
                        else:
                            test_input.append(f"{random.uniform(-10, 10):.2f}")
                    elif param_type == 'long':
                        if i == 0:
                            test_input.append('0')
                        elif i == 1:
                            test_input.append('1000000')
                        else:
                            test_input.append(str(random.randint(1000000, 10000000)))
                    else:
                        test_input.append(f"test{i}")
                
                test_cases.append({
                    "input": " ".join(test_input),
                    "output": ""
                })
        
        elif analysis['program_type'] == 'scanf':
            # 为scanf程序生成测试用例
            for i in range(num_tests):
                test_input = []
                
                for param_type in analysis['scanf_params']:
                    if param_type == 'int':
                        if i == 0:
                            test_input.append('0')
                        elif i == 1:
                            test_input.append('1')
                        elif i == 2:
                            test_input.append('-1')
                        else:
                            test_input.append(str(random.randint(-100, 100)))
                    elif param_type == 'float':
                        if i == 0:
                            test_input.append('0.0')
                        elif i == 1:
                            test_input.append('1.5')
                        elif i == 2:
                            test_input.append('-1.5')
                        else:
                            test_input.append(f"{random.uniform(-10, 10):.2f}")
                    elif param_type == 'char':
                        chars = ['a', 'b', 'c', 'd', 'e', 'A', 'B', 'C', '1', '2']
                        test_input.append(chars[i % len(chars)])
                    else:
                        test_input.append(f"test{i}")
                
                test_cases.append({
                    "input": "\n".join(test_input),
                    "output": ""
                })
        
        else:
            # 未知类型，尝试一些通用测试
            for i in range(min(5, num_tests)):
                test_cases.append({
                    "input": str(i),
                    "output": ""
                })
        
        return test_cases
    
    def compile_and_run_c(self, c_file_path: str, test_input: str, is_argv: bool = True) -> Optional[str]:
        """编译并运行C程序获取输出"""
        try:
            # 编译C程序
            executable_path = os.path.join(self.temp_dir, f"test_program_{random.randint(1000, 9999)}")
            compile_cmd = ["gcc", "-o", executable_path, c_file_path, "-lm"]  # 添加数学库
            
            compile_result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=30)
            if compile_result.returncode != 0:
                print(f"⚠️ 编译失败: {compile_result.stderr[:200]}...")
                return None
            
            # 运行程序
            if is_argv:
                args = test_input.split() if test_input.strip() else []
                run_cmd = [executable_path] + args
                run_result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=10)
            else:
                run_cmd = [executable_path]
                run_result = subprocess.run(run_cmd, input=test_input, capture_output=True, text=True, timeout=10)
            
            if run_result.returncode != 0:
                print(f"⚠️ 运行失败 (返回码: {run_result.returncode}): {run_result.stderr[:100]}...")
                return None
            
            output = run_result.stdout.strip()
            return output if output else None
            
        except subprocess.TimeoutExpired:
            print(f"⚠️ 程序运行超时")
            return None
        except Exception as e:
            print(f"⚠️ 运行程序出错: {e}")
            return None
    
    def generate_test_samples_for_c(self, c_file_path: str, num_tests: int = 10) -> Dict[str, Any]:
        """为C程序生成测试用例"""
        print(f"🔍 分析C程序: {os.path.basename(c_file_path)}")
        
        # 1. 分析程序
        analysis = self.analyze_c_program(c_file_path)
        print(f"📊 程序类型: {analysis['program_type']}, 代码长度: {analysis['content_length']}")
        
        if analysis['program_type'] == 'unknown':
            return {
                'success': False,
                'error': '无法识别程序类型',
                'test_cases': [],
                'analysis': analysis
            }
        
        # 2. 生成测试输入
        test_cases = self.generate_smart_test_inputs(analysis, num_tests)
        print(f"🎯 生成了 {len(test_cases)} 个测试输入")
        
        # 3. 运行程序获取期望输出
        is_argv = analysis['program_type'] == 'argv'
        successful_tests = []
        failed_tests = []
        
        for i, test_case in enumerate(test_cases):
            print(f"🧪 运行测试 {i+1}/{len(test_cases)}: {test_case['input'][:30]}...")
            
            output = self.compile_and_run_c(c_file_path, test_case['input'], is_argv)
            if output is not None:
                test_case['output'] = output
                successful_tests.append(test_case)
                print(f"✅ 输出: {output}")
            else:
                failed_tests.append(test_case)
                print(f"❌ 测试失败")
        
        print(f"📈 成功生成 {len(successful_tests)} 个有效测试用例")
        
        return {
            'success': len(successful_tests) > 0,
            'test_cases': successful_tests,
            'failed_tests': len(failed_tests),
            'analysis': analysis
        }
    
    def save_test_samples(self, test_cases: List[Dict[str, str]], output_path: str):
        """保存测试用例到JSON文件"""
        try:
            with open(output_path, 'w') as f:
                json.dump(test_cases, f, indent=2)
            print(f"💾 测试用例已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False
    
    def log_generation_result(self, c_file_path: str, result: Dict[str, Any]):
        """记录生成结果到日志"""
        try:
            log_dir = os.path.join(self.output_base_dir, "logs")
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(log_dir, f"test_generation_log_{today}.json")
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "c_file": os.path.basename(c_file_path),
                "c_file_path": c_file_path,
                "success": result.get('success', False),
                "test_count": len(result.get('test_cases', [])),
                "failed_tests": result.get('failed_tests', 0),
                "program_type": result.get('analysis', {}).get('program_type', 'unknown'),
                "content_length": result.get('analysis', {}).get('content_length', 0),
                "error": result.get('error', None)
            }
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
            else:
                log_data = {
                    "session_info": {
                        "start_time": datetime.now().isoformat(),
                        "output_base_dir": self.output_base_dir
                    },
                    "generations": []
                }
            
            log_data["generations"].append(log_entry)
            log_data["session_info"]["last_update"] = datetime.now().isoformat()
            
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            # 同时保存CSV格式
            csv_log_file = os.path.join(log_dir, f"test_generation_log_{today}.csv")
            if not os.path.exists(csv_log_file):
                with open(csv_log_file, 'w') as f:
                    f.write("timestamp,c_file,success,test_count,failed_tests,program_type,content_length,error\n")
            
            with open(csv_log_file, 'a') as f:
                error_str = str(log_entry["error"]).replace(',', ';').replace('\n', ' ') if log_entry["error"] else ""
                f.write(f"{log_entry['timestamp']},{log_entry['c_file']},{log_entry['success']},{log_entry['test_count']},{log_entry['failed_tests']},{log_entry['program_type']},{log_entry['content_length']},{error_str}\n")
            
        except Exception as e:
            print(f"⚠️ 日志保存失败: {e}")
    
    def find_missing_test_files(self) -> List[str]:
        """找到所有没有预生成测试用例的C文件"""
        missing_files = []
        
        for subdir in ["argv", "scanf"]:
            subdir_path = os.path.join(self.raw_data_dir, subdir)
            if os.path.exists(subdir_path):
                c_files = [os.path.join(subdir_path, f) for f in os.listdir(subdir_path) if f.endswith('.c')]
                
                for c_file in c_files:
                    # 检查是否有对应的预生成测试用例
                    test_file = self.find_corresponding_test(c_file)
                    if not test_file:
                        missing_files.append(c_file)
        
        return missing_files
    
    def batch_generate_tests(self, max_files: int = None) -> Dict[str, Any]:
        """批量生成测试用例"""
        print("🔍 搜索没有预生成测试用例的C文件...")
        
        missing_files = self.find_missing_test_files()
        print(f"📊 找到 {len(missing_files)} 个没有预生成测试用例的C文件")
        
        if max_files is not None and len(missing_files) > max_files:
            missing_files = missing_files[:max_files]
            print(f"⚠️ 限制处理前 {max_files} 个文件")
        
        results = {
            'total_files': len(missing_files),
            'success': 0,
            'failed': 0,
            'total_tests_generated': 0,
            'program_types': {},
            'details': [],
            'start_time': time.time()
        }
        
        for i, c_file_path in enumerate(missing_files):
            print(f"\n📁 处理文件 {i+1}/{len(missing_files)}: {os.path.basename(c_file_path)}")
            
            # 生成测试用例
            result = self.generate_test_samples_for_c(c_file_path, num_tests=10)
            
            if result['success']:
                # 保存测试用例
                c_filename = os.path.basename(c_file_path)
                test_dir = "argv" if "argv" in c_file_path else "scanf"
                output_dir = os.path.join(self.output_base_dir, test_dir)
                os.makedirs(output_dir, exist_ok=True)
                
                output_path = os.path.join(output_dir, c_filename + ".json")
                save_success = self.save_test_samples(result['test_cases'], output_path)
                
                if save_success:
                    results['success'] += 1
                    results['total_tests_generated'] += len(result['test_cases'])
                    
                    # 统计程序类型
                    program_type = result['analysis']['program_type']
                    if program_type not in results['program_types']:
                        results['program_types'][program_type] = 0
                    results['program_types'][program_type] += 1
                else:
                    results['failed'] += 1
                    result['error'] = '保存失败'
            else:
                results['failed'] += 1
            
            # 记录结果
            self.log_generation_result(c_file_path, result)
            
            results['details'].append({
                'file': os.path.basename(c_file_path),
                'directory': os.path.dirname(c_file_path),
                'success': result['success'],
                'test_count': len(result.get('test_cases', [])),
                'program_type': result.get('analysis', {}).get('program_type', 'unknown'),
                'error': result.get('error', None)
            })
            
            # 每处理10个文件显示一次进度
            if (i + 1) % 10 == 0:
                print(f"📈 进度: {i+1}/{len(missing_files)}, 成功: {results['success']}, 失败: {results['failed']}")
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        return results

def main():
    output_base_dir = "/home/changdi/sactor/test_no_test"
    
    print(f"🚀 开始为没有预生成测试用例的C程序生成测试用例")
    print(f"📁 输出目录: {output_base_dir}")
    
    generator = MissingTestGenerator(output_base_dir)
    
    try:
        results = generator.batch_generate_tests(max_files=None)
        
        print(f"\n📊 测试用例生成结果:")
        print(f"处理文件数: {results['total_files']}")
        print(f"成功生成: {results['success']}")
        print(f"生成失败: {results['failed']}")
        print(f"总测试用例数: {results['total_tests_generated']}")
        print(f"平均每个文件: {results['total_tests_generated']/results['success']:.1f} 个测试用例" if results['success'] > 0 else "平均每个文件: 0 个测试用例")
        print(f"处理时间: {results['duration']:.2f} 秒")
        
        print(f"\n📈 程序类型统计:")
        for program_type, count in results['program_types'].items():
            print(f"  {program_type}: {count} 个文件")
        
        # 保存详细结果
        results_file = os.path.join(output_base_dir, "test_generation_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 详细结果已保存到: {results_file}")
        print(f"📝 日志文件保存在: {output_base_dir}/logs/")
        
        return results
        
    finally:
        if hasattr(generator, 'temp_dir') and os.path.exists(generator.temp_dir):
            shutil.rmtree(generator.temp_dir)

if __name__ == "__main__":
    main()
