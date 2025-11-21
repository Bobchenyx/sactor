#!/usr/bin/env python3
"""
增强版批量翻译脚本 - 支持动态生成测试用例
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import time
import random
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# 导入原有的翻译器
sys.path.append('/home/changdi/sactor')
from batch_translate_correct import CorrectDataTranslator

class EnhancedTranslator(CorrectDataTranslator):
    def __init__(self):
        super().__init__()
        self.test_generator = CTestGenerator()
    
    def analyze_c_program(self, c_file_path: str) -> Dict[str, any]:
        """分析C程序，确定输入类型和参数"""
        try:
            with open(c_file_path, 'r') as f:
                content = f.read()
            
            analysis = {
                'has_argv': False,
                'has_scanf': False,
                'argv_params': [],
                'scanf_params': [],
                'program_type': 'unknown'
            }
            
            # 检查命令行参数
            if 'argv[' in content and 'argc' in content:
                analysis['has_argv'] = True
                analysis['program_type'] = 'argv'
                
                # 分析参数类型
                lines = content.split('\n')
                for line in lines:
                    if 'argv[' in line and ('atoi' in line or 'atof' in line):
                        if 'atoi' in line:
                            analysis['argv_params'].append('int')
                        elif 'atof' in line:
                            analysis['argv_params'].append('float')
                        else:
                            analysis['argv_params'].append('string')
            
            # 检查scanf输入
            if 'scanf(' in content:
                analysis['has_scanf'] = True
                analysis['program_type'] = 'scanf'
                
                # 分析scanf格式
                import re
                scanf_patterns = re.findall(r'scanf\s*\(\s*["\']([^"\']+)["\']', content)
                for pattern in scanf_patterns:
                    if '%d' in pattern:
                        analysis['scanf_params'].append('int')
                    elif '%f' in pattern or '%lf' in pattern:
                        analysis['scanf_params'].append('float')
                    elif '%s' in pattern:
                        analysis['scanf_params'].append('string')
                    else:
                        analysis['scanf_params'].append('unknown')
            
            return analysis
            
        except Exception as e:
            print(f"❌ 分析C程序失败: {e}")
            return {'program_type': 'unknown'}
    
    def generate_smart_test_inputs(self, analysis: Dict[str, any], num_tests: int = 10) -> List[Dict[str, str]]:
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
                        else:
                            # 生成一些特殊的测试值
                            special_values = [5, 15, 20, 25, 30, 50, 75, 99]
                            if i-4 < len(special_values):
                                test_input.append(str(special_values[i-4]))
                            else:
                                test_input.append(str(random.randint(1, 100)))
                    elif param_type == 'float':
                        if i == 0:
                            test_input.append('0.0')
                        elif i == 1:
                            test_input.append('1.5')
                        else:
                            test_input.append(f"{random.uniform(0, 10):.2f}")
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
                        else:
                            test_input.append(str(random.randint(1, 100)))
                    elif param_type == 'float':
                        if i == 0:
                            test_input.append('0.0')
                        elif i == 1:
                            test_input.append('1.5')
                        else:
                            test_input.append(f"{random.uniform(0, 10):.2f}")
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
            executable_path = os.path.join(self.temp_dir, "test_program")
            compile_cmd = ["gcc", "-o", executable_path, c_file_path]
            
            compile_result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=30)
            if compile_result.returncode != 0:
                print(f"⚠️ 编译失败: {compile_result.stderr}")
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
                print(f"⚠️ 运行失败 (返回码: {run_result.returncode}): {run_result.stderr}")
                return None
            
            output = run_result.stdout.strip()
            return output if output else None
            
        except subprocess.TimeoutExpired:
            print(f"⚠️ 程序运行超时")
            return None
        except Exception as e:
            print(f"⚠️ 运行程序出错: {e}")
            return None
    
    def generate_test_samples_for_c(self, c_file_path: str, num_tests: int = 10) -> List[Dict[str, str]]:
        """为C程序生成测试用例"""
        print(f"🔍 分析C程序: {os.path.basename(c_file_path)}")
        
        # 1. 分析程序
        analysis = self.analyze_c_program(c_file_path)
        print(f"📊 程序类型: {analysis['program_type']}")
        
        if analysis['program_type'] == 'unknown':
            print("❌ 无法识别程序类型，无法生成测试用例")
            return []
        
        # 2. 生成测试输入
        test_cases = self.generate_smart_test_inputs(analysis, num_tests)
        print(f"🎯 生成了 {len(test_cases)} 个测试输入")
        
        # 3. 运行程序获取期望输出
        is_argv = analysis['program_type'] == 'argv'
        successful_tests = []
        
        for i, test_case in enumerate(test_cases):
            print(f"🧪 运行测试 {i+1}/{len(test_cases)}: {test_case['input'][:30]}...")
            
            output = self.compile_and_run_c(c_file_path, test_case['input'], is_argv)
            if output is not None:
                test_case['output'] = output
                successful_tests.append(test_case)
                print(f"✅ 输出: {output}")
            else:
                print(f"❌ 测试失败")
        
        print(f"📈 成功生成 {len(successful_tests)} 个有效测试用例")
        return successful_tests
    
    def create_test_config_with_generation(self, c_file_path: str, output_dir: str) -> tuple[str, str, bool]:
        """创建测试配置，如果没有预生成测试则动态生成"""
        c_filename = os.path.basename(c_file_path)
        
        # 首先尝试找到预生成的测试用例
        test_file_path = self.find_corresponding_test(c_file_path)
        
        if test_file_path and os.path.exists(test_file_path):
            print(f"🎯 使用预生成测试用例: {os.path.basename(test_file_path)}")
            test_samples_path = test_file_path
            used_pregen = True
        else:
            print(f"🔧 没有预生成测试用例，动态生成测试用例...")
            # 动态生成测试用例
            test_cases = self.generate_test_samples_for_c(c_file_path, num_tests=10)
            
            if not test_cases:
                raise ValueError(f"无法为 {c_file_path} 生成测试用例")
            
            # 保存生成的测试用例
            test_samples_path = os.path.join(output_dir, "generated_test_samples.json")
            with open(test_samples_path, 'w') as f:
                json.dump(test_cases, f, indent=2)
            
            used_pregen = False
            print(f"💾 动态生成的测试用例已保存到: {test_samples_path}")
        
        # 创建test_task.json
        test_task = []
        with open(test_samples_path, 'r') as f:
            test_samples = json.load(f)
        
        for i in range(len(test_samples)):
            test_task.append({
                "command": f"sactor run-tests --type bin {test_samples_path} %t {i} --feed-as-args",
                "test_id": i
            })
        
        test_task_path = os.path.join(output_dir, "test_task.json")
        with open(test_task_path, 'w') as f:
            json.dump(test_task, f, indent=2)
        
        return test_task_path, test_samples_path, used_pregen
    
    def batch_translate_all(self, output_base_dir: str, max_files: int = None) -> Dict:
        """批量翻译所有C文件（包括没有预生成测试的文件）"""
        all_c_files = []
        
        # 收集所有C文件
        for subdir in ["argv", "scanf"]:
            subdir_path = os.path.join(self.raw_data_dir, subdir)
            if os.path.exists(subdir_path):
                c_files = [os.path.join(subdir_path, f) for f in os.listdir(subdir_path) if f.endswith('.c')]
                all_c_files.extend(c_files)
        
        print(f"🎯 发现 {len(all_c_files)} 个C文件")
        
        if max_files is not None and len(all_c_files) > max_files:
            all_c_files = all_c_files[:max_files]
            print(f"⚠️ 限制处理前 {max_files} 个文件")
        
        total_files = len(all_c_files)
        print(f"🚀 开始批量翻译 {total_files} 个C文件（支持动态生成测试用例）")
        
        results = {
            'total': total_files,
            'success': 0,
            'failed': 0,
            'verified': 0,
            'pregen_tests': 0,
            'generated_tests': 0,
            'total_processing_time': 0,
            'total_attempts': 0,
            'total_api_cost': 0,
            'details': [],
            'start_time': time.time()
        }
        
        for i, c_file_path in enumerate(all_c_files):
            print(f"\n📁 处理文件 {i+1}/{total_files}: {os.path.basename(c_file_path)}")
            
            relative_path = os.path.relpath(c_file_path, self.raw_data_dir)
            file_output_dir = os.path.join(output_base_dir, relative_path.replace('.c', ''))
            os.makedirs(file_output_dir, exist_ok=True)
            
            start_time = time.time()
            try:
                # 使用增强版的测试配置创建方法
                test_task_path, test_samples_path, used_pregen = self.create_test_config_with_generation(c_file_path, file_output_dir)
                
                if used_pregen:
                    results['pregen_tests'] += 1
                else:
                    results['generated_tests'] += 1
                
                # 执行翻译
                translation_result = self.translate_with_sactor_docker(c_file_path, file_output_dir, test_task_path)
                
                if not translation_result['success']:
                    result = {
                        'success': False,
                        'error': translation_result['error'],
                        'verification': None,
                        'test_count': 0,
                        'used_pregen': used_pregen,
                        'processing_time': time.time() - start_time,
                        'attempts': translation_result.get('attempts', 0),
                        'api_cost': translation_result.get('api_cost', {})
                    }
                else:
                    # 验证翻译结果
                    verification_results = self.verify_translation_result(translation_result['result_dir'])
                    
                    result = {
                        'success': True,
                        'error': None,
                        'verification': verification_results,
                        'test_count': verification_results.get('test_count', 0),
                        'result_dir': translation_result['result_dir'],
                        'used_pregen': used_pregen,
                        'processing_time': time.time() - start_time,
                        'attempts': translation_result.get('attempts', 0),
                        'api_cost': translation_result.get('api_cost', {})
                    }
                
                # 记录日志
                self.log_translation_result(c_file_path, result, output_base_dir)
                
                if result['success']:
                    results['success'] += 1
                    if result['verification'] and result['verification']['overall']:
                        results['verified'] += 1
                
                processing_time = result.get('processing_time', 0)
                attempts = result.get('attempts', 0)
                api_cost = result.get('api_cost', {})
                total_cost = api_cost.get('total_cost', 0)
                
                results['total_processing_time'] += processing_time
                results['total_attempts'] += attempts
                results['total_api_cost'] += total_cost
                
                results['details'].append({
                    'file': os.path.basename(c_file_path),
                    'directory': os.path.dirname(c_file_path),
                    'success': result['success'],
                    'verified': result['verification']['overall'] if result['verification'] else False,
                    'test_count': result['test_count'],
                    'used_pregen': result['used_pregen'],
                    'processing_time': processing_time,
                    'attempts': attempts,
                    'api_cost': api_cost,
                    'error': result['error']
                })
                
                results['failed'] = results['total'] - results['success']
                
                if (i + 1) % 10 == 0:
                    self._save_progress(results, output_base_dir, i + 1)
                    print(f"📈 进度统计: 处理时间 {processing_time:.1f}s, 尝试次数 {attempts}, API成本 ${total_cost:.4f}")
                
            except Exception as e:
                result = {
                    'success': False,
                    'error': f"翻译失败: {e}",
                    'verification': None,
                    'test_count': 0,
                    'used_pregen': False,
                    'processing_time': time.time() - start_time,
                    'attempts': 0,
                    'api_cost': {'total_cost': 0, 'error': str(e)}
                }
                
                self.log_translation_result(c_file_path, result, output_base_dir)
                results['failed'] += 1
                results['details'].append({
                    'file': os.path.basename(c_file_path),
                    'success': False,
                    'error': str(e)
                })
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        if results['total'] > 0:
            results['avg_processing_time'] = results['total_processing_time'] / results['total']
            results['avg_attempts'] = results['total_attempts'] / results['total']
            results['avg_api_cost'] = results['total_api_cost'] / results['total']
        
        return results

def main():
    output_base_dir = "/home/changdi/sactor/test_enhanced"
    
    os.makedirs(output_base_dir, exist_ok=True)
    
    print(f"🚀 启动增强版批量翻译（支持动态生成测试用例）")
    
    translator = EnhancedTranslator()
    
    try:
        results = translator.batch_translate_all(output_base_dir, max_files=None)
        
        print(f"\n📊 增强版批量翻译结果:")
        print(f"处理文件数: {results['total']}")
        print(f"翻译成功: {results['success']}")
        print(f"翻译失败: {results['failed']}")
        print(f"验证通过: {results['verified']}")
        print(f"使用预生成测试: {results['pregen_tests']}")
        print(f"动态生成测试: {results['generated_tests']}")
        print(f"总处理时间: {results['duration']:.2f} 秒")
        print(f"总尝试次数: {results['total_attempts']}")
        print(f"总API成本: ${results['total_api_cost']:.4f}")
        print(f"平均处理时间: {results['avg_processing_time']:.2f} 秒/文件")
        print(f"平均尝试次数: {results['avg_attempts']:.1f} 次/文件")
        print(f"平均API成本: ${results['avg_api_cost']:.4f}/文件")
        print(f"成功率: {results['success']/results['total']*100:.1f}%")
        print(f"验证率: {results['verified']/results['total']*100:.1f}%")
        
        results_file = os.path.join(output_base_dir, "enhanced_translation_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 详细结果已保存到: {results_file}")
        
        return results
        
    finally:
        if hasattr(translator, 'temp_dir') and os.path.exists(translator.temp_dir):
            shutil.rmtree(translator.temp_dir)

if __name__ == "__main__":
    main()




