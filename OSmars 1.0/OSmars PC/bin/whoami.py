#!/usr/bin/env python3
import os
print(os.getenv('USER') or os.getenv('USERNAME') or 'unknown')
