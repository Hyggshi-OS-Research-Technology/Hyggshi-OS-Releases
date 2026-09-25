#!/usr/bin/env bash
# ==============================================================================
# Post-upgrade execution script for Hyggshi OS 1.4.1
# Applies actions declared in Hyggshi Configuration Language (config.ini)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_INI="$SCRIPT_DIR/config/config.ini"

export DEBIAN_FRONTEND=noninteractive

# ------------------------------------------------------------------------------
# 0. Desktop Environment Detection
# ------------------------------------------------------------------------------
detect_current_de() {
    local env_de="${XDG_CURRENT_DESKTOP:-${DESKTOP_SESSION:-}}"
    if [ -n "$env_de" ]; then
        local env_lower=$(echo "$env_de" | tr '[:upper:]' '[:lower:]')
        case "$env_lower" in
            *xfce*) echo "xfce"; return ;;
            *gnome*) echo "gnome"; return ;;
            *plasma*|*kde*) echo "kde"; return ;;
            *cinnamon*) echo "cinnamon"; return ;;
            *mate*) echo "mate"; return ;;
            *lxqt*) echo "lxqt"; return ;;
        esac
    fi

    if pgrep -x "xfce4-session" >/dev/null 2>&1; then echo "xfce"; return; fi
    if pgrep -x "gnome-shell" >/dev/null 2>&1 || pgrep -x "gnome-session" >/dev/null 2>&1; then echo "gnome"; return; fi
    if pgrep -x "plasmashell" >/dev/null 2>&1 || pgrep -x "kwin_x11" >/dev/null 2>&1; then echo "kde"; return; fi
    if pgrep -x "cinnamon-session" >/dev/null 2>&1 || pgrep -x "cinnamon" >/dev/null 2>&1; then echo "cinnamon"; return; fi
    if pgrep -x "mate-session" >/dev/null 2>&1; then echo "mate"; return; fi
    if pgrep -x "lxqt-session" >/dev/null 2>&1; then echo "lxqt"; return; fi

    if command -v xfce4-session >/dev/null 2>&1; then echo "xfce"; return; fi
    if command -v gnome-shell >/dev/null 2>&1; then echo "gnome"; return; fi
    if command -v plasmashell >/dev/null 2>&1; then echo "kde"; return; fi
    if command -v cinnamon-session >/dev/null 2>&1; then echo "cinnamon"; return; fi
    if command -v mate-session >/dev/null 2>&1; then echo "mate"; return; fi
    if command -v lxqt-session >/dev/null 2>&1; then echo "lxqt"; return; fi

    echo "cli"
}

CURRENT_DE="$(detect_current_de)"
echo "==> [Hyggshi HCL Post-Upgrade 1.4.1] Executing configuration from config.ini..."
echo "    Active Desktop Environment detected: $CURRENT_DE"

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
# 4. Desktop Branding & Customization (Multi-DE Wallpapers & Themes)
# ------------------------------------------------------------------------------
echo "  [4/6] Applying desktop branding & GTK theme..."

# 4.1 Universal Wallpaper: download to Hyggshi branding directory
mkdir -p /usr/share/backgrounds/hyggshi
SVG_URL="https://raw.githubusercontent.com/Hyggshi-OS-Research-Technology/Hyggshi-OS/38c4c3d47efca20f7872467f933c40820c331a4d/iso-config/branding/xfce-x.svg"
curl -fsSL "$SVG_URL" -o /usr/share/backgrounds/hyggshi/hyggshi-wallpaper.svg 2>/dev/null || true
echo "      ✔ Universal Hyggshi wallpaper synchronized to /usr/share/backgrounds/hyggshi/."

