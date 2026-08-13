#!/usr/bin/env python3
"""Przykładowa komenda OSmars: /bin/fastfetch.py"""
import platform
import os
import sys

def main():
    sudo = os.environ.get("OSMARS_SUDO") == "1"
    print("to jest tylko test")
    return 0

if __name__ == "__main__":
    sys.exit(main())