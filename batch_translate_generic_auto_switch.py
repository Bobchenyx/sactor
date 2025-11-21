#!/usr/bin/env python3
"""
通用批量翻译 - 带自动模型切换
支持任意 C 文件数据集
"""

import subprocess
import sys
import time
import re
import argparse


class ModelManager:
    def __init__(self):
        self.config_path = "/home/changdi/sactor/sactor.toml"
        self.available_models = self._parse_available_models()
        self.current_model_index = 0
        
    def _parse_available_models(self):
        """从 sactor.toml 解析可用模型列表"""
        try:
            with open(self.config_path, 'r') as f:
                content = f.read()
            
            # 查找 [Qwen] 部分中的 available models
            qwen_section = re.search(r'\[Qwen\](.*?)(?=\n\[|\Z)', content, re.DOTALL)
            if not qwen_section:
                print("⚠️  未找到 [Qwen] 配置部分")
                return []
            
            qwen_content = qwen_section.group(1)
            
            # 提取 available models 列表
            array_match = re.search(r'available_models\s*=\s*\[(.*?)\]', qwen_content, re.DOTALL)
            if array_match:
                models_str = array_match.group(1)
                models = re.findall(r'"([^"]+)"', models_str)
                if models:
                    print(f"✅ 找到 {len(models)} 个可用模型")
                    return models
            
            print("⚠️  未找到 available models 配置")
            return []
            
        except Exception as e:
            print(f"⚠️  解析配置文件失败: {e}")
            return []
    
    def get_current_model(self):
        """获取当前模型"""
        if not self.available_models:
            return "unknown"
        return self.available_models[self.current_model_index]
    
    def switch_to_next_model(self):
        """切换到下一个模型"""
        if not self.available_models:
            print("❌ 没有可用的备用模型")
            return False
        
        self.current_model_index += 1
        
        if self.current_model_index >= len(self.available_models):
            print(f"❌ 已尝试所有 {len(self.available_models)} 个可用模型")
            return False
        
        new_model = self.available_models[self.current_model_index]
        
        print(f"\n{'='*80}")
        print(f"🔄 切换到备用模型: {new_model}")
        print(f"   (第 {self.current_model_index + 1}/{len(self.available_models)} 个模型)")
        print(f"{'='*80}\n")
        
        # 更新配置文件
        try:
            with open(self.config_path, 'r') as f:
                content = f.read()
            
            # 替换 model = "xxx" 行
            new_content = re.sub(
                r'(\[Qwen\].*?model\s*=\s*")[^"]+(")',
                f'\\1{new_model}\\2',
                content,
                flags=re.DOTALL
            )
            
            with open(self.config_path, 'w') as f:
                f.write(new_content)
            
            print(f"✅ 已更新配置: model = \"{new_model}\"")
            return True
            
        except Exception as e:
            print(f"❌ 更新配置失败: {e}")
            return False


