#!/usr/bin/env python3
"""
自动模型切换的批量翻译脚本 - 用于 test_4k_accept
当检测到 API 配额错误时，自动切换到下一个可用模型
"""

import subprocess
import time
import re
import sys
import os
import signal


class ModelManager:
    def __init__(self, config_path="/home/changdi/sactor/sactor.toml"):
        self.config_path = config_path
        self.available_models = self._parse_available_models()
        self.current_model_index = 0
        
    def _parse_available_models(self):
        """从 sactor.toml 解析可用模型列表"""
        try:
            with open(self.config_path, 'r') as f:
                content = f.read()
            
            # 查找 [Qwen] 部分中的 available models 注释
            qwen_section = re.search(r'\[Qwen\](.*?)(?=\n\[|\Z)', content, re.DOTALL)
            if not qwen_section:
                print("⚠️  未找到 [Qwen] 配置部分")
                return []
            
            qwen_content = qwen_section.group(1)
            
            # 提取 available models 列表（支持三种格式）
            # 格式1: available_models = ["model1", "model2", ...]
            array_match = re.search(r'available_models\s*=\s*\[(.*?)\]', qwen_content, re.DOTALL)
            if array_match:
                models_str = array_match.group(1)
                # 提取所有引号内的模型名称
                models = re.findall(r'"([^"]+)"', models_str)
                if models:
                    print(f"✅ 找到 {len(models)} 个可用模型: {', '.join(models[:3])}...")
                    return models
            
            print("⚠️  未找到 available models 配置")
            return []
            
        except Exception as e:
            print(f"⚠️  解析配置文件失败: {e}")
            return []
    
    def get_current_model(self):
        """获取当前配置的模型"""
        try:
            with open(self.config_path, 'r') as f:
                content = f.read()
            
            # 在 [Qwen] 部分查找 model 配置
            qwen_section = re.search(r'\[Qwen\](.*?)(?=\n\[|\Z)', content, re.DOTALL)
            if not qwen_section:
                return None
            
            qwen_content = qwen_section.group(1)
            match = re.search(r'^model\s*=\s*["\']([^"\']+)["\']', qwen_content, re.MULTILINE)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            print(f"⚠️  读取当前模型失败: {e}")
            return None
    
    def switch_to_next_model(self):
        """切换到下一个模型"""
        if not self.available_models:
            print("❌ 没有可用的备用模型")
            return False
        
        current_model = self.get_current_model()
        
        # 找到当前模型在列表中的位置
        if current_model and current_model in self.available_models:
            self.current_model_index = self.available_models.index(current_model)
        
        # 切换到下一个模型
        self.current_model_index = (self.current_model_index + 1) % len(self.available_models)
        next_model = self.available_models[self.current_model_index]
        
        print(f"\n{'='*80}")
        print(f"🔄 切换模型: {current_model} -> {next_model}")
        print(f"{'='*80}\n")
        
        # 更新配置文件
        return self._update_model_in_config(next_model)
    
    def _update_model_in_config(self, new_model):
        """更新配置文件中的模型"""
        try:
            with open(self.config_path, 'r') as f:
                content = f.read()
            
            # 在 [Qwen] 部分替换 model 配置
            def replace_in_qwen(match):
                qwen_section = match.group(0)
                # 只替换 Qwen 部分中的第一个 model 配置
                updated_section = re.sub(
                    r'^(model\s*=\s*)["\']([^"\']+)["\']',
                    f'\\1"{new_model}"',
                    qwen_section,
                    count=1,
                    flags=re.MULTILINE
                )
                return updated_section
            
            new_content = re.sub(
                r'\[Qwen\].*?(?=\n\[|\Z)',
                replace_in_qwen,
                content,
                flags=re.DOTALL
            )
            
            # 写回文件
            with open(self.config_path, 'w') as f:
                f.write(new_content)
            
            print(f"✅ 配置已更新: model = \"{new_model}\"")
            return True
            
        except Exception as e:
            print(f"❌ 更新配置失败: {e}")
            return False


class AutoSwitchTranslator:
    def __init__(self, workers=10, num_tests=6):
        self.workers = workers
        self.num_tests = num_tests
        self.model_manager = ModelManager()
        self.process = None
        self.quota_error_count = 0
        self.switch_count = 0
        # 不限制最大切换次数，尝试所有可用模型
        
    def detect_quota_error(self, line):
        """检测是否是配额错误"""
        # 排除正常的进度信息（包含🔄但不是错误）
        if re.search(r'🔄\s*开始翻译', line):
            return False
        
        # 排除跳过信息
        if re.search(r'⏭️.*已存在.*跳过', line):
            return False
        
        # 配额错误模式
        quota_patterns = [
            r'Error code: 403',             # 403错误
            r'Error code: 429',             # 429 Too Many Requests
            r'rate.*limit',                 # rate limit
            r'quota.*exceeded',             # quota exceeded
            r'exhausted',                   # exhausted
            r'AllocationQuota',             # AllocationQuota错误
            r'free tier.*exhausted',        # free tier exhausted
            r'API.*配额.*错误',              # 中文错误消息
            r'配额.*用完',                   # 中文：配额用完
        ]
        
        for pattern in quota_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def run_translation(self):
        """运行翻译进程"""
        cmd = [
            "python3",
            "/home/changdi/sactor/batch_translate_test_4k_accept.py",
            "--workers", str(self.workers),
            "--num-tests", str(self.num_tests)
        ]
        
        print(f"🚀 启动翻译进程: {' '.join(cmd)}\n")
        
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
            # 实时输出并监控
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    print(line, end='', flush=True)
                    
                    # 检测配额错误
                    if self.detect_quota_error(line):
                        print(f"\n⚠️  检测到配额错误: {line.strip()}")
                        quota_error_detected = True
                        self.quota_error_count += 1
                        
                        # 立即切换模型（检测到1次就切换）
                        if self.quota_error_count >= 1:
                            print(f"\n🛑 触发模型切换条件 (检测到 {self.quota_error_count} 次配额错误)")
                            # 立即返回，不等待进程结束
                            return quota_error_detected
            
            # 只有正常读取完所有输出才等待进程
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
        print("🚀 自动模型切换 - Test 4K Accept 翻译")
        print("="*80)
        print(f"⚙️  并发数: {self.workers}")
        print(f"🧪 测试用例数: {self.num_tests} 个")
        print(f"📋 当前模型: {self.model_manager.get_current_model()}")
        print(f"📋 可用模型: {len(self.model_manager.available_models)} 个")
        print("="*80)
        print()
        
        # 循环尝试所有可用模型，直到成功或所有模型都尝试过
        while True:
            # 运行翻译
            quota_error = self.run_translation()
            
            if not quota_error:
                # 正常完成
                print("\n✅ 翻译任务完成")
                break
            
            # 检测到配额错误，切换模型
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
            
            self.quota_error_count = 0  # 重置配额错误计数
            
            # 等待几秒钟后重试
            print("⏳ 等待 5 秒后重新启动翻译...\n")
            time.sleep(5)
        
        print("\n" + "="*80)
        print("📊 任务结束")
        print("="*80)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='自动模型切换的批量翻译 (test_4k_accept)')
    parser.add_argument('--workers', type=int, default=10, help='并发数 (默认: 10)')
    parser.add_argument('--num-tests', type=int, default=6, help='使用的测试用例数量 (默认: 6)')
    args = parser.parse_args()
    
    try:
        translator = AutoSwitchTranslator(workers=args.workers, num_tests=args.num_tests)
        translator.run_with_auto_switch()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断，退出")
        sys.exit(0)


if __name__ == "__main__":
    main()

