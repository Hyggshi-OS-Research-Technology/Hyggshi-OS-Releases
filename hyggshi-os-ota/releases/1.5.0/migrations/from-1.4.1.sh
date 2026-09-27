#!/usr/bin/env bash
# Migration script: Hyggshi OS 1.4.1 -> 1.5.0
set -euo pipefail

echo "==> [Hyggshi Migration 1.4.1 -> 1.5.0] Starting system migration..."

# 1. Ensure latest APT repository configuration
REPO_FILE="/etc/apt/sources.list.d/hyggshi.list"
if [ ! -f "$REPO_FILE" ]; then
    echo "  ✔ Initializing Hyggshi APT repository configuration..."
    echo "deb [signed-by=/usr/share/keyrings/hyggshi-archive-keyring.gpg] https://hyggshi-os-foundation.github.io/apt-repo stable main" > "$REPO_FILE"
fi

# 2. Prepare configuration directory
mkdir -p /etc/hyggshi

echo "==> [Hyggshi Migration 1.4.1 -> 1.5.0] Migration completed successfully."
