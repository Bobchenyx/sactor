#!/usr/bin/env python3
"""
通用批量翻译脚本 - 支持任意 C 文件数据集
可以翻译 test_4k_accept 或 test_4k_accept_34 等不同数据集
"""

import os
import json
import subprocess
import shutil
import tempfile
import threading
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed


class GenericTranslator:
    def __init__(self, c_files_dir, json_dir, output_base_dir, num_tests=6):
        self.c_files_dir = c_files_dir
        self.json_dir = json_dir
        self.output_base_dir = output_base_dir
        self.sactor_docker_image = "sactor"
        self.print_lock = threading.Lock()
        self.num_tests = num_tests
        
        # 统计
        self.total_tasks = 0
        self.completed = 0
        self.failed = 0
        self.skipped = 0
        
        print("=" * 80)
        print("🚀 通用批量翻译工具")
        print("=" * 80)
        print(f"📁 C 文件目录: {self.c_files_dir}")
        print(f"📁 JSON 目录: {self.json_dir}")
        print(f"📁 输出目录: {self.output_base_dir}")
        print(f"🧪 测试用例数: {self.num_tests} 个")
        print("=" * 80)
    
    def collect_translation_tasks(self):
        """收集所有翻译任务"""
        tasks = []
        
        # 遍历所有问题目录
        problem_dirs = sorted([d for d in os.listdir(self.c_files_dir) 
                              if os.path.isdir(os.path.join(self.c_files_dir, d)) 
                              and d.startswith('p')])
        
        for problem_id in problem_dirs:
            c_dir = os.path.join(self.c_files_dir, problem_id, 'C')
            if not os.path.exists(c_dir):
                continue
            
            # 找到该问题的第一个 JSON 文件
            json_problem_dir = os.path.join(self.json_dir, problem_id, 'C')
            json_file = None
            
            if os.path.exists(json_problem_dir):
                json_files = sorted([f for f in os.listdir(json_problem_dir) 
                                   if f.endswith('.json')])
                if json_files:
                    json_file = os.path.join(json_problem_dir, json_files[0])
            
            if not json_file:
                continue  # 没有 JSON 就跳过
            
            # 获取所有 C 文件
            c_files = sorted([f for f in os.listdir(c_dir) if f.endswith('.c')])
            
            for c_filename in c_files:
                c_file = os.path.join(c_dir, c_filename)
                submission_id = c_filename.replace('.c', '')
                
                # 输出目录结构: output_base_dir/problem_id/Rust/submission_id/
                output_dir = os.path.join(self.output_base_dir, problem_id, 
                                         'Rust', submission_id, 
                                         'translated_code_unidiomatic')
                
                tasks.append({
                    'task_id': f"{problem_id}/{submission_id}",
                    'problem_id': problem_id,
                    'submission_id': submission_id,
                    'c_file': c_file,
                    'json_file': json_file,
                    'output_dir': os.path.dirname(output_dir)
                })
        
        return tasks
    
    def translate_single_task(self, task):
        """翻译单个任务"""
        task_id = task['task_id']
        c_file = task['c_file']
        json_file = task['json_file']
        output_dir = task['output_dir']
        
        # 检查是否已经翻译过（只检查 combined.rs）
        combined_rust_file = os.path.join(output_dir, 'translated_code_unidiomatic', 'combined.rs')
        
        if os.path.exists(combined_rust_file) and os.path.getsize(combined_rust_file) > 100:
            with self.print_lock:
                self.skipped += 1
                progress = f"[{self.completed + self.failed + self.skipped}/{self.total_tasks}]"
                print(f"⏭️  {progress} {task_id} - 已存在，跳过", flush=True)
            return {'status': 'skipped', 'task_id': task_id}
        
        # 创建临时目录用于test_task.json
        temp_dir = f"/tmp/sactor_translate_{task['submission_id']}"
        os.makedirs(temp_dir, exist_ok=True)
        
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
            with self.print_lock:
                print(f"\n{'='*60}")
                print(f"🔄 开始翻译: {task_id}")
                print(f"   C文件: {c_file}")
                print(f"   JSON: {json_file}")
                print(f"   输出: {output_dir}")
                print(f"{'='*60}\n")
            
            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            output_lines = []
            for line in process.stdout:
                with self.print_lock:
                    print(line, end='', flush=True)
                output_lines.append(line)
            
            process.wait()
            
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # 检查结果
            if os.path.exists(combined_rust_file) and os.path.getsize(combined_rust_file) > 100:
                with self.print_lock:
                    self.completed += 1
                    progress = f"[{self.completed + self.failed}/{self.total_tasks}]"
                    print(f"\n✅ {progress} {task_id} - 翻译成功\n")
                return {'status': 'success', 'task_id': task_id}
            else:
                with self.print_lock:
                    self.failed += 1
                    progress = f"[{self.completed + self.failed}/{self.total_tasks}]"
                    print(f"\n❌ {progress} {task_id} - 翻译失败 (未找到输出文件)")
                    print(f"   期望文件: {combined_rust_file}")
                    print(f"   Docker返回码: {process.returncode}")
                    if output_lines:
                        print(f"   最后10行输出:")
                        for line in output_lines[-10:]:
                            print(f"     {line.rstrip()}")
                    print()
                return {'status': 'failed', 'task_id': task_id}
                
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            with self.print_lock:
                self.failed += 1
                progress = f"[{self.completed + self.failed}/{self.total_tasks}]"
                print(f"❌ {progress} {task_id}: {str(e)}")
            return {'status': 'error', 'task_id': task_id, 'error': str(e)}
    
    def run(self, workers=4):
        """执行批量翻译"""
        # 收集任务
        tasks = self.collect_translation_tasks()
        if not tasks:
            print("❌ 没有找到任何翻译任务")
            return
        
        self.total_tasks = len(tasks)
        
        print(f"\n⚙️  配置:")
        print(f"   并发数: {workers}")
        print(f"   测试用例数: {self.num_tests} 个")
        
        # 创建输出目录
        os.makedirs(self.output_base_dir, exist_ok=True)
        
        print(f"\n🔄 开始翻译 {self.total_tasks} 个任务...\n")
        
        start_time = time.time()
        
        # 使用线程池执行翻译
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.translate_single_task, task): task 
                      for task in tasks}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    with self.print_lock:
                        self.failed += 1
                        print(f"❌ 任务执行异常: {str(e)}")
        
        elapsed = time.time() - start_time
        
        # 统计结果
        print("\n" + "=" * 80)
        print("📊 翻译完成统计")
        print("=" * 80)
        print(f"✅ 成功: {self.completed}")
        print(f"⏭️  跳过 (已存在): {self.skipped}")
        print(f"❌ 失败: {self.failed}")
        print(f"📁 总任务: {self.total_tasks}")
        print(f"⏱️  用时: {elapsed:.1f} 秒")
        if elapsed > 0:
            print(f"📈 速度: {self.total_tasks / elapsed:.2f} 个/秒")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='通用批量翻译工具 - 支持任意 C 文件数据集',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

