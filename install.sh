#!/bin/bash
set -e

echo "==> Installing Hyggshi OS APT repository..."

# Add GPG public key
curl -fsSL https://hyggshi-os-foundation.github.io/apt-repo/hyggshi-archive-keyring.gpg | \
  sudo gpg --dearmor -o /usr/share/keyrings/hyggshi-archive-keyring.gpg

# Add repo source
echo "deb [signed-by=/usr/share/keyrings/hyggshi-archive-keyring.gpg] https://hyggshi-os-foundation.github.io/apt-repo stable main" | \
  sudo tee /etc/apt/sources.list.d/hyggshi.list > /dev/null

# Update package list
sudo hyggshi-ota --check
echo "To update, please run: sudo hyggshi-ota --upgrade"
echo ""
echo "Hyggshi OS APT repository installed successfully!"
echo ""
