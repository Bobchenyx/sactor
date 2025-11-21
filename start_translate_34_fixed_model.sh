#!/bin/bash
# 翻译 test_4k_accept_34 (第3-4批) - 使用固定模型 qwen3-coder-flash-2025-07-28
# 不修改原始 sactor.toml

# 参数设置（可以通过命令行修改）
WORKERS=${1:-10}        # 并发数，默认10
NUM_TESTS=${2:-6}       # 测试用例数，默认6

echo "================================================================================"
echo "🚀 开始翻译 test_4k_accept_34 (第3-4批) - 固定模型"
echo "================================================================================"
echo ""
echo "📁 C文件: /home/changdi/CodeNet/test_4k_accept_34"
echo "📁 JSON: /home/changdi/sactor/generated_tests"
echo "📁 输出: /home/changdi/sactor/translated_rust_4k_34"
echo ""
echo "⚙️  配置:"
echo "   - 模型: qwen3-coder-flash-2025-07-28 (固定)"
echo "   - 并发数: $WORKERS"
echo "   - 测试用例数: $NUM_TESTS"
echo "   - 不修改原始 sactor.toml"
echo ""
echo "================================================================================"
echo ""

cd /home/changdi/sactor

# 创建临时配置文件（for Docker）
TEMP_TOML="/tmp/sactor_34_fixed.toml"
cp /home/changdi/sactor/sactor.toml "$TEMP_TOML"

# 修改临时配置：设置固定模型
sed -i '/\[Qwen\]/,/^\[/ s/model = ".*"/model = "qwen3-coder-flash-2025-07-28"/' "$TEMP_TOML"

echo "✅ 创建临时配置: $TEMP_TOML"
echo "✅ 模型设置为: qwen3-coder-flash-2025-07-28"
echo ""