1. 翻译 test_4k_accept (第1-2个Accepted):
   python3 batch_translate_generic.py \\
       --c-files /home/changdi/CodeNet/test_4k_accept \\
       --json-files /home/changdi/sactor/generated_tests \\
       --output /home/changdi/sactor/translated_rust_4k \\
       --workers 10

2. 翻译 test_4k_accept_34 (第3-4个Accepted):
   python3 batch_translate_generic.py \\
       --c-files /home/changdi/CodeNet/test_4k_accept_34 \\
       --json-files /home/changdi/sactor/generated_tests \\
       --output /home/changdi/sactor/translated_rust_4k_34 \\
       --workers 10

3. 自定义测试用例数量:
   python3 batch_translate_generic.py \\
       --c-files /home/changdi/CodeNet/test_4k_accept \\
       --json-files /home/changdi/sactor/generated_tests \\
       --output /home/changdi/sactor/translated_rust_4k \\
       --num-tests 10 \\
       --workers 8
        """
    )
    
    parser.add_argument('--c-files', required=True, 
                       help='C文件目录 (例如: /home/changdi/CodeNet/test_4k_accept)')
    parser.add_argument('--json-files', required=True,
                       help='JSON测试文件目录 (例如: /home/changdi/sactor/generated_tests)')
    parser.add_argument('--output', required=True,
                       help='输出目录 (例如: /home/changdi/sactor/translated_rust_4k)')
    parser.add_argument('--workers', type=int, default=4, 
                       help='并发数 (默认: 4)')
    parser.add_argument('--num-tests', type=int, default=6,
                       help='使用的测试用例数量 (默认: 6)')
    
    args = parser.parse_args()
    
    # 验证目录存在
    if not os.path.exists(args.c_files):
        print(f"❌ C文件目录不存在: {args.c_files}")
        return
    
    if not os.path.exists(args.json_files):
        print(f"❌ JSON文件目录不存在: {args.json_files}")
        return
    
    translator = GenericTranslator(
        c_files_dir=args.c_files,
        json_dir=args.json_files,
        output_base_dir=args.output,
        num_tests=args.num_tests
    )
    translator.run(workers=args.workers)


if __name__ == "__main__":
    main()

