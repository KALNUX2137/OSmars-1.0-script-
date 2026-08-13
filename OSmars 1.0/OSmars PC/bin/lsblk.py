#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _osmars_lib import get_os

def main():
    os = get_os()
    os.cmd_lsblk(sys.argv[1:])

if __name__ == "__main__":
    main()
