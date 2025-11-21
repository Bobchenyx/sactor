#!/usr/bin/env python3
"""
动态生成C程序测试用例的工具
用于为没有预生成测试用例的C文件生成test_samples.json
"""

import os
import sys
import json
import subprocess
import tempfile
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse

class CTestGenerator:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix='c_test_gen_')
    
    def __del__(self):
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
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
    
    def generate_test_inputs(self, analysis: Dict[str, Any], num_tests: int = 10) -> List[Dict[str, str]]:
        """根据程序分析结果生成测试输入"""
        test_cases = []
        
        if analysis['program_type'] == 'argv':
            # 生成命令行参数测试用例
            for i in range(num_tests):
                test_input = []
                
                for param_type in analysis['argv_params']:
                    if param_type == 'int':
                        # 生成整数，包括边界值和随机值
                        if i == 0:
                            test_input.append('0')
                        elif i == 1:
                            test_input.append('1')
                        elif i == 2:
                            test_input.append('10')
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
                    "output": ""  # 将在运行后填充
                })
        
        elif analysis['program_type'] == 'scanf':
            # 生成scanf输入测试用例
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
            # 未知类型，尝试生成一些通用测试用例
            for i in range(min(5, num_tests)):
                test_cases.append({
                    "input": str(i),
                    "output": ""
                })
        
        return test_cases
    
    def compile_and_run_c(self, c_file_path: str, test_input: str, is_argv: bool = True) -> Optional[str]:
        """编译并运行C程序，获取输出"""
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
                # 命令行参数方式
                args = test_input.split() if test_input.strip() else []
                run_cmd = [executable_path] + args
                run_result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=10)
            else:
                # 标准输入方式
                run_cmd = [executable_path]
                run_result = subprocess.run(run_cmd, input=test_input, capture_output=True, text=True, timeout=10)
            
            if run_result.returncode != 0:
                print(f"⚠️ 运行失败 (返回码: {run_result.returncode}): {run_result.stderr}")
                return None
            
            # 清理输出（去除多余的空白字符）
            output = run_result.stdout.strip()
            return output if output else None
            
        except subprocess.TimeoutExpired:
            print(f"⚠️ 程序运行超时")
            return None
        except Exception as e:
            print(f"⚠️ 运行程序出错: {e}")
            return None
    
    def generate_test_samples(self, c_file_path: str, num_tests: int = 10) -> List[Dict[str, str]]:
        """为C程序生成完整的测试用例"""
        print(f"🔍 分析C程序: {os.path.basename(c_file_path)}")
        
        # 1. 分析程序
        analysis = self.analyze_c_program(c_file_path)
        print(f"📊 程序类型: {analysis['program_type']}")
        
        if analysis['program_type'] == 'unknown':
            print("❌ 无法识别程序类型，无法生成测试用例")
            return []
        
        # 2. 生成测试输入
        test_cases = self.generate_test_inputs(analysis, num_tests)
        print(f"🎯 生成了 {len(test_cases)} 个测试输入")
        
        # 3. 运行程序获取期望输出
        is_argv = analysis['program_type'] == 'argv'
        successful_tests = []
        
        for i, test_case in enumerate(test_cases):
            print(f"🧪 运行测试 {i+1}/{len(test_cases)}: {test_case['input'][:50]}...")
            
            output = self.compile_and_run_c(c_file_path, test_case['input'], is_argv)
            if output is not None:
                test_case['output'] = output
                successful_tests.append(test_case)
                print(f"✅ 输出: {output}")
            else:
                print(f"❌ 测试失败")
        
        print(f"📈 成功生成 {len(successful_tests)} 个有效测试用例")
        return successful_tests
    
    def save_test_samples(self, test_cases: List[Dict[str, str]], output_path: str):
        """保存测试用例到JSON文件"""
        try:
            with open(output_path, 'w') as f:
                json.dump(test_cases, f, indent=2)
            print(f"💾 测试用例已保存到: {output_path}")
        except Exception as e:
            print(f"❌ 保存失败: {e}")

def main():
    parser = argparse.ArgumentParser(description='为C程序生成测试用例')
    parser.add_argument('c_file', help='C程序文件路径')
    parser.add_argument('-o', '--output', help='输出JSON文件路径')
    parser.add_argument('-n', '--num-tests', type=int, default=10, help='生成测试用例数量')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.c_file):
        print(f"❌ C文件不存在: {args.c_file}")
        sys.exit(1)
    
    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        c_filename = os.path.basename(args.c_file)
        output_path = c_filename + '.json'
    
    # 生成测试用例
    generator = CTestGenerator()
    test_cases = generator.generate_test_samples(args.c_file, args.num_tests)
    
    if test_cases:
        generator.save_test_samples(test_cases, output_path)
        print(f"\n🎉 成功为 {os.path.basename(args.c_file)} 生成了 {len(test_cases)} 个测试用例")
    else:
        print(f"\n❌ 无法为 {os.path.basename(args.c_file)} 生成测试用例")
        sys.exit(1)

if __name__ == "__main__":
    main()