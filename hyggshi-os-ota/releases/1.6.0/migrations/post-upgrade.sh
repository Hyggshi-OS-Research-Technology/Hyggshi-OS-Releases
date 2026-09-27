#!/usr/bin/env bash
# Post-upgrade script for Hyggshi OS 1.6.0
set -euo pipefail

echo "==> [Post-Upgrade 1.6.0] Performing cleanup and finalizing system configuration..."

# 1. Update desktop database caches
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q || true
fi

# 2. Clean obsolete packages
DEBIAN_FRONTEND=noninteractive apt-get autoremove -y -qq 2>/dev/null || true

# 3. Record event in OTA log file
LOG_FILE="/var/log/hyggshi-ota.log"
echo "[$(date -Iseconds)] Successfully upgraded to Hyggshi OS 1.6.0" >> "$LOG_FILE"

echo "==> [Post-Upgrade 1.6.0] Post-upgrade tasks finalized."
