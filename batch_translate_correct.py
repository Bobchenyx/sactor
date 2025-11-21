#!/usr/bin/env python3
"""
使用正确数据目录的 SACToR 批量翻译脚本
- 原始程序: /home/changdi/sactor-datasets/Project_CodeNet/raw_data/
- 测试用例: /home/changdi/sactor-datasets/Project_CodeNet/generated_tests/
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

class CorrectDataTranslator:
    """使用正确数据目录的 SACToR 批量翻译器"""
    
    def __init__(self):
        """初始化翻译器"""
        # 创建临时工作目录
        self.temp_dir = tempfile.mkdtemp(prefix='sactor_correct_')
        print(f"📁 临时工作目录: {self.temp_dir}")
        
        # 正确的数据目录
        self.raw_data_dir = "/home/changdi/sactor-datasets/Project_CodeNet/raw_data"
        self.test_data_dir = "/home/changdi/sactor-datasets/Project_CodeNet/generated_tests"
    
    def __del__(self):
        """清理临时目录"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _get_model_info(self) -> str:
        """获取当前使用的模型信息"""
        try:
            # 读取sactor.toml配置文件
            config_path = "/home/changdi/sactor/sactor.toml"
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    content = f.read()
                    # 查找OpenAI模型配置
                    if 'llm = "OpenAI"' in content:
                        # 查找model配置 - 更精确的匹配
                        import re
                        # 查找[OpenAI]部分下的model配置
                        openai_section = re.search(r'\[OpenAI\](.*?)(?=\[|$)', content, re.DOTALL)
                        if openai_section:
                            model_match = re.search(r'model = "([^"]+)"', openai_section.group(1))
                            if model_match:
                                return model_match.group(1)
                    # 查找其他LLM配置
                    elif 'llm = "AzureOpenAI"' in content:
                        model_match = re.search(r'model = "([^"]+)"', content)
                        if model_match:
                            return f"AzureOpenAI-{model_match.group(1)}"
                    elif 'llm = "DeepSeek"' in content:
                        model_match = re.search(r'model = "([^"]+)"', content)
                        if model_match:
                            return f"DeepSeek-{model_match.group(1)}"
                    elif 'llm = "Anthropic"' in content:
                        model_match = re.search(r'model = "([^"]+)"', content)
                        if model_match:
                            return f"Anthropic-{model_match.group(1)}"
                    elif 'llm = "Google"' in content:
                        model_match = re.search(r'model = "([^"]+)"', content)
                        if model_match:
                            return f"Google-{model_match.group(1)}"
                    elif 'llm = "Ollama"' in content:
                        model_match = re.search(r'model = "([^"]+)"', content)
                        if model_match:
                            return f"Ollama-{model_match.group(1)}"
            return "Unknown"
        except Exception as e:
            print(f"⚠️ 获取模型信息失败: {e}")
            return "Unknown"
    
    def log_translation_result(self, c_file_path: str, result: Dict, output_base_dir: str):
        """记录每个C文件的翻译结果到日志文件"""
        try:
            # 创建日志目录
            log_dir = os.path.join(output_base_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            # 创建日志文件名（基于日期和模型）
            today = datetime.now().strftime("%Y-%m-%d")
            model_name = self._get_model_info().replace('-', '_').replace('.', '_')
            log_file = os.path.join(log_dir, f"translation_log_{today}_{model_name}.json")
            
            # 准备日志条目
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "c_file": os.path.basename(c_file_path),
                "c_file_path": c_file_path,
                "success": result.get('success', False),
                "processing_time": result.get('processing_time', 0),
                "attempts": result.get('attempts', 0),
                "api_cost": result.get('api_cost', {}),
                "test_count": result.get('test_count', 0),
                "verified": result.get('verification', {}).get('overall', False) if result.get('verification') else False,
                "error": result.get('error', None),
                "model": self._get_model_info()
            }
            
            # 读取现有日志或创建新日志
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
            else:
                log_data = {
                    "session_info": {
                        "start_time": datetime.now().isoformat(),
                        "output_base_dir": output_base_dir
                    },
                    "translations": []
                }
            
            # 添加新条目
            log_data["translations"].append(log_entry)
            log_data["session_info"]["last_update"] = datetime.now().isoformat()
            
            # 保存日志
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            # 同时创建CSV格式的日志（便于分析）
            csv_log_file = os.path.join(log_dir, f"translation_log_{today}_{model_name}.csv")
            
            # 检查CSV文件是否存在，如果不存在则创建标题行
            if not os.path.exists(csv_log_file):
                with open(csv_log_file, 'w') as f:
                    f.write("timestamp,c_file,success,processing_time,attempts,api_cost_total,test_count,verified,error,model\n")
            
            # 追加CSV条目
            with open(csv_log_file, 'a') as f:
                api_cost_total = log_entry["api_cost"].get("total_cost", 0) if log_entry["api_cost"] else 0
                error_str = str(log_entry["error"]).replace(',', ';').replace('\n', ' ') if log_entry["error"] else ""
                model_str = str(log_entry["model"]).replace(',', ';').replace('\n', ' ') if log_entry["model"] else "Unknown"
                f.write(f"{log_entry['timestamp']},{log_entry['c_file']},{log_entry['success']},{log_entry['processing_time']:.2f},{log_entry['attempts']},{api_cost_total:.4f},{log_entry['test_count']},{log_entry['verified']},{error_str},{model_str}\n")
            
            print(f"📝 日志已保存: {log_file}")
            
        except Exception as e:
            print(f"⚠️ 日志保存失败: {e}")
    
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
            print(f"✅ 加载了 {len(test_samples)} 个测试用例")
            return test_samples
        except Exception as e:
            print(f"❌ 加载测试用例失败: {e}")
            return []
    
    def create_test_config(self, c_file_path: str, output_dir: str) -> tuple[str, str, bool]:
        """创建测试配置 - 只处理有对应测试用例的文件"""
        c_filename = os.path.basename(c_file_path)
        
        # 查找对应的测试用例（现在肯定存在，因为已经筛选过了）
        test_file_path = self.find_corresponding_test(c_file_path)
        
        if not test_file_path:
            raise ValueError(f"没有找到对应的测试用例: {c_file_path}")
        
        # 使用预生成的测试用例 - 直接使用绝对路径，不复制
        print(f"🎯 使用预生成测试用例: {os.path.basename(test_file_path)}")
        test_samples_path = test_file_path  # 直接使用原始路径
        used_pregen = True
        
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
    
    def estimate_api_cost(self, c_file_path: str, attempts: int) -> Dict:
        """估算API成本"""
        try:
            # 读取C文件内容来估算token数量
            with open(c_file_path, 'r') as f:
                c_content = f.read()
            
            # 简单估算：每个字符约等于0.75个token（英文）
            input_tokens = len(c_content) * 0.75
            
            # 估算输出：假设每次尝试生成约2倍输入长度的Rust代码
            output_tokens_per_attempt = input_tokens * 2
            
            # 如果attempts为0，说明没有进行翻译尝试，可能是直接成功或其他原因
            # 检查是否有llm_stat.json文件来获取真实的API调用信息
            # 正确的路径转换：从 raw_data 转换到 test 目录
            if '/raw_data/' in c_file_path:
                # 从 /home/changdi/sactor-datasets/Project_CodeNet/raw_data/argv/s997395205.c
                # 转换为 /home/changdi/sactor/test/argv/s997395205/llm_stat.json
                relative_path = c_file_path.replace('/home/changdi/sactor-datasets/Project_CodeNet/raw_data/', '')
                test_dir_path = os.path.join('/home/changdi/sactor/test', relative_path.replace('.c', ''))
                llm_stat_path = os.path.join(test_dir_path, "llm_stat.json")
            else:
                llm_stat_path = None
                
            if llm_stat_path and os.path.exists(llm_stat_path):
                try:
                    with open(llm_stat_path, 'r') as f:
                        llm_stat = json.load(f)
                    total_queries = llm_stat.get('total_queries', 0)
                    if total_queries > 0:
                        attempts = total_queries
                        print(f"📊 从llm_stat.json获取到真实API调用次数: {attempts}")
                except Exception as e:
                    print(f"⚠️ 读取llm_stat.json失败: {e}")
            
            if attempts == 0:
                # 假设至少进行了一次成功的翻译
                attempts = 1
            
            # 总token估算
            total_input_tokens = input_tokens * attempts
            total_output_tokens = output_tokens_per_attempt * attempts
            
            # OpenAI GPT-4o定价 (2025年最新)
            # Input: $2.50 per 1M tokens = $0.0025 per 1K tokens
            # Output: $10.00 per 1M tokens = $0.01 per 1K tokens
            input_cost = (total_input_tokens / 1000) * 0.0025
            output_cost = (total_output_tokens / 1000) * 0.01
            total_cost = input_cost + output_cost
            
            return {
                'input_tokens': int(total_input_tokens),
                'output_tokens': int(total_output_tokens),
                'input_cost': input_cost,
                'output_cost': output_cost,
                'total_cost': total_cost,
                'cost_per_attempt': total_cost / attempts if attempts > 0 else total_cost,
                'estimated_attempts': attempts if attempts > 0 else 1
            }
            
        except Exception as e:
            return {
                'input_tokens': 0,
                'output_tokens': 0,
                'input_cost': 0,
                'output_cost': 0,
                'total_cost': 0,
                'cost_per_attempt': 0,
                'estimated_attempts': 0,
                'error': str(e)
            }
    
    def translate_with_sactor_docker(self, c_file_path: str, output_dir: str, test_task_path: str) -> Dict:
        """使用 SACToR Docker 进行翻译 - 直接使用绝对路径"""
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
            
            # 使用较长的超时时间，显示输出
            print(f"🚀 执行SACToR Docker命令...")
            result = subprocess.run(cmd, text=True, timeout=600)
            
            # 估算API成本（会尝试从llm_stat.json获取真实attempts）
            api_cost = self.estimate_api_cost(c_file_path, 0)
            attempts = api_cost.get('estimated_attempts', 0)
            
            # 尝试从输出中提取尝试次数信息作为备用
            output_text = (result.stdout or "") + (result.stderr or "")
            
            # 查找尝试次数相关的信息
            if "Attempt" in output_text or "attempt" in output_text:
                output_attempts = output_text.lower().count("attempt")
                if output_attempts > attempts:
                    attempts = output_attempts
            
            # 查找 MAX_ATTEMPTS_EXCEEDED 错误
            if "MAX_ATTEMPTS_EXCEEDED" in output_text:
                attempts = 20  # 从配置文件中读取的最大尝试次数
                # 重新计算API成本
                api_cost = self.estimate_api_cost(c_file_path, attempts)
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f"SACToR Docker 翻译失败: {result.stderr[:500]}...",
                    'result_dir': None,
                    'attempts': attempts,
                    'api_cost': api_cost
                }
            
            return {
                'success': True,
                'error': None,
                'result_dir': os.path.join(output_dir, "result"),
                'attempts': attempts,
                'api_cost': api_cost
            }
            
        except subprocess.TimeoutExpired:
            # 超时时也估算成本
            api_cost = self.estimate_api_cost(c_file_path, 20)
            return {
                'success': False,
                'error': "SACToR Docker 翻译超时 (10分钟)",
                'result_dir': None,
                'attempts': 20,  # 超时通常意味着达到了最大尝试次数
                'api_cost': api_cost
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"SACToR Docker 翻译出错: {e}",
                'result_dir': None,
                'attempts': 0,
                'api_cost': {'total_cost': 0, 'error': str(e)}
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
            
            # 计算测试数量 - 从多个可能的位置查找test_samples.json
            test_count = 0
            possible_test_paths = [
                os.path.join(result_dir, "..", "test_samples.json"),
                os.path.join(result_dir, "test_samples.json"),
                os.path.join(os.path.dirname(result_dir), "test_samples.json")
            ]
            
            for test_samples_path in possible_test_paths:
                if os.path.exists(test_samples_path):
                    try:
                        with open(test_samples_path, 'r') as f:
                            test_samples = json.load(f)
                        # 过滤掉空的测试用例
                        if isinstance(test_samples, list):
                            test_count = len([t for t in test_samples if t])  # 过滤空元素
                        else:
                            test_count = len(test_samples) if test_samples else 0
                        break
                    except Exception as e:
                        print(f"⚠️ 读取测试用例失败 {test_samples_path}: {e}")
                        continue
            
            # 如果还是找不到，尝试从test_task.json推断
            if test_count == 0:
                test_task_path = os.path.join(result_dir, "..", "test_task.json")
                if os.path.exists(test_task_path):
                    try:
                        with open(test_task_path, 'r') as f:
                            test_tasks = json.load(f)
                        if isinstance(test_tasks, list):
                            test_count = len([t for t in test_tasks if t])  # 过滤空元素
                        else:
                            test_count = len(test_tasks) if test_tasks else 0
                    except Exception as e:
                        print(f"⚠️ 读取测试任务失败 {test_task_path}: {e}")
            
            verification_results['test_count'] = test_count
            
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
            print(f"🎯 正确数据翻译: {os.path.basename(c_file_path)}")
            
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
                    'processing_time': time.time() - start_time,
                    'attempts': translation_result.get('attempts', 0),
                    'api_cost': translation_result.get('api_cost', {})
                }
            
            # 3. 验证翻译结果
            verification_results = self.verify_translation_result(translation_result['result_dir'])
            
            return {
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
            
        except Exception as e:
            return {
                'success': False,
                'error': f"翻译失败: {e}",
                'verification': None,
                'test_count': 0,
                'used_pregen': False,
                'processing_time': time.time() - start_time,
                'attempts': 0,
                'api_cost': {'total_cost': 0, 'error': str(e)}
            }
    
    def batch_translate(self, output_base_dir: str, max_files: int = None) -> Dict:
        """批量翻译 - 只处理有对应测试用例的 C 文件"""
        all_c_files = []
        skipped_files = []
        
        # 收集有对应测试用例的 C 文件
        for subdir in ["argv", "scanf"]:
            subdir_path = os.path.join(self.raw_data_dir, subdir)
            if os.path.exists(subdir_path):
                c_files = [os.path.join(subdir_path, f) for f in os.listdir(subdir_path) if f.endswith('.c')]
                
                for c_file in c_files:
                    # 检查是否有对应的测试用例
                    test_file = self.find_corresponding_test(c_file)
                    if test_file:
                        all_c_files.append(c_file)
                    else:
                        skipped_files.append(c_file)
        
        print(f"🎯 筛选结果:")
        print(f"   - 有测试用例的 C 文件: {len(all_c_files)} 个")
        print(f"   - 跳过没有测试用例的文件: {len(skipped_files)} 个")
        
        # 限制处理文件数量（如果指定）
        if max_files is not None and len(all_c_files) > max_files:
            all_c_files = all_c_files[:max_files]
            print(f"⚠️ 限制处理前 {max_files} 个文件")
        
        total_files = len(all_c_files)
        print(f"🚀 开始正确数据批量翻译 {total_files} 个 C 文件")
        
        results = {
            'total': total_files,
            'success': 0,
            'failed': 0,
            'verified': 0,
            'skipped': len(skipped_files),
            'total_processing_time': 0,
            'total_attempts': 0,
            'total_api_cost': 0,
            'avg_processing_time': 0,
            'avg_attempts': 0,
            'avg_api_cost': 0,
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
            
            # 记录翻译结果到日志
            self.log_translation_result(c_file_path, result, output_base_dir)
            
            if result['success']:
                results['success'] += 1
                if result['verification'] and result['verification']['overall']:
                    results['verified'] += 1
            
            # 统计处理时间、尝试次数和API成本
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
                'processing_time': processing_time,
                'attempts': attempts,
                'api_cost': api_cost,
                'error': result['error']
            })
            
            results['failed'] = results['total'] - results['success']
            
            # 每处理 10 个文件保存一次进度
            if (i + 1) % 10 == 0:
                self._save_progress(results, output_base_dir, i + 1)
                print(f"📈 进度统计: 处理时间 {processing_time:.1f}s, 尝试次数 {attempts}, API成本 ${total_cost:.4f}")
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        # 计算平均处理时间、平均尝试次数和平均API成本
        if results['total'] > 0:
            results['avg_processing_time'] = results['total_processing_time'] / results['total']
            results['avg_attempts'] = results['total_attempts'] / results['total']
            results['avg_api_cost'] = results['total_api_cost'] / results['total']
        
        return results
    
    def _save_progress(self, results: Dict, output_base_dir: str, processed_count: int):
        """保存进度"""
        progress_file = os.path.join(output_base_dir, f"progress_{processed_count}.json")
        with open(progress_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 进度已保存: {processed_count}/{results['total']} 文件")

def main():
    """主函数"""
    # 获取模型信息
    translator = CorrectDataTranslator()
    model_name = translator._get_model_info().replace('-', '_').replace('.', '_')
    
    # 配置路径 - 包含模型名称
    output_base_dir = f"/home/changdi/sactor/test_{model_name}"
    
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
    
    # 创建翻译器
    translator = CorrectDataTranslator()
    
    try:
        # 批量翻译
        results = translator.batch_translate(output_base_dir, max_files=None)
        
        # 输出结果统计
        print(f"\n📊 SACToR 批量翻译结果 (仅处理有测试用例的文件):")
        print(f"处理文件数: {results['total']}")
        print(f"跳过文件数: {results['skipped']}")
        print(f"翻译成功: {results['success']}")
        print(f"翻译失败: {results['failed']}")
        print(f"验证通过: {results['verified']}")
        print(f"总处理时间: {results['duration']:.2f} 秒")
        print(f"总尝试次数: {results['total_attempts']}")
        print(f"总API成本: ${results['total_api_cost']:.4f}")
        print(f"平均处理时间: {results['avg_processing_time']:.2f} 秒/文件")
        print(f"平均尝试次数: {results['avg_attempts']:.1f} 次/文件")
        print(f"平均API成本: ${results['avg_api_cost']:.4f}/文件")
        print(f"成功率: {results['success']/results['total']*100:.1f}%")
        print(f"验证率: {results['verified']/results['total']*100:.1f}%")
        
        # 保存详细结果
        results_file = os.path.join(output_base_dir, "sactor_correct_results.json")
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
