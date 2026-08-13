#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSmars fastfetch 1.0"""
import json
import os
import platform
import shutil
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    cols = shutil.get_terminal_size((80, 24)).columns
    line = "─" * min(40, cols)

    print(f"┌{line}┐")
    print(f"│  🪐 OSmars fastfetch 1.0".ljust(len(line)+1) + "│")
    print(f"└{line}┘")

    info = [
        ("OS", "OSmars (userland)"),
        ("Host", platform.node() or "?"),
        ("Kernel", f"{platform.system()} {platform.release()}"),
        ("Arch", platform.machine() or "?"),
        ("Python", platform.python_version()),
        ("Shell", os.environ.get("SHELL") or os.environ.get("COMSPEC") or "?"),
        ("Root", str(root)),
    ]
    try:
        import psutil
        vm = psutil.virtual_memory()
        info.append(("CPU", f"{psutil.cpu_percent(interval=0.15):.0f}% · {psutil.cpu_count()} threads"))
        info.append(("RAM", f"{vm.used//(1024**2)} / {vm.total//(1024**2)} MiB ({vm.percent:.0f}%)"))
    except Exception:
        pass

    w = max(len(k) for k, _ in info)
    for k, v in info:
        print(f"  {k.ljust(w)} : {v}")

    ver = root / "ver"
    if ver.is_dir():
        rows = []
        for f in sorted(ver.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                rows.append((str(d.get("id")), str(d.get("version")), str(d.get("type") or "")))
            except Exception:
                rows.append((f.stem, "?", ""))
        if rows:
            print()
            print("  Packages:")
            for i, v, ty in rows:
                extra = f" [{ty}]" if ty else ""
                print(f"    • {i}  v{v}{extra}")

    apps = root / "apps"
    if apps.is_dir():
        names = sorted(p.name for p in apps.iterdir() if p.is_dir())
        if names:
            print()
            print(f"  Apps ({len(names)}): " + ", ".join(names))

if __name__ == "__main__":
    main()
