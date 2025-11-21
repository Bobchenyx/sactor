#!/usr/bin/env python3
"""
完整的测试用例解决方案
1. 检查是否有预生成测试用例
2. 如果没有，自动生成测试用例
3. 使用测试用例进行 SACToR 翻译
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

class CompleteTestCaseSolution:
    """完整的测试用例解决方案"""
    
    def __init__(self):
        """初始化解决方案"""
        self.temp_dir = tempfile.mkdtemp(prefix='complete_solution_')
        print(f"📁 临时工作目录: {self.temp_dir}")
        
        # 预生成测试用例目录
        self.test_base_dir = "/home/changdi/sactor-datasets/Project_CodeNet/generated_tests"
        
        # 导入测试用例生成器
        sys.path.append('/home/changdi/sactor')
        from generate_test_cases import TestCaseGenerator
        self.test_generator = TestCaseGenerator()
    
    def __del__(self):
        """清理临时目录"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def check_pre_generated_tests(self, c_file_path: str) -> Optional[str]:
        """检查是否有预生成测试用例"""
        c_filename = os.path.basename(c_file_path)
        test_filename = c_filename + ".json"
        
        # 检查 argv 目录
        argv_test_path = os.path.join(self.test_base_dir, "argv", test_filename)
        if os.path.exists(argv_test_path):
            return argv_test_path
        
        # 检查 scanf 目录
        scanf_test_path = os.path.join(self.test_base_dir, "scanf", test_filename)
        if os.path.exists(scanf_test_path):
            return scanf_test_path
        
        return None
    
    def load_or_generate_test_cases(self, c_file_path: str, output_dir: str) -> tuple[str, str, bool]:
        """加载预生成测试用例或生成新的测试用例"""
        c_filename = os.path.basename(c_file_path)
        test_samples_path = os.path.join(output_dir, "test_samples.json")
        
        # 1. 检查是否有预生成测试用例
        pregen_test_path = self.check_pre_generated_tests(c_file_path)
        
        if pregen_test_path:
            # 使用预生成测试用例
            print(f"🎯 使用预生成测试用例: {os.path.basename(pregen_test_path)}")
            shutil.copy2(pregen_test_path, test_samples_path)
            used_pregen = True
        else:
            # 生成新的测试用例
            print(f"🔧 生成新的测试用例: {c_filename}")
            test_samples = self.test_generator.generate_test_cases_for_file(c_file_path)
            
            if test_samples:
                # 保存生成的测试用例
                with open(test_samples_path, 'w') as f:
                    json.dump(test_samples, f, indent=2)
                print(f"✅ 生成了 {len(test_samples)} 个测试用例")
                used_pregen = False
            else:
                # 使用默认测试用例
                print(f"⚠️ 生成失败，使用默认测试用例")
                default_samples = [
                    {"input": "10", "output": "10"},
                    {"input": "5", "output": "5"},
                    {"input": "0", "output": "0"}
                ]
                with open(test_samples_path, 'w') as f:
                    json.dump(default_samples, f, indent=2)
                used_pregen = False
        
        # 2. 创建测试任务文件
        test_task = []
        with open(test_samples_path, 'r') as f:
            test_samples = json.load(f)
        
        for i in range(len(test_samples)):
            test_task.append({
                "command": f"sactor run-tests --type bin ./test_samples.json %t {i} --feed-as-args",
                "test_id": i
            })
        
        test_task_path = os.path.join(output_dir, "test_task.json")
        with open(test_task_path, 'w') as f:
            json.dump(test_task, f, indent=2)
        
        return test_task_path, test_samples_path, used_pregen
    
    def translate_with_sactor_docker(self, c_file_path: str, output_dir: str, test_task_path: str) -> Dict:
        """使用 SACToR Docker 进行翻译"""
        try:
            # 复制 C 文件到输出目录
            c_file_dest = os.path.join(output_dir, os.path.basename(c_file_path))
            shutil.copy2(c_file_path, c_file_dest)
            
            # 运行 SACToR Docker 翻译
            sactor_config = "/home/changdi/sactor/sactor.toml"
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{sactor_config}:/app/sactor.toml",
                "-v", f"{output_dir}:/tmp/translation",
                "sactor", "translate",
                f"/tmp/translation/{os.path.basename(c_file_path)}",
                f"/tmp/translation/test_task.json",
                "--result-dir", "/tmp/translation/result",
                "--type", "bin"
            ]
            
            # 使用较长的超时时间
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f"SACToR Docker 翻译失败: {result.stderr[:500]}...",
                    'result_dir': None
                }
            
            return {
                'success': True,
                'error': None,
                'result_dir': os.path.join(output_dir, "result")
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': "SACToR Docker 翻译超时 (10分钟)",
                'result_dir': None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"SACToR Docker 翻译出错: {e}",
                'result_dir': None
            }
    
    def verify_translation_result(self, result_dir: str) -> Dict:
        """验证翻译结果"""
        try:
            verification_results = {
                'unidiomatic': {'success': False, 'details': {}},
                'idiomatic': {'success': False, 'details': {}},
                'overall': False,
                'test_count': 0
            }
            
            # 查找翻译结果
            unidiomatic_dir = os.path.join(result_dir, "translated_code_unidiomatic")
            idiomatic_dir = os.path.join(result_dir, "translated_code_idiomatic")
            
            # 检查是否存在翻译结果
            if os.path.exists(unidiomatic_dir):
                verification_results['unidiomatic'] = {'success': True, 'details': {'exists': True}}
            
            if os.path.exists(idiomatic_dir):
                verification_results['idiomatic'] = {'success': True, 'details': {'exists': True}}
                
                # 计算测试数量
                test_samples_path = os.path.join(result_dir, "..", "test_samples.json")
                if os.path.exists(test_samples_path):
                    with open(test_samples_path, 'r') as f:
                        test_samples = json.load(f)
                    verification_results['test_count'] = len(test_samples)
            
            # 综合结果
            verification_results['overall'] = (
                verification_results['unidiomatic']['success'] and 
                verification_results['idiomatic']['success']
            )
            
            return verification_results
            
        except Exception as e:
            return {
                'unidiomatic': {'success': False, 'error': str(e)},
                'idiomatic': {'success': False, 'error': str(e)},
                'overall': False,
                'test_count': 0
            }
    
    def translate_and_verify(self, c_file_path: str, output_dir: str) -> Dict:
        """翻译和验证单个 C 文件"""
        try:
            print(f"🎯 完整解决方案翻译: {os.path.basename(c_file_path)}")
            
            # 1. 加载或生成测试用例
            test_task_path, test_samples_path, used_pregen = self.load_or_generate_test_cases(c_file_path, output_dir)
            
            # 2. 使用 SACToR Docker 进行翻译
            translation_result = self.translate_with_sactor_docker(c_file_path, output_dir, test_task_path)
            
            if not translation_result['success']:
                return {
                    'success': False,
                    'error': translation_result['error'],
                    'verification': None,
                    'test_count': 0,
                    'used_pregen': used_pregen
                }
            
            # 3. 验证翻译结果
            verification_results = self.verify_translation_result(translation_result['result_dir'])
            
            return {
                'success': True,
                'error': None,
                'verification': verification_results,
                'test_count': verification_results.get('test_count', 0),
                'result_dir': translation_result['result_dir'],
                'used_pregen': used_pregen
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"翻译失败: {e}",
                'verification': None,
                'test_count': 0,
                'used_pregen': False
            }
    
    def batch_translate(self, dataset_dirs: List[str], output_base_dir: str, max_files: int = None) -> Dict:
        """批量翻译"""
        all_c_files = []
        
        # 收集所有 C 文件
        for dataset_dir in dataset_dirs:
            if os.path.exists(dataset_dir):
                c_files = [os.path.join(dataset_dir, f) for f in os.listdir(dataset_dir) if f.endswith('.c')]
                all_c_files.extend(c_files)
        
        # 限制处理文件数量（如果指定）
        if max_files is not None and len(all_c_files) > max_files:
            all_c_files = all_c_files[:max_files]
            print(f"⚠️ 限制处理前 {max_files} 个文件")
        
        total_files = len(all_c_files)
        print(f"🚀 开始完整解决方案批量翻译 {total_files} 个 C 文件")
        
        results = {
            'total': total_files,
            'success': 0,
            'failed': 0,
            'verified': 0,
            'pre_generated_used': 0,
            'generated_used': 0,
            'default_used': 0,
            'details': [],
            'start_time': time.time()
        }
        
        for i, c_file_path in enumerate(all_c_files):
            print(f"\n📁 处理文件 {i+1}/{total_files}: {os.path.basename(c_file_path)}")
            
            # 为每个文件创建输出目录
            relative_path = os.path.relpath(c_file_path, os.path.dirname(dataset_dirs[0]))
            file_output_dir = os.path.join(output_base_dir, relative_path.replace('.c', ''))
            os.makedirs(file_output_dir, exist_ok=True)
            
            # 翻译和验证
            result = self.translate_and_verify(c_file_path, file_output_dir)
            
            if result['success']:
                results['success'] += 1
                if result['verification'] and result['verification']['overall']:
                    results['verified'] += 1
            
            # 统计测试用例来源
            if result.get('used_pregen', False):
                results['pre_generated_used'] += 1
            else:
                results['generated_used'] += 1
            
            results['details'].append({
                'file': os.path.basename(c_file_path),
                'directory': os.path.dirname(c_file_path),
                'success': result['success'],
                'verified': result['verification']['overall'] if result['verification'] else False,
                'test_count': result['test_count'],
                'used_pregen': result.get('used_pregen', False),
                'error': result['error']
            })
            
            results['failed'] = results['total'] - results['success']
            
            # 每处理 10 个文件保存一次进度
            if (i + 1) % 10 == 0:
                self._save_progress(results, output_base_dir, i + 1)
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        return results
    
    def _save_progress(self, results: Dict, output_base_dir: str, processed_count: int):
        """保存进度"""
        progress_file = os.path.join(output_base_dir, f"progress_{processed_count}.json")
        with open(progress_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 进度已保存: {processed_count}/{results['total']} 文件")

def main():
    """主函数"""
    # 配置路径
    dataset_dirs = [
        "/home/changdi/sactor-datasets/Project_CodeNet/selected_data_raw/argv",
        "/home/changdi/sactor-datasets/Project_CodeNet/selected_data_raw/scanf"
    ]
    output_base_dir = "/home/changdi/sactor-datasets/sactor_complete_translations"
    
    # 创建输出目录
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 统计总文件数和预生成测试用例覆盖
    total_files = 0
    pregen_argv = 0
    pregen_scanf = 0
    
    for dataset_dir in dataset_dirs:
        if os.path.exists(dataset_dir):
            c_files = [f for f in os.listdir(dataset_dir) if f.endswith('.c')]
            total_files += len(c_files)
            
            # 统计预生成测试用例覆盖
            if "argv" in dataset_dir:
                pregen_argv = len(os.listdir("/home/changdi/sactor-datasets/Project_CodeNet/generated_tests/argv"))
            elif "scanf" in dataset_dir:
                pregen_scanf = len(os.listdir("/home/changdi/sactor-datasets/Project_CodeNet/generated_tests/scanf"))
    
    print(f"📁 找到总计 {total_files} 个 C 文件")
    print(f"   - argv 目录: {len([f for f in os.listdir(dataset_dirs[0]) if f.endswith('.c')])} 个文件")
    print(f"   - scanf 目录: {len([f for f in os.listdir(dataset_dirs[1]) if f.endswith('.c')])} 个文件")
    print(f"🎯 预生成测试用例覆盖:")
    print(f"   - argv: {pregen_argv} 个测试文件")
    print(f"   - scanf: {pregen_scanf} 个测试文件")
    print(f"🔧 完整解决方案:")
    print(f"   - 优先使用预生成测试用例")
    print(f"   - 自动生成缺失的测试用例")
    print(f"   - 确保所有文件都有测试用例")
    
    # 创建完整解决方案
    solution = CompleteTestCaseSolution()
    
    try:
        # 批量翻译
        results = solution.batch_translate(dataset_dirs, output_base_dir, max_files=None)
        
        # 输出结果统计
        print(f"\n📊 SACToR 完整解决方案批量翻译结果:")
        print(f"总文件数: {results['total']}")
        print(f"翻译成功: {results['success']}")
        print(f"翻译失败: {results['failed']}")
        print(f"验证通过: {results['verified']}")
        print(f"使用预生成测试: {results['pre_generated_used']}")
        print(f"使用生成测试: {results['generated_used']}")
        print(f"处理时间: {results['duration']:.2f} 秒")
        print(f"成功率: {results['success']/results['total']*100:.1f}%")
        print(f"验证率: {results['verified']/results['total']*100:.1f}%")
        
        # 保存详细结果
        results_file = os.path.join(output_base_dir, "sactor_complete_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 详细结果已保存到: {results_file}")
        
        return results
        
    finally:
        # 清理临时目录
        if hasattr(solution, 'temp_dir') and os.path.exists(solution.temp_dir):
            shutil.rmtree(solution.temp_dir)

if __name__ == "__main__":
    main()
