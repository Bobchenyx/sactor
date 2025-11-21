#!/bin/bash
# 在Docker中测试Qwen缓存功能

echo "================================================================================"
echo "🧪 在Docker中测试Qwen显式缓存"
echo "================================================================================"

# 创建测试C文件
TEST_DIR="/tmp/sactor_cache_test_$$"
mkdir -p "$TEST_DIR"

# 创建第一个测试C文件
cat > "$TEST_DIR/test1.c" << 'EOF'
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        printf("Usage: %s <a> <b>\n", argv[0]);
        return 1;
    }
    int a = atoi(argv[1]);
    int b = atoi(argv[2]);
    printf("%d\n", add(a, b));
    return 0;
}
EOF

# 创建第二个测试C文件
cat > "$TEST_DIR/test2.c" << 'EOF'
#include <stdio.h>

int subtract(int a, int b) {
    return a - b;
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        printf("Usage: %s <a> <b>\n", argv[0]);
        return 1;
    }
    int a = atoi(argv[1]);
    int b = atoi(argv[2]);
    printf("%d\n", subtract(a, b));
    return 0;
}
EOF

echo ""
echo "📁 测试文件已创建: $TEST_DIR"
echo "  - test1.c (加法)"
echo "  - test2.c (减法)"

# 创建输出目录
OUTPUT_DIR="/tmp/sactor_cache_output_$$"
mkdir -p "$OUTPUT_DIR"

echo ""
echo "================================================================================"
echo "📝 第一次翻译 (创建缓存)"
echo "================================================================================"

# 运行第一次翻译
docker run --rm \
  -v "$TEST_DIR:/data/c_files" \
  -v "/home/changdi/sactor/sactor.toml:/app/sactor.toml" \
  -v "$OUTPUT_DIR:/app/output" \
  sactor generate-tests \
  /data/c_files/test1.c \
  3 \
  --type bin \
  --out-test-sample-path /app/output/test1_samples.json

echo ""
echo "✅ 第一次翻译完成"

# 等待1秒
sleep 1

echo ""
echo "================================================================================"
echo "📝 第二次翻译 (应该命中缓存)"
echo "================================================================================"

# 运行第二次翻译
docker run --rm \
  -v "$TEST_DIR:/data/c_files" \
  -v "/home/changdi/sactor/sactor.toml:/app/sactor.toml" \
  -v "$OUTPUT_DIR:/app/output" \
  sactor generate-tests \
  /data/c_files/test2.c \
  3 \
  --type bin \
  --out-test-sample-path /app/output/test2_samples.json

echo ""
echo "✅ 第二次翻译完成"

echo ""
echo "================================================================================"
echo "📊 查看结果"
echo "================================================================================"

if [ -f "$OUTPUT_DIR/test1_samples.json" ]; then
    echo "✅ test1 测试用例生成成功"
    echo "   文件: $OUTPUT_DIR/test1_samples.json"
fi

if [ -f "$OUTPUT_DIR/test2_samples.json" ]; then
    echo "✅ test2 测试用例生成成功"
    echo "   文件: $OUTPUT_DIR/test2_samples.json"
fi

echo ""
echo "================================================================================"
echo "💡 如何确认缓存是否生效"
echo "================================================================================"
echo ""
echo "1. 查看SACToR输出日志中的token使用情况"
echo "2. 第二次调用的prompt_tokens中应该有cached_tokens字段"
echo "3. cached_tokens应该包含system message的tokens"
echo ""
echo "如果想查看详细的API调用统计，需要在SACToR代码中添加日志输出"
echo ""
echo "================================================================================"

# 清理
echo ""
read -p "按Enter清理测试文件..." 
rm -rf "$TEST_DIR" "$OUTPUT_DIR"
echo "🧹 测试文件已清理"

