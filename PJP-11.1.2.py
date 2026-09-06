#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified PAQJP+PJP – Simplified (Lossless, configurable number of transforms)
=============================================================================
- Base transforms (single, no pairs), default 256, but user can reduce.
- Time‑limited modes (default 300s)
- Final verification + fallback to raw+backend
- Quantum‑inspired transforms (optional)
- Output naming: input.txt.pjp (or .pjp.lzh)
- ALL transforms are individually lossless for every input.
- Main menu has only 3 options: Compress, Decompress, Exit.
"""

import math
import random
import decimal
import hashlib
import base64
import heapq
import struct
import os
import tempfile
import re
import urllib.request
import sys
import subprocess
import importlib
import time
from typing import Optional, List, Tuple, Dict, Callable, Any
from collections import Counter

# ------------------------------------------------------------------
# Optional backend: paq (restored for Option 2)
# ------------------------------------------------------------------
try:
    import paq
except ImportError:
    paq = None

USE_QUANTUM = False
HAS_QISKIT = False
HAS_ZSTD = False

def install_package(pkg: str) -> bool:
    """Install a package non‑interactively."""
    print(f"Installing {pkg}...")
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            '--no-input', '--disable-pip-version-check', pkg
        ])
        return True
    except Exception:
        return False

# ---------- Prompt 1: Quantum ----------
quantum_choice = input("Enable quantum‑inspired transforms (requires Qiskit)? (y/n) [default n]: ").strip().lower()
if quantum_choice == 'y':
    try:
        from qiskit import QuantumCircuit
        HAS_QISKIT = True
        USE_QUANTUM = True
        print("Quantum transforms ENABLED.")
    except ImportError:
        if install_package('qiskit'):
            try:
                from qiskit import QuantumCircuit
                HAS_QISKIT = True
                USE_QUANTUM = True
                print("Quantum transforms ENABLED.")
            except ImportError:
                print("Qiskit installation failed or import still failing. Quantum transforms disabled.")
        else:
            print("Qiskit installation failed. Quantum transforms disabled.")
else:
    print("Quantum transforms disabled.")

# ---------- Prompt 2: Install zstandard (mandatory) ----------
zstd_choice = input("Install zstandard backend? (mandatory, y/n) [default y]: ").strip().lower()
if zstd_choice == 'n':
    print("ERROR: zstandard is mandatory for this tool. Exiting.")
    sys.exit(1)
else:
    try:
        import zstandard as zstd
        zstd_cctx = zstd.ZstdCompressor(level=22)
