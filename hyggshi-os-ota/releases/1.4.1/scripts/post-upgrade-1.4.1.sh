#!/usr/bin/env bash
# Post-upgrade script for Hyggshi OS 1.4.1
set -euo pipefail

echo "==> [Post-Upgrade 1.4.1] Finalizing Hyggshi OS 1.4.1 configuration..."

# 1. Update Flatpak & Flathub configurations if installed
if command -v flatpak >/dev/null 2>&1; then
    echo "  ✔ Verifying and updating Flatpak / Flathub remotes..."
    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true
    flatpak update --appstream 2>/dev/null || true
fi

# 2. Record OTA upgrade in log
LOG_FILE="/var/log/hyggshi-ota.log"
echo "[$(date -Iseconds)] Successfully upgraded to Hyggshi OS 1.4.1 (Verdant Valley)" >> "$LOG_FILE"

echo "==> [Post-Upgrade 1.4.1] Completed successfully."
