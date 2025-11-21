#!/usr/bin/env python3
"""
使用 SACToR 相同验证机制的批量翻译脚本
"""

import os
import subprocess
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from enum import Enum, auto

class VerifyResult(Enum):
    SUCCESS = auto()
    COMPILE_ERROR = auto()
    TEST_ERROR = auto()
    TEST_TIMEOUT = auto()
    CLIPPY_ERROR = auto()
    VALGRIND_ERROR = auto()

class SafetyVerifier:
    """使用 SACToR 相同的安全验证机制"""
    
    def __init__(self, config: dict):
        self.config = config
        self.timeout = config.get('timeout_seconds', 60)
        
    def verify_compilation(self, rust_code_path: str) -> Tuple[VerifyResult, Optional[str]]:
        """验证编译 - 对应 SACToR 的 cargo build 检查"""
        print("🔨 验证编译...")
        
        # 1. 代码格式化检查
        fmt_cmd = ["cargo", "fmt", "--manifest-path", rust_code_path]
        result = subprocess.run(fmt_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return VerifyResult.COMPILE_ERROR, f"格式化失败: {result.stderr}"
        
        # 2. 编译检查
        build_cmd = ["cargo", "build", "--manifest-path", rust_code_path]
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return VerifyResult.COMPILE_ERROR, f"编译失败: {result.stderr}"
        
        print("✅ 编译验证通过")
        return VerifyResult.SUCCESS, None
    
    def verify_clippy(self, rust_code_path: str) -> Tuple[VerifyResult, Optional[str]]:
        """验证 Clippy 静态分析 - 对应 SACToR 的 cargo clippy 检查"""
        print("🔍 验证 Clippy 静态分析...")
        
        # 1. 自动修复
        fix_cmd = ["cargo", "clippy", "--fix", "--allow-no-vcs", "--manifest-path", rust_code_path]
        result = subprocess.run(fix_cmd, capture_output=True, text=True)
        
        # 2. Clippy 检查
        clippy_cmd = ["cargo", "clippy", "--manifest-path", rust_code_path]
        result = subprocess.run(clippy_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # 统计警告和错误
            warnings, errors = self._count_warnings_errors(result.stderr)
            if errors > 0:
                return VerifyResult.CLIPPY_ERROR, f"Clippy 发现 {errors} 个错误"
            elif warnings > 0:
                print(f"⚠️  Clippy 发现 {warnings} 个警告，但编译通过")
        
        print("✅ Clippy 验证通过")
        return VerifyResult.SUCCESS, None
    
    def verify_valgrind(self, executable_path: str, test_inputs: List[str]) -> Tuple[VerifyResult, Optional[str]]:
        """验证 Valgrind 内存检查 - 对应 SACToR 的 valgrind 检查"""
        print("🧪 验证 Valgrind 内存检查...")
        
        valgrind_cmd = [
            'valgrind',
            '--error-exitcode=1',
            '--leak-check=no',
            '--trace-children=yes',
            '--'
        ]
        
        for test_input in test_inputs:
            cmd = valgrind_cmd + [executable_path] + test_input.split()
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=self.timeout
                )
                
                if result.returncode != 0:
                    return VerifyResult.VALGRIND_ERROR, f"Valgrind 发现内存问题: {result.stderr}"
                    
            except subprocess.TimeoutExpired:
                return VerifyResult.TEST_TIMEOUT, f"Valgrind 测试超时"
        
        print("✅ Valgrind 验证通过")
        return VerifyResult.SUCCESS, None
    
    def verify_functionality(self, executable_path: str, test_inputs: List[str]) -> Tuple[VerifyResult, Optional[str]]:
        """验证功能正确性 - 对应 SACToR 的测试用例验证"""
        print("🧪 验证功能正确性...")
        
        for i, test_input in enumerate(test_inputs):
            cmd = [executable_path] + test_input.split()
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=self.timeout
                )
                
                if result.returncode != 0:
                    return VerifyResult.TEST_ERROR, f"测试 {i} 失败: {result.stderr}"
                
                print(f"✅ 测试 {i+1} 通过: {test_input}")
                    
            except subprocess.TimeoutExpired:
                return VerifyResult.TEST_TIMEOUT, f"测试 {i} 超时"
        
        print("✅ 功能验证通过")
        return VerifyResult.SUCCESS, None
    
    def verify_safety(self, rust_code_path: str) -> Tuple[VerifyResult, Optional[str]]:
        """验证代码安全性 - 检查 unsafe 关键字"""
        print("🛡️  验证代码安全性...")
        
        # 读取 Rust 代码文件
        src_dir = os.path.join(os.path.dirname(rust_code_path), "src")
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith('.rs'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        content = f.read()
                        if 'unsafe' in content:
                            return VerifyResult.COMPILE_ERROR, f"发现 unsafe 关键字: {file_path}"
        
        print("✅ 安全性验证通过 (无 unsafe 关键字)")
        return VerifyResult.SUCCESS, None
    
    def _count_warnings_errors(self, clippy_output: str) -> Tuple[int, int]:
        """统计 Clippy 输出中的警告和错误数量"""
        lines = clippy_output.split('\n')
        warnings = sum(1 for line in lines if 'warning:' in line)
        errors = sum(1 for line in lines if 'error:' in line)
        return warnings, errors
    
    def comprehensive_verify(self, rust_code_path: str, executable_path: str, test_inputs: List[str]) -> Dict:
        """综合验证 - 使用 SACToR 相同的验证流程"""
        print(f"\n🔍 开始综合验证: {os.path.basename(rust_code_path)}")
        
        verification_results = {
            'compilation': None,
            'clippy': None,
            'safety': None,
            'functionality': None,
            'valgrind': None,
            'overall': False
        }
        
        # 1. 编译验证
        result, error = self.verify_compilation(rust_code_path)
        verification_results['compilation'] = result == VerifyResult.SUCCESS
        if result != VerifyResult.SUCCESS:
            print(f"❌ 编译验证失败: {error}")
            return verification_results
        
        # 2. 安全性验证
        result, error = self.verify_safety(rust_code_path)
        verification_results['safety'] = result == VerifyResult.SUCCESS
        if result != VerifyResult.SUCCESS:
            print(f"❌ 安全性验证失败: {error}")
            return verification_results
        
        # 3. Clippy 验证
        result, error = self.verify_clippy(rust_code_path)
        verification_results['clippy'] = result == VerifyResult.SUCCESS
        if result != VerifyResult.SUCCESS:
            print(f"❌ Clippy 验证失败: {error}")
            return verification_results
        
        # 4. 功能验证
        result, error = self.verify_functionality(executable_path, test_inputs)
        verification_results['functionality'] = result == VerifyResult.SUCCESS
        if result != VerifyResult.SUCCESS:
            print(f"❌ 功能验证失败: {error}")
            return verification_results
        
        # 5. Valgrind 验证
        result, error = self.verify_valgrind(executable_path, test_inputs)
        verification_results['valgrind'] = result == VerifyResult.SUCCESS
        if result != VerifyResult.SUCCESS:
            print(f"❌ Valgrind 验证失败: {error}")
            return verification_results
        
        # 综合结果
        verification_results['overall'] = all([
            verification_results['compilation'],
            verification_results['safety'],
            verification_results['clippy'],
            verification_results['functionality'],
            verification_results['valgrind']
        ])
        
        if verification_results['overall']:
            print("🎉 所有验证通过！代码安全且功能正确")
        else:
            print("❌ 部分验证失败")
        
        return verification_results

def create_test_task_json(output_dir: str) -> str:
    """创建测试任务文件"""
    test_task = [
        {"command": "echo '10'", "test_id": 0},
        {"command": "echo '123'", "test_id": 1},
        {"command": "echo '456'", "test_id": 2},
        {"command": "echo '999'", "test_id": 3},
        {"command": "echo '0'", "test_id": 4}
    ]
    
    test_task_path = os.path.join(output_dir, "test_task.json")
    with open(test_task_path, 'w') as f:
        json.dump(test_task, f, indent=2)
    
    return test_task_path

def create_cargo_toml(output_dir: str) -> str:
    """创建 Cargo.toml 文件"""
    cargo_content = '''[workspace]

[package]
name = "translated_code"
version = "0.1.0"
edition = "2021"

[dependencies]
'''
    
    cargo_path = os.path.join(output_dir, "Cargo.toml")
    with open(cargo_path, 'w') as f:
        f.write(cargo_content)
    
    return cargo_path

def translate_c_file_with_verification(c_file_path: str, output_dir: str, sactor_config: str, config: dict) -> Dict:
    """翻译单个 C 文件并进行完整验证"""
    try:
        print(f"\n🚀 开始翻译: {os.path.basename(c_file_path)}")
        
        # 创建必要的文件
        test_task_path = create_test_task_json(output_dir)
        cargo_path = create_cargo_toml(output_dir)
        
        # 创建 src 目录
        src_dir = os.path.join(output_dir, "src")
        os.makedirs(src_dir, exist_ok=True)
        
        # 运行 SACToR 翻译
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
        
        print("📝 运行 SACToR 翻译...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            return {
                'success': False,
                'error': f"SACToR 翻译失败: {result.stderr}",
                'verification': None
            }
        
        print("✅ SACToR 翻译完成")
        
        # 查找生成的 Rust 代码
        result_dir = os.path.join(output_dir, "result")
        rust_files = []
        if os.path.exists(result_dir):
            for root, dirs, files in os.walk(result_dir):
                for file in files:
                    if file.endswith('.rs'):
                        rust_files.append(os.path.join(root, file))
        
        if not rust_files:
            return {
                'success': False,
                'error': "未找到生成的 Rust 代码",
                'verification': None
            }
        
        # 复制生成的代码到测试目录
        main_rust_path = None
        for rust_file in rust_files:
            if 'combined.rs' in rust_file:
                main_rust_path = os.path.join(src_dir, "main.rs")
                subprocess.run(["cp", rust_file, main_rust_path])
                break
        
        if not main_rust_path or not os.path.exists(main_rust_path):
            return {
                'success': False,
                'error': "未找到完整的 Rust 代码",
                'verification': None
            }
        
        # 构建项目
        build_cmd = ["cargo", "build", "--manifest-path", cargo_path]
        result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=output_dir)
        
        if result.returncode != 0:
            return {
                'success': False,
                'error': f"构建失败: {result.stderr}",
                'verification': None
            }
        
        # 查找可执行文件
        executable_path = os.path.join(output_dir, "target", "debug", "translated_code")
        if not os.path.exists(executable_path):
            return {
                'success': False,
                'error': "未找到可执行文件",
                'verification': None
            }
        
        # 进行综合验证
        verifier = SafetyVerifier(config)
        test_inputs = ["10", "123", "456", "999", "0"]
        
        verification_results = verifier.comprehensive_verify(
            cargo_path, executable_path, test_inputs
        )
        
        return {
            'success': True,
            'error': None,
            'verification': verification_results,
            'rust_code_path': main_rust_path,
            'executable_path': executable_path
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': "翻译超时",
            'verification': None
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"翻译出错: {e}",
            'verification': None
        }

