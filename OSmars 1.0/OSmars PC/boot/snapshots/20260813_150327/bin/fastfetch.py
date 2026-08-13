#!/usr/bin/env python3
"""Przykładowa komenda OSmars: /bin/fastfetch.py"""
import platform
import os
import sys

def main():
    sudo = os.environ.get("OSMARS_SUDO") == "1"
    print("┌─ OSmars fastfetch ─────────────────")
    print(f"│ OS:      OSmars (Python userland)")
    print(f"│ Host:    {platform.node()}")
    print(f"│ Kernel:  {platform.release()}")
    print(f"│ Python:  {platform.python_version()}")
    print(f"│ Arch:    {platform.machine()}")
    if sudo:
        print("│ Mode:    sudo")
    print("└────────────────────────────────────")
    return 0

if __name__ == "__main__":
    sys.exit(main())
