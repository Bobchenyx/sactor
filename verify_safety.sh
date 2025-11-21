#!/bin/bash

echo "=== Rust 代码安全性验证 ==="

# 1. 编译检查
echo "1. 编译检查..."
cargo check --manifest-path /tmp/sactor_atoi/result/translated_code_idiomatic/Cargo.toml
if [ $? -eq 0 ]; then
    echo "✅ 编译通过"
else
    echo "❌ 编译失败"
fi

# 2. Clippy 检查
echo "2. Clippy 静态分析..."
cargo clippy --manifest-path /tmp/sactor_atoi/result/translated_code_idiomatic/Cargo.toml
if [ $? -eq 0 ]; then
    echo "✅ Clippy 检查通过"
else
    echo "❌ Clippy 发现问题"
fi

# 3. 检查 unsafe 关键字
echo "3. 检查 unsafe 关键字..."
if grep -r "unsafe" /tmp/sactor_atoi/result/translated_code_idiomatic/ --include="*.rs"; then
    echo "❌ 发现 unsafe 关键字"
else
    echo "✅ 没有 unsafe 关键字"
fi

# 4. 运行测试
echo "4. 运行测试..."
cargo test --manifest-path /tmp/sactor_atoi/result/translated_code_idiomatic/Cargo.toml
if [ $? -eq 0 ]; then
    echo "✅ 所有测试通过"
else
    echo "❌ 测试失败"
fi

echo "=== 验证完成 ==="