# 创建自定义翻译脚本，使用临时配置文件
cat > /tmp/translate_34_runner.py << 'EOF'
#!/usr/bin/env python3
import os
import json
import subprocess
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class Translator34Fixed:
    def __init__(self, num_tests=6):
        self.c_files_dir = "/home/changdi/CodeNet/test_4k_accept_34"
        self.json_dir = "/home/changdi/sactor/generated_tests"
        self.output_base_dir = "/home/changdi/sactor/translated_rust_4k_34"
        self.sactor_docker_image = "sactor"
        self.config_file = "/tmp/sactor_34_fixed.toml"  # 使用临时配置
        self.print_lock = threading.Lock()
        self.num_tests = num_tests
        
        self.total_tasks = 0
        self.completed = 0
        self.failed = 0
        self.skipped = 0
    
    def collect_translation_tasks(self):
        """收集所有翻译任务"""
        tasks = []
        problem_dirs = sorted([d for d in os.listdir(self.c_files_dir) 
                              if os.path.isdir(os.path.join(self.c_files_dir, d)) 
                              and d.startswith('p')])
        
        for problem_id in problem_dirs:
            c_dir = os.path.join(self.c_files_dir, problem_id, 'C')
            if not os.path.exists(c_dir):
                continue
            
            json_problem_dir = os.path.join(self.json_dir, problem_id, 'C')
            json_file = None
            
            if os.path.exists(json_problem_dir):
                json_files = sorted([f for f in os.listdir(json_problem_dir) 
                                   if f.endswith('.json')])
                if json_files:
                    json_file = os.path.join(json_problem_dir, json_files[0])
            
            if not json_file:
                continue
            
            c_files = sorted([f for f in os.listdir(c_dir) if f.endswith('.c')])
            
            for c_filename in c_files:
                c_file = os.path.join(c_dir, c_filename)
                submission_id = c_filename.replace('.c', '')
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
        
        combined_rust_file = os.path.join(output_dir, 'translated_code_unidiomatic', 'combined.rs')
        
        if os.path.exists(combined_rust_file) and os.path.getsize(combined_rust_file) > 100:
            with self.print_lock:
                self.skipped += 1
                progress = f"[{self.completed + self.failed + self.skipped}/{self.total_tasks}]"
                print(f"⏭️  {progress} {task_id} - 已存在，跳过", flush=True)
            return {'status': 'skipped', 'task_id': task_id}
        
        temp_dir = f"/tmp/sactor_translate_{task['submission_id']}"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            with open(json_file, 'r') as f:
                test_samples = json.load(f)
            
            test_samples_limited = test_samples[:self.num_tests]
            
            test_samples_path = os.path.join(temp_dir, 'test_samples.json')
            with open(test_samples_path, 'w') as f:
                json.dump(test_samples_limited, f, indent=2)
            
            test_task = []
            for i in range(len(test_samples_limited)):
                test_task.append({
                    "command": f"sactor run-tests --type bin ./test_samples.json %t {i} --feed-as-stdin",
                    "test_id": i
                })
            
            test_task_path = os.path.join(temp_dir, 'test_task.json')
            with open(test_task_path, 'w') as f:
                json.dump(test_task, f, indent=2)
            
            c_dir = os.path.dirname(c_file)
            c_filename = os.path.basename(c_file)
            os.makedirs(output_dir, exist_ok=True)
            
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{c_dir}:/input:ro",
                "-v", f"{temp_dir}:/work:ro",
                "-v", f"{output_dir}:/output",
                "-v", f"{self.config_file}:/app/sactor.toml:ro",  # 使用临时配置
                "-w", "/work",
                self.sactor_docker_image,
                "translate",
                "--type", "bin",
                "--unidiomatic-only",
                "--result-dir", "/output",
                f"/input/{c_filename}",
                "/work/test_task.json"
            ]
            
            with self.print_lock:
                print(f"\n{'='*60}")
                print(f"🔄 翻译: {task_id}")
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
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            if os.path.exists(combined_rust_file) and os.path.getsize(combined_rust_file) > 100:
                with self.print_lock:
                    self.completed += 1
                    progress = f"[{self.completed + self.failed}/{self.total_tasks}]"
                    print(f"\n✅ {progress} {task_id} - 成功\n")
                return {'status': 'success', 'task_id': task_id}
            else:
                with self.print_lock:
                    self.failed += 1
                    progress = f"[{self.completed + self.failed}/{self.total_tasks}]"
                    print(f"\n❌ {progress} {task_id} - 失败\n")
                return {'status': 'failed', 'task_id': task_id}
                
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            with self.print_lock:
                self.failed += 1
                print(f"❌ {task_id}: {str(e)}")
            return {'status': 'error', 'task_id': task_id, 'error': str(e)}
    
    def run(self, workers=10):
        """执行批量翻译"""
        tasks = self.collect_translation_tasks()
        if not tasks:
            print("❌ 没有找到任何翻译任务")
            return
        
        self.total_tasks = len(tasks)
        print(f"\n🔄 开始翻译 {self.total_tasks} 个任务...\n")
        
        os.makedirs(self.output_base_dir, exist_ok=True)
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.translate_single_task, task): task 
                      for task in tasks}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    with self.print_lock:
                        self.failed += 1
                        print(f"❌ 任务异常: {str(e)}")
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 80)
        print("📊 翻译完成")
        print("=" * 80)
        print(f"✅ 成功: {self.completed}")
        print(f"⏭️  跳过: {self.skipped}")
        print(f"❌ 失败: {self.failed}")
        print(f"📁 总数: {self.total_tasks}")
        print(f"⏱️  用时: {elapsed:.1f} 秒")
        print("=" * 80)


if __name__ == "__main__":
    import sys
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    num_tests = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    
    translator = Translator34Fixed(num_tests=num_tests)
    translator.run(workers=workers)
EOF

chmod +x /tmp/translate_34_runner.py

# 运行翻译，传递参数
python3 -u /tmp/translate_34_runner.py "$WORKERS" "$NUM_TESTS"

EXIT_CODE=$?

# 清理临时文件
rm -f "$TEMP_TOML"
rm -f /tmp/translate_34_runner.py

echo ""
echo "✅ 临时文件已清理"
echo "================================================================================"

exit $EXIT_CODE
