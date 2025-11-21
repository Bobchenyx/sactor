#!/bin/bash
# 翻译整个 CodeNet 所有 Accepted 的 C 文件
# 支持断点续传

# 参数设置
WORKERS=${1:-10}        # 并发数，默认10
NUM_TESTS=${2:-6}       # 测试用例数，默认6

echo "================================================================================"
echo "🚀 CodeNet 全量 Accepted C → Rust 翻译 (从第5个开始)"
echo "================================================================================"
echo ""
echo "📁 输入: CodeNet 所有 Accepted C 文件"
echo "📁 输出: /home/changdi/sactor/translated_rust_all_accepted"
echo "📝 进度: /home/changdi/sactor/translation_progress.json"
echo ""
echo "⚙️  配置:"
echo "   - 并发数: $WORKERS"
echo "   - 测试用例数: $NUM_TESTS"
echo "   - 断点续传: 启用"
echo "   - 跳过策略: 跳过每题前4个Accepted"
echo ""
echo "💡 说明:"
echo "   - 第1-2批已翻译: test_4k_accept (前2个)"
echo "   - 第3-4批已翻译: test_4k_accept_34 (第3-4个)"
echo "   - 本次翻译: 第5个及以后的所有Accepted"
echo ""
echo "💡 提示:"
echo "   - 按 Ctrl+C 可以安全中断"
echo "   - 进度会自动保存"
echo "   - 重新运行会自动从中断处继续"
echo ""
echo "================================================================================"
echo ""

cd /home/changdi/sactor

python3 -u translate_all_codenet_accepted.py \
    --resume \
    --workers "$WORKERS" \
    --num-tests "$NUM_TESTS"

