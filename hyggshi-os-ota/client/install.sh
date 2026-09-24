#!/usr/bin/env bash
# ==============================================================================
# Installation script for Hyggshi OS OTA Client
# Supports both local repository run and direct one-liner via:
# curl -fsSL <URL>/install.sh | sudo bash
# ==============================================================================
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "❌ Please run the installer with superuser privileges (sudo ./install.sh or curl ... | sudo bash)"
    exit 1
fi

RAW_BASE_URL="https://raw.githubusercontent.com/Hyggshi-OS-Research-Technology/Hyggshi-OS-Releases/main/hyggshi-os-ota/client"

# Check if running from a local checkout directory containing bin/hyggshi-ota
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

fetch_install_file() {
    local rel_path="$1"
    local dest_path="$2"
    local mode="$3"

    if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/$rel_path" ]; then
        install -m "$mode" "$SCRIPT_DIR/$rel_path" "$dest_path"
    else
        mkdir -p "$(dirname "$dest_path")"
        curl -fsSL "$RAW_BASE_URL/$rel_path" -o "$dest_path"
        chmod "$mode" "$dest_path"
    fi
}

echo "==> Installing Hyggshi OS OTA Client..."

# 0. Ensure required dependencies (jq, curl)
if ! command -v jq >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
    echo "  [0/4] Installing required system tools (jq, curl)..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq || true
    apt-get install -y -qq jq curl 2>/dev/null || true
fi

# 1. Install CLI binary
echo "  [1/4] Installing hyggshi-ota CLI tool to /usr/local/bin/..."
fetch_install_file "bin/hyggshi-ota" "/usr/local/bin/hyggshi-ota" "0755"

# 2. Initialize /etc/hyggshi-release if not present
if [ ! -f /etc/hyggshi-release ]; then
    echo "  [2/4] Initializing OS identification file /etc/hyggshi-release..."
    fetch_install_file "etc/hyggshi-release" "/etc/hyggshi-release" "0644"
else
    echo "  [2/4] Preserving existing /etc/hyggshi-release."
fi

# 3. Initialize /etc/hyggshi-ota.conf if not present
if [ ! -f /etc/hyggshi-ota.conf ]; then
    echo "  [3/4] Installing configuration file /etc/hyggshi-ota.conf..."
    fetch_install_file "etc/hyggshi-ota.conf" "/etc/hyggshi-ota.conf" "0644"
else
    echo "  [3/4] Preserving existing configuration in /etc/hyggshi-ota.conf."
fi

# 4. Register systemd timer if systemd is available
if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
    echo "  [4/4] Registering periodic background update check Systemd timer..."
    fetch_install_file "systemd/hyggshi-ota-check.service" "/etc/systemd/system/hyggshi-ota-check.service" "0644"
    fetch_install_file "systemd/hyggshi-ota-check.timer" "/etc/systemd/system/hyggshi-ota-check.timer" "0644"
    systemctl daemon-reload
    systemctl enable --now hyggshi-ota-check.timer 2>/dev/null || true
    echo "      ✔ Systemd timer successfully enabled and started."
else
    echo "  [4/4] Skipping systemd registration (systemd not running or in container)."
fi

echo ""
echo "✅ Hyggshi OS OTA Client installed successfully!"
echo ""
echo "Quick Commands:"
echo "  hyggshi-ota status       # View system release and update channel"
echo "  hyggshi-ota check        # Check for new updates"
echo "  sudo hyggshi-ota upgrade # Upgrade operating system"
echo ""
