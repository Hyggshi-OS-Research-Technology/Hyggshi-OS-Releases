#!/usr/bin/env bash
# ==============================================================================
# HCL Parser & Executor Wrapper
# ==============================================================================
""":"
python3 "$0" "$@"
exit $?
"""
import argparse
import os
import re
import shutil
import subprocess
import sys


class Colors:
    BOLD = "\033[1m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    RED = "\033[0;31m"
    NC = "\033[0m"


class HclParser:
    def __init__(self, config_file: str, base_dir: str):
        self.config_file = config_file
        self.base_dir = os.path.abspath(base_dir)
        self.raw_sections: dict[str, list[tuple[str, any]]] = {}
        self.variables: dict[str, str] = {}

    def parse(self) -> dict[str, list[tuple[str, any]]]:
        if not os.path.isfile(self.config_file):
            raise FileNotFoundError(f"HCL config file not found: {self.config_file}")

        with open(self.config_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        current_section = "default"
        self.raw_sections[current_section] = []

        in_func = False
        func_name = ""
        func_key = ""
        func_args: list[tuple[str, str]] = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith(";"):
                continue

            if ";" in line:
                parts = line.split(";")
                line = parts[0].strip()
                if not line:
                    continue

            sec_match = re.match(r"^\[([^\]]+)\]$", line)
            if sec_match:
                current_section = sec_match.group(1).strip()
                if current_section not in self.raw_sections:
                    self.raw_sections[current_section] = []
                continue

            if in_func:
                if line == ")":
                    in_func = False
                    self.raw_sections[current_section].append(
                        (func_key, {"type": "function", "func": func_name, "args": func_args})
                    )
                    func_name = ""
                    func_key = ""
                    func_args = []
                    continue
                else:
                    arg_match = re.match(r"^([a-zA-Z0-9_-]+)\s*=\s*(.+)$", line)
                    if arg_match:
                        k = arg_match.group(1).strip()
                        v = arg_match.group(2).strip().strip('"').strip("'")
                        func_args.append((k, v))
                    continue

            kv_match = re.match(r"^([a-zA-Z0-9_-]+)\s*=\s*(.+)$", line)
            if kv_match:
                k = kv_match.group(1).strip()
                val_part = kv_match.group(2).strip()

                func_start_match = re.match(r"^([a-zA-Z0-9_-]+)\((.*)$", val_part)
                if func_start_match:
                    func_name = func_start_match.group(1).strip()
                    rest = func_start_match.group(2).strip()
                    func_key = k

                    if rest.endswith(")"):
                        inside = rest[:-1].strip()
                        func_args = []
                        if inside:
                            for item in re.split(r",\s*(?=[a-zA-Z0-9_-]+\s*=)", inside):
                                item = item.strip()
                                if "=" in item:
                                    ik, iv = item.split("=", 1)
                                    func_args.append((ik.strip(), iv.strip().strip('"').strip("'")))
                                else:
                                    func_args.append(("_arg0", item.strip().strip('"').strip("'")))
                        self.raw_sections[current_section].append(
                            (func_key, {"type": "function", "func": func_name, "args": func_args})
                        )
                    else:
                        in_func = True
                        func_args = []
                        if rest:
                            if "=" in rest:
                                ik, iv = rest.split("=", 1)
                                func_args.append((ik.strip(), iv.strip().strip('"').strip("'")))
                    continue

                clean_val = val_part.strip('"').strip("'")
                self.raw_sections[current_section].append((k, clean_val))
                self.variables[k] = clean_val

        return self.raw_sections

    def resolve_vars(self, text: str) -> str:
        for k, v in self.variables.items():
            text = text.replace(f"${{{k}}}", str(v))
        return text

    def download_asset(self, url: str, dest: str) -> bool:
        try:
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except Exception:
                    pass
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            res = subprocess.run(["curl", "-fsSL", url, "-o", dest], check=False)
            if res.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 0:
                os.chmod(dest, 0o644)
                return True
            import urllib.request
            urllib.request.urlretrieve(url, dest)
            if os.path.exists(dest):
                os.chmod(dest, 0o644)
                return True
        except Exception as e:
            print(f"      ⚠ Download failed: {e}")
        return False

    def handle_copy(self, args: dict, key: str, ver: str) -> None:
        source_val = args.get("source", "").strip()
        target_dir = args.get("target", "").strip()
        rename = args.get("rename", "").strip()
        download_url = args.get("download", "").strip()

        os.makedirs(target_dir, exist_ok=True)
        dest_name = rename if rename else os.path.basename(source_val)
        dest_path = os.path.join(target_dir, dest_name)

        # 1. Download attribute specified explicitly
        if download_url:
            print(f"  → Downloading & overwriting asset [{key}]: {dest_path}")
            if self.download_asset(download_url, dest_path):
                print(f"      ✔ [Force Overwrite] Successfully installed {dest_name}")
            return

        # 2. Source is an HTTP/HTTPS URL
        if source_val.startswith("http://") or source_val.startswith("https://"):
            print(f"  → Downloading & overwriting remote asset [{key}]: {source_val} -> {dest_path}")
            if self.download_asset(source_val, dest_path):
                print(f"      ✔ [Force Overwrite] Successfully installed {dest_name}")
            return

        # 3. Check local file
        src = os.path.join(self.base_dir, source_val.lstrip("./"))
        if not os.path.exists(src) and "config/resources/" in source_val:
            alt_src = os.path.join(self.base_dir, source_val.replace("config/resources/", "resources/").lstrip("./"))
            if os.path.exists(alt_src):
                src = alt_src

        if os.path.exists(src):
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            shutil.copy2(src, dest_path)
            os.chmod(dest_path, 0o644)
            print(f"  ✔ [Force Overwrite] Copied asset [{key}]: {os.path.basename(src)} -> {dest_path}")
        else:
            # 4. Fallback: Local file not packaged, fetch directly from GitHub OTA repository
            clean_rel = source_val.lstrip("./")
            remote_url = f"https://raw.githubusercontent.com/Hyggshi-OS-Research-Technology/Hyggshi-OS-Releases/main/hyggshi-os-ota/releases/{ver}/{clean_rel}"
            print(f"  → Local asset '{clean_rel}' not found, fetching from OTA repository: {remote_url}")
            if self.download_asset(remote_url, dest_path):
                print(f"      ✔ [Force Overwrite] Successfully fetched and installed {dest_name} -> {dest_path}")
            else:
                print(f"      ❌ Could not install asset [{key}] to {dest_path}")

    def detect_desktop_environment(self) -> str:
        """
        Auto-detect current active Desktop Environment:
        xfce, gnome, kde, cinnamon, mate, lxqt, or cli
        """
        # 1. Environment variables
        for var in ["XDG_CURRENT_DESKTOP", "DESKTOP_SESSION", "GDMSESSION", "XDG_SESSION_DESKTOP"]:
            val = os.environ.get(var, "")
            if val:
                val_l = val.lower()
                for de in ["xfce", "gnome", "kde", "plasma", "cinnamon", "mate", "lxqt"]:
                    if de in val_l:
                        return "kde" if de == "plasma" else de

        # 2. Inspect active GUI processes
        try:
            ps_out = subprocess.check_output(["ps", "-A", "-o", "comm="], text=True, stderr=subprocess.DEVNULL)
            procs = set(ps_out.strip().split())
            if "xfce4-session" in procs:
                return "xfce"
            if any(p in procs for p in ["gnome-shell", "gnome-session", "gnome-session-b"]):
                return "gnome"
            if any(p in procs for p in ["plasmashell", "kwin_x11", "kwin_wayland", "startplasma-x11", "startplasma"]):
                return "kde"
            if any(p in procs for p in ["cinnamon-sessio", "cinnamon-session", "cinnamon"]):
                return "cinnamon"
            if "mate-session" in procs:
                return "mate"
            if "lxqt-session" in procs:
                return "lxqt"
        except Exception:
            pass

        # 3. Check sudo user session via loginctl
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            try:
                sessions_out = subprocess.check_output(["loginctl", "list-sessions", "--no-legend"], text=True, stderr=subprocess.DEVNULL)
                for line in sessions_out.strip().splitlines():
                    parts = line.split()
                    if len(parts) >= 3 and parts[2] == sudo_user:
                        sess_id = parts[0]
                        show_out = subprocess.check_output(["loginctl", "show-session", sess_id, "-p", "Desktop"], text=True, stderr=subprocess.DEVNULL)
                        for sline in show_out.splitlines():
                            if sline.startswith("Desktop="):
                                dval = sline.split("=", 1)[1].lower()
                                for de in ["xfce", "gnome", "kde", "plasma", "cinnamon", "mate", "lxqt"]:
                                    if de in dval:
                                        return "kde" if de == "plasma" else de
            except Exception:
                pass

        # 4. Check default session symlink in /etc/alternatives
        if os.path.exists("/etc/alternatives/x-session-manager"):
            try:
                target = os.path.realpath("/etc/alternatives/x-session-manager").lower()
                for de in ["xfce", "gnome", "kde", "plasma", "cinnamon", "mate", "lxqt"]:
                    if de in target:
                        return "kde" if de == "plasma" else de
            except Exception:
                pass

        # 5. Check installed binaries in PATH
        for b, de in [("xfce4-session", "xfce"), ("gnome-shell", "gnome"), ("plasmashell", "kde"),
                      ("cinnamon-session", "cinnamon"), ("mate-session", "mate"), ("lxqt-session", "lxqt")]:
            if shutil.which(b):
                return de

        return "cli"

    def is_de_allowed(self, args: dict, active_de: str) -> tuple[bool, str]:
        """
        Check whether an HCL component is allowed to run under the active DE.
        Returns (is_allowed, reason_if_skipped).
        """
        target_de = args.get("de", "all").strip().lower()
        exclude_de = args.get("exclude_de", "").strip().lower()

        if target_de != "all":
            allowed = [d.strip() for d in target_de.split(",") if d.strip()]
            if "all" not in allowed and active_de not in allowed:
                return False, f"target DE is '{target_de}', active system DE is '{active_de}'"

        if exclude_de:
            excluded = [d.strip() for d in exclude_de.split(",") if d.strip()]
            if active_de in excluded:
                return False, f"active DE '{active_de}' is excluded by ({exclude_de})"

        return True, ""

    def execute(self) -> None:
        self.parse()

        print(f"\n{Colors.CYAN}{Colors.BOLD}======================================================={Colors.NC}")
        print(f"{Colors.CYAN}{Colors.BOLD}   HYGGSHI OS HCL PARSER & COMPONENT EXECUTOR        {Colors.NC}")
        print(f"{Colors.CYAN}{Colors.BOLD}======================================================={Colors.NC}")
        print(f"Reading HCL Config: {Colors.BLUE}{self.config_file}{Colors.NC}")
        print(f"Working Directory : {Colors.BLUE}{self.base_dir}{Colors.NC}\n")

        # 1. Base info
        base_entries = dict(self.raw_sections.get("my-version-os-base", []))
        ver = base_entries.get("Version", "1.4.1")
        codename = base_entries.get("codename", "Verdant Valley")
        name_template = base_entries.get("name", "Hyggshi OS ${Version} ${codename} Debian Edition")
        self.variables["Version"] = ver
        self.variables["codename"] = codename
        resolved_name = self.resolve_vars(name_template)

        # 2. Desktop Environment Resolution
        detected_de = self.detect_desktop_environment()
        de_entries = dict(self.raw_sections.get("Desktop-Environment", []))
        auto_detect = de_entries.get("auto-detect", "true").lower() == "true"
        target_cfg = de_entries.get("target", "auto").strip().lower()

        if not auto_detect and target_cfg != "auto" and target_cfg:
            active_de = target_cfg
        else:
            active_de = detected_de

        self.variables["CURRENT_DE"] = active_de
        self.variables["DETECTED_DE"] = detected_de

        print(f"{Colors.BOLD}Target Release Profile:{Colors.NC}")
        print(f"  • Version : {Colors.GREEN}{ver}{Colors.NC}")
        print(f"  • Codename: {Colors.GREEN}{codename}{Colors.NC}")
        print(f"  • Desktop : {Colors.GREEN}{active_de}{Colors.NC} (Detected: {detected_de}, Auto-detect: {'enabled' if auto_detect else 'disabled'})")
        print(f"  • Fullname: {Colors.GREEN}{resolved_name}{Colors.NC}\n")

        # 3. [ota] Section checks
        ota_entries = dict(self.raw_sections.get("ota", []))
        if ota_entries.get("check-disk-space", "false").lower() == "true":
            print(f"{Colors.BOLD}[HCL/OTA] Validating disk space...{Colors.NC}")
            try:
                avail_kb = int(subprocess.check_output(["df", "/", "--output=avail"]).decode().split()[1])
                if avail_kb < 300 * 1024:
                    print(f"{Colors.RED}❌ Insufficient disk space for update!{Colors.NC}")
                    sys.exit(1)
                print(f"  ✔ Disk space check passed ({avail_kb // 1024} MB free).")
            except Exception as e:
                print(f"  ⚠ Disk check warning: {e}")

        # 3. [package] Section
        package_entries = self.raw_sections.get("package", [])
        apt_packages_to_install = []

        print(f"\n{Colors.BOLD}[HCL/Package] Processing package directives...{Colors.NC}")

        # 3.1 First Pass: Collect and install all declared APT packages first so tools like wget/curl are ready
        for key, val in package_entries:
            if isinstance(val, str) and val.lower() == "true":
                pkg_name = key
                if pkg_name == "python":
                    pkg_name = "python3"
                apt_packages_to_install.append(pkg_name)

        if apt_packages_to_install:
            print(f"  → Installing declared core APT packages first: {', '.join(apt_packages_to_install)}")
            env = os.environ.copy()
            env["DEBIAN_FRONTEND"] = "noninteractive"
            subprocess.run(["apt-get", "update", "-qq"], env=env, check=False)
            subprocess.run(["apt-get", "install", "-y", "-qq"] + apt_packages_to_install, env=env, check=False)

        # 3.2 Second Pass: Execute complex components (install-web, commands, copy)
        for key, val in package_entries:
            if isinstance(val, dict) and val.get("type") == "function":
                func_name = val.get("func")
                args = dict(val.get("args", []))
                func_arg_list = val.get("args", [])

                allowed, reason = self.is_de_allowed(args, active_de)
                if not allowed:
                    print(f"  ⏭ Skipping [{key}] ({reason})")
                    continue

                if func_name == "install-web":
                    print(f"  → Executing install-web component [{key}]:")
                    for ak, av in func_arg_list:
                        if ak == "run":
                            print(f"      $ {av}")
                            res = subprocess.run(av, shell=True, check=False)
                            # Fallback if wget fails, try curl
                            if res.returncode != 0 and av.strip().startswith("wget "):
                                curl_fallback = av.replace("wget ", "curl -fsSL -O ")
                                print(f"      [Fallback to curl] $ {curl_fallback}")
                                subprocess.run(curl_fallback, shell=True, check=False)

                elif func_name == "command":
                    print(f"  → Executing command [{key}]:")
                    dl_url = args.get("download")
                    if dl_url:
                        filename = os.path.basename(dl_url.split("?")[0])
                        downloads_dir = os.path.expanduser("~/Downloads")
                        os.makedirs(downloads_dir, exist_ok=True)
                        dest_file = os.path.join(downloads_dir, filename)
                        print(f"      Downloading {filename}...")

                        sudo_user = os.environ.get("SUDO_USER")
                        user_dest = None
                        if sudo_user:
                            try:
                                import pwd
                                user_home = pwd.getpwnam(sudo_user).pw_dir
                                user_dl = os.path.join(user_home, "Downloads")
                                os.makedirs(user_dl, exist_ok=True)
                                user_dest = os.path.join(user_dl, filename)
                            except Exception:
                                pass

                        ret = subprocess.run(["curl", "-fsSL", dl_url, "-o", dest_file], check=False)
                        if ret.returncode != 0:
                            import urllib.request
                            urllib.request.urlretrieve(dl_url, dest_file)

                        if user_dest and os.path.exists(dest_file):
                            try:
                                shutil.copy2(dest_file, user_dest)
                                if sudo_user:
                                    import pwd
                                    pw = pwd.getpwnam(sudo_user)
                                    os.chown(user_dest, pw.pw_uid, pw.pw_gid)
                            except Exception:
                                pass
                        print(f"      ✔ Downloaded to {dest_file}")

                    for ak, av in func_arg_list:
                        if ak == "run":
                            print(f"      $ {av}")
                            subprocess.run(av, shell=True, check=False)
                        elif ak == "file" and args.get("action") == "run":
                            cmd_file = os.path.join(self.base_dir, av.lstrip("./"))
                            if os.path.isfile(cmd_file):
                                print(f"      $ bash {cmd_file}")
                                os.chmod(cmd_file, 0o755)
                                subprocess.run(["bash", cmd_file], check=False)

                elif func_name == "copy":
                    self.handle_copy(args, key, ver)

        # 4. [customization] Section
        cust_entries = self.raw_sections.get("customization", [])
        if cust_entries:
            print(f"\n{Colors.BOLD}[HCL/Customization] Applying customization directives...{Colors.NC}")
            for key, val in cust_entries:
                if isinstance(val, dict) and val.get("type") == "function":
                    func_name = val.get("func")
                    args = dict(val.get("args", []))
                    allowed, reason = self.is_de_allowed(args, active_de)
                    if not allowed:
                        print(f"  ⏭ Skipping [{key}] ({reason})")
                        continue

                    if func_name == "copy":
                        self.handle_copy(args, key, ver)
                    elif func_name == "command":
                        for ak, av in val.get("args", []):
                            if ak == "run":
                                print(f"      $ {av}")
                                subprocess.run(av, shell=True, check=False)

        # 5. [compilers] Section
        comp_entries = self.raw_sections.get("compilers", [])
        if comp_entries:
            print(f"\n{Colors.BOLD}[HCL/Compilers] Executing compiler directives & extensions...{Colors.NC}")
            for key, val in comp_entries:
                if isinstance(val, dict) and val.get("type") == "function":
                    func_name = val.get("func")
                    args = dict(val.get("args", []))
                    allowed, reason = self.is_de_allowed(args, active_de)
                    if not allowed:
                        print(f"  ⏭ Skipping [{key}] ({reason})")
                        continue
                    if func_name == "command" and args.get("action") == "run":
                        file_rel = args.get("file", "").lstrip("./")
                        target_script = os.path.join(self.base_dir, file_rel)

                        # Check fallback path if resources/hyggshi-extensions-welcome vs resources/hyggshi-welcome
                        if not os.path.isfile(target_script) and "hyggshi-extensions-welcome" in file_rel:
                            alt_rel = file_rel.replace("hyggshi-extensions-welcome", "hyggshi-welcome")
                            alt_path = os.path.join(self.base_dir, alt_rel)
                            if os.path.isfile(alt_path):
                                target_script = alt_path

                        # If target script is not found locally, fetch the full resources archive from OTA repo
                        if not os.path.isfile(target_script):
                            tar_url = f"https://raw.githubusercontent.com/Hyggshi-OS-Research-Technology/Hyggshi-OS-Releases/main/hyggshi-os-ota/releases/{ver}/resources.tar.gz"
                            print(f"  → Extension sources not found locally. Fetching resources bundle from: {tar_url}")
                            local_tar = os.path.join(self.base_dir, "resources.tar.gz")
                            if self.download_asset(tar_url, local_tar):
                                print(f"      ✔ Unpacking extension sources into {self.base_dir}...")
                                subprocess.run(["tar", "-xzf", local_tar, "-C", self.base_dir], check=False)
                                sym_ext = os.path.join(self.base_dir, "resources", "hyggshi-extensions-welcome")
                                target_wel = os.path.join(self.base_dir, "resources", "hyggshi-welcome")
                                if os.path.isdir(target_wel) and not os.path.exists(sym_ext):
                                    try:
                                        os.symlink("hyggshi-welcome", sym_ext)
                                    except Exception:
                                        pass
                                # Re-check paths after unpacking
                                if os.path.isfile(os.path.join(self.base_dir, file_rel)):
                                    target_script = os.path.join(self.base_dir, file_rel)
                                elif "hyggshi-extensions-welcome" in file_rel:
                                    alt_path = os.path.join(self.base_dir, file_rel.replace("hyggshi-extensions-welcome", "hyggshi-welcome"))
                                    if os.path.isfile(alt_path):
                                        target_script = alt_path

                        if os.path.isfile(target_script):
                            script_dir = os.path.dirname(target_script)
                            os.chmod(target_script, 0o755)
                            print(f"  → Building and installing component [{key}]: {target_script}")
                            env = os.environ.copy()
                            env["SRC_DIR"] = script_dir
                            env["DEBIAN_FRONTEND"] = "noninteractive"
                            res = subprocess.run(["bash", target_script], env=env, check=False)
                            if res.returncode == 0:
                                print(f"      ✔ Component [{key}] built and installed successfully.")
                            else:
                                print(f"      ⚠ Component [{key}] build exited with code {res.returncode}")
                        else:
                            print(f"  ❌ Compiler target script not found: {target_script}")

        # 6. Safe update of /etc/os-release (NON-DESTRUCTIVE)
        print(f"\n{Colors.BOLD}[HCL/System] Synchronizing /etc/os-release safely...{Colors.NC}")
        os_release_file = "/etc/os-release"
        if os.path.isfile(os_release_file):
            with open(os_release_file, "r", encoding="utf-8") as f:
                content = f.read()

            content = re.sub(r"^VERSION_ID=.*$", f'VERSION_ID="{ver}"', content, flags=re.MULTILINE)
            content = re.sub(r"^VERSION=.*$", f'VERSION="{ver} ({codename}) (Debian trixie)"', content, flags=re.MULTILINE)
            content = re.sub(r"^PRETTY_NAME=.*$", f'PRETTY_NAME="{resolved_name}"', content, flags=re.MULTILINE)
            content = re.sub(r"^NAME=.*$", f'NAME="{resolved_name}"', content, flags=re.MULTILINE)
            content = re.sub(r"^VERSION_CODENAME=.*$", f'VERSION_CODENAME="{codename}"', content, flags=re.MULTILINE)

            with open(os_release_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✔ Safely updated /etc/os-release (preserved ID_LIKE, HYGGSHI_BASE_*, LOGO).")

        print(f"\n{Colors.GREEN}{Colors.BOLD}✨ HCL components executed successfully!{Colors.NC}\n")


def main():
    parser = argparse.ArgumentParser(description="Hyggshi HCL OTA Parser & Executor")
    parser.add_argument("--config", required=True, help="Path to config.ini")
    parser.add_argument("--base-dir", default=".", help="Base directory of the release assets")
    parser.add_argument("--apply", action="store_true", help="Execute the components declared in HCL")

    args = parser.parse_args()

    executor = HclParser(config_file=args.config, base_dir=args.base_dir)
    if args.apply:
        executor.execute()
    else:
        sections = executor.parse()
        print(f"Parsed {len(sections)} HCL sections successfully.")


if __name__ == "__main__":
    main()
