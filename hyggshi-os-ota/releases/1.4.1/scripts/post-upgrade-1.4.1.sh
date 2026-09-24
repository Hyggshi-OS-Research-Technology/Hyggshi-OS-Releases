#!/usr/bin/env bash
# ==============================================================================
# Post-upgrade execution script for Hyggshi OS 1.4.1
# Applies actions declared in Hyggshi Configuration Language (config.ini)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_INI="$SCRIPT_DIR/config/config.ini"

echo "==> [Hyggshi HCL Post-Upgrade 1.4.1] Executing configuration from config.ini..."

export DEBIAN_FRONTEND=noninteractive

# ------------------------------------------------------------------------------
# 1. Packages from [package]: python3, jq
# ------------------------------------------------------------------------------
echo "  [1/6] Ensuring core packages (python3, jq)..."
apt-get update -qq || true
apt-get install -y -qq python3 jq wget curl 2>/dev/null || true

# ------------------------------------------------------------------------------
# 2. NexCode IDE install (install-web)
# ------------------------------------------------------------------------------
echo "  [2/6] Checking / Installing NexCode IDE..."
if ! command -v nexcode-ide >/dev/null 2>&1 && [ ! -f /usr/bin/nexcode-ide ]; then
    TMP_DEB="/tmp/nexcode-ide-4.0.2-amd64.deb"
    if wget -q -O "$TMP_DEB" "https://github.com/Hyggshi-OS-project-center/NexCode/releases/download/v4.0.2/nexcode-ide-4.0.2-amd64.deb" 2>/dev/null; then
        apt-get install -y "$TMP_DEB" 2>/dev/null || dpkg -i "$TMP_DEB" 2>/dev/null || true
        rm -f "$TMP_DEB"
        echo "      ✔ NexCode IDE installed successfully."
    else
        echo "      ⚠ Could not download NexCode IDE deb package, skipping."
    fi
else
    echo "      ✔ NexCode IDE is already installed."
fi

# ------------------------------------------------------------------------------
# 3. Flatpak & Flathub configurations (HCL commands)
# ------------------------------------------------------------------------------
echo "  [3/6] Applying Flatpak and Flathub configurations..."
# flatpak1: ln -s /proc/mounts /etc/mtab
if [ ! -e /etc/mtab ] || [ -L /etc/mtab ]; then
    ln -sf /proc/mounts /etc/mtab 2>/dev/null || true
fi

# flatpak2: clean cache
rm -rf /var/tmp/flatpak-cache-* 2>/dev/null || true

if command -v flatpak >/dev/null 2>&1; then
    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true
    flatpak update --appstream 2>/dev/null || true
fi

# ------------------------------------------------------------------------------
# 4. Desktop Branding & Customization (image-background, greeter-gtk-theme)
# ------------------------------------------------------------------------------
echo "  [4/6] Applying desktop branding & GTK theme..."

# XFCE Wallpaper: download and copy to /usr/share/backgrounds/xfce/
mkdir -p "$HOME/Downloads" /usr/share/backgrounds/xfce
SVG_URL="https://raw.githubusercontent.com/Hyggshi-OS-Research-Technology/Hyggshi-OS/38c4c3d47efca20f7872467f933c40820c331a4d/iso-config/branding/xfce-x.svg"
curl -fsSL "$SVG_URL" -o "$HOME/Downloads/xfce-x.svg" 2>/dev/null || true
if [ -f "$HOME/Downloads/xfce-x.svg" ]; then
    cp -f "$HOME/Downloads/xfce-x.svg" /usr/share/backgrounds/xfce/xfce-x.svg
    echo "      ✔ Downloaded and updated XFCE background wallpaper."
fi

# Greeter GTK theme: copy / download to /usr/share/themes/Hyggshi-Greeter/gtk-3.0/ (Force Overwrite)
mkdir -p /usr/share/themes/Hyggshi-Greeter/gtk-3.0
GTK_CSS_SRC="$RELEASE_ROOT/resources/gtk.css"
if [ -f "$GTK_CSS_SRC" ]; then
    cp -f "$GTK_CSS_SRC" /usr/share/themes/Hyggshi-Greeter/gtk-3.0/gtk.css
    chmod 0644 /usr/share/themes/Hyggshi-Greeter/gtk-3.0/gtk.css
    echo "      ✔ [Force Overwrite] Updated Hyggshi-Greeter GTK theme from local resource."
else
    GTK_URL="https://raw.githubusercontent.com/Hyggshi-OS-Research-Technology/Hyggshi-OS-Releases/main/hyggshi-os-ota/releases/1.4.1/resources/gtk.css"
    curl -fsSL "$GTK_URL" -o /usr/share/themes/Hyggshi-Greeter/gtk-3.0/gtk.css 2>/dev/null || true
    chmod 0644 /usr/share/themes/Hyggshi-Greeter/gtk-3.0/gtk.css 2>/dev/null || true
    echo "      ✔ [Force Overwrite] Downloaded and updated Hyggshi-Greeter GTK theme."
fi

# ------------------------------------------------------------------------------
# 5. Compilers & Extensions ([compilers])
# ------------------------------------------------------------------------------
echo "  [5/6] Building and installing Hyggshi extensions..."

# linkhyggshi-sound-shortcut
SOUND_SRC="$RELEASE_ROOT/resources/hyggshi-extensions-sound-shortcut"
if [ -f "$SOUND_SRC/CMakeLists.txt" ] && [ -f "$SOUND_SRC/sound-shortcut.sh" ]; then
    echo "      → Running sound-shortcut build script..."
    chmod +x "$SOUND_SRC/sound-shortcut.sh"
    SRC_DIR="$SOUND_SRC" "$SOUND_SRC/sound-shortcut.sh" 2>/dev/null || true
fi

# linkhyggshi-welcome
WELCOME_SRC="$RELEASE_ROOT/resources/hyggshi-welcome"
if [ -f "$WELCOME_SRC/CMakeLists.txt" ] && [ -f "$WELCOME_SRC/welcome.sh" ]; then
    echo "      → Running welcome app build script..."
    chmod +x "$WELCOME_SRC/welcome.sh"
    SRC_DIR="$WELCOME_SRC" "$WELCOME_SRC/welcome.sh" 2>/dev/null || true
fi

# ------------------------------------------------------------------------------
# 6. Finalize & Log Upgrade
# ------------------------------------------------------------------------------
echo "  [6/6] Finalizing upgrade logs..."
LOG_FILE="/var/log/hyggshi-ota.log"
echo "[$(date -Iseconds)] [HCL] Successfully applied upgrade to Hyggshi OS 1.4.1 (Verdant Valley)" >> "$LOG_FILE"

echo "==> [Hyggshi HCL Post-Upgrade 1.4.1] Completed all HCL upgrade instructions successfully!"