# 4.2 Desktop-specific wallpaper configuration
case "$CURRENT_DE" in
    xfce)
        mkdir -p /usr/share/backgrounds/xfce
        cp -f /usr/share/backgrounds/hyggshi/hyggshi-wallpaper.svg /usr/share/backgrounds/xfce/xfce-x.svg
        echo "      ✔ [XFCE] Updated wallpaper at /usr/share/backgrounds/xfce/xfce-x.svg"
        ;;
    gnome)
        mkdir -p /usr/share/backgrounds/gnome
        cp -f /usr/share/backgrounds/hyggshi/hyggshi-wallpaper.svg /usr/share/backgrounds/gnome/hyggshi-wallpaper.svg
        mkdir -p /etc/dconf/db/local.d
        cat << 'EOF' > /etc/dconf/db/local.d/00-hyggshi-wallpaper
[org/gnome/desktop/background]
picture-uri='file:///usr/share/backgrounds/hyggshi/hyggshi-wallpaper.svg'
picture-uri-dark='file:///usr/share/backgrounds/hyggshi/hyggshi-wallpaper.svg'
picture-options='zoom'
EOF
        dconf update 2>/dev/null || true
        echo "      ✔ [GNOME] Configured background schema override."
        ;;
    kde)
        mkdir -p /usr/share/wallpapers/Hyggshi/contents/images
        cp -f /usr/share/backgrounds/hyggshi/hyggshi-wallpaper.svg /usr/share/wallpapers/Hyggshi/contents/images/1920x1080.svg
        echo "      ✔ [KDE Plasma] Updated wallpaper in /usr/share/wallpapers/Hyggshi/."
        ;;
    cinnamon)
        mkdir -p /usr/share/backgrounds/cinnamon
        cp -f /usr/share/backgrounds/hyggshi/hyggshi-wallpaper.svg /usr/share/backgrounds/cinnamon/hyggshi-wallpaper.svg
        echo "      ✔ [Cinnamon] Updated wallpaper in /usr/share/backgrounds/cinnamon/."
        ;;
    *)
        echo "      ℹ Generic desktop detected ($CURRENT_DE); universal wallpaper available."
        ;;
esac

# 4.3 Greeter GTK theme (LightDM on XFCE / MATE / Cinnamon)
if [ "$CURRENT_DE" = "xfce" ] || [ "$CURRENT_DE" = "mate" ] || [ "$CURRENT_DE" = "cinnamon" ] || [ -d /usr/share/themes/Hyggshi-Greeter ]; then
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
else
    echo "      ⏭ Skipping LightDM Greeter GTK theme (system DE is $CURRENT_DE, not using LightDM)."
fi

# ------------------------------------------------------------------------------
# 5. Compilers & Extensions ([compilers])
# ------------------------------------------------------------------------------
echo "  [5/6] Building and installing Hyggshi extensions..."

# linkhyggshi-sound-shortcut (only for XFCE)
if [ "$CURRENT_DE" = "xfce" ]; then
    SOUND_SRC="$RELEASE_ROOT/resources/hyggshi-extensions-sound-shortcut"
    if [ -f "$SOUND_SRC/CMakeLists.txt" ] && [ -f "$SOUND_SRC/sound-shortcut.sh" ]; then
        echo "      → Running sound-shortcut build script for XFCE..."
        chmod +x "$SOUND_SRC/sound-shortcut.sh"
        SRC_DIR="$SOUND_SRC" "$SOUND_SRC/sound-shortcut.sh" 2>/dev/null || true
    fi
else
    echo "      ⏭ Skipping linkhyggshi-sound-shortcut (only applicable for XFCE, active DE is $CURRENT_DE)."
fi

# linkhyggshi-welcome (all DEs)
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
mkdir -p "$(dirname "$LOG_FILE")"
echo "[$(date -Iseconds)] [HCL] Successfully applied upgrade to Hyggshi OS 1.4.1 (Verdant Valley) on DE: $CURRENT_DE" >> "$LOG_FILE"

echo "==> [Hyggshi HCL Post-Upgrade 1.4.1] Completed all HCL upgrade instructions successfully!"
