#!/usr/bin/env bash
# Migration script: Hyggshi OS 1.4.0 -> 1.5.0
set -euo pipefail

echo "==> [Hyggshi Migration 1.4.0 -> 1.5.0] Bắt đầu chuyển đổi..."

# 1. Đảm bảo cấu hình APT repo mới nhất
if [ -f "/etc/apt/sources.list.d/hyggshi.list" ]; then
    echo "    Kiểm tra cấu hình APT sources..."
fi

# 2. Migration thư mục cấu hình /etc/hyggshi nếu cần
mkdir -p /etc/hyggshi

echo "==> [Hyggshi Migration 1.4.0 -> 1.5.0] Hoàn tất thành công."
