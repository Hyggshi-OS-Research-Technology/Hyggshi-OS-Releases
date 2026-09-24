#!/usr/bin/env bash
# Migration script: Hyggshi OS 1.4.1 -> 1.6.0
set -euo pipefail

echo "==> [Hyggshi Migration 1.4.1 -> 1.6.0] Starting system migration..."

# 1. Update APT keyring if available
KEY_SRC="/tmp/hyggshi-ota-run/keys/hyggshi-ota.gpg"
if [ -f "$KEY_SRC" ]; then
    echo "  ✔ Updating Hyggshi repository keyring..."
    install -m 0644 "$KEY_SRC" /usr/share/keyrings/hyggshi-archive-keyring.gpg
fi

# 2. Ensure Hyggshi APT repository configuration exists
REPO_FILE="/etc/apt/sources.list.d/hyggshi.list"
if [ ! -f "$REPO_FILE" ]; then
    echo "  ✔ Initializing Hyggshi APT repository configuration..."
    echo "deb [signed-by=/usr/share/keyrings/hyggshi-archive-keyring.gpg] https://hyggshi-os-foundation.github.io/apt-repo stable main" > "$REPO_FILE"
fi

# 3. Synchronize package index and upgrade packages via APT
echo "  ✔ Synchronizing package index (apt update)..."
apt-get update -qq || true

echo "  ✔ Upgrading core system packages..."
DEBIAN_FRONTEND=noninteractive apt-get --only-upgrade install -y -qq nexfetch nexcode-ide 2>/dev/null || true

echo "==> [Hyggshi Migration 1.4.1 -> 1.6.0] System migration completed successfully."
