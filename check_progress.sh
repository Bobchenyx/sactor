#!/bin/bash
clear
echo "================================================================================"
echo "🚀 C-to-Rust 翻译进度监控"
echo "================================================================================"
echo ""

# 统计数据
total_rs=$(find /home/changdi/sactor/translated_rust_4k -name "*.rs" 2>/dev/null | wc -l)
combined_rs=$(find /home/changdi/sactor/translated_rust_4k -name "combined.rs" 2>/dev/null | wc -l)
success_count=$(find /home/changdi/sactor/translated_rust_4k -type d -name "translated_code_unidiomatic" 2>/dev/null | wc -l)
total_tasks=1561

# 计算进度（使用整数运算）
progress=$((success_count * 100 / total_tasks))
bar_length=50
filled=$((progress * bar_length / 100))
empty=$((bar_length - filled))

# 显示统计
echo "📊 翻译统计:"
echo "   ✅ 成功翻译: $success_count / $total_tasks 个C文件"
echo "   📝 生成.rs文件: $total_rs 个"
echo "   📦 combined.rs: $combined_rs 个"
echo ""

# 进度条
printf "📈 进度: ["
printf "%${filled}s" | tr ' ' '█'
printf "%${empty}s" | tr ' ' '░'
printf "] %d%%\n" "$progress"
echo ""

# 进程状态
process_count=$(ps aux | grep batch_translate_test_4k | grep -v grep | wc -l)
if [ $process_count -gt 0 ]; then
    echo "⚙️  状态: 运行中 ✓"
    echo "   模型: qwen3-coder-flash"
    echo "   并发: 10 workers"
    echo "   日志: /home/changdi/sactor/translate_coder_flash.log"
else
    echo "⚠️  状态: 已停止"
fi

echo ""
echo "================================================================================"
echo "💡 使用方法:"
echo "   watch -n 10 bash /home/changdi/sactor/check_progress.sh  # 每10秒刷新"
echo "   tail -f /home/changdi/sactor/translate_coder_flash.log   # 查看实时日志"
echo "================================================================================"
