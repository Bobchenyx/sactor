#!/bin/bash
# 启动 CodeNet 第21-40批 Accepted C → Rust 翻译脚本

# 参数设置
WORKERS=${1:-10}        # 并发数，默认10
NUM_TESTS=${2:-6}       # 测试用例数，默认6

echo "================================================================================"
echo "🚀 CodeNet 第21-40批 Accepted C → Rust 翻译"
echo "================================================================================"
echo ""
echo "📁 输入: CodeNet 每题第21-40个 Accepted C 文件"
echo "📁 输出: /home/changdi/sactor/translated_rust_21_to_40"
echo "📝 进度: /home/changdi/sactor/translation_progress_21_to_40.json"
echo "📋 日志: /home/changdi/sactor/translation_log_21_to_40.txt"
echo ""
echo "⚙️  配置:"
echo "   - 并发数: $WORKERS"
echo "   - 测试用例数: $NUM_TESTS"
echo "   - 翻译范围: 每题第21-40个 (索引20-39)"
echo "   - 如果题目没有40个Accepted，会自动跳过"
echo ""
echo "💡 调整参数:"
echo "   ./start_translate_21_to_40.sh [并发数] [测试数]"
echo "   例如: ./start_translate_21_to_40.sh 20 10"
echo ""
echo "================================================================================"
echo ""

cd /home/changdi/sactor

python3 -u translate_codenet_21_to_40.py \
    --workers "$WORKERS" \
    --num-tests "$NUM_TESTS"

echo ""
echo "================================================================================"
echo "✅ 翻译脚本已退出"
echo "================================================================================"
echo ""
echo "📊 查看结果:"
echo "   - 输出目录: /home/changdi/sactor/translated_rust_21_to_40"
echo "   - 日志文件: tail -f /home/changdi/sactor/translation_log_21_to_40.txt"
echo "   - 进度文件: cat /home/changdi/sactor/translation_progress_21_to_40.json"
echo ""
echo "🔄 继续翻译（会从断点继续）:"
echo "   ./start_translate_21_to_40.sh $WORKERS $NUM_TESTS"
echo ""
echo "================================================================================"

