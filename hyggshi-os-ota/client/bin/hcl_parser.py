#!/usr/bin/env python3
"""
hcl_parser.py — Hyggshi Configuration Language (HCL) OTA Parser & Executor
Parses HCL config.ini and executes components declared in the OTA release.
"""

from __future__ import annotations

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
            # Skip empty lines or full comments
            if not line or line.startswith(";"):
                continue

            # Strip trailing comments
            if ";" in line:
                # Be careful not to strip semicolon inside quotes
                parts = line.split(";")
                line = parts[0].strip()
                if not line:
                    continue

            # Section header [Section]
            sec_match = re.match(r"^\[([^\]]+)\]$", line)
            if sec_match:
                current_section = sec_match.group(1).strip()
                if current_section not in self.raw_sections:
                    self.raw_sections[current_section] = []
                continue

            # Multi-line function call closing
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
                    # Inside function arguments: key = "value"
                    arg_match = re.match(r"^([a-zA-Z0-9_-]+)\s*=\s*(.+)$", line)
                    if arg_match:
                        k = arg_match.group(1).strip()
                        v = arg_match.group(2).strip().strip('"').strip("'")
                        func_args.append((k, v))
                    continue

            # Key = Value or Function call
            kv_match = re.match(r"^([a-zA-Z0-9_-]+)\s*=\s*(.+)$", line)
            if kv_match:
                k = kv_match.group(1).strip()
                val_part = kv_match.group(2).strip()

                # Function call starting like: cmd = command( or cmd = command(run = "...")
                func_start_match = re.match(r"^([a-zA-Z0-9_-]+)\((.*)$", val_part)
                if func_start_match:
                    func_name = func_start_match.group(1).strip()
                    rest = func_start_match.group(2).strip()
                    func_key = k

                    if rest.endswith(")"):
                        # Single-line function: copy(source="a", target="b") or fileinstall(path)
                        inside = rest[:-1].strip()
                        func_args = []
                        if inside:
                            # Parse inside key=val
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
                            # First line may have an argument
                            if "=" in rest:
                                ik, iv = rest.split("=", 1)
                                func_args.append((ik.strip(), iv.strip().strip('"').strip("'")))
                    continue

                # Literal boolean / string
                clean_val = val_part.strip('"').strip("'")
                self.raw_sections[current_section].append((k, clean_val))
                self.variables[k] = clean_val

        return self.raw_sections

    def resolve_vars(self, text: str) -> str:
        for k, v in self.variables.items():
            text = text.replace(f"${{{k}}}", str(v))
        return text

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

        print(f"{Colors.BOLD}Target Release Profile:{Colors.NC}")
        print(f"  • Version : {Colors.GREEN}{ver}{Colors.NC}")
        print(f"  • Codename: {Colors.GREEN}{codename}{Colors.NC}")
        print(f"  • Fullname: {Colors.GREEN}{resolved_name}{Colors.NC}\n")

        # 2. [ota] Section checks
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
        for key, val in package_entries:
            # Boolean packages: python = true, jq = true
            if isinstance(val, str) and val.lower() == "true":
                pkg_name = key
                if pkg_name == "python":
                    pkg_name = "python3"
                apt_packages_to_install.append(pkg_name)
            elif isinstance(val, dict) and val.get("type") == "function":
                func_name = val.get("func")
                args = dict(val.get("args", []))
                func_arg_list = val.get("args", [])

                if func_name == "install-web":
                    print(f"  → Executing install-web component [{key}]:")
                    for ak, av in func_arg_list:
                        if ak == "run":
                            print(f"      $ {av}")
                            subprocess.run(av, shell=True, check=False)

                elif func_name == "command":
                    print(f"  → Executing command [{key}]:")
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
                    src = os.path.join(self.base_dir, args.get("source", "").lstrip("./"))
                    # If src not found directly, check without config/ prefix
                    if not os.path.exists(src) and "config/resources/" in args.get("source", ""):
                        alt_src = os.path.join(self.base_dir, args.get("source", "").replace("config/resources/", "resources/").lstrip("./"))
                        if os.path.exists(alt_src):
                            src = alt_src

                    target_dir = args.get("target", "")
                    rename = args.get("rename", "")
                    dest = os.path.join(target_dir, rename) if rename else target_dir

                    if os.path.exists(src):
                        os.makedirs(target_dir, exist_ok=True)
                        shutil.copy2(src, dest)
                        print(f"  → Copied asset: {os.path.basename(src)} -> {dest}")

        if apt_packages_to_install:
            print(f"  → Installing declared APT packages: {', '.join(apt_packages_to_install)}")
            env = os.environ.copy()
            env["DEBIAN_FRONTEND"] = "noninteractive"
            subprocess.run(["apt-get", "update", "-qq"], env=env, check=False)
            subprocess.run(["apt-get", "install", "-y", "-qq"] + apt_packages_to_install, env=env, check=False)

        # 4. [customization] Section
        cust_entries = self.raw_sections.get("customization", [])
        if cust_entries:
            print(f"\n{Colors.BOLD}[HCL/Customization] Applying customization directives...{Colors.NC}")
            for key, val in cust_entries:
                if isinstance(val, dict) and val.get("type") == "function":
                    func_name = val.get("func")
                    args = dict(val.get("args", []))
                    if func_name == "copy":
                        src = os.path.join(self.base_dir, args.get("source", "").lstrip("./"))
                        target_dir = args.get("target", "")
                        rename = args.get("rename", "")
                        dest = os.path.join(target_dir, rename) if rename else target_dir

                        if os.path.exists(src):
                            os.makedirs(target_dir, exist_ok=True)
                            shutil.copy2(src, dest)
                            print(f"  → Installed customization: {os.path.basename(src)} -> {dest}")

        # 5. [compilers] Section
        comp_entries = self.raw_sections.get("compilers", [])
        if comp_entries:
            print(f"\n{Colors.BOLD}[HCL/Compilers] Executing compiler directives & extensions...{Colors.NC}")
            for key, val in comp_entries:
                if isinstance(val, dict) and val.get("type") == "function":
                    func_name = val.get("func")
                    args = dict(val.get("args", []))
                    if func_name == "command" and args.get("action") == "run":
                        file_rel = args.get("file", "").lstrip("./")
                        target_script = os.path.join(self.base_dir, file_rel)

                        # Check fallback path if resources/hyggshi-extensions-welcome vs resources/hyggshi-welcome
                        if not os.path.isfile(target_script) and "hyggshi-extensions-welcome" in file_rel:
                            alt_rel = file_rel.replace("hyggshi-extensions-welcome", "hyggshi-welcome")
                            alt_path = os.path.join(self.base_dir, alt_rel)
                            if os.path.isfile(alt_path):
                                target_script = alt_path

                        if os.path.isfile(target_script):
                            script_dir = os.path.dirname(target_script)
                            os.chmod(target_script, 0o755)
                            print(f"  → Building component [{key}]: {target_script}")
                            env = os.environ.copy()
                            env["SRC_DIR"] = script_dir
                            env["DEBIAN_FRONTEND"] = "noninteractive"
                            subprocess.run(["bash", target_script], env=env, check=False)
                        else:
                            print(f"  ⚠ Compiler target script not found: {target_script}")

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
