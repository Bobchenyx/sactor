#!/usr/bin/env python3
"""
使用 LLM 生成的测试用例进行批量翻译
- 原始程序: /home/changdi/sactor-datasets/Project_CodeNet/raw_data/
- LLM生成的测试用例: /home/changdi/sactor/llm_generated_tests/
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
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import argparse

class LLMTestTranslator:
    """使用 LLM 生成的测试用例进行批量翻译"""
    
    def __init__(self, max_workers: int = 4, output_base_dir: str = None):
        """初始化翻译器"""
        self.temp_dir = tempfile.mkdtemp(prefix='sactor_llm_test_')
        self.max_workers = max_workers
        self.lock = threading.Lock()
        
        # 数据目录
        self.codenet_data_dir = "/home/changdi/CodeNet/Project_CodeNet/data"
        
        # 查找最新的测试生成目录
        sactor_dir = "/home/changdi/sactor"
        test_gen_dirs = [d for d in os.listdir(sactor_dir) if d.startswith('test_generation_')]
        if test_gen_dirs:
            # 选择最新的
            test_gen_dirs.sort(reverse=True)
            self.llm_test_dir = os.path.join(sactor_dir, test_gen_dirs[0])
            print(f"📁 使用测试目录: {self.llm_test_dir}")
        else:
            # 回退到默认目录
            self.llm_test_dir = "/home/changdi/sactor/llm_generated_tests"
            print(f"⚠️ 未找到 test_generation_* 目录，使用默认: {self.llm_test_dir}")
        
        # 统计计数器（用于计算准确率）
        self.success_count = 0
        self.total_count = 0
        
        # 日志文件路径
        if output_base_dir:
            log_dir = os.path.join(output_base_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            self.csv_log_file = os.path.join(log_dir, f"translation_log.csv")
            # 创建 CSV 表头
            with open(self.csv_log_file, 'w') as f:
                f.write("timestamp,c_file,success,processing_time,test_count,verified,success_rate,error\n")
        else:
            self.csv_log_file = None
        
        print(f"📁 临时工作目录: {self.temp_dir}")
        print(f"📁 CodeNet 数据目录: {self.codenet_data_dir}")
        print(f"🔧 并行处理线程数: {self.max_workers}")
        if self.csv_log_file:
            print(f"📝 CSV 日志文件: {self.csv_log_file}")
    
    def __del__(self):
        """清理临时目录"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _get_model_info(self) -> str:
        """获取当前使用的模型信息"""
        try:
            config_path = "/home/changdi/sactor/sactor.toml"
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    content = f.read()
                    import re
                    
                    # 查找当前使用的LLM
                    llm_match = re.search(r'llm = "([^"]+)"', content)
                    if llm_match:
                        llm_type = llm_match.group(1)
                        
                        # 根据LLM类型查找对应的model配置
                        section_match = re.search(rf'\[{llm_type}\](.*?)(?=\[|$)', content, re.DOTALL)
                        if section_match:
                            model_match = re.search(r'model = "([^"]+)"', section_match.group(1))
                            if model_match:
                                return f"{llm_type}-{model_match.group(1)}"
                    
            return "Unknown"
        except Exception as e:
            print(f"⚠️ 获取模型信息失败: {e}")
            return "Unknown"
    
    def find_c_file_by_name(self, c_filename: str) -> Optional[str]:
        """根据文件名在 CodeNet 中查找对应的 C 文件"""
        # 遍历所有问题目录查找
        for item in os.listdir(self.codenet_data_dir):
            problem_dir = os.path.join(self.codenet_data_dir, item)
            if os.path.isdir(problem_dir) and item.startswith('p'):
                c_dir = os.path.join(problem_dir, 'C')
                c_file_path = os.path.join(c_dir, c_filename)
                if os.path.exists(c_file_path):
                    return c_file_path
        return None
    
    def collect_files_to_translate(self) -> List[tuple]:
        """收集所有有 LLM 测试的文件"""
        files_to_translate = []
        
        # 遍历 llm_generated_tests 目录中的所有测试文件
        if not os.path.exists(self.llm_test_dir):
            print(f"⚠️ 测试目录不存在: {self.llm_test_dir}")
            return []
        
        for filename in os.listdir(self.llm_test_dir):
            if filename.endswith('_test_samples.json'):
                # 提取 C 文件名
                c_name = filename.replace('_test_samples.json', '')
                c_filename = c_name + '.c'
                
                # 查找测试任务文件
                test_samples_path = os.path.join(self.llm_test_dir, filename)
                test_task_path = os.path.join(self.llm_test_dir, f"{c_name}_test_task.json")
                
                if not os.path.exists(test_task_path):
                    continue
                
                # 在 CodeNet 中查找对应的 C 文件
                c_file_path = self.find_c_file_by_name(c_filename)
                if c_file_path:
                    files_to_translate.append((c_file_path, test_samples_path, test_task_path))
        
        return files_to_translate
    
    def fix_test_task_paths(self, test_task_path: str, test_samples_path: str) -> str:
        """修正 test_task.json 中的路径，返回修正后的临时文件路径"""
        with open(test_task_path, 'r') as f:
            test_tasks = json.load(f)
        
        # 获取文件名
        test_samples_basename = os.path.basename(test_samples_path)
        
        # 修正每个命令中的路径
        modified = False
        for task in test_tasks:
            if 'command' in task:
                cmd = task['command']
                # 将任何绝对路径替换为相对路径
                # 匹配 /app/output/xxx_test_samples.json 或其他绝对路径
                import re
                new_cmd = re.sub(r'/[^\s]+_test_samples\.json', f'./{test_samples_basename}', cmd)
                if cmd != new_cmd:
                    modified = True
                task['command'] = new_cmd
        
        if modified:
            print(f"   ℹ️  修正了 test_task.json 中的路径: /app/output/... → ./{test_samples_basename}")
        
        # 保存到临时目录
        import tempfile
        temp_file = os.path.join(tempfile.gettempdir(), f'fixed_{os.path.basename(test_task_path)}')
        with open(temp_file, 'w') as f:
            json.dump(test_tasks, f, indent=2)
        
        return temp_file
    
    def translate_single_file(self, c_file_path: str, test_samples_path: str, test_task_path: str, output_base_dir: str) -> Dict:
        """翻译单个C文件"""
        start_time = time.time()
        c_filename = os.path.basename(c_file_path)
        
        try:
            # 打印文件信息
            print(f"\n🔍 准备翻译: {c_filename}")
            print(f"   C 文件路径: {c_file_path}")
            print(f"   测试样本: {test_samples_path}")
            print(f"   测试任务: {test_task_path}")
            
            # 自动修正 test_task.json 中的路径
            fixed_test_task_path = self.fix_test_task_paths(test_task_path, test_samples_path)
            print(f"   修正后的测试任务: {fixed_test_task_path}")
            
            # 读取测试用例数量
            with open(test_samples_path, 'r') as f:
                test_samples = json.load(f)
            test_count = len(test_samples)
            print(f"   测试用例数: {test_count}")
            
            # 创建输出目录
            c_name = c_filename.replace('.c', '')
            file_output_dir = os.path.join(output_base_dir, c_name)
            os.makedirs(file_output_dir, exist_ok=True)
            
            # 构建Docker命令 - 需要同时挂载 C 文件、测试目录和结果目录
            sactor_config = "/home/changdi/sactor/sactor.toml"
            fixed_test_task_dir = os.path.dirname(fixed_test_task_path)
            
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{sactor_config}:/app/sactor.toml",
                "-v", f"{c_file_path}:/tmp/test_c/{c_filename}",  # 挂载单个 C 文件
                "-v", f"{test_samples_path}:/tmp/test_task/{os.path.basename(test_samples_path)}",  # 挂载 test_samples
                "-v", f"{fixed_test_task_path}:/tmp/test_task/{os.path.basename(fixed_test_task_path)}",  # 挂载修正后的 test_task
                "-v", f"{file_output_dir}:/tmp/result",
                "sactor", "translate",
                f"/tmp/test_c/{c_filename}",
                f"/tmp/test_task/{os.path.basename(fixed_test_task_path)}",
                "--result-dir", "/tmp/result",
                "--type", "bin"
            ]
            
            print(f"   Docker 命令: {' '.join(cmd)}")
            print(f"\n▶️  开始翻译...\n")
            print("=" * 80)
            
            # 运行翻译 (2分钟超时) - 不捕获输出，直接实时显示
            result = subprocess.run(cmd, timeout=600)
            
            processing_time = time.time() - start_time
            print("=" * 80)
            print(f"\n⏱️  翻译耗时: {processing_time:.2f} 秒")
            
            # 清理临时文件
            if os.path.exists(fixed_test_task_path):
                os.remove(fixed_test_task_path)
            
            if result.returncode == 0:
                # 检查翻译结果 - 直接在 file_output_dir 中
                unidiomatic_dir = os.path.join(file_output_dir, "translated_code_unidiomatic")
                idiomatic_dir = os.path.join(file_output_dir, "translated_code_idiomatic")
                
                verification = {
                    'unidiomatic': os.path.exists(unidiomatic_dir),
                    'idiomatic': os.path.exists(idiomatic_dir),
                    'overall': os.path.exists(unidiomatic_dir) and os.path.exists(idiomatic_dir)
                }
                
                return {
                    'success': True,
                    'c_file': c_filename,
                    'processing_time': processing_time,
                    'attempts': 1,  # Docker输出中不包含尝试次数
                    'api_cost': {},
                    'test_count': test_count,
                    'verification': verification,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'c_file': c_filename,
                    'error': f"Translation failed with return code: {result.returncode}",
                    'processing_time': processing_time,
                    'attempts': 0,
                    'api_cost': {},
                    'test_count': test_count,
                    'verification': None
                }
                
        except subprocess.TimeoutExpired as e:
            print(f"\n⏱️  超时！翻译时间超过 2 分钟")
            
            # 清理临时文件
            if 'fixed_test_task_path' in locals() and os.path.exists(fixed_test_task_path):
                os.remove(fixed_test_task_path)
            return {
                'success': False,
                'c_file': c_filename,
                'error': "Translation timeout (5 minutes)",
                'processing_time': 600,
                'attempts': 0,
                'api_cost': {},
                'test_count': 0,
                'verification': None
            }
        except Exception as e:
            # 清理临时文件
            if 'fixed_test_task_path' in locals() and os.path.exists(fixed_test_task_path):
                os.remove(fixed_test_task_path)
            return {
                'success': False,
                'c_file': c_filename,
                'error': f"Exception: {str(e)}",
                'processing_time': time.time() - start_time,
                'attempts': 0,
                'api_cost': {},
                'test_count': 0,
                'verification': None
            }
    
    def batch_translate(self, output_base_dir: str, max_files: int = None) -> Dict:
        """批量翻译 - 并行版本"""
        # 收集所有有LLM测试的文件
        print(f"🔍 正在扫描 LLM 生成的测试用例...")
        all_files_to_translate = self.collect_files_to_translate()
        
        print(f"📊 找到 {len(all_files_to_translate)} 个有LLM测试用例的C文件")
        
        # 限制处理文件数量
        if max_files is not None and len(all_files_to_translate) > max_files:
            all_files_to_translate = all_files_to_translate[:max_files]
            print(f"⚠️ 限制处理前 {max_files} 个文件")
        
        results = {
            'total': len(all_files_to_translate),
            'success': 0,
            'failed': 0,
            'verified': 0,
            'total_processing_time': 0,
            'total_attempts': 0,
            'total_api_cost': 0,
            'details': [],
            'start_time': time.time()
        }
        
        processed_count = 0
        
        # 使用线程池进行并行处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.translate_single_file, c_file, test_samples, test_task, output_base_dir): c_file 
                for c_file, test_samples, test_task in all_files_to_translate
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
                            if result.get('verification', {}).get('overall'):
                                results['verified'] += 1
                        else:
                            results['failed'] += 1
                        
                        results['total_processing_time'] += result['processing_time']
                        results['total_attempts'] += result.get('attempts', 0)
                        results['details'].append(result)
                        
                        # 实时保存到 CSV
                        self._log_result_to_csv(result)
                        
                        # 计算当前成功率
                        success_rate = (results['success'] / processed_count * 100)
                        
                        if result['success']:
                            print(f"\n✅ ===== [{processed_count}/{len(all_files_to_translate)}] {result['c_file']}: 翻译成功 ({result['test_count']} 个测试) | 成功率: {success_rate:.1f}% =====\n")
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            print(f"\n❌ ===== [{processed_count}/{len(all_files_to_translate)}] {result['c_file']}: 失败 | 成功率: {success_rate:.1f}% =====")
                            print(f"   错误: {error_msg}\n")
                        
                        # 每处理5个文件保存一次进度
                        if processed_count % 5 == 0:
                            self._save_progress(results, output_base_dir, processed_count)
                            
                except Exception as e:
                    with self.lock:
                        results['failed'] += 1
                        success_rate = (results['success'] / processed_count * 100)
                        print(f"\n❌ [{processed_count}/{len(all_files_to_translate)}] {os.path.basename(c_file_path)}: 异常 | 成功率: {success_rate:.1f}%")
                        print(f"   💥 Exception详情:\n{str(e)}")
                        import traceback
                        print(f"   堆栈跟踪:\n{traceback.format_exc()}")
                        
                        error_result = {
                            'success': False,
                            'c_file': os.path.basename(c_file_path),
                            'error': f"Exception in worker: {str(e)}",
                            'processing_time': 0,
                            'attempts': 0,
                            'api_cost': {},
                            'test_count': 0,
                            'verification': None
                        }
                        results['details'].append(error_result)
                        
                        # 保存到 CSV
                        self._log_result_to_csv(error_result)
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        # 计算平均值
        if results['total'] > 0:
            results['avg_processing_time'] = results['total_processing_time'] / results['total']
            results['avg_attempts'] = results['total_attempts'] / results['total'] if results['total_attempts'] > 0 else 0
        
        return results
    
    def _log_result_to_csv(self, result: Dict):
        """将单个结果实时保存到 CSV（包含准确率）"""
        if not self.csv_log_file:
            return
        
        try:
            with self.lock:
                # 更新计数器
                self.total_count += 1
                if result.get('success', False):
                    self.success_count += 1
                
                # 计算当前准确率
                success_rate = (self.success_count / self.total_count * 100) if self.total_count > 0 else 0
                
                timestamp = datetime.now().isoformat()
                c_file = result.get('c_file', 'unknown')
                success = result.get('success', False)
                processing_time = result.get('processing_time', 0)
                test_count = result.get('test_count', 0)
                verified = result.get('verification', {}).get('overall', False) if result.get('verification') else False
                error = str(result.get('error', '')).replace(',', ';').replace('\n', ' ')[:200]
                
                csv_line = f"{timestamp},{c_file},{success},{processing_time:.2f},{test_count},{verified},{success_rate:.2f},{error}\n"
                
                with open(self.csv_log_file, 'a') as f:
                    f.write(csv_line)
                    f.flush()  # 强制刷新到磁盘
                
                # 调试信息
                print(f"   📊 CSV已保存: {c_file} | 准确率: {success_rate:.1f}%")
        except Exception as e:
            print(f"⚠️ CSV 日志保存失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_progress(self, results: Dict, output_base_dir: str, processed_count: int):
        """保存进度"""
        progress_file = os.path.join(output_base_dir, f"progress_{processed_count}.json")
        with open(progress_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 进度已保存: {processed_count}/{results['total']} 文件")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='使用LLM生成的测试用例进行批量翻译（并行版本）')
    parser.add_argument('--max-files', type=int, default=None, help='最多处理的文件数量（默认：全部）')
    parser.add_argument('--workers', type=int, default=4, help='并行处理的线程数（默认：4）')
    args = parser.parse_args()
    
    print("🚀 SACToR 批量翻译器 (使用LLM生成的测试用例)")
    print("=" * 60)
    print(f"🔧 配置: ")
    print(f"   - 并行线程数: {args.workers}")
    print(f"   - 最多处理文件: {'所有' if args.max_files is None else args.max_files}")
    print("=" * 60)
    
    # 先创建一个临时翻译器来获取模型名称
    temp_translator = LLMTestTranslator(max_workers=1)
    model_name = temp_translator._get_model_info().replace('-', '_').replace('.', '_')
    del temp_translator
    
    # 创建以日期命名的输出目录
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base_dir = f"/home/changdi/sactor/test_translation_{model_name}_{date_str}"
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 创建翻译器（传入 output_base_dir 以初始化日志）
    translator = LLMTestTranslator(max_workers=args.workers, output_base_dir=output_base_dir)
    
    print(f"📁 输出目录: {output_base_dir}")
    print(f"🤖 使用模型: {translator._get_model_info()}")
    
    try:
        # 批量翻译
        results = translator.batch_translate(output_base_dir, max_files=args.max_files)
        
        # 输出结果统计
        print(f"\n📊 批量翻译结果:")
        print(f"处理文件数: {results['total']}")
        print(f"翻译成功: {results['success']}")
        print(f"翻译失败: {results['failed']}")
        print(f"验证通过: {results['verified']}")
        print(f"总处理时间: {results['duration']:.2f} 秒 ({results['duration']/60:.1f} 分钟)")
        print(f"平均处理时间: {results['avg_processing_time']:.2f} 秒/文件")
        if results['total'] > 0:
            print(f"成功率: {results['success']/results['total']*100:.1f}%")
            print(f"验证率: {results['verified']/results['total']*100:.1f}%")
        
        # 保存详细结果
        results_file = os.path.join(output_base_dir, "translation_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 详细结果已保存到:")
        print(f"   JSON: {results_file}")
        print(f"   CSV:  {translator.csv_log_file}")
        
        return results
        
    finally:
        # 清理临时目录
        if hasattr(translator, 'temp_dir') and os.path.exists(translator.temp_dir):
            shutil.rmtree(translator.temp_dir)

if __name__ == "__main__":
    main()

