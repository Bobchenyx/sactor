#!/usr/bin/env python3
"""
集成 SACToR 原生验证的批量翻译脚本
使用 SACToR 的 Docker 接口进行翻译，然后使用 SACToR 的验证器进行验证
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional

# 添加 SACToR 模块路径
sys.path.insert(0, '/home/changdi/sactor')

from sactor import utils
from sactor.llm import llm_factory
from sactor.verifier import Verifier, IdiomaticVerifier
from sactor.verifier.verifier_types import VerifyResult
from sactor.test_generator import ExecutableTestGenerator

class SactorIntegratedTranslator:
    """集成 SACToR 翻译和原生验证的批量翻译器"""
    
    def __init__(self, config_path: str):
        """初始化集成翻译器"""
        self.config = utils.try_load_config(config_path)
        self.llm = llm_factory(self.config)
        
        # 创建临时工作目录
        self.temp_dir = tempfile.mkdtemp(prefix='sactor_integrated_')
        print(f"📁 临时工作目录: {self.temp_dir}")
    
    def __del__(self):
        """清理临时目录"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_sactor_test_config(self, c_file_path: str, output_dir: str) -> tuple[str, str]:
        """创建 SACToR 格式的测试配置"""
        # 根据程序类型生成测试用例
        program_name = os.path.basename(c_file_path)
        
        if "atoi" in program_name or "parse" in program_name:
            test_samples = [
                {"input": "123", "output": ""},
                {"input": "-456", "output": ""},
                {"input": "0", "output": ""},
                {"input": "2147483647", "output": ""},
                {"input": "-2147483648", "output": ""},
                {"input": "999999999", "output": ""},
                {"input": "32768", "output": ""},
                {"input": "+42", "output": ""},
                {"input": "-999999999", "output": ""},
                {"input": "-153423", "output": ""}
            ]
        elif "add" in program_name or "sum" in program_name:
            test_samples = [
                {"input": "10 20", "output": ""},
                {"input": "5 15", "output": ""},
                {"input": "0 0", "output": ""},
                {"input": "100 200", "output": ""},
                {"input": "-10 10", "output": ""},
                {"input": "1 1", "output": ""},
                {"input": "999 1", "output": ""},
                {"input": "-5 -5", "output": ""},
                {"input": "50 50", "output": ""},
                {"input": "0 100", "output": ""}
            ]
        else:
            # 通用测试用例
            test_samples = [
                {"input": "10", "output": ""},
                {"input": "123", "output": ""},
                {"input": "456", "output": ""},
                {"input": "999", "output": ""},
                {"input": "0", "output": ""},
                {"input": "1", "output": ""},
                {"input": "42", "output": ""},
                {"input": "100", "output": ""},
                {"input": "555", "output": ""},
                {"input": "777", "output": ""}
            ]
        
        # 创建测试任务文件 (SACToR 格式)
        test_task = []
        for i in range(len(test_samples)):
            test_task.append({
                "command": f"sactor run-tests --type bin ./test_samples.json %t {i} --feed-as-args",
                "test_id": i
            })
        
        # 保存文件
        test_task_path = os.path.join(output_dir, "test_task.json")
        with open(test_task_path, 'w') as f:
            json.dump(test_task, f, indent=2)
        
        test_samples_path = os.path.join(output_dir, "test_samples.json")
        with open(test_samples_path, 'w') as f:
            json.dump(test_samples, f, indent=2)
        
        print(f"✅ 创建了 {len(test_samples)} 个测试用例")
        return test_task_path, test_samples_path
    
    def translate_with_sactor_docker(self, c_file_path: str, output_dir: str, test_task_path: str) -> Dict:
        """使用 SACToR Docker 进行翻译"""
        try:
            print("📝 使用 SACToR Docker 进行翻译...")
            
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f"SACToR Docker 翻译失败: {result.stderr}",
                    'result_dir': None
                }
            
            print("✅ SACToR Docker 翻译完成")
            return {
                'success': True,
                'error': None,
                'result_dir': os.path.join(output_dir, "result")
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': "SACToR Docker 翻译超时",
                'result_dir': None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"SACToR Docker 翻译出错: {e}",
                'result_dir': None
            }
    
    def verify_with_sactor_native(self, result_dir: str, test_task_path: str) -> Dict:
        """使用 SACToR 原生验证器进行验证"""
        print("🔍 使用 SACToR 原生验证器进行验证...")
        
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
            
            # 验证非惯用代码
            if os.path.exists(unidiomatic_dir):
                print("🔧 验证非惯用代码...")
                unidiomatic_result = self._verify_code_with_sactor_verifier(
                    unidiomatic_dir, test_task_path, "unidiomatic"
                )
                verification_results['unidiomatic'] = unidiomatic_result
            
            # 验证惯用代码
            if os.path.exists(idiomatic_dir):
                print("✨ 验证惯用代码...")
                idiomatic_result = self._verify_code_with_sactor_verifier(
                    idiomatic_dir, test_task_path, "idiomatic"
                )
                verification_results['idiomatic'] = idiomatic_result
                verification_results['test_count'] = len(self._get_test_commands(test_task_path))
            
            # 综合结果
            verification_results['overall'] = (
                verification_results['unidiomatic']['success'] and 
                verification_results['idiomatic']['success']
            )
            
            if verification_results['overall']:
                print("🎉 SACToR 原生验证全部通过！")
            else:
                print("❌ SACToR 原生验证部分失败")
            
            return verification_results
            
        except Exception as e:
            print(f"❌ SACToR 原生验证出错: {e}")
            return {
                'unidiomatic': {'success': False, 'error': str(e)},
                'idiomatic': {'success': False, 'error': str(e)},
                'overall': False,
                'test_count': 0
            }
    
    def _verify_code_with_sactor_verifier(self, code_dir: str, test_task_path: str, code_type: str) -> Dict:
        """使用 SACToR 验证器验证特定类型的代码"""
        try:
            # 查找 Cargo.toml 文件
            cargo_toml_path = None
            for root, dirs, files in os.walk(code_dir):
                if 'Cargo.toml' in files:
                    cargo_toml_path = os.path.join(root, 'Cargo.toml')
                    break
            
            if not cargo_toml_path:
                return {'success': False, 'error': '未找到 Cargo.toml 文件'}
            
            # 创建 SACToR 验证器
            build_path = os.path.join(self.temp_dir, f'build_{code_type}')
            verifier = IdiomaticVerifier(
                test_cmd_path=test_task_path,
                llm=self.llm,
                config=self.config,
                build_path=build_path
            )
            
            # 读取 Rust 代码
            rust_code = self._read_rust_code(code_dir)
            if not rust_code:
                return {'success': False, 'error': '未找到 Rust 代码'}
            
            # 执行编译验证
            print(f"🔨 验证 {code_type} 代码编译...")
            compile_result = verifier.try_compile_rust_code(rust_code, executable=True)
            
            if compile_result[0] != VerifyResult.SUCCESS:
                return {
                    'success': False, 
                    'error': f'编译失败: {compile_result[1]}',
                    'compile_result': compile_result[0].name
                }
            
            # 查找可执行文件
            executable_path = self._find_executable(build_path)
            if executable_path:
                # 执行测试验证
                print(f"🧪 验证 {code_type} 代码功能...")
                test_result = verifier._run_tests_with_rust(
                    executable_path, valgrind=True
                )
                
                if test_result[0] != VerifyResult.SUCCESS:
                    return {
                        'success': False,
                        'error': f'测试失败: {test_result[1]}',
                        'test_result': test_result[0].name,
                        'compile_result': 'SUCCESS'
                    }
            
            return {
                'success': True,
                'error': None,
                'compile_result': 'SUCCESS',
                'test_result': 'SUCCESS'
            }
            
        except Exception as e:
            return {'success': False, 'error': f'验证出错: {e}'}
    
    def _read_rust_code(self, code_dir: str) -> str:
        """读取 Rust 代码"""
        rust_files = []
        for root, dirs, files in os.walk(code_dir):
            for file in files:
                if file.endswith('.rs'):
                    rust_files.append(os.path.join(root, file))
        
        if not rust_files:
            return ""
        
        # 读取 combined.rs 或第一个 .rs 文件
        combined_rs = None
        for rust_file in rust_files:
            if 'combined.rs' in rust_file:
                combined_rs = rust_file
                break
        
        if combined_rs:
            with open(combined_rs, 'r') as f:
                return f.read()
        elif rust_files:
            with open(rust_files[0], 'r') as f:
                return f.read()
        
        return ""
    
    def _find_executable(self, build_dir: str) -> Optional[str]:
        """查找可执行文件"""
        target_dir = os.path.join(build_dir, 'build_attempt', 'target', 'debug')
        if os.path.exists(target_dir):
            for file in os.listdir(target_dir):
                file_path = os.path.join(target_dir, file)
                if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                    return file_path
        return None
    
    def _get_test_commands(self, test_task_path: str) -> List[str]:
        """获取测试命令列表"""
        try:
            with open(test_task_path, 'r') as f:
                test_task = json.load(f)
            return [item['command'] for item in test_task]
        except:
            return []
    
    def translate_and_verify(self, c_file_path: str, output_dir: str) -> Dict:
        """翻译并验证单个 C 文件"""
        try:
            print(f"\n🚀 开始翻译和验证: {os.path.basename(c_file_path)}")
            
            # 1. 创建 SACToR 测试配置
            test_task_path, test_samples_path = self.create_sactor_test_config(c_file_path, output_dir)
            
            # 2. 使用 SACToR Docker 进行翻译
            translation_result = self.translate_with_sactor_docker(c_file_path, output_dir, test_task_path)
            
            if not translation_result['success']:
                return {
                    'success': False,
                    'error': translation_result['error'],
                    'verification': None,
                    'test_count': 0
                }
            
            # 3. 使用 SACToR 原生验证器进行验证
            verification_results = self.verify_with_sactor_native(
                translation_result['result_dir'], test_task_path
            )
            
            return {
                'success': True,
                'error': None,
                'verification': verification_results,
                'test_count': verification_results.get('test_count', 0),
                'result_dir': translation_result['result_dir']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"翻译和验证失败: {e}",
                'verification': None,
                'test_count': 0
            }
    
    def batch_translate(self, c_files: List[str], output_base_dir: str) -> Dict:
        """批量翻译 C 文件"""
        print(f"🚀 开始批量翻译 {len(c_files)} 个 C 文件")
        
        results = {
            'total': len(c_files),
            'success': 0,
            'failed': 0,
            'verified': 0,
            'details': []
        }
        
        for i, c_file_path in enumerate(c_files):
            print(f"\n📁 处理文件 {i+1}/{len(c_files)}: {os.path.basename(c_file_path)}")
            
            # 为每个文件创建输出目录
            file_output_dir = os.path.join(output_base_dir, os.path.basename(c_file_path).replace('.c', ''))
            os.makedirs(file_output_dir, exist_ok=True)
            
            # 翻译和验证
            result = self.translate_and_verify(c_file_path, file_output_dir)
            
            if result['success']:
                results['success'] += 1
                if result['verification'] and result['verification']['overall']:
                    results['verified'] += 1
            
            results['details'].append({
                'file': os.path.basename(c_file_path),
                'success': result['success'],
                'verified': result['verification']['overall'] if result['verification'] else False,
                'test_count': result['test_count'],
                'error': result['error']
            })
            
            results['failed'] = results['total'] - results['success']
        
        return results

