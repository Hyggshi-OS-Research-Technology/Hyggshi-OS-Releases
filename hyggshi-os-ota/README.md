# 🛰️ Hyggshi OS OTA Repository & Client System

Independent **Over-The-Air (OTA)** operating system update mechanism dedicated to **Hyggshi OS**.

Official Repository: [Hyggshi-OS-Research-Technology/Hyggshi-OS-Releases](https://github.com/Hyggshi-OS-Research-Technology/Hyggshi-OS-Releases)

---

## 📌 1. Architecture & Directory Layout

The `hyggshi-os-ota` repository is completely decoupled from the **APT Application Repository** (which hosts userland apps like `nexfetch` and `nexcode-ide`):

```
hyggshi-os-ota/
├── metadata/                  # Tracks the latest release per update channel
│   ├── stable.json            # Official stable releases
│   ├── beta.json              # Public beta preview releases
│   └── testing.json           # Developer and nightly testing builds
│
├── releases/                  # Release manifests and version migration scripts
│   ├── 1.4.1/
│   │   └── release.json
│   ├── 1.5.0/
│   │   ├── release.json
│   │   └── migrations/
│   │       └── from-1.4.1.sh
│   └── 1.6.0/
│       ├── release.json
│       └── migrations/
│           ├── pre-upgrade.sh # Disk space, network, and configuration backup checks
│           ├── from-1.5.0.sh  # System migration script from 1.5.0 to 1.6.0
│           ├── from-1.4.1.sh  # System migration script from 1.4.1 to 1.6.0
│           └── post-upgrade.sh# Cache cleanups, desktop db refresh, and audit logging
│
├── keys/                      # GPG public keys for manifest/update verification
│   └── hyggshi-ota.gpg
│
├── client/                    # Client-side tools installed on Hyggshi OS devices
│   ├── bin/hyggshi-ota        # Main CLI update tool
│   ├── etc/hyggshi-release    # Template for /etc/hyggshi-release
│   ├── etc/hyggshi-ota.conf   # Configuration template (/etc/hyggshi-ota.conf)
│   ├── systemd/               # Background update check timer & service
│   └── install.sh             # Client installation script
│
└── README.md
```

---

## ⚙️ 2. Device Upgrade Execution Flow

```text
/etc/hyggshi-release (e.g., version 1.5.0)
        ↓
hyggshi-ota check / upgrade
        ↓
Hyggshi OS OTA Repo (metadata/stable.json)
        ↓
New version detected: 1.6.0 (Cosmos)
        ↓
Download & execute [1/5]: pre-upgrade.sh (disk space validation, backup)
        ↓
Download & execute [2/5]: migrations/from-1.5.0.sh (configuration transition)
        ↓
Synchronize [3/5]: APT repository & core package upgrades
        ↓
Download & execute [4/5]: post-upgrade.sh (cache cleanups & /var/log/hyggshi-ota.log)
        ↓
Update [5/5]: /etc/hyggshi-release -> 1.6.0
        ↓
🎉 Complete! System reboot prompt if requires_reboot=true
```

---

## 💻 3. Client Usage Guide

### Install Client on Hyggshi OS:
```bash
cd hyggshi-os-ota/client
sudo ./install.sh
```

### CLI Command Reference (`hyggshi-ota`):
```bash
# 1. Display current system and OTA status
hyggshi-ota status

# 2. Check for available updates
hyggshi-ota check

# 3. Perform operating system upgrade
sudo hyggshi-ota upgrade

# 4. Switch release channels (stable, beta, testing)
sudo hyggshi-ota channel beta

# 5. Review update history log
hyggshi-ota log
```

---

## 🛠️ 4. Release Maintainer Guide

To publish a new operating system release (e.g., `1.7.0`):

1. **Create release folder:**
   ```bash
   mkdir -p releases/1.7.0/migrations
   ```

2. **Create `releases/1.7.0/release.json`:**
   ```json
   {
     "version": "1.7.0",
     "codename": "Dawn",
     "release_date": "2026-12-01",
     "min_supported_version": "1.5.0",
     "changelog": [
       "Upgraded to latest Linux Kernel LTS",
       "Performance improvements for nexDE desktop",
       "Updated core system runtime packages"
     ],
     "requires_reboot": true,
     "pre_upgrade_script": "migrations/pre-upgrade.sh",
     "post_upgrade_script": "migrations/post-upgrade.sh",
     "migrations": [
       {
         "from": "1.6.0",
         "script": "migrations/from-1.6.0.sh"
       }
     ]
   }
   ```

3. **Add transition script:**  
   Write migration logic in `releases/1.7.0/migrations/from-1.6.0.sh`.

4. **Update channel metadata:**  
   Edit `metadata/stable.json` to point `latest_version` to `"1.7.0"`.

5. **Commit and push to GitHub:**
   ```bash
   git add .
   git commit -m "release: Hyggshi OS 1.7.0 (Dawn)"
   git push origin main
   ```
   All devices running Hyggshi OS will immediately detect the new release via `hyggshi-ota check`!
