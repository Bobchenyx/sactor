#!/usr/bin/env python3
"""
从CodeNet数据集中随机抽取文件，使用SACToR批量生成测试
统计时间、调用次数和API成本
"""

import os
import subprocess
import json
import time
import random
import glob
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class RandomTestGenerator:
    def __init__(self):
        self.codenet_base = "/home/changdi/CodeNet/Project_CodeNet/data"
        self.output_dir = "/home/changdi/sactor/random_test_results"
        self.config_file = "/home/changdi/sactor/sactor.toml"
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "test_samples"), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)
        
        # 读取配置信息
        self._load_config()
        
        print(f"📁 输出目录: {self.output_dir}")
        print(f"🤖 当前模型: {self.current_llm} - {self.current_model}")
    
    def _load_config(self):
        """加载配置文件信息"""
        try:
            import toml
            with open(self.config_file, 'r') as f:
                config = toml.load(f)
            
            self.current_llm = config['general']['llm']
            
            if self.current_llm == 'Qwen' and 'Qwen' in config:
                self.current_model = config['Qwen']['model']
            elif self.current_llm == 'OpenAI' and 'OpenAI' in config:
                self.current_model = config['OpenAI']['model']
            else:
                self.current_model = "Unknown"
                
        except Exception as e:
            self.current_llm = "Unknown"
            self.current_model = "Unknown"
            print(f"⚠️ 读取配置失败: {e}")
    
    def find_c_files(self) -> List[str]:
        """查找所有C文件"""
        pattern = os.path.join(self.codenet_base, "*", "C", "*.c")
        c_files = glob.glob(pattern)
        print(f"🔍 找到 {len(c_files)} 个C文件")
        return c_files
    
    def analyze_c_file(self, c_file_path: str) -> Dict:
        """分析C文件，确定程序类型"""
        try:
            with open(c_file_path, 'r') as f:
                content = f.read()
            
            analysis = {
                'file_path': c_file_path,
                'file_size': len(content),
                'has_argv': 'argv[' in content and 'argc' in content,
                'has_scanf': 'scanf(' in content,
                'has_main': 'main(' in content,
                'program_type': 'unknown'
            }
            
            if analysis['has_argv']:
                analysis['program_type'] = 'argv'
            elif analysis['has_scanf']:
                analysis['program_type'] = 'scanf'
            elif analysis['has_main']:
                analysis['program_type'] = 'main_only'
            
            return analysis
            
        except Exception as e:
            return {
                'file_path': c_file_path,
                'error': str(e),
                'program_type': 'error'
            }
    
    def generate_test_for_file(self, c_file_path: str, num_tests: int = 10) -> Dict:
        """为单个C文件生成测试用例"""
        c_filename = os.path.basename(c_file_path)
        c_name = c_filename.replace('.c', '')
        
        # 分析文件
        analysis = self.analyze_c_file(c_file_path)
        
        if analysis.get('error'):
            return {
                "success": False,
                "error": f"File analysis failed: {analysis['error']}",
                "file_info": analysis
            }
        
        # 确定程序类型和输入方式
        if analysis['program_type'] == 'argv':
            feed_mode = "--feed-as-args"
        elif analysis['program_type'] == 'scanf':
            feed_mode = "--feed-as-stdin"
        else:
            # 尝试argv模式作为默认
            feed_mode = "--feed-as-args"
        
        # 输出文件路径
        output_test_samples = os.path.join(self.output_dir, "test_samples", f"{c_name}_test_samples.json")
        output_test_task = os.path.join(self.output_dir, "test_samples", f"{c_name}_test_task.json")
        
        # 构建Docker命令
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{os.path.dirname(c_file_path)}:/data",
            "-v", f"{self.config_file}:/app/sactor_1.toml",
            "-v", f"{self.output_dir}:/app/output",
            "sactor", "generate-tests",
            f"/data/{c_filename}",
            str(num_tests),
            "--type", "bin",
            feed_mode,
            "--out-test-sample-path", f"/app/output/test_samples/{c_name}_test_samples.json",
            "--out-test-task-path", f"/app/output/test_samples/{c_name}_test_task.json"
        ]
        
        print(f"🚀 生成测试用例: {c_filename}")
        print(f"   程序类型: {analysis['program_type']}")
        print(f"   文件大小: {analysis['file_size']} 字符")
        print(f"   输入方式: {feed_mode}")
        
        start_time = time.time()
        api_calls = 0
        api_cost = 0.0
        
        # 预先估算API调用次数（在try之前，避免超时时未定义）
        estimated_calls = num_tests // 5 + 1  # 每5个测试用例大约1次API调用
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            processing_time = time.time() - start_time
            
            # 从输出中提取信息
            output_text = result.stdout + result.stderr
            
            # 使用API成本估算
            # 假设每次调用平均使用1000输入tokens + 500输出tokens
            input_tokens = estimated_calls * 1000
            output_tokens = estimated_calls * 500
            
            # 根据模型计算成本
            if self.current_llm == 'Qwen':
                # Qwen3-coder-plus定价 (2025年)
                # Input: ¥0.008/1K tokens, Output: ¥0.02/1K tokens
                api_cost = (input_tokens / 1000) * 0.008 + (output_tokens / 1000) * 0.02
            elif self.current_llm == 'OpenAI':
                # GPT-5定价 (2025年)
                # Input: $0.0025/1K tokens, Output: $0.01/1K tokens
                api_cost = (input_tokens / 1000) * 0.0025 + (output_tokens / 1000) * 0.01
            else:
                # 默认使用GPT-5定价
                api_cost = (input_tokens / 1000) * 0.0025 + (output_tokens / 1000) * 0.01
            
            if result.returncode == 0:
                # 检查输出文件是否生成
                if os.path.exists(output_test_samples):
                    with open(output_test_samples, 'r') as f:
                        test_samples = json.load(f)
                    
                    return {
                        "success": True,
                        "c_file": c_filename,
                        "file_info": analysis,
                        "test_count": len(test_samples),
                        "processing_time": processing_time,
                        "api_calls": estimated_calls,
                        "api_cost": api_cost,
                        "output_files": {
                            "test_samples": output_test_samples,
                            "test_task": output_test_task
                        },
                        "docker_output": output_text[:500]  # 保存部分输出用于调试
                    }
                else:
                    return {
                        "success": False,
                        "error": "Output file not generated",
                        "processing_time": processing_time,
                        "api_calls": estimated_calls,
                        "api_cost": api_cost,
                        "docker_output": output_text[:500]
                    }
            else:
                return {
                    "success": False,
                    "error": f"Docker command failed: {result.stderr[:200]}",
                    "processing_time": processing_time,
                    "api_calls": estimated_calls,
                    "api_cost": api_cost,
                    "docker_output": output_text[:500]
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Timeout (120 seconds)",
                "processing_time": 120,
                "api_calls": estimated_calls,
                "api_cost": api_cost
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception: {str(e)}",
                "processing_time": time.time() - start_time,
                "api_calls": estimated_calls,
                "api_cost": api_cost
            }
    
    def random_sample_and_generate(self, sample_size: int = 20, tests_per_file: int = 10) -> Dict:
        """随机抽样并生成测试用例"""
        print(f"🎲 随机抽样 {sample_size} 个文件进行测试生成")
        
        # 查找所有C文件
        all_c_files = self.find_c_files()
        
        if len(all_c_files) == 0:
            return {"error": "No C files found"}
        
        # 随机抽样
        if len(all_c_files) > sample_size:
            sampled_files = random.sample(all_c_files, sample_size)
        else:
            sampled_files = all_c_files
            sample_size = len(all_c_files)
        
        print(f"📊 抽样结果: {sample_size} 个文件")
        
        results = {
            'sample_size': sample_size,
            'tests_per_file': tests_per_file,
            'total_files': len(sampled_files),
            'llm_provider': self.current_llm,
            'model_name': self.current_model,
            'success': 0,
            'failed': 0,
            'total_tests_generated': 0,
            'total_processing_time': 0,
            'total_api_calls': 0,
            'total_api_cost': 0,
            'program_types': {},
            'details': [],
            'start_time': time.time()
        }
        
        for i, c_file_path in enumerate(sampled_files):
            print(f"\n📁 处理文件 {i+1}/{len(sampled_files)}: {os.path.basename(c_file_path)}")
            
            result = self.generate_test_for_file(c_file_path, tests_per_file)
            
            if result['success']:
                results['success'] += 1
                results['total_tests_generated'] += result['test_count']
                print(f"✅ 成功生成 {result['test_count']} 个测试用例")
            else:
                results['failed'] += 1
                print(f"❌ 失败: {result['error']}")
            
            # 统计信息
            results['total_processing_time'] += result['processing_time']
            results['total_api_calls'] += result['api_calls']
            results['total_api_cost'] += result['api_cost']
            
            # 程序类型统计
            program_type = result.get('file_info', {}).get('program_type', 'unknown')
            if program_type not in results['program_types']:
                results['program_types'][program_type] = 0
            results['program_types'][program_type] += 1
            
            results['details'].append(result)
            
            # 每处理5个文件保存一次进度
            if (i + 1) % 5 == 0:
                self._save_progress(results, i + 1)
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        # 计算平均值
        if results['total_files'] > 0:
            results['avg_processing_time'] = results['total_processing_time'] / results['total_files']
            results['avg_api_calls'] = results['total_api_calls'] / results['total_files']
            results['avg_api_cost'] = results['total_api_cost'] / results['total_files']
            results['avg_tests_per_file'] = results['total_tests_generated'] / results['success'] if results['success'] > 0 else 0
        
        return results
    
    def _save_progress(self, results: Dict, processed_count: int):
        """保存进度"""
        progress_file = os.path.join(self.output_dir, "logs", f"progress_{processed_count}.json")
        with open(progress_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 进度已保存: {processed_count}/{results['total_files']} 文件")
    
    def log_translation_result(self, result: Dict):
        """记录翻译结果到日志文件"""
        try:
            log_dir = os.path.join(self.output_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            # 创建日志文件名（基于日期）
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(log_dir, f"random_test_generation_{today}.json")
            csv_log_file = os.path.join(log_dir, f"random_test_generation_{today}.csv")
            
            # 准备日志条目
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "c_file": result.get('c_file', 'unknown'),
                "success": result.get('success', False),
                "processing_time": result.get('processing_time', 0),
                "api_calls": result.get('api_calls', 0),
                "api_cost": result.get('api_cost', 0),
                "test_count": result.get('test_count', 0),
                "program_type": result.get('file_info', {}).get('program_type', 'unknown'),
                "file_size": result.get('file_info', {}).get('file_size', 0),
                "error": result.get('error', None)
            }
            
            # 读取现有日志或创建新日志
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
            else:
                log_data = {
                    "session_info": {
                        "start_time": datetime.now().isoformat(),
                        "output_dir": self.output_dir
                    },
                    "results": []
                }
            
            # 添加新条目
            log_data["results"].append(log_entry)
            log_data["session_info"]["last_update"] = datetime.now().isoformat()
            
            # 保存JSON日志
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            # 检查CSV文件是否存在，如果不存在则创建标题行
            if not os.path.exists(csv_log_file):
                with open(csv_log_file, 'w') as f:
                    f.write("timestamp,c_file,success,processing_time,api_calls,api_cost,test_count,program_type,file_size,error\n")
            
            # 追加CSV条目
            with open(csv_log_file, 'a') as f:
                error_str = str(log_entry["error"]).replace(',', ';').replace('\n', ' ') if log_entry["error"] else ""
                f.write(f"{log_entry['timestamp']},{log_entry['c_file']},{log_entry['success']},{log_entry['processing_time']:.2f},{log_entry['api_calls']},{log_entry['api_cost']:.4f},{log_entry['test_count']},{log_entry['program_type']},{log_entry['file_size']},{error_str}\n")
            
        except Exception as e:
            print(f"⚠️ 日志保存失败: {e}")

def main():
    """主函数"""
    print("🚀 CodeNet 随机测试用例生成器")
    print("=" * 60)
    
    generator = RandomTestGenerator()
    
    try:
        # 随机抽样并生成测试用例
        results = generator.random_sample_and_generate(sample_size=500, tests_per_file=8)
        
        if "error" in results:
            print(f"❌ 错误: {results['error']}")
            return
        
        # 输出结果统计
        print(f"\n📊 随机测试生成结果:")
        print(f"🤖 使用模型: {results['llm_provider']} - {results['model_name']}")
        print(f"抽样文件数: {results['sample_size']}")
        print(f"每文件测试数: {results['tests_per_file']}")
        print(f"生成成功: {results['success']}")
        print(f"生成失败: {results['failed']}")
        print(f"总测试用例数: {results['total_tests_generated']}")
        print(f"总处理时间: {results['duration']:.2f} 秒")
        print(f"总API调用次数: {results['total_api_calls']}")
        print(f"总API成本: ¥{results['total_api_cost']:.4f}")
        print(f"平均处理时间: {results['avg_processing_time']:.2f} 秒/文件")
        print(f"平均API调用: {results['avg_api_calls']:.1f} 次/文件")
        print(f"平均API成本: ¥{results['avg_api_cost']:.4f}/文件")
        print(f"平均测试用例数: {results['avg_tests_per_file']:.1f} 个/文件")
        print(f"成功率: {results['success']/results['total_files']*100:.1f}%")
        
        print(f"\n📈 程序类型统计:")
        for program_type, count in results['program_types'].items():
            percentage = count / results['total_files'] * 100
            print(f"  {program_type}: {count} 个文件 ({percentage:.1f}%)")
        
        # 保存详细结果
        results_file = os.path.join(generator.output_dir, "logs", "random_generation_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 详细结果已保存到: {results_file}")
        print(f"📁 生成的测试用例保存在: {generator.output_dir}/test_samples/")
        print(f"📝 日志文件保存在: {generator.output_dir}/logs/")
        
        return results
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
