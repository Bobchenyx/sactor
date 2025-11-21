#!/usr/bin/env python3
"""
翻译 CodeNet 每题第41到第80个 Accepted 的 C 文件
支持断点续传、进度记录、增量翻译
"""

import os
import json
import csv
import subprocess
import shutil
import tempfile
import threading
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


class CodeNet41To80Translator:
    def __init__(self, workers=10, num_tests=6, resume=True):
        # 路径配置
        self.codenet_data_dir = "/home/changdi/CodeNet/Project_CodeNet/data"
        self.metadata_dir = "/home/changdi/CodeNet/Project_CodeNet/metadata"
        self.json_dir = "/home/changdi/sactor/generated_tests"
        self.output_base_dir = "/home/changdi/sactor/translated_rust_41_to_80"
        
        # 进度文件
        self.progress_file = "/home/changdi/sactor/translation_progress_41_to_80.json"
        self.log_file = "/home/changdi/sactor/translation_log_41_to_80.txt"
        
        # 配置
        self.sactor_docker_image = "sactor"
        self.workers = workers
        self.num_tests = num_tests
        self.resume = resume
        
        # 统计
        self.print_lock = threading.Lock()
        self.total_tasks = 0
        self.completed = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = None
        self.last_report_time = None
        
        # 失败原因统计
        self.fail_reasons = {}
        
        # 进度数据
        self.progress_data = self._load_progress() if resume else {}
        
        os.makedirs(self.output_base_dir, exist_ok=True)
        
        print("=" * 80)
        print("🚀 CodeNet 第41-80批 Accepted C → Rust 翻译工具")
        print("=" * 80)
        print(f"📁 CodeNet数据: {self.codenet_data_dir}")
        print(f"📁 输出目录: {self.output_base_dir}")
        print(f"📝 进度文件: {self.progress_file}")
        print(f"⚙️  并发数: {workers}")
        print(f"🧪 测试数: {num_tests}")
        print(f"🔄 断点续传: {'启用' if resume else '禁用'}")
        print(f"⏭️  跳过策略: 跳过每题前40个Accepted (第1-40批已完成)")
        print(f"📊 翻译范围: 每题第41到第80个Accepted (索引40-79)")
        print("=" * 80)
    
    def _load_progress(self):
        """加载进度文件"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                print(f"✅ 加载进度文件: {len(data.get('completed', []))} 个已完成")
                return data
            except Exception as e:
                print(f"⚠️  加载进度文件失败: {e}")
                return {}
        return {}
    
    def _save_progress(self):
        """保存进度"""
        try:
            progress = {
                'completed': list(self.progress_data.get('completed', set())),
                'failed': list(self.progress_data.get('failed', set())),
                'last_update': datetime.now().isoformat(),
                'statistics': {
                    'total_completed': self.completed,
                    'total_failed': self.failed,
                    'total_skipped': self.skipped
                }
            }
            
            # 原子写入
            temp_file = self.progress_file + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(progress, f, indent=2)
            os.replace(temp_file, self.progress_file)
            
        except Exception as e:
            print(f"⚠️  保存进度失败: {e}")
    
    def _log_message(self, message):
        """记录日志"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except:
            pass
    
    def _print_progress_summary(self):
        """打印进度汇总（需要在 print_lock 内调用）"""
        elapsed = time.time() - self.start_time
        speed = self.completed / elapsed if elapsed > 0 else 0
        total_processed = self.completed + self.failed
        
        # 预估剩余时间
        if speed > 0:
            remaining = self.total_tasks - total_processed
            eta_seconds = remaining / speed
            eta_hours = eta_seconds / 3600
            eta_str = f"{eta_hours:.1f}小时"
        else:
            eta_str = "计算中..."
        
        print("\n" + "=" * 60)
        print("📊 进度汇总")
        print("=" * 60)
        print(f"✅ 成功: {self.completed}")
        print(f"❌ 失败: {self.failed}")
        
        # 显示失败原因统计
        if self.fail_reasons:
            print("   失败原因:")
            for reason, count in sorted(self.fail_reasons.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"   - {reason}: {count} 个")
        
        print(f"⏭️  跳过: {self.skipped}")
        print(f"📊 总进度: {total_processed}/{self.total_tasks} ({total_processed*100//self.total_tasks}%)")
        print(f"⚡ 速度: {speed:.2f} 个/秒")
        print(f"⏱️  已用时: {elapsed/3600:.1f} 小时")
        print(f"⏰ 预计剩余: {eta_str}")
        print("=" * 60 + "\n", flush=True)
    
    def _is_completed(self, task_id):
        """检查任务是否已完成"""
        completed_set = self.progress_data.get('completed', set())
        if not isinstance(completed_set, set):
            completed_set = set(self.progress_data.get('completed', []))
            self.progress_data['completed'] = completed_set
        return task_id in completed_set
    
    def _mark_completed(self, task_id):
        """标记任务完成"""
        if 'completed' not in self.progress_data:
            self.progress_data['completed'] = set()
        elif not isinstance(self.progress_data['completed'], set):
            self.progress_data['completed'] = set(self.progress_data['completed'])
        
        self.progress_data['completed'].add(task_id)
        
        # 每10个任务保存一次进度
        if len(self.progress_data['completed']) % 10 == 0:
            self._save_progress()
    
    def collect_accepted_c_files_41_to_80(self):
        """收集第41到第80个 Accepted 的 C 文件"""
        print("\n🔍 扫描 CodeNet 第41-80批 Accepted C 文件...")
        
        tasks = []
        metadata_files = sorted([f for f in os.listdir(self.metadata_dir) 
                                if f.endswith('.csv') and f.startswith('p')])
        
        total_problems = len(metadata_files)
        processed = 0
        collected_count = 0
        skipped_pre_existing = 0
        
        for metadata_file in metadata_files:
            problem_id = metadata_file.replace('.csv', '')
            metadata_path = os.path.join(self.metadata_dir, metadata_file)
            
            try:
                # 读取 metadata，找到所有 Accepted 的 C 文件
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    accepted_submissions = []
                    
                    for row in reader:
                        if row['language'] == 'C' and row['status'] == 'Accepted':
                            accepted_submissions.append(row['submission_id'])
                
                # 找到该问题的测试 JSON
                json_problem_dir = os.path.join(self.json_dir, problem_id, 'C')
                json_file = None
                
                if os.path.exists(json_problem_dir):
                    json_files = sorted([f for f in os.listdir(json_problem_dir) 
                                       if f.endswith('.json')])
                    if json_files:
                        json_file = os.path.join(json_problem_dir, json_files[0])
                
                # 为第41到第80个 Accepted 的 C 文件创建任务
                # 索引40-79 (Python从0开始，所以第41个是索引40)
                for idx, submission_id in enumerate(accepted_submissions):
                    # 只处理第41-80个 (索引40-79)
                    if idx < 40 or idx >= 80:
                        if idx < 40:
                            skipped_pre_existing += 1
                        continue
                    
                    c_file = os.path.join(self.codenet_data_dir, problem_id, 
                                         'C', f"{submission_id}.c")
                    
                    if not os.path.exists(c_file):
                        continue
                    
                    task_id = f"{problem_id}/{submission_id}"
                    
                    # 检查是否已完成
                    if self.resume and self._is_completed(task_id):
                        self.skipped += 1
                        continue
                    
                    output_dir = os.path.join(self.output_base_dir, problem_id,
                                             'Rust', submission_id)
                    
                    # 检查输出文件是否已存在
                    combined_rs = os.path.join(output_dir, 
                                              'translated_code_unidiomatic', 'combined.rs')
                    
                    if os.path.exists(combined_rs) and os.path.getsize(combined_rs) > 100:
                        self.skipped += 1
                        self._mark_completed(task_id)
                        continue
                    
                    tasks.append({
                        'task_id': task_id,
                        'problem_id': problem_id,
                        'submission_id': submission_id,
                        'c_file': c_file,
                        'json_file': json_file,
                        'output_dir': output_dir
                    })
                    collected_count += 1
                
            except Exception as e:
                self._log_message(f"ERROR: Failed to process {problem_id}: {e}")
                continue
            
            processed += 1
            if processed % 100 == 0:
                print(f"   进度: {processed}/{total_problems} ({processed*100//total_problems}%) "
                      f"- 收集了 {collected_count} 个任务, 跳过 {self.skipped} 个已完成, "
                      f"跳过前40个 {skipped_pre_existing} 个", flush=True)
        
        print("\n✅ 扫描完成:")
        print(f"   - 共收集 {len(tasks)} 个待翻译任务")
        print(f"   - 跳过 {self.skipped} 个已完成任务")
        print(f"   - 跳过 {skipped_pre_existing} 个前40个Accepted文件")
        print(f"   - 覆盖 {total_problems} 个问题")
        
        return tasks
    
    def translate_single_task(self, task):
        """翻译单个任务"""
        task_id = task['task_id']
        c_file = task['c_file']
        json_file = task['json_file']
        output_dir = task['output_dir']
        
        # 如果没有 JSON，跳过
        if not json_file:
            with self.print_lock:
                self.skipped += 1
                if self.skipped % 50 == 0:
                    progress = f"[跳过: {self.skipped}]"
                    print(f"⏭️  {progress} 无JSON，已跳过 {self.skipped} 个", flush=True)
                self._log_message(f"SKIP (no JSON): {task_id}")
            return {'status': 'skipped', 'reason': 'no_json'}
        
        # 显示开始翻译
        with self.print_lock:
            progress = f"[{self.completed + self.failed + 1}/{self.total_tasks}]"
            print(f"🔄 {progress} 翻译中: {task_id}", flush=True)
        
        # 使用 tempfile.mkdtemp 避免权限问题和目录冲突
        temp_dir = tempfile.mkdtemp(prefix=f"sactor_{task['submission_id']}_")
        
        combined_rust_file = os.path.join(output_dir, 'translated_code_unidiomatic', 'combined.rs')
        
        try:
            # 从test_samples.json创建test_task.json
            with open(json_file, 'r') as f:
                test_samples = json.load(f)
            
            # 只使用指定数量的测试用例
            test_samples_limited = test_samples[:self.num_tests]
            
            # 复制test_samples.json到临时目录（只包含指定数量）
            test_samples_path = os.path.join(temp_dir, 'test_samples.json')
            with open(test_samples_path, 'w') as f:
                json.dump(test_samples_limited, f, indent=2)
            
            # 创建test_task.json - 应该是命令列表（只使用指定数量）
            test_task = []
            for i in range(len(test_samples_limited)):
                test_task.append({
                    "command": f"sactor run-tests --type bin ./test_samples.json %t {i} --feed-as-stdin",
                    "test_id": i
                })
            
            test_task_path = os.path.join(temp_dir, 'test_task.json')
            with open(test_task_path, 'w') as f:
                json.dump(test_task, f, indent=2)
            
            # 准备目录
            c_dir = os.path.dirname(c_file)
            c_filename = os.path.basename(c_file)
            os.makedirs(output_dir, exist_ok=True)
            
            # Docker命令
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{c_dir}:/input:ro",
                "-v", f"{temp_dir}:/work:ro",
                "-v", f"{output_dir}:/output",
                "-v", "/home/changdi/sactor/sactor.toml:/app/sactor.toml:ro",
                "-w", "/work",
                self.sactor_docker_image,
                "translate",
                "--type", "bin",
                "--unidiomatic-only",
                "--result-dir", "/output",
                f"/input/{c_filename}",
                "/work/test_task.json"
            ]
            
            # 执行翻译
            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            output, _ = process.communicate(timeout=300)
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # 检查结果
            if os.path.exists(combined_rust_file) and os.path.getsize(combined_rust_file) > 100:
                with self.print_lock:
                    self.completed += 1
                    self._mark_completed(task_id)
                    progress = f"[{self.completed}/{self.total_tasks}]"
                    elapsed = time.time() - self.start_time
                    speed = self.completed / elapsed if elapsed > 0 else 0
                    print(f"✅ {progress} {task_id} (速度: {speed:.2f}/s)", flush=True)
                    self._log_message(f"SUCCESS: {task_id}")
                    
                    # 每10个任务打印一次汇总
                    if self.completed % 10 == 0:
                        self._print_progress_summary()
                
                return {'status': 'success', 'task_id': task_id}
            else:
                # 分析失败原因
                fail_reason = "未知原因"
                if not os.path.exists(combined_rust_file):
                    fail_reason = "输出文件未生成"
                elif os.path.getsize(combined_rust_file) <= 100:
                    fail_reason = f"输出文件太小 ({os.path.getsize(combined_rust_file)} bytes)"
                
                # 尝试从输出中提取错误信息
                error_hints = []
                if output:
                    if "Error code: 403" in output or "Error code: 429" in output:
                        error_hints.append("API配额错误")
                    if "timeout" in output.lower():
                        error_hints.append("超时")
                    if "compilation failed" in output.lower():
                        error_hints.append("编译失败")
                    if "test failed" in output.lower():
                        error_hints.append("测试失败")
                
                if error_hints:
                    fail_reason += f" ({', '.join(error_hints)})"
                
                with self.print_lock:
                    self.failed += 1
                    progress = f"[{self.completed + self.failed}/{self.total_tasks}]"
                    print(f"❌ {progress} {task_id} - {fail_reason}", flush=True)
                    
                    # 统计失败原因
                    reason_key = fail_reason.split('(')[0].strip()
                    self.fail_reasons[reason_key] = self.fail_reasons.get(reason_key, 0) + 1
                    
                    # 显示最后几行输出（如果有的话）
                    if output and len(output) > 200:
                        last_lines = output.strip().split('\n')[-3:]
                        print(f"   最后输出: {' | '.join(last_lines)}", flush=True)
                    
                    self._log_message(f"FAIL: {task_id} - {fail_reason}")
                return {'status': 'failed', 'task_id': task_id, 'reason': fail_reason}
                
        except subprocess.TimeoutExpired:
            shutil.rmtree(temp_dir, ignore_errors=True)
            with self.print_lock:
                self.failed += 1
                progress = f"[{self.completed + self.failed}/{self.total_tasks}]"
                print(f"❌ {progress} {task_id} - 翻译超时 (>5分钟)", flush=True)
                self._log_message(f"TIMEOUT: {task_id}")
            return {'status': 'timeout', 'task_id': task_id}
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            with self.print_lock:
                self.failed += 1
                progress = f"[{self.completed + self.failed}/{self.total_tasks}]"
                error_msg = str(e)[:100]
                print(f"❌ {progress} {task_id} - 异常: {error_msg}", flush=True)
                self._log_message(f"ERROR: {task_id} - {str(e)}")
            return {'status': 'error', 'task_id': task_id, 'error': str(e)}
    
    def run(self):
        """执行批量翻译"""
        # 收集任务
        tasks = self.collect_accepted_c_files_41_to_80()
        if not tasks:
            print("❌ 没有找到任何待翻译任务")
            return
        
        self.total_tasks = len(tasks)
        self.start_time = time.time()
        
        print(f"\n⚙️  开始翻译 {self.total_tasks} 个任务 (并发数: {self.workers}, 测试数: {self.num_tests})...")
        print("   按 Ctrl+C 可安全中断（进度会自动保存）\n")
        
        try:
            # 使用线程池执行翻译
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = {executor.submit(self.translate_single_task, task): task 
                          for task in tasks}
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    except Exception as e:
                        with self.print_lock:
                            self.failed += 1
                            progress = f"[{self.completed + self.failed}/{self.total_tasks}]"
                            print(f"❌ {progress} 任务执行异常: {str(e)[:100]}", flush=True)
                            self._log_message(f"TASK_EXCEPTION: {str(e)}")
        except KeyboardInterrupt:
            print("\n\n⚠️  收到中断信号，正在保存进度并退出...")
            self._save_progress()
            self._log_message("INFO: Translation interrupted by user.")
            print("✅ 进度已保存。")
            return
        
        elapsed = time.time() - self.start_time
        
        # 最终统计
        self._print_progress_summary()
        self._save_progress()
        self._log_message("INFO: Translation task completed.")
        
        print("\n" + "=" * 80)
        print("📊 翻译任务完成")
        print("=" * 80)
        print(f"✅ 成功: {self.completed}")
        print(f"❌ 失败: {self.failed}")
        print(f"⏭️  跳过: {self.skipped}")
        print(f"📁 总任务: {self.total_tasks}")
        print(f"⏱️  总用时: {elapsed:.1f} 秒 ({elapsed/3600:.1f} 小时)")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='翻译CodeNet每题第41-80个Accepted的C文件到Rust')
    parser.add_argument('--workers', type=int, default=10, help='并发数 (默认: 10)')
    parser.add_argument('--num-tests', type=int, default=6, help='使用的测试用例数量 (默认: 6)')
    parser.add_argument('--no-resume', action='store_false', dest='resume', help='禁用断点续传')
    args = parser.parse_args()
    
    translator = CodeNet41To80Translator(workers=args.workers, num_tests=args.num_tests, resume=args.resume)
    translator.run()


if __name__ == "__main__":
    main()

