#!/bin/bash
# 翻译 test_4k_accept_34 (第3-4批) - 使用现有JSON

cd /home/changdi/sactor

echo "================================================================================"
echo "🚀 开始翻译 test_4k_accept_34 (第3-4批)"
echo "================================================================================"
echo ""
echo "📁 C文件: /home/changdi/CodeNet/test_4k_accept_34"
echo "📁 JSON: /home/changdi/sactor/generated_tests (复用现有)"
echo "📁 输出: /home/changdi/sactor/translated_rust_4k_34"
echo ""
echo "⚙️  配置:"
echo "   - 并发数: 10"
echo "   - 测试用例数: 6"
echo "   - 自动模型切换: 启用"
echo ""
echo "================================================================================"
echo ""

python3 -u batch_translate_generic_auto_switch.py \
    --c-files /home/changdi/CodeNet/test_4k_accept_34 \
    --json-files /home/changdi/sactor/generated_tests \
    --output /home/changdi/sactor/translated_rust_4k_34 \
    --workers 10 \
    --num-tests 6