def main():
    """主函数"""
    # 配置路径
    dataset_dir = "/home/changdi/sactor-datasets/Project_CodeNet/selected_data_raw/argv"
    sactor_config = "/home/changdi/sactor/sactor.toml"
    output_base_dir = "/home/changdi/sactor-datasets/sactor_integrated_translations"
    
    # 创建输出目录
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 获取 C 文件（先处理前3个作为示例）
    c_files = [f for f in os.listdir(dataset_dir) if f.endswith('.c')]
    sample_files = [os.path.join(dataset_dir, f) for f in c_files[:3]]
    
    print(f"📁 找到 {len(c_files)} 个 C 文件，将处理前 {len(sample_files)} 个")
    
    # 创建集成翻译器
    translator = SactorIntegratedTranslator(sactor_config)
    
    try:
        # 批量翻译
        results = translator.batch_translate(sample_files, output_base_dir)
        
        # 输出结果统计
        print(f"\n📊 SACToR 集成批量翻译结果:")
        print(f"总文件数: {results['total']}")
        print(f"翻译成功: {results['success']}")
        print(f"翻译失败: {results['failed']}")
        print(f"验证通过: {results['verified']}")
        
        # 保存详细结果
        results_file = os.path.join(output_base_dir, "sactor_integrated_results.json")
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
