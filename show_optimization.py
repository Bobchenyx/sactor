#!/usr/bin/env python3
"""
显示优化配置的详细信息
"""

import toml

def show_config_diff(before_file, after_file):
    """显示配置文件的差异"""
    
    print("\n" + "="*80)
    print("🔧 SACToR 配置优化对比")
    print("="*80)
    
    # 读取配置
    with open(before_file, 'r') as f:
        before = toml.load(f)
    
    with open(after_file, 'r') as f:
        after = toml.load(f)
    
    # 对比关键参数
    print(f"\n{'参数':<40} {'优化前':<20} {'优化后':<20}")
    print("-" * 80)
    
    # General section
    print(f"{'max_translation_attempts':<40} {before['general']['max_translation_attempts']:>19} {after['general']['max_translation_attempts']:>19}")
    print(f"{'max_verifier_harness_attempts':<40} {before['general']['max_verifier_harness_attempts']:>19} {after['general']['max_verifier_harness_attempts']:>19}")
    
    # Test generator
    print(f"{'test_generator.max_attempts':<40} {before['test_generator']['max_attempts']:>19} {after['test_generator']['max_attempts']:>19}")
    
    # Temperature
    before_temp = before.get('Qwen', {}).get('temperature', '未设置')
    after_temp = after.get('Qwen', {}).get('temperature', '未设置')
    print(f"{'Qwen.temperature':<40} {str(before_temp):>19} {str(after_temp):>19}")
    
    # System message length
    before_msg_len = len(before['general']['system_message'])
    after_msg_len = len(after['general']['system_message'])
    print(f"{'system_message长度 (字符)':<40} {before_msg_len:>19} {after_msg_len:>19}")
    
    print("\n" + "="*80)
    print("📊 预期效果")
    print("="*80)
    
    # 计算减少的尝试次数
    before_total_attempts = (
        before['general']['max_translation_attempts'] +
        before['general']['max_verifier_harness_attempts'] +
        before['test_generator']['max_attempts']
    )
    
    after_total_attempts = (
        after['general']['max_translation_attempts'] +
        after['general']['max_verifier_harness_attempts'] +
        after['test_generator']['max_attempts']
    )
    
    reduction = (before_total_attempts - after_total_attempts) / before_total_attempts * 100
    
    print(f"\n最大总尝试次数:")
    print(f"  优化前: {before_total_attempts} 次")
    print(f"  优化后: {after_total_attempts} 次")
    print(f"  减少: {reduction:.1f}%")
    
    # Token估算
    avg_tokens_per_attempt = 2000
    before_tokens = before_total_attempts * avg_tokens_per_attempt
    after_tokens = after_total_attempts * avg_tokens_per_attempt
    token_reduction = (before_tokens - after_tokens) / before_tokens * 100
    
    print(f"\nToken使用量估算 (每个文件):")
    print(f"  优化前: ~{before_tokens:,} tokens")
    print(f"  优化后: ~{after_tokens:,} tokens")
    print(f"  减少: {token_reduction:.1f}%")
    
    # API成本估算 (假设 $0.002/1K tokens for qwen)
    cost_per_1k_tokens = 0.002
    before_cost = before_tokens / 1000 * cost_per_1k_tokens
    after_cost = after_tokens / 1000 * cost_per_1k_tokens
    cost_reduction = (before_cost - after_cost) / before_cost * 100
    
    print(f"\nAPI成本估算 (每个文件):")
    print(f"  优化前: ${before_cost:.4f}")
    print(f"  优化后: ${after_cost:.4f}")
    print(f"  节省: {cost_reduction:.1f}%")
    
    # 对于500个文件的总成本
    print(f"\n处理500个文件的总成本:")
    print(f"  优化前: ${before_cost * 500:.2f}")
    print(f"  优化后: ${after_cost * 500:.2f}")
    print(f"  节省: ${(before_cost - after_cost) * 500:.2f}")
    
    print("\n" + "="*80)
    print("💡 关键优化")
    print("="*80)
    print("\n1. ✅ 减少重试次数")
    print("   - 翻译尝试: 20 → 5 (-75%)")
    print("   - 验证尝试: 6 → 3 (-50%)")
    print("   - 测试生成: 6 → 3 (-50%)")
    
    print("\n2. ✅ 优化System Message")
    print(f"   - 长度: {before_msg_len} → {after_msg_len} 字符 ({(after_msg_len - before_msg_len) / before_msg_len * 100:+.1f}%)")
    print("   - 更简洁，提高cache命中率")
    
    print("\n3. ✅ 降低Temperature")
    print(f"   - 温度: {before_temp} → {after_temp}")
    print("   - 减少随机性，更快收敛")
    
    print("\n" + "="*80)
    print("⚠️  注意事项")
    print("="*80)
    print("\n1. 成功率可能略微下降 (预计 70% → 65-68%)")
    print("2. 对于复杂程序，5次尝试可能不够")
    print("3. 建议先小规模测试（50个文件）验证效果")
    print("4. 可以根据实际效果调整参数")
    
    print("\n" + "="*80)
    print("🚀 开始使用")
    print("="*80)
    print("\n当前已应用优化配置！可以直接运行:")
    print("\n  cd /home/changdi/sactor")
    print("  python3 batch_generate_tests.py --sample-size 50 --workers 5 --num-tests 8")
    print("\n如需回滚:")
    print("\n  cp /home/changdi/sactor/sactor.toml.before_optimization /home/changdi/sactor/sactor.toml")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    before_file = "/home/changdi/sactor/sactor.toml.before_optimization"
    after_file = "/home/changdi/sactor/sactor.toml"
    show_config_diff(before_file, after_file)

