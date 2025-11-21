#!/bin/bash
# 翻译 test_4k_accept_34 (第3-4个Accepted) 的快速启动脚本

echo "================================================================================"
echo "🚀 开始翻译 test_4k_accept_34 (第3-4个Accepted C文件)"
echo "================================================================================"
echo ""
echo "📁 输入: /home/changdi/CodeNet/test_4k_accept_34"
echo "📁 测试JSON: /home/changdi/sactor/generated_tests"
echo "📁 输出: /home/changdi/sactor/translated_rust_4k_34"
echo ""
echo "⚙️  配置:"
echo "   - 自动模型切换: 启用"
echo "   - 并发数: 10"
echo "   - 测试用例数: 6"
echo ""
echo "================================================================================"
echo ""

cd /home/changdi/sactor

python3 -u batch_translate_generic_auto_switch.py \
    --c-files /home/changdi/CodeNet/test_4k_accept_34 \
    --json-files /home/changdi/sactor/generated_tests \
    --output /home/changdi/sactor/translated_rust_4k_34 \
    --workers 10 \
    --num-tests 6

echo ""
echo "================================================================================"
echo "📊 翻译任务结束"
echo "================================================================================"

