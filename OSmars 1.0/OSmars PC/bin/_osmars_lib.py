#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wspólne ładowanie OSMarsPC z katalogu hosta (obok OSmars PC/)."""
from __future__ import annotations
import importlib.util
import os
import sys
from pathlib import Path


def find_root() -> Path:
    # bin/ jest w OSmars PC/bin → ROOT = parents[1]
    here = Path(__file__).resolve().parent
    if here.name == "bin":
        return here.parent
    # fallback: szukaj w górę
    for p in [here, *here.parents]:
        if (p / "boot").is_dir() and (p / "system").is_dir():
            return p
    return here.parent


def get_os():
    root = find_root()
    host = root.parent
    # cwd musi być hostem, bo ROOT_DIR = cwd / "OSmars PC"
    os.chdir(str(host))
    candidates = [
        host / "OSmars_recovery.py",
        host / "osmars_recovery.py",
        root / "boot" / "recovery.py",
    ]
    rec = next((c for c in candidates if c.is_file()), None)
    if not rec:
        print("Nie znaleziono OSmars_recovery.py obok katalogu OSmars PC")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("osmars_recovery_mod", rec)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.OSMarsPC()