class AutoSwitchTranslator:
    def __init__(self, c_files_dir, json_dir, output_dir, workers=10, num_tests=6):
        self.c_files_dir = c_files_dir
        self.json_dir = json_dir
        self.output_dir = output_dir
        self.workers = workers
        self.num_tests = num_tests
        self.model_manager = ModelManager()
        self.process = None
        self.quota_error_count = 0
        self.switch_count = 0
    
    def detect_quota_error(self, line):
        """检测是否是配额错误"""
        # 排除正常的进度信息
        if re.search(r'🔄\s*开始翻译', line):
            return False
        
        # 排除速度统计
        if re.search(r'速度.*\d+\.\d+个/秒', line):
            return False
        
        quota_patterns = [
            r'Error code: 403',
            r'Error code: 429',
            r'rate.*limit',
            r'quota.*exceeded',
            r'exhausted',
            r'AllocationQuota',
            r'free tier.*exhausted',
            r'API.*配额.*错误',
            r'配额.*用完',
            r'AccessDenied.Unpurchased',
        ]
        
        line_lower = line.lower()
        for pattern in quota_patterns:
            if re.search(pattern, line_lower, re.IGNORECASE):
                return True
        return False
    
    def run_translation(self):
        """运行翻译进程"""
        cmd = [
            "python3",
            "/home/changdi/sactor/batch_translate_generic.py",
            "--c-files", self.c_files_dir,
            "--json-files", self.json_dir,
            "--output", self.output_dir,
            "--workers", str(self.workers),
            "--num-tests", str(self.num_tests)
        ]
        
        print(f"🚀 启动翻译进程:")
        print(f"   C文件: {self.c_files_dir}")
        print(f"   JSON: {self.json_dir}")
        print(f"   输出: {self.output_dir}")
        print(f"   并发: {self.workers}, 测试: {self.num_tests}\n")
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        quota_error_detected = False
        
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    print(line, end='')
                    
                    if self.detect_quota_error(line):
                        print(f"\n⚠️  检测到配额错误: {line.strip()}")
                        quota_error_detected = True
                        self.quota_error_count += 1
                        return quota_error_detected
            
            self.process.wait()
            return quota_error_detected
            
        except KeyboardInterrupt:
            print("\n\n⚠️  收到中断信号，正在停止...")
            self.process.terminate()
            self.process.wait()
            raise
    
    def run_with_auto_switch(self):
        """运行带自动切换的翻译"""
        print("="*80)
        print("🚀 自动模型切换 - 通用批量翻译")
        print("="*80)
        print(f"📁 C文件: {self.c_files_dir}")
        print(f"📁 输出: {self.output_dir}")
        print(f"⚙️  并发: {self.workers}, 测试: {self.num_tests}")
        print(f"📋 当前模型: {self.model_manager.get_current_model()}")
        print(f"📋 可用模型: {len(self.model_manager.available_models)} 个")
        print("="*80)
        print()
        
        while True:
            quota_error = self.run_translation()
            
            if not quota_error:
                print("\n✅ 翻译任务完成")
                break
            
            self.switch_count += 1
            print(f"\n⚠️  配额错误 (第 {self.switch_count} 次切换)")
            
            # 停止当前进程
            if self.process and self.process.poll() is None:
                print("🛑 停止当前翻译进程...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    print("⚠️  进程未响应，强制终止...")
                    self.process.kill()
                    self.process.wait()
            
            # 切换模型
            if not self.model_manager.switch_to_next_model():
                print("❌ 模型切换失败，停止翻译")
                break
            
            # 检查是否已经尝试过所有模型
            if self.switch_count >= len(self.model_manager.available_models):
                print(f"\n⚠️  已尝试所有 {len(self.model_manager.available_models)} 个可用模型，停止翻译")
                break
            
            self.quota_error_count = 0
            
            print("⏳ 等待 5 秒后重新启动翻译...\n")
            time.sleep(5)
        
        print("\n" + "="*80)
        print("📊 任务结束")
        print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description='通用批量翻译 - 带自动模型切换',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

1. 翻译 test_4k_accept (第1-2个Accepted):
   python3 batch_translate_generic_auto_switch.py \\
       --c-files /home/changdi/CodeNet/test_4k_accept \\
       --json-files /home/changdi/sactor/generated_tests \\
       --output /home/changdi/sactor/translated_rust_4k \\
       --workers 10

2. 翻译 test_4k_accept_34 (第3-4个Accepted):
   python3 batch_translate_generic_auto_switch.py \\
       --c-files /home/changdi/CodeNet/test_4k_accept_34 \\
       --json-files /home/changdi/sactor/generated_tests \\
       --output /home/changdi/sactor/translated_rust_4k_34 \\
       --workers 10 \\
       --num-tests 8
        """
    )
    
    parser.add_argument('--c-files', required=True,
                       help='C文件目录')
    parser.add_argument('--json-files', required=True,
                       help='JSON测试文件目录')
    parser.add_argument('--output', required=True,
                       help='输出目录')
    parser.add_argument('--workers', type=int, default=10,
                       help='并发数 (默认: 10)')
    parser.add_argument('--num-tests', type=int, default=6,
                       help='使用的测试用例数量 (默认: 6)')
    
    args = parser.parse_args()
    
    try:
        translator = AutoSwitchTranslator(
            c_files_dir=args.c_files,
            json_dir=args.json_files,
            output_dir=args.output,
            workers=args.workers,
            num_tests=args.num_tests
        )
        translator.run_with_auto_switch()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断，退出")
        sys.exit(0)


if __name__ == "__main__":
    main()

