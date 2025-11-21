#!/usr/bin/env python3
"""
批量翻译脚本 - 基于已生成的测试用例
从 generated_tests 目录中的 JSON 文件，为对应的 C 程序生成 Rust 翻译
"""

import os
import json
import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import argparse
import threading


class BatchTranslator:
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
        self.generated_tests_dir = "/home/changdi/sactor/generated_tests"
        self.codenet_base = "/home/changdi/CodeNet/new-data"
        self.output_base = "/home/changdi/sactor/translated_rust"
        self.sactor_docker_image = "sactor:latest"
        
        # 统计
        self.total_files = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = None
        
        # 输出锁，防止多线程输出混乱
        self.print_lock = threading.Lock()
        
    def collect_test_json_files(self):
        """收集所有已生成的测试 JSON 文件"""
        print("🔍 扫描已生成的测试用例...")
        
        json_files = []
        problem_count = {}
        for root, dirs, files in os.walk(self.generated_tests_dir):
            for file in files:
                if file.endswith('.c.json'):
                    json_path = os.path.join(root, file)
                    json_files.append(json_path)
                    # 统计每个问题的文件数
                    problem_id = os.path.basename(os.path.dirname(os.path.dirname(json_path)))
                    problem_count[problem_id] = problem_count.get(problem_id, 0) + 1
        
        print(f"✅ 找到 {len(json_files)} 个测试 JSON 文件，覆盖 {len(problem_count)} 个问题")
        return sorted(json_files)
    
    def get_c_file_path(self, json_path):
        """从 JSON 路径推导出对应的 C 文件路径"""
        # json_path: /home/changdi/sactor/generated_tests/p00000/C/s123456789.c.json
        # c_path: /home/changdi/CodeNet/new-data/p00000/C/s123456789.c
        
        rel_path = os.path.relpath(json_path, self.generated_tests_dir)
        # rel_path: p00000/C/s123456789.c.json
        
        c_filename = os.path.basename(json_path).replace('.json', '')
        # c_filename: s123456789.c
        
        problem_dir = rel_path.split('/')[0]  # p00000
        
        c_path = os.path.join(self.codenet_base, problem_dir, 'C', c_filename)
        return c_path, problem_dir, c_filename
    
    def get_rust_output_path(self, problem_dir, c_filename):
        """获取 Rust 输出路径 - 每个C文件对应一个文件夹"""
        # s123456789.c -> s123456789
        c_name_without_ext = c_filename.replace('.c', '')
        
        # /home/changdi/sactor/translated_rust/p00000/Rust/s123456789/
        rust_dir = os.path.join(self.output_base, problem_dir, 'Rust', c_name_without_ext)
        
        # /home/changdi/sactor/translated_rust/p00000/Rust/s123456789/translated.rs
        rust_path = os.path.join(rust_dir, 'translated.rs')
        
        return rust_path, rust_dir
    
    def check_if_translated(self, rust_path):
        """检查是否已经翻译过"""
        if os.path.exists(rust_path):
            # 检查文件是否为空或太小
            if os.path.getsize(rust_path) > 100:  # 至少100字节
                return True
        return False
    
    def create_test_task_json(self, test_samples_filename, test_samples_host_path, output_path):
        """从 test_samples.json 创建 test_task.json"""
        try:
            # 在 Docker 容器内，test_samples.json 会被挂载到 /test_samples/
            docker_test_samples_path = f"/test_samples/{test_samples_filename}"
            
            # 读取测试样本以确定数量
            with open(test_samples_host_path, 'r') as f:
                test_samples = json.load(f)
            
            # 创建 test task 格式，使用 Docker 内部路径
            test_tasks = []
            for i in range(len(test_samples)):
                test_tasks.append({
                    "command": f"sactor run-tests --type bin {docker_test_samples_path} %t {i} --feed-as-stdin",
                    "test_id": i
                })
            
            # 保存 test_task.json
            with open(output_path, 'w') as f:
                json.dump(test_tasks, f, indent=2)
            
            return True
        except Exception as e:
            print(f"⚠️  创建 test_task.json 失败: {e}")
            return False
    
    def translate_with_sactor(self, c_file_path, test_json_path, rust_output_path):
        """使用 SACToR Docker 进行翻译"""
        
        # rust_output_path 是 .../Rust/s123456789/translated.rs
        # output_dir 是 .../Rust/s123456789/
        output_dir = os.path.dirname(rust_output_path)
        
        # 创建子目录（让SACToR可以在这个目录下工作）
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建临时目录用于 test_task.json
        import tempfile
        temp_dir = tempfile.mkdtemp()
        test_task_path = os.path.join(temp_dir, "test_task.json")
        
        # 从 test_samples.json 创建 test_task.json
        test_samples_filename = os.path.basename(test_json_path)
        if not self.create_test_task_json(test_samples_filename, test_json_path, test_task_path):
            return {
                "success": False,
                "error": "Failed to create test_task.json"
            }
        
        # Docker 挂载路径
        c_dir = os.path.dirname(c_file_path)
        test_samples_dir = os.path.dirname(test_json_path)
        
        c_filename = os.path.basename(c_file_path)
        test_task_filename = os.path.basename(test_task_path)
        
        # 关键理解: SACToR的--result-dir会在指定目录下创建:
        # - translated_code_unidiomatic/
        # - llm_stat.json
        # - 等等
        # 我们需要为每个C文件创建独立的子目录，所以:
        # rust_output_path = .../Rust/s123456789/translated.rs
        # output_dir = .../Rust/s123456789/  ← 挂载这个目录到Docker的/output
        
        c_name_without_ext = c_filename.replace('.c', '')
        
        # SACToR会在output_dir下创建translated_code_unidiomatic/combined.rs
        # 然后我们需要找到这个文件
        expected_rust_file = os.path.join(output_dir, "translated_code_unidiomatic", "combined.rs")
        
        # 构建 Docker 命令 - 挂载到 output_dir (即 .../Rust/s123456789/)
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{c_dir}:/input:ro",
            "-v", f"{temp_dir}:/test_task:ro",
            "-v", f"{test_samples_dir}:/test_samples:ro",
            "-v", f"{output_dir}:/output",  # 挂载到C文件专属的子目录
            "-v", "/home/changdi/sactor/sactor.toml:/app/sactor.toml:ro",
            self.sactor_docker_image,
            "translate",
            "--type", "bin",
            "--unidiomatic-only",  # 只生成unidiomatic版本，节省50%的API调用
            "--result-dir", "/output",
            f"/input/{c_filename}",
            f"/test_task/{test_task_filename}"
        ]
        
        try:
            # 实时显示输出，但仍然捕获以便错误处理
            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时打印输出（使用锁保证不混乱）
            output_lines = []
            for line in process.stdout:
                with self.print_lock:
                    print(line, end='', flush=True)  # 实时显示，立即刷新
                output_lines.append(line)
            
            # 等待进程结束
            return_code = process.wait(timeout=300)
            
            if return_code == 0:
                # 检查 SACToR 生成的文件 (combined.rs)
                if os.path.exists(expected_rust_file):
                    if os.path.getsize(expected_rust_file) > 100:
                        # 复制 combined.rs 到 translated.rs (更清晰的名字)
                        import shutil
                        shutil.copy2(expected_rust_file, rust_output_path)
                        
                        # 清理临时目录
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        
                        return {
                            "success": True,
                            "rust_file": rust_output_path,
                            "file_size": os.path.getsize(rust_output_path)
                        }
                    else:
                        import shutil
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return {
                            "success": False,
                            "error": "Generated Rust file too small"
                        }
                else:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return {
                        "success": False,
                        "error": f"Expected output not found: {expected_rust_file}"
                    }
            else:
                # 从捕获的输出中提取最后的错误信息
                error_msg = ''.join(output_lines[-50:]) if output_lines else "Unknown error"
                shutil.rmtree(temp_dir, ignore_errors=True)
                return {
                    "success": False,
                    "error": f"Translation failed (code {return_code}): {error_msg[:500]}"
                }
                
        except subprocess.TimeoutExpired:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "success": False,
                "error": "Translation timeout (>5 minutes)"
            }
        except Exception as e:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "success": False,
                "error": f"Exception: {str(e)}"
            }
    
    def translate_single_file(self, json_path, index=0, total=0):
        """翻译单个文件"""
        try:
            # 获取对应的 C 文件路径
            c_file_path, problem_dir, c_filename = self.get_c_file_path(json_path)
            
            # 检查 C 文件是否存在
            if not os.path.exists(c_file_path):
                if index > 0:
                    with self.print_lock:
                        print(f"❌ [{index}/{total}] C文件不存在: {problem_dir}/{c_filename}")
                return {
                    "success": False,
                    "error": f"C file not found: {c_file_path}",
                    "json_file": json_path,
                    "skipped": False
                }
            
            # 获取 Rust 输出路径
            rust_output_path, rust_dir = self.get_rust_output_path(problem_dir, c_filename)
            
            # 检查是否已经翻译
            if self.check_if_translated(rust_output_path):
                if index > 0:
                    with self.print_lock:
                        print(f"⏭️  [{index}/{total}] 跳过: {problem_dir}/{c_filename} (已翻译)")
                return {
                    "success": True,
                    "skipped": True,
                    "rust_file": rust_output_path,
                    "message": "Already translated"
                }
            
            # 执行翻译
            with self.print_lock:
                print(f"\n{'='*80}")
                print(f"🔄 [{index}/{total}] 翻译中: {problem_dir}/{c_filename}")
                print(f"{'='*80}")
            start_time = time.time()
            
            result = self.translate_with_sactor(c_file_path, json_path, rust_output_path)
            with self.print_lock:
                print(f"{'='*80}")
            
            processing_time = time.time() - start_time
            result["processing_time"] = processing_time
            result["c_file"] = c_filename
            result["problem_dir"] = problem_dir
            result["json_file"] = json_path
            result["skipped"] = False
            
            if result["success"]:
                with self.print_lock:
                    print(f"✅ [{index}/{total}] 成功: {problem_dir}/{c_filename} -> {os.path.basename(rust_output_path)} ({processing_time:.1f}s)")
            else:
                error_msg = result.get('error', 'Unknown error')
                # 截断过长的错误消息
                if len(error_msg) > 150:
                    error_msg = error_msg[:150] + "..."
                with self.print_lock:
                    print(f"❌ [{index}/{total}] 失败: {problem_dir}/{c_filename} - {error_msg}")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception: {str(e)}",
                "json_file": json_path,
                "skipped": False
            }
    
    def batch_translate(self):
        """批量翻译所有文件"""
        self.start_time = time.time()
        
        print("="*80)
        print("🚀 SACToR 批量翻译 - 基于已生成测试")
        print("="*80)
        print(f"📁 测试目录: {self.generated_tests_dir}")
        print(f"📁 C 文件目录: {self.codenet_base}")
        print(f"📁 输出目录: {self.output_base}")
        print(f"⚙️  并发数: {self.max_workers}")
        print("="*80)
        print()
        
        # 收集所有测试 JSON 文件
        json_files = self.collect_test_json_files()
        self.total_files = len(json_files)
        
        if self.total_files == 0:
            print("⚠️  没有找到测试 JSON 文件")
            return
        
        print(f"\n开始处理 {self.total_files} 个文件...\n")
        
        # 并发处理
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_json = {
                executor.submit(self.translate_single_file, json_path, i+1, self.total_files): (json_path, i+1)
                for i, json_path in enumerate(json_files)
            }
            
            for future in as_completed(future_to_json):
                json_path, idx = future_to_json[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result.get("skipped"):
                        self.skipped += 1
                    elif result["success"]:
                        self.successful += 1
                    else:
                        self.failed += 1
                    
                    # 显示进度 - 每5个文件显示一次
                    completed = self.successful + self.failed + self.skipped
                    if completed % 5 == 0 or completed == self.total_files:
                        elapsed = time.time() - self.start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta = (self.total_files - completed) / rate if rate > 0 else 0
                        print(f"\n{'='*80}")
                        print(f"📊 进度汇总: {completed}/{self.total_files} ({completed*100//self.total_files}%)")
                        print(f"   ✅ 成功: {self.successful} | ❌ 失败: {self.failed} | ⏭️  跳过: {self.skipped}")
                        print(f"   ⏱️  速度: {rate:.2f}个/秒 | ETA: {eta/60:.1f}分钟 | 已用时: {elapsed/60:.1f}分钟")
                        print(f"{'='*80}\n")
                
                except Exception as e:
                    print(f"❌ 处理失败: {json_path} - {str(e)}")
                    self.failed += 1
        
        # 打印最终报告
        self.print_final_report(results)
    
    def print_final_report(self, results):
        """打印最终报告"""
        total_time = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("📊 批量翻译完成报告")
        print("="*80)
        print(f"⏱️  总耗时: {total_time/60:.1f} 分钟")
        print(f"📁 总文件数: {self.total_files}")
        print(f"✅ 成功翻译: {self.successful} ({self.successful/self.total_files*100:.1f}%)")
        print(f"⏭️  跳过(已存在): {self.skipped} ({self.skipped/self.total_files*100:.1f}%)")
        print(f"❌ 失败: {self.failed} ({self.failed/self.total_files*100:.1f}%)")
        print(f"⚡ 平均速度: {self.total_files/total_time*60:.1f} 个/分钟")
        print("="*80)
        
        # 保存详细结果
        if results:
            report_file = os.path.join(self.output_base, "translation_report.json")
            os.makedirs(self.output_base, exist_ok=True)
            
            with open(report_file, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "total_files": self.total_files,
                    "successful": self.successful,
                    "failed": self.failed,
                    "skipped": self.skipped,
                    "total_time_seconds": total_time,
                    "results": results
                }, f, indent=2)
            
            print(f"\n📄 详细报告已保存到: {report_file}")
        
        # 显示失败案例
        if self.failed > 0:
            print("\n❌ 失败案例:")
            failed_results = [r for r in results if not r["success"] and not r.get("skipped")]
            for i, result in enumerate(failed_results[:10], 1):
                print(f"  {i}. {result.get('problem_dir', 'Unknown')}/{result.get('c_file', 'Unknown')}")
                print(f"     错误: {result.get('error', 'Unknown')[:100]}")
            
            if len(failed_results) > 10:
                print(f"  ... 还有 {len(failed_results) - 10} 个失败案例")
        
        print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(description='批量翻译 C 到 Rust（基于已生成测试）')
    parser.add_argument('--workers', type=int, default=10, help='并发worker数量（默认: 10）')
    
    args = parser.parse_args()
    
    translator = BatchTranslator(max_workers=args.workers)
    translator.batch_translate()


if __name__ == "__main__":
    main()

