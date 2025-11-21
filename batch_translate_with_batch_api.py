#!/usr/bin/env python3
"""
使用Batch API优化的批量翻译脚本

策略：
1. 收集所有C文件的测试生成请求
2. 使用Batch API一次性提交
3. 等待结果（50%成本折扣）
4. 解析结果并保存

适用场景：大批量翻译（>50个文件），可以等待
"""

import os
import json
import time
from datetime import datetime
from openai import OpenAI
from pathlib import Path

class BatchAPITranslator:
    def __init__(self):
        """初始化Batch API翻译器"""
        self.client = OpenAI(
            api_key="sk-aaca0ccf722143a39ec3c6e38a0a4bc2",
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        )
        
        self.raw_data_dir = "/home/changdi/CodeNet/new-data"
        self.output_dir = f"/home/changdi/sactor/batch_api_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.output_dir, exist_ok=True)
        
        print("="*80)
        print("🚀 Batch API 批量翻译器")
        print("="*80)
        print(f"📁 数据源: {self.raw_data_dir}")
        print(f"📁 输出: {self.output_dir}")
        print("="*80)
    
    def collect_c_files(self, sample_size=100):
        """收集C文件"""
        print(f"\n🔍 收集C文件 (最多 {sample_size} 个)...")
        
        all_c_files = []
        problem_dirs = sorted([d for d in os.listdir(self.raw_data_dir) 
                              if d.startswith('p') and os.path.isdir(os.path.join(self.raw_data_dir, d))])
        
        import random
        random.shuffle(problem_dirs)
        
        for problem_dir in problem_dirs[:sample_size]:
            c_dir = os.path.join(self.raw_data_dir, problem_dir, 'C')
            if os.path.exists(c_dir):
                c_files = [os.path.join(c_dir, f) for f in os.listdir(c_dir) if f.endswith('.c')]
                if c_files:
                    all_c_files.append(random.choice(c_files))
            
            if len(all_c_files) >= sample_size:
                break
        
        print(f"✅ 收集到 {len(all_c_files)} 个C文件")
        return all_c_files
    
    def create_batch_requests(self, c_files, num_tests=8):
        """创建batch请求"""
        print(f"\n📝 创建Batch API请求...")
        
        requests = []
        file_mapping = {}  # custom_id -> c_file_path
        
        for idx, c_file_path in enumerate(c_files):
            try:
                # 读取C代码
                with open(c_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    c_code = f.read()
                
                # 限制代码长度
                if len(c_code) > 10000:
                    c_code = c_code[:10000]
                
                custom_id = f"test-gen-{idx}"
                file_mapping[custom_id] = c_file_path
                
                # 创建测试生成请求
                request = {
                    "custom_id": custom_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "qwen3-coder-plus",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert in generating test cases for C programs. Generate diverse test inputs that cover edge cases, typical cases, and boundary conditions.",
                                "cache_control": {"type": "ephemeral"}
                            },
                            {
                                "role": "user",
                                "content": f"""Analyze this C program and generate {num_tests} test cases in JSON format.

C Code:
```c
{c_code}
```

Output format (JSON array):
[
  {{"input": "test_input_1", "output": "expected_output_1"}},
  {{"input": "test_input_2", "output": "expected_output_2"}},
  ...
]

Requirements:
1. Detect if the program uses command-line arguments (argc/argv) or standard input (scanf)
2. Generate diverse test inputs (edge cases: 0, 1, negative; typical: 10, 100; boundary: max values)
3. Predict the expected output for each input
4. Output ONLY the JSON array, no explanations"""
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000
                    }
                }
                
                requests.append(request)
                
            except Exception as e:
                print(f"⚠️  跳过文件 {c_file_path}: {e}")
                continue
        
        print(f"✅ 创建了 {len(requests)} 个请求")
        return requests, file_mapping
    
    def save_batch_file(self, requests):
        """保存为JSONL格式"""
        batch_file_path = os.path.join(self.output_dir, "batch_requests.jsonl")
        
        print(f"\n💾 保存batch文件: {batch_file_path}")
        
        with open(batch_file_path, 'w') as f:
            for req in requests:
                f.write(json.dumps(req) + '\n')
        
        print(f"✅ 保存完成，共 {len(requests)} 行")
        return batch_file_path
    
    def submit_batch(self, batch_file_path):
        """提交batch任务"""
        print(f"\n📤 上传batch文件...")
        
        try:
            # 上传文件
            with open(batch_file_path, 'rb') as f:
                batch_file = self.client.files.create(
                    file=f,
                    purpose='batch'
                )
            
            print(f"✅ 文件上传成功: {batch_file.id}")
            
            # 创建batch任务
            print(f"\n🚀 创建batch任务...")
            batch = self.client.batches.create(
                input_file_id=batch_file.id,
                endpoint="/v1/chat/completions",
                completion_window="24h"
            )
            
            print(f"✅ Batch任务创建成功!")
            print(f"   Batch ID: {batch.id}")
            print(f"   状态: {batch.status}")
            
            # 保存batch信息
            batch_info_path = os.path.join(self.output_dir, "batch_info.json")
            with open(batch_info_path, 'w') as f:
                json.dump({
                    "batch_id": batch.id,
                    "file_id": batch_file.id,
                    "status": batch.status,
                    "created_at": str(batch.created_at),
                    "request_counts": getattr(batch, 'request_counts', {})
                }, f, indent=2)
            
            return batch.id
            
        except Exception as e:
            print(f"❌ 提交失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def wait_for_completion(self, batch_id, max_wait_minutes=30):
        """等待batch完成"""
        print(f"\n⏳ 等待batch完成 (最多 {max_wait_minutes} 分钟)...")
        print(f"   Tip: 你可以关闭程序，稍后用batch_id查询结果")
        
        max_checks = max_wait_minutes * 2  # 每30秒检查一次
        
        for i in range(max_checks):
            try:
                batch = self.client.batches.retrieve(batch_id)
                
                status = batch.status
                request_counts = getattr(batch, 'request_counts', {})
                
                print(f"\r   [{i+1}/{max_checks}] 状态: {status} | "
                      f"完成: {request_counts.get('completed', 0)}/{request_counts.get('total', 0)}", 
                      end='', flush=True)
                
                if status == "completed":
                    print("\n\n✅ Batch完成！")
                    return batch
                    
                elif status in ["failed", "expired", "cancelled"]:
                    print(f"\n\n❌ Batch失败: {status}")
                    return None
                
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                print(f"\n⚠️  检查状态时出错: {e}")
                time.sleep(30)
                continue
        
        print(f"\n\n⏰ 超时: {max_wait_minutes}分钟内未完成")
        print(f"   Batch仍在运行，稍后可以用以下命令查询:")
        print(f"   python3 -c \"from openai import OpenAI; client = OpenAI(...); print(client.batches.retrieve('{batch_id}'))\"")
        return None
    
    def download_results(self, batch):
        """下载结果"""
        print(f"\n📥 下载结果...")
        
        try:
            # 下载结果文件
            result_file = self.client.files.content(batch.output_file_id)
            
            # 解析JSONL
            results = []
            for line in result_file.text.split('\n'):
                if line.strip():
                    results.append(json.loads(line))
            
            print(f"✅ 下载完成，共 {len(results)} 个结果")
            
            # 保存原始结果
            results_path = os.path.join(self.output_dir, "batch_results.jsonl")
            with open(results_path, 'w') as f:
                f.write(result_file.text)
            
            return results
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            return []
    
    def process_results(self, results, file_mapping):
        """处理结果"""
        print(f"\n📊 处理结果...")
        
        success_count = 0
        failed_count = 0
        
        for result in results:
            custom_id = result.get('custom_id')
            c_file_path = file_mapping.get(custom_id)
            
            if not c_file_path:
                continue
            
            if 'error' in result:
                print(f"❌ {custom_id}: {result['error']}")
                failed_count += 1
                continue
            
            try:
                # 提取响应
                response_body = result['response']['body']
                content = response_body['choices'][0]['message']['content']
                
                # 解析JSON测试用例
                # 尝试从content中提取JSON
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    test_cases = json.loads(json_match.group())
                    
                    # 保存测试用例
                    c_filename = os.path.basename(c_file_path).replace('.c', '')
                    output_path = os.path.join(self.output_dir, f"{c_filename}_tests.json")
                    
                    with open(output_path, 'w') as f:
                        json.dump(test_cases, f, indent=2)
                    
                    success_count += 1
                    print(f"✅ {custom_id}: 生成 {len(test_cases)} 个测试用例")
                else:
                    print(f"⚠️  {custom_id}: 无法解析JSON")
                    failed_count += 1
                    
            except Exception as e:
                print(f"⚠️  {custom_id}: 处理失败 - {e}")
                failed_count += 1
        
        print(f"\n" + "="*80)
        print(f"📊 结果统计")
        print(f"="*80)
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {failed_count}")
        print(f"📁 输出目录: {self.output_dir}")
        
        return success_count, failed_count
    
    def run(self, sample_size=100, num_tests=8, max_wait_minutes=30):
        """运行完整流程"""
        
        # 1. 收集C文件
        c_files = self.collect_c_files(sample_size)
        
        if not c_files:
            print("❌ 没有找到C文件")
            return
        
        # 2. 创建batch请求
        requests, file_mapping = self.create_batch_requests(c_files, num_tests)
        
        if not requests:
            print("❌ 没有创建任何请求")
            return
        
        # 保存文件映射
        mapping_path = os.path.join(self.output_dir, "file_mapping.json")
        with open(mapping_path, 'w') as f:
            json.dump(file_mapping, f, indent=2)
        
        # 3. 保存batch文件
        batch_file_path = self.save_batch_file(requests)
        
        # 4. 提交batch
        batch_id = self.submit_batch(batch_file_path)
        
        if not batch_id:
            print("❌ Batch提交失败")
            return
        
        # 5. 等待完成
        batch = self.wait_for_completion(batch_id, max_wait_minutes)
        
        if not batch:
            print("⚠️  Batch未在预期时间内完成")
            return
        
        # 6. 下载结果
        results = self.download_results(batch)
        
        if not results:
            print("❌ 没有获取到结果")
            return
        
        # 7. 处理结果
        self.process_results(results, file_mapping)
        
        print(f"\n✅ 完成！输出目录: {self.output_dir}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch API批量翻译')
    parser.add_argument('--sample-size', type=int, default=100, help='处理文件数量')
    parser.add_argument('--num-tests', type=int, default=8, help='每个文件生成的测试数量')
    parser.add_argument('--max-wait', type=int, default=30, help='最大等待时间（分钟）')
    
    args = parser.parse_args()
    
    translator = BatchAPITranslator()
    translator.run(
        sample_size=args.sample_size,
        num_tests=args.num_tests,
        max_wait_minutes=args.max_wait
    )

if __name__ == "__main__":
    main()

