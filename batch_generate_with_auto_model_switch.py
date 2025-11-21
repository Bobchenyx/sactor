#!/usr/bin/env python3
"""
带自动模型切换的批量测试生成脚本

当遇到403错误（quota用完）时，自动切换到下一个可用模型
"""

import os
import sys
import re
import subprocess
import time
from pathlib import Path

class ModelManager:
    """管理模型切换"""
    
    def __init__(self, toml_path="/home/changdi/sactor/sactor.toml"):
        self.toml_path = toml_path
        
        # 从toml读取可用模型列表
        self.available_models = self._parse_available_models()
        self.current_model_index = 0
        self.used_models = set()
        
        print("="*80)
        print("🔄 模型自动切换管理器")
        print("="*80)
        print(f"📝 配置文件: {self.toml_path}")
        print(f"📋 可用模型数量: {len(self.available_models)}")
        print(f"   模型列表:")
        for i, model in enumerate(self.available_models, 1):
            print(f"      {i}. {model}")
        print("="*80)
    
    def _parse_available_models(self):
        """从toml文件解析可用模型列表"""
        with open(self.toml_path, 'r') as f:
            content = f.read()
        
        # 尝试解析新格式：available_models = [...]
        array_match = re.search(r'available_models\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if array_match:
            models_str = array_match.group(1)
            # 提取所有引号内的模型名称
            models = re.findall(r'"([^"]+)"', models_str)
            if models:
                print(f"✅ 从toml解析到 {len(models)} 个可用模型: {', '.join(models[:3])}...")
                return models
        
        # 兼容旧格式：# available models: ...
        comment_match = re.search(r'# available models: (.+)', content)
        if comment_match:
            models_str = comment_match.group(1)
            # 分割并清理模型名称
            models = [m.strip() for m in models_str.split(',')]
            print(f"✅ 从toml解析到 {len(models)} 个可用模型（旧格式）")
            return models
        
        print("⚠️  未找到 available models 列表，使用默认模型")
        return ["qwen3-coder-plus", "qwen-plus-latest", "qwen3-max"]
    
    def get_current_model(self):
        """获取当前使用的模型（只读取[Qwen]部分）"""
        with open(self.toml_path, 'r') as f:
            content = f.read()
        
        # 只查找[Qwen]部分的model配置
        match = re.search(r'\[Qwen\].*?^model = "([^"]+)"', content, re.MULTILINE | re.DOTALL)
        if match:
            return match.group(1)
        return None
    
    def switch_to_next_model(self):
        """切换到下一个未使用的模型"""
        current_model = self.get_current_model()
        if current_model:
            self.used_models.add(current_model)
            print(f"❌ 模型 {current_model} 配额已用完，标记为已使用")
        
        # 找到下一个未使用的模型
        next_model = None
        for model in self.available_models:
            if model not in self.used_models:
                next_model = model
                break
        
        if not next_model:
            print("❌ 所有模型配额都已用完！")
            return False
        
        # 更新toml文件
        with open(self.toml_path, 'r') as f:
            content = f.read()
        
        # 只替换[Qwen]部分的model配置
        # 使用更精确的正则表达式，确保在[Qwen]段落中
        qwen_section_pattern = r'(\[Qwen\].*?^model = ")[^"]+(")'
        new_content = re.sub(
            qwen_section_pattern,
            f'\\1{next_model}\\2',
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        
        with open(self.toml_path, 'w') as f:
            f.write(new_content)
        
        print(f"✅ 已切换到新模型: {next_model}")
        print(f"   剩余可用模型: {len(self.available_models) - len(self.used_models) - 1}")
        
        return True
    
    def has_available_models(self):
        """检查是否还有可用模型"""
        return len(self.used_models) < len(self.available_models)


class BatchGeneratorWithAutoSwitch:
    """带自动模型切换的批量生成器"""
    
    def __init__(self, workers=15, num_tests=8):
        self.workers = workers
        self.num_tests = num_tests
        self.model_manager = ModelManager()
        self.max_retries_per_batch = 3  # 每批最多重试3次
    
    def run_batch_generation(self):
        """运行批量生成"""
        cmd = [
            "python3",
            "/home/changdi/sactor/batch_generate_tests.py",
            "--workers", str(self.workers),
            "--num-tests", str(self.num_tests)
        ]
        
        print(f"\n🚀 启动批量测试生成")
        print(f"   命令: {' '.join(cmd)}")
        print(f"   当前模型: {self.model_manager.get_current_model()}")
        print()
        
        # 使用Popen实时显示输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # 实时读取输出并检测403错误
        quota_errors = 0
        last_output_time = time.time()
        
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line, end='')
                last_output_time = time.time()
                
                # 检测403/429错误或quota相关错误
                line_lower = line.lower()
                if (('403' in line or '429' in line) or
                    ('quota' in line_lower and ('error' in line_lower or 'exceeded' in line_lower or 'insufficient' in line_lower)) or
                    'rate limit' in line_lower or 'ratelimiterror' in line_lower or
                    'permissiondeniederror' in line_lower or 'permission denied' in line_lower or
                    'insufficient_quota' in line_lower or
                    ('api' in line_lower and '配额' in line) or  # 中文配额错误
                    '🚫' in line or '💰' in line):  # emoji标记的错误
                    quota_errors += 1
                    print(f"\n⚠️  [自动切换] 检测到配额错误 (第{quota_errors}次): {line.strip()[:100]}")
                    
                    # 检测到1次就立即切换模型
                    if quota_errors >= 1:
                        print("\n" + "="*80)
                        print("🔄 检测到配额错误 (403/429)，立即切换模型...")
                        print("="*80)
                        
                        # 终止当前进程
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        
                        # 切换模型
                        if self.model_manager.switch_to_next_model():
                            print("\n等待5秒后重新开始...")
                            time.sleep(5)
                            # 递归重新运行
                            return self.run_batch_generation()
                        else:
                            print("\n❌ 无法切换模型，停止运行")
                            return False
        
        process.wait()
        return_code = process.returncode
        
        if return_code == 0:
            print("\n✅ 批量生成完成！")
            return True
        else:
            print(f"\n⚠️  进程异常退出，返回码: {return_code}")
            return False
    
    def run_with_auto_recovery(self):
        """带自动恢复的运行"""
        retry_count = 0
        
        while retry_count < self.max_retries_per_batch:
            try:
                success = self.run_batch_generation()
                
                if success:
                    print("\n🎉 所有任务完成！")
                    return True
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  用户中断")
                print("   进度已保存，可以稍后继续运行")
                return False
                
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")
                import traceback
                traceback.print_exc()
            
            retry_count += 1
            
            if retry_count < self.max_retries_per_batch and self.model_manager.has_available_models():
                print(f"\n🔄 第 {retry_count} 次重试...")
                time.sleep(10)
            else:
                break
        
        print("\n❌ 达到最大重试次数或无可用模型")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='带自动模型切换的批量测试生成')
    parser.add_argument('--workers', type=int, default=15, help='并行线程数（默认：15）')
    parser.add_argument('--num-tests', type=int, default=8, help='每个文件的测试数量（默认：8）')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("🤖 SACToR 批量测试生成 - 智能模型切换版")
    print("="*80)
    print("✨ 特性:")
    print("   - 自动检测403/quota错误")
    print("   - 自动切换到下一个可用模型")
    print("   - 断点续传支持")
    print("   - 实时日志输出")
    print("="*80)
    
    generator = BatchGeneratorWithAutoSwitch(
        workers=args.workers,
        num_tests=args.num_tests
    )
    
    success = generator.run_with_auto_recovery()
    
    if success:
        print("\n✅ 任务成功完成！")
        sys.exit(0)
    else:
        print("\n⚠️  任务未完全完成")
        sys.exit(1)


if __name__ == "__main__":
    main()

