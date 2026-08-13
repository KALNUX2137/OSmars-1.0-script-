#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""from_mars install|uninstall|update <pkg>"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _osmars_lib import get_os

def main():
    args = sys.argv[1:]
    os = get_os()
    if not args:
        print("Użycie: from_mars install|uninstall|update [nazwa]")
        return
    sub = args[0].lower()
    rest = " ".join(args[1:]).strip()
    if sub == "install":
        os.from_mars_install(rest)
    elif sub in ("uninstall", "remove", "rm"):
        os.from_mars_uninstall(rest)
    elif sub == "update":
        os.from_mars_update(rest)
    else:
        print("Użycie: from_mars install|uninstall|update [nazwa]")

if __name__ == "__main__":
    main()