def main():
    # 配置
    dataset_dir = "/home/changdi/sactor-datasets/Project_CodeNet/selected_data_raw/argv"
    sactor_config = "/home/changdi/sactor/sactor.toml"
    output_base_dir = "/home/changdi/sactor-datasets/verified_translations"
    
    config = {
        'timeout_seconds': 60,
        'max_attempts': 3
    }
    
    # 创建输出目录
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 获取 C 文件
    c_files = [f for f in os.listdir(dataset_dir) if f.endswith('.c')]
    print(f"📁 找到 {len(c_files)} 个 C 文件")
    
    # 批量翻译和验证（先处理前3个作为示例）
    sample_files = c_files[:3]
    
    results = {
        'total': len(sample_files),
        'success': 0,
        'failed': 0,
        'verified': 0,
        'details': []
    }
    
    for c_file in sample_files:
        c_file_path = os.path.join(dataset_dir, c_file)
        
        # 为每个文件创建输出目录
        file_output_dir = os.path.join(output_base_dir, c_file.replace('.c', ''))
        os.makedirs(file_output_dir, exist_ok=True)
        
        # 复制 C 文件
        subprocess.run(["cp", c_file_path, file_output_dir])
        
        # 翻译和验证
        result = translate_c_file_with_verification(c_file_path, file_output_dir, sactor_config, config)
        
        if result['success']:
            results['success'] += 1
            if result['verification'] and result['verification']['overall']:
                results['verified'] += 1
        
        results['details'].append({
            'file': c_file,
            'success': result['success'],
            'verified': result['verification']['overall'] if result['verification'] else False,
            'error': result['error']
        })
        
        results['failed'] = results['total'] - results['success']
    
    # 输出结果统计
    print(f"\n📊 批量翻译和验证结果:")
    print(f"总文件数: {results['total']}")
    print(f"翻译成功: {results['success']}")
    print(f"翻译失败: {results['failed']}")
    print(f"验证通过: {results['verified']}")
    
    # 保存详细结果
    results_file = os.path.join(output_base_dir, "translation_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 详细结果已保存到: {results_file}")
    
    return results

if __name__ == "__main__":
    main()
