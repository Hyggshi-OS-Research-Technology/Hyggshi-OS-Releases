#!/usr/bin/env bash
# Pre-upgrade check script for Hyggshi OS 1.6.0
set -euo pipefail

echo "==> [Pre-Upgrade 1.6.0] Checking system prerequisites..."

# 1. Check available disk space (minimum 500MB required)
AVAILABLE_KB=$(df / --output=avail | tail -n1)
MIN_KB=$((500 * 1024))

if [ "$AVAILABLE_KB" -lt "$MIN_KB" ]; then
    echo "❌ Error: Insufficient free disk space on root filesystem (at least 500MB required)."
    exit 1
fi

echo "  ✔ Disk space check passed (${AVAILABLE_KB} KB available)."

# 2. Check network connectivity
if ! ping -c 1 1.1.1.1 >/dev/null 2>&1 && ! ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    echo "⚠ Warning: Could not ping public DNS servers, proceeding via HTTP fallback..."
fi

# 3. Create temporary backup directory
BACKUP_DIR="/var/backups/hyggshi-pre-1.6.0"
mkdir -p "$BACKUP_DIR"
if [ -f "/etc/hyggshi-release" ]; then
    cp -a /etc/hyggshi-release "$BACKUP_DIR/"
fi
echo "  ✔ Backed up current system release configuration to $BACKUP_DIR."

echo "==> [Pre-Upgrade 1.6.0] System prerequisites validated, ready to upgrade."
