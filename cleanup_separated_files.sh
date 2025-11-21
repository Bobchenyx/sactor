#!/bin/bash
# 清理 SACToR 生成的分离文件，只保留 combined.rs

echo "================================================================================
🧹 清理 SACToR 生成的分离文件
================================================================================
"

BASE_DIR="/home/changdi/sactor/translated_rust_4k"

# 统计删除前的情况
echo "📊 清理前统计:"
echo "   combined.rs 文件: $(find "$BASE_DIR" -name "combined.rs" 2>/dev/null | wc -l) 个"
echo "   functions 目录: $(find "$BASE_DIR" -type d -name "functions" 2>/dev/null | wc -l) 个"
echo "   structs 目录: $(find "$BASE_DIR" -type d -name "structs" 2>/dev/null | wc -l) 个"
echo "   global_vars 目录: $(find "$BASE_DIR" -type d -name "global_vars" 2>/dev/null | wc -l) 个"
echo ""

# 计算占用空间
BEFORE_SIZE=$(du -sh "$BASE_DIR" 2>/dev/null | cut -f1)
echo "   总占用空间: $BEFORE_SIZE"
echo ""

read -p "确认删除分离文件？(y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消"
    exit 0
fi

echo ""
echo "🗑️  开始清理..."

# 删除 functions 目录
DELETED_FUNCTIONS=$(find "$BASE_DIR" -type d -name "functions" 2>/dev/null | wc -l)
find "$BASE_DIR" -type d -name "functions" -exec rm -rf {} + 2>/dev/null
echo "   ✅ 删除了 $DELETED_FUNCTIONS 个 functions 目录"

# 删除 structs 目录
DELETED_STRUCTS=$(find "$BASE_DIR" -type d -name "structs" 2>/dev/null | wc -l)
find "$BASE_DIR" -type d -name "structs" -exec rm -rf {} + 2>/dev/null
echo "   ✅ 删除了 $DELETED_STRUCTS 个 structs 目录"

# 删除 global_vars 目录
DELETED_GLOBALS=$(find "$BASE_DIR" -type d -name "global_vars" 2>/dev/null | wc -l)
find "$BASE_DIR" -type d -name "global_vars" -exec rm -rf {} + 2>/dev/null
echo "   ✅ 删除了 $DELETED_GLOBALS 个 global_vars 目录"

echo ""
echo "📊 清理后统计:"
echo "   combined.rs 文件: $(find "$BASE_DIR" -name "combined.rs" 2>/dev/null | wc -l) 个 (保留)"

AFTER_SIZE=$(du -sh "$BASE_DIR" 2>/dev/null | cut -f1)
echo "   总占用空间: $AFTER_SIZE (之前: $BEFORE_SIZE)"

echo ""
echo "================================================================================
✅ 清理完成
================================================================================
"
