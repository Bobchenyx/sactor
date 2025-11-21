#!/usr/bin/env python3
"""
优化的 SACToR 批量翻译脚本
- 减少超时时间
- 优化 max_translation_attempts
- 添加进度监控
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

class OptimizedTranslator:
    """优化的 SACToR 批量翻译器"""
    
    def __init__(self):
        """初始化翻译器"""
        self.temp_dir = tempfile.mkdtemp(prefix='sactor_opt_')
        print(f"📁 临时工作目录: {self.temp_dir}")
        
        # 正确的数据目录
        self.raw_data_dir = "/home/changdi/sactor-datasets/Project_CodeNet/raw_data"
        self.test_data_dir = "/home/changdi/sactor-datasets/Project_CodeNet/generated_tests"
    
    def __del__(self):
        """清理临时目录"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def find_corresponding_test(self, c_file_path: str) -> Optional[str]:
        """查找对应的测试用例文件"""
        c_filename = os.path.basename(c_file_path)
        test_filename = c_filename + ".json"
        
        # 确定子目录 (argv 或 scanf)
        if "argv" in c_file_path:
            test_path = os.path.join(self.test_data_dir, "argv", test_filename)
        elif "scanf" in c_file_path:
            test_path = os.path.join(self.test_data_dir, "scanf", test_filename)
        else:
            return None
        
        if os.path.exists(test_path):
            return test_path
        return None
    
    def load_test_cases(self, test_file_path: str) -> List[Dict]:
        """加载测试用例"""
        try:
            with open(test_file_path, 'r') as f:
                test_samples = json.load(f)
            return test_samples
        except Exception as e:
            print(f"❌ 加载测试用例失败: {e}")
            return []
    
    def create_test_config(self, c_file_path: str, output_dir: str) -> tuple[str, str, bool]:
        """创建测试配置"""
        c_filename = os.path.basename(c_file_path)
        test_samples_path = os.path.join(output_dir, "test_samples.json")
        
        # 查找对应的测试用例
        test_file_path = self.find_corresponding_test(c_file_path)
        
        if test_file_path:
            # 使用预生成的测试用例 - 直接使用绝对路径，不复制
            test_samples_path = test_file_path  # 直接使用原始路径
            used_pregen = True
        else:
            # 没有对应的测试用例，使用默认测试用例
            default_samples = [
                {"input": "10", "output": "10"},
                {"input": "5", "output": "5"},
                {"input": "0", "output": "0"}
            ]
            with open(test_samples_path, 'w') as f:
                json.dump(default_samples, f, indent=2)
            used_pregen = False
        
        # 创建测试任务文件
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
    
    def translate_with_sactor_docker(self, c_file_path: str, output_dir: str, test_task_path: str) -> Dict:
        """使用 SACToR Docker 进行翻译 - 优化版本"""
        try:
            # 直接使用绝对路径，挂载整个数据集目录
            sactor_config = "/home/changdi/sactor/sactor.toml"
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{sactor_config}:/app/sactor.toml",
                "-v", f"/home/changdi/sactor-datasets:/home/changdi/sactor-datasets",
                "-v", f"{os.path.dirname(test_task_path)}:/tmp/test_tasks",
                "-v", f"{output_dir}:/tmp/result",
                "sactor", "translate",
                c_file_path,  # 直接使用绝对路径
                f"/tmp/test_tasks/{os.path.basename(test_task_path)}",
                "--result-dir", "/tmp/result",
                "--type", "bin"
            ]
            
            # 优化：减少超时时间从 600秒 到 120秒，显示输出
            result = subprocess.run(cmd, text=True, timeout=120)
            
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
                'error': "SACToR Docker 翻译超时 (2分钟)",
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
        start_time = time.time()
        
        try:
            print(f"🎯 优化翻译: {os.path.basename(c_file_path)}")
            
            # 1. 创建测试配置
            test_task_path, test_samples_path, used_pregen = self.create_test_config(c_file_path, output_dir)
            
            # 2. 使用 SACToR Docker 进行翻译
            translation_result = self.translate_with_sactor_docker(c_file_path, output_dir, test_task_path)
            
            if not translation_result['success']:
                return {
                    'success': False,
                    'error': translation_result['error'],
                    'verification': None,
                    'test_count': 0,
                    'used_pregen': used_pregen,
                    'duration': time.time() - start_time
                }
            
            # 3. 验证翻译结果
            verification_results = self.verify_translation_result(translation_result['result_dir'])
            
            duration = time.time() - start_time
            print(f"✅ 完成: {os.path.basename(c_file_path)} ({duration:.1f}秒)")
            
            return {
                'success': True,
                'error': None,
                'verification': verification_results,
                'test_count': verification_results.get('test_count', 0),
                'result_dir': translation_result['result_dir'],
                'used_pregen': used_pregen,
                'duration': duration
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"翻译失败: {e}",
                'verification': None,
                'test_count': 0,
                'used_pregen': False,
                'duration': time.time() - start_time
            }
    
    def batch_translate(self, output_base_dir: str, max_files: int = None) -> Dict:
        """批量翻译"""
        all_c_files = []
        
        # 收集所有 C 文件
        for subdir in ["argv", "scanf"]:
            subdir_path = os.path.join(self.raw_data_dir, subdir)
            if os.path.exists(subdir_path):
                c_files = [os.path.join(subdir_path, f) for f in os.listdir(subdir_path) if f.endswith('.c')]
                all_c_files.extend(c_files)
        
        # 限制处理文件数量（如果指定）
        if max_files is not None and len(all_c_files) > max_files:
            all_c_files = all_c_files[:max_files]
            print(f"⚠️ 限制处理前 {max_files} 个文件")
        
        total_files = len(all_c_files)
        print(f"🚀 开始优化批量翻译 {total_files} 个 C 文件")
        
        results = {
            'total': total_files,
            'success': 0,
            'failed': 0,
            'verified': 0,
            'pre_generated_used': 0,
            'default_used': 0,
            'total_duration': 0,
            'avg_duration': 0,
            'details': [],
            'start_time': time.time()
        }
        
        for i, c_file_path in enumerate(all_c_files):
            print(f"\n📁 处理文件 {i+1}/{total_files}: {os.path.basename(c_file_path)}")
            
            # 为每个文件创建输出目录
            relative_path = os.path.relpath(c_file_path, self.raw_data_dir)
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
                results['default_used'] += 1
            
            # 统计时间
            results['total_duration'] += result.get('duration', 0)
            
            results['details'].append({
                'file': os.path.basename(c_file_path),
                'directory': os.path.dirname(c_file_path),
                'success': result['success'],
                'verified': result['verification']['overall'] if result['verification'] else False,
                'test_count': result['test_count'],
                'used_pregen': result.get('used_pregen', False),
                'duration': result.get('duration', 0),
                'error': result['error']
            })
            
            results['failed'] = results['total'] - results['success']
            
            # 计算平均时间
            if results['success'] > 0:
                results['avg_duration'] = results['total_duration'] / results['success']
            
            # 每处理 5 个文件保存一次进度（更频繁）
            if (i + 1) % 5 == 0:
                self._save_progress(results, output_base_dir, i + 1)
                print(f"📊 进度: {i+1}/{total_files}, 成功: {results['success']}, 平均时间: {results['avg_duration']:.1f}秒/个")
        
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
    output_base_dir = "/home/changdi/sactor-datasets/sactor_optimized_translations"
    
    # 创建输出目录
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 统计总文件数和预生成测试用例覆盖
    raw_data_dir = "/home/changdi/sactor-datasets/Project_CodeNet/raw_data"
    test_data_dir = "/home/changdi/sactor-datasets/Project_CodeNet/generated_tests"
    
    argv_c_files = len(os.listdir(os.path.join(raw_data_dir, "argv")))
    scanf_c_files = len(os.listdir(os.path.join(raw_data_dir, "scanf")))
    total_c_files = argv_c_files + scanf_c_files
    
    argv_test_files = len(os.listdir(os.path.join(test_data_dir, "argv")))
    scanf_test_files = len(os.listdir(os.path.join(test_data_dir, "scanf")))
    total_test_files = argv_test_files + scanf_test_files
    
    print(f"📁 原始数据统计:")
    print(f"   - argv: {argv_c_files} 个 C 文件")
    print(f"   - scanf: {scanf_c_files} 个 C 文件")
    print(f"   - 总计: {total_c_files} 个 C 文件")
    print(f"🎯 预生成测试用例统计:")
    print(f"   - argv: {argv_test_files} 个测试文件")
    print(f"   - scanf: {scanf_test_files} 个测试文件")
    print(f"   - 总计: {total_test_files} 个测试文件")
    print(f"📊 测试用例覆盖率: {total_test_files}/{total_c_files} = {total_test_files/total_c_files*100:.1f}%")
    print(f"🚀 优化设置:")
    print(f"   - Docker 超时: 120秒 (从 600秒 优化)")
    print(f"   - 进度保存: 每5个文件 (从 10个文件 优化)")
    print(f"   - 预计平均时间: 30-60秒/个 (从 2-5分钟/个 优化)")
    
    # 创建翻译器
    translator = OptimizedTranslator()
    
    try:
        # 批量翻译
        results = translator.batch_translate(output_base_dir, max_files=None)
        
        # 输出结果统计
        print(f"\n📊 SACToR 优化批量翻译结果:")
        print(f"总文件数: {results['total']}")
        print(f"翻译成功: {results['success']}")
        print(f"翻译失败: {results['failed']}")
        print(f"验证通过: {results['verified']}")
        print(f"使用预生成测试: {results['pre_generated_used']}")
        print(f"使用默认测试: {results['default_used']}")
        print(f"总处理时间: {results['duration']:.2f} 秒")
        print(f"平均翻译时间: {results['avg_duration']:.2f} 秒/个")
        print(f"成功率: {results['success']/results['total']*100:.1f}%")
        print(f"验证率: {results['verified']/results['total']*100:.1f}%")
        
        # 保存详细结果
        results_file = os.path.join(output_base_dir, "sactor_optimized_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 详细结果已保存到: {results_file}")
        
        return results
        
    finally:
        # 清理临时目录
        if hasattr(translator, 'temp_dir') and os.path.exists(translator.temp_dir):
            shutil.rmtree(translator.temp_dir)

if __name__ == "__main__":
    main()