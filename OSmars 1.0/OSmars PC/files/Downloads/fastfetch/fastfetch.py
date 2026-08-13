#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSmars /bin/fastfetch.py"""
import platform
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    print("╔══════════════════════════════════╗")
    print("║     OSmars fastfetch 1.1.0       ║")
    print("╚══════════════════════════════════╝")
    print(f"  Host:   {platform.node()}")
    print(f"  OS:     {platform.system()} {platform.release()}")
    print(f"  Python: {platform.python_version()}")
    print(f"  Root:   {root}")
    ver = root / "ver"
    if ver.is_dir():
        print("  Versions:")
        for f in sorted(ver.glob("*.json")):
            try:
                import json
                d = json.loads(f.read_text(encoding="utf-8"))
                print(f"    {d.get('id')}: {d.get('version')} ({d.get('name')})")
            except Exception:
                print(f"    {f.name}")

if __name__ == "__main__":
    main()
