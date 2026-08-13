#!/usr/bin/env python3
# Auto-wrapper OSmars dla Hello Mars
import runpy
from pathlib import Path
root = Path(__file__).resolve().parents[1]
entry = root / 'apps' / 'hello' / 'main.py'
runpy.run_path(str(entry), run_name='__main__')
