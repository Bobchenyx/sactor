#!/usr/bin/env python3
"""
从翻译结果创建C2Rust数据集
格式: 原始C文件 + 对应的combined.rs
"""

import os
import json
import argparse
from pathlib import Path


class C2RustDatasetCreator:
    def __init__(self, output_file="c2rust_dataset.jsonl"):
        # 所有翻译结果目录
        self.translation_dirs = [
            "/home/changdi/sactor/translated_rust_4k",
            "/home/changdi/sactor/translated_rust_4k_34",
            "/home/changdi/sactor/translated_rust_5_to_20",
            "/home/changdi/sactor/translated_rust_21_to_40",
            "/home/changdi/sactor/translated_rust_41_to_80",
        ]
        
        # C文件根目录
        self.c_files_roots = [
            "/home/changdi/CodeNet/test_4k_accept",
            "/home/changdi/CodeNet/test_4k_accept_34",
            "/home/changdi/CodeNet/Project_CodeNet/data",
        ]
        
        self.output_file = output_file
        self.dataset_id_counter = 0
        
        # 加载5个不同的系统提示词
        self.prompts = self._load_prompts()
        self.prompt_index = 0  # 轮流使用提示词
    
    def _load_prompts(self):
        """加载5个不同的提示词"""
        prompt_dir = "/home/changdi/Moxin-C2Rust-Datasets/scripts/instructions/function"
        prompts = []
        
        for i in range(1, 6):
            prompt_file = os.path.join(prompt_dir, f"function_instruction_{i}.txt")
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt = f.read().strip()
                    prompts.append(prompt + "\n\n")
            except Exception as e:
                print(f"⚠️  无法加载提示词文件 {prompt_file}: {e}")
                # 使用默认提示词作为备份
                prompts.append(
                    "You are a C-to-Rust code translator.\n"
                    "Output only the translated Rust function, with no comments or explanations.\n\n"
                    "Requirements\n"
                    "\t•\tPreserve full functional equivalence.\n"
                    "\t•\tConvert types accurately; prefer references and slices over pointers.\n"
                    "\t•\tUse safe Rust by default; mark unsafe only when required.\n"
                    "\t•\tReplace manual memory operations with Box or Vec.\n"
                    "\t•\tUse Result/Option instead of raw error codes or nulls.\n"
                    "\t•\tFollow Rust naming conventions (snake_case).\n"
                    "\t•\tAvoid external dependencies except libc if necessary.\n\n"
                    "Translate the following C function into idiomatic, safe Rust:\n\n"
                )
        
        if not prompts:
            raise RuntimeError("无法加载任何提示词文件")
        
        print(f"✅ 成功加载 {len(prompts)} 个提示词")
        return prompts
    
    def _get_next_prompt(self):
        """获取下一个提示词（轮流使用）"""
        prompt = self.prompts[self.prompt_index]
        self.prompt_index = (self.prompt_index + 1) % len(self.prompts)
        return prompt
    
    def find_c_file(self, problem_id, submission_id):
        """查找原始C文件"""
        # 尝试各个可能的位置
        possible_paths = [
            # test_4k_accept
            f"/home/changdi/CodeNet/test_4k_accept/{problem_id}/C/{submission_id}.c",
            # test_4k_accept_34
            f"/home/changdi/CodeNet/test_4k_accept_34/{problem_id}/C/{submission_id}.c",
            # 原始CodeNet数据
            f"/home/changdi/CodeNet/Project_CodeNet/data/{problem_id}/C/{submission_id}.c",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def read_file_safely(self, filepath):
        """安全读取文件内容"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                print(f"⚠️  无法读取文件 {filepath}: {e}")
                return None
        except Exception as e:
            print(f"⚠️  读取文件出错 {filepath}: {e}")
            return None
    
    def collect_translation_pairs(self):
        """收集所有翻译对"""
        pairs = []
        
        for trans_dir in self.translation_dirs:
            if not os.path.exists(trans_dir):
                print(f"⏭️  跳过不存在的目录: {trans_dir}")
                continue
            
            print(f"🔍 扫描: {trans_dir}")
            
            # 遍历所有问题目录
            for problem_id in sorted(os.listdir(trans_dir)):
                problem_path = os.path.join(trans_dir, problem_id)
                if not os.path.isdir(problem_path):
                    continue
                
                rust_dir = os.path.join(problem_path, "Rust")
                if not os.path.exists(rust_dir):
                    continue
                
                # 遍历所有提交
                for submission_id in os.listdir(rust_dir):
                    submission_path = os.path.join(rust_dir, submission_id)
                    if not os.path.isdir(submission_path):
                        continue
                    
                    # 查找combined.rs
                    combined_rs = os.path.join(submission_path, 
                                              "translated_code_unidiomatic", 
                                              "combined.rs")
                    
                    if not os.path.exists(combined_rs):
                        continue
                    
                    # 查找原始C文件
                    c_file = self.find_c_file(problem_id, submission_id)
                    if not c_file:
                        print(f"⚠️  找不到C文件: {problem_id}/{submission_id}")
                        continue
                    
                    # 读取内容
                    c_content = self.read_file_safely(c_file)
                    rust_content = self.read_file_safely(combined_rs)
                    
                    if c_content is None or rust_content is None:
                        continue
                    
                    # 跳过空文件或过小的文件
                    if len(c_content.strip()) < 10 or len(rust_content.strip()) < 10:
                        continue
                    
                    pairs.append({
                        "problem_id": problem_id,
                        "submission_id": submission_id,
                        "c_file": c_file,
                        "rust_file": combined_rs,
                        "c_content": c_content,
                        "rust_content": rust_content,
                    })
        
        print(f"\n✅ 共收集到 {len(pairs)} 个有效翻译对")
        return pairs
    
    def create_dataset_entry(self, pair):
        """创建单个数据集条目"""
        dataset_id = f"c2rust_{self.dataset_id_counter}"
        self.dataset_id_counter += 1
        
        # 获取下一个提示词（轮流使用5个提示词）
        # 记录当前使用的prompt编号（1-5）
        current_prompt_id = self.prompt_index + 1
        system_prompt = self._get_next_prompt()
        
        # 构建用户消息（系统提示 + C代码）
        user_content = system_prompt + pair["c_content"]
        
        # 构建助手消息（Rust代码）
        assistant_content = pair["rust_content"]
        
        entry = {
            "dataset": "c2rust",
            "id": dataset_id,
            "problem_id": pair["problem_id"],
            "submission_id": pair["submission_id"],
            "prompt_id": current_prompt_id,  # 记录使用的是哪个prompt (1-5)
            "messages": [
                {
                    "role": "user",
                    "content": user_content
                },
                {
                    "role": "assistant",
                    "content": assistant_content
                }
            ]
        }
        
        return entry
    
    def create_dataset(self, sample_only=False, sample_count=10):
        """创建数据集"""
        print("=" * 80)
        print("🚀 C2Rust 数据集生成器")
        print("=" * 80)
        
        # 收集翻译对
        pairs = self.collect_translation_pairs()
        
        if not pairs:
            print("❌ 没有找到任何翻译对")
            return
        
        # 如果只生成样本
        if sample_only:
            pairs = pairs[:sample_count]
            print(f"\n📝 生成样本数据集 (前 {sample_count} 条)")
        
        # 生成数据集
        output_path = self.output_file
        if sample_only:
            output_path = output_path.replace(".jsonl", "_sample.jsonl")
        
        print(f"\n📝 写入数据集: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for pair in pairs:
                entry = self.create_dataset_entry(pair)
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        print(f"✅ 数据集生成完成: {len(pairs)} 条记录")
        print(f"📁 输出文件: {output_path}")
        
        # 显示统计信息
        self.print_statistics(pairs, output_path)
    
    def print_statistics(self, pairs, output_path):
        """打印统计信息"""
        print("\n" + "=" * 80)
        print("📊 数据集统计")
        print("=" * 80)
        
        # 计算代码长度统计
        c_lengths = [len(p["c_content"]) for p in pairs]
        rust_lengths = [len(p["rust_content"]) for p in pairs]
        
        print(f"总记录数: {len(pairs)}")
        print(f"\nC代码长度:")
        print(f"  最小: {min(c_lengths)} 字符")
        print(f"  最大: {max(c_lengths)} 字符")
        print(f"  平均: {sum(c_lengths) // len(c_lengths)} 字符")
        
        print(f"\nRust代码长度:")
        print(f"  最小: {min(rust_lengths)} 字符")
        print(f"  最大: {max(rust_lengths)} 字符")
        print(f"  平均: {sum(rust_lengths) // len(rust_lengths)} 字符")
        
        # 文件大小
        file_size = os.path.getsize(output_path)
        print(f"\n数据集文件大小: {file_size / (1024*1024):.2f} MB")
        
        # 按问题统计
        problems = set(p["problem_id"] for p in pairs)
        print(f"\n覆盖问题数: {len(problems)}")
        print(f"平均每题样本数: {len(pairs) / len(problems):.1f}")
        
        # 统计prompt使用分布
        print(f"\nPrompt使用分布:")
        print(f"  使用了 {len(self.prompts)} 个不同的prompt")
        print(f"  轮流分配，每个prompt约使用 {len(pairs) // len(self.prompts)} 次")
        
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='从翻译结果创建C2Rust数据集')
    parser.add_argument('--output', '-o', default='c2rust_dataset.jsonl',
                       help='输出文件名 (默认: c2rust_dataset.jsonl)')
    parser.add_argument('--sample', action='store_true',
                       help='只生成样本数据集 (前10条)')
    parser.add_argument('--sample-count', type=int, default=10,
                       help='样本数量 (默认: 10)')
    
    args = parser.parse_args()
    
    creator = C2RustDatasetCreator(output_file=args.output)
    creator.create_dataset(sample_only=args.sample, sample_count=args.sample_count)


if __name__ == "__main__":
    main()

