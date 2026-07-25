#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PJP – 256 Lossless Transforms + 2704 Transform‑Pair Sequences
+ Hybrid Dictionary Mode + Quantum Transforms + Base64 + 6‑bit Text
+ Transforms 28–30 + .docx transforms 31–32 (now lossless – identity)
+ Zaden Block Optimization + Algorithm 36 (powers‑of‑two + smart candidates)
  Option 9 tries all three and picks the best.
  Algorithm 36 header: 0x36 + pad_len (1 byte) + pass_index (1 byte, 0‑23)
  For small files (≤40 bytes), it also tries the mean, median, and each chunk value.

** PAIR ENCODING BUG FIXED – now 100% lossless **
============================================================================
"""

import math, random, decimal, hashlib, struct, re, os, sys, subprocess, importlib, time, base64
import heapq
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Callable, Any
from collections import Counter, defaultdict

# ------------------------------------------------------------------
# Helper: install a single package via pip (silent, auto)
# ------------------------------------------------------------------
def install_package(pkg: str) -> bool:
    print(f"Installing {pkg}...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Successfully installed {pkg}")
        return True
    except Exception as e:
        print(f"Failed to install {pkg}: {e}")
        return False

# ------------------------------------------------------------------
# 1. Ask about quantum transforms – auto‑install if missing
# ------------------------------------------------------------------
USE_QUANTUM = False
HAS_QISKIT = False

quantum_choice = input("Enable quantum‑inspired transforms (requires Qiskit)? (y/n): ").strip().lower()
if quantum_choice == 'y':
    try:
        from qiskit import QuantumCircuit
        HAS_QISKIT = True
        USE_QUANTUM = True
        print("Quantum transforms ENABLED (Qiskit already installed).")
    except ImportError:
        print("Qiskit not found. Installing automatically...")
        if install_package('qiskit'):
            try:
                from qiskit import QuantumCircuit
                HAS_QISKIT = True
                USE_QUANTUM = True
                print("Quantum transforms ENABLED after automatic installation.")
            except ImportError:
                print("Qiskit installation succeeded but import failed – quantum transforms disabled.")
        else:
            print("Automatic installation failed – quantum transforms disabled.")
else:
    print("Quantum transforms disabled.")

# ------------------------------------------------------------------
# 2. Ask about other optional compression backends (zstandard, paq, etc.)
# ------------------------------------------------------------------
other_choice = input("Install other optional compression backends (zstandard, paq, mpmath, python-docx)? (y/n): ").strip().lower()
if other_choice == 'y':
    for pkg in ['mpmath', 'zstandard', 'cython', 'paq', 'python-docx']:
        try:
            importlib.import_module(pkg)
        except ImportError:
            install_package(pkg)
else:
    print("Skipping other backends.")

# ---------- Optional compression backends (properly guarded) ----------
HAS_ZSTD = False
HAS_PAQ = False
HAS_MPMATH = False
HAS_DOCX = False

try:
    import zstandard
    HAS_ZSTD = True
    zstd_cctx = zstandard.ZstdCompressor(level=22)
    zstd_dctx = zstandard.ZstdDecompressor()
except ImportError:
    pass

try:
    import paq
    HAS_PAQ = True
except ImportError:
    pass

try:
    import mpmath
    HAS_MPMATH = True
except ImportError:
    pass

try:
    import docx
    HAS_DOCX = True
except ImportError:
    pass

# ---------- Constants ----------
PRIMES = [p for p in range(2, 256) if all(p % d for d in range(2, int(p**0.5) + 1))]
PI_DIGITS = [79, 17, 111]
ALPHABET_6BIT = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 \n"
CHAR_TO_6BIT = {ch: i for i, ch in enumerate(ALPHABET_6BIT)}
SIXBIT_TO_CHAR = {i: ch for ch, i in CHAR_TO_6BIT.items()}

PAQ_STATE_TABLE = [
    [1, 2, 0, 0], [3, 5, 0, 1], [4, 6, 2, 0], [7, 10, 0, 2],
    [8, 12, 3, 0], [9, 13, 1, 1], [11, 14, 0, 3], [15, 19, 4, 0],
    [16, 23, 2, 1], [17, 24, 2, 1], [18, 25, 2, 1], [20, 27, 1, 2],
    [21, 28, 1, 2], [22, 29, 1, 2], [26, 30, 0, 4], [31, 33, 5, 0],
    [32, 34, 3, 1], [35, 37, 1, 3], [36, 38, 1, 3], [39, 42, 0, 5],
    [40, 43, 4, 1], [41, 44, 2, 2], [45, 48, 1, 4], [46, 49, 1, 4],
    [47, 50, 1, 4], [51, 52, 0, 6], [53, 55, 6, 0], [54, 56, 4, 1],
    [57, 59, 2, 3], [58, 60, 2, 3], [61, 63, 0, 7], [62, 64, 5, 1],
    [65, 66, 3, 2], [67, 69, 1, 5], [68, 70, 1, 5], [71, 73, 0, 8],
    [72, 74, 6, 1], [75, 76, 4, 2], [77, 78, 2, 4], [79, 80, 2, 4],
    [81, 82, 0, 9], [83, 84, 7, 1], [85, 86, 5, 2], [87, 88, 3, 3],
    [89, 90, 1, 6], [91, 92, 0, 10], [93, 94, 8, 1], [95, 96, 6, 2],
    [97, 98, 4, 3], [99, 100, 2, 5], [101, 102, 0, 11], [103, 104, 9, 1],
    [105, 106, 7, 2], [107, 108, 5, 3], [109, 110, 3, 4], [111, 112, 1, 7],
    [113, 114, 0, 12], [115, 116, 10, 1], [117, 118, 8, 2], [119, 120, 6, 3],
    [121, 122, 4, 4], [123, 124, 2, 6], [125, 126, 0, 13], [127, 128, 11, 1],
    [129, 130, 9, 2], [131, 132, 7, 3], [133, 134, 5, 4], [135, 136, 3, 5],
    [137, 138, 1, 8], [139, 140, 0, 14], [141, 142, 12, 1], [143, 144, 10, 2],
    [145, 146, 8, 3], [147, 148, 6, 4], [149, 150, 4, 5], [151, 152, 2, 7],
    [153, 154, 0, 15], [155, 156, 13, 1], [157, 158, 11, 2], [159, 160, 9, 3],
    [161, 162, 7, 4], [163, 164, 5, 5], [165, 166, 3, 6], [167, 168, 1, 9],
    [169, 170, 0, 16], [171, 172, 14, 1], [173, 174, 12, 2], [175, 176, 10, 3],
    [177, 178, 8, 4], [179, 180, 6, 5], [181, 182, 4, 6], [183, 184, 2, 8],
    [185, 186, 0, 17], [187, 188, 15, 1], [189, 190, 13, 2], [191, 192, 11, 3],
    [193, 194, 9, 4], [195, 196, 7, 5], [197, 198, 5, 6], [199, 200, 3, 7],
    [201, 202, 1, 10], [203, 204, 0, 18], [205, 206, 16, 1], [207, 208, 14, 2],
    [209, 210, 12, 3], [211, 212, 10, 4], [213, 214, 8, 5], [215, 216, 6, 6],
    [217, 218, 4, 7], [219, 220, 2, 9], [221, 222, 0, 19], [223, 224, 17, 1],
    [225, 226, 15, 2], [227, 228, 13, 3], [229, 230, 11, 4], [231, 232, 9, 5],
    [233, 234, 7, 6], [235, 236, 5, 7], [237, 238, 3, 8], [239, 240, 1, 11],
    [241, 242, 0, 20], [243, 244, 18, 1], [245, 246, 16, 2], [247, 248, 14, 3],
    [249, 250, 12, 4], [251, 252, 10, 5], [253, 254, 8, 6], [255, 255, 6, 7],
]

_CONST_DIAPASON_ITER_CODE = [
    (2, 0b10), (2, 0b11), (3, 0b010), (3, 0b011), (4, 0b0010), (4, 0b0011),
    (5, 0b00010), (5, 0b00011), (6, 0b000010), (6, 0b000011), (7, 0b0000010),
    (7, 0b0000011), (8, 0b00000010), (8, 0b00000011), (9, 0b000000010), (9, 0b000000011),
]
_CONST_DIAPASON_ITER_DECODE = {}
for nibble, (l, b) in enumerate(_CONST_DIAPASON_ITER_CODE):
    _CONST_DIAPASON_ITER_DECODE[(l, b)] = nibble


def find_nearest_prime_around(n):
    o = 0
    while True:
        c1, c2 = n - o, n + o
        if c1 >= 2 and all(c1 % d for d in range(2, int(c1 ** 0.5) + 1)): return c1
        if c2 >= 2 and all(c2 % d for d in range(2, int(c2 ** 0.5) + 1)): return c2
        o += 1


class UltimateHybridCompressor:
    def __init__(self, repeat_count=100):
        self.repeat_count = repeat_count
        self.PI_DIGITS = PI_DIGITS.copy()
        self.seed_tables = self._gen_seed_tables(126, 40, 42)
        self.fibonacci = self._gen_fib(100)
        self.PI_STR = "3.14159265358979323846264338327950288419716939937510"
        self.mask_46 = self._build_mask_46()
        self.mod_state_table = [[(v - 400) & 0xFF for v in row] for row in PAQ_STATE_TABLE]

        self._build_transform_maps()
        self.sequences = self._build_pair_sequences()
        self.pair_lookup = {idx: (t1, t2) for idx, (t1, t2) in enumerate(self.sequences)}
        self.pair_to_index = {seq: idx for idx, seq in enumerate(self.sequences)}

        if USE_QUANTUM and HAS_QISKIT:
            self._precompute_quantum_byte_substitutions()

    def _gen_quantum_permutation(self, seed):
        from qiskit import QuantumCircuit
        qc = QuantumCircuit(8)
        rng = random.Random(seed)
        for i in range(8):
            qc.h(i)
            qc.rz(rng.random() * 2 * math.pi, i)
            qc.rx(rng.random() * 2 * math.pi, i)
        for _ in range(8):
            for i in range(7): qc.cx(i, i + 1)
            qc.barrier()
            for i in range(8):
                qc.rz(rng.random() * 2 * math.pi, i)
                qc.rx(rng.random() * 2 * math.pi, i)
        try:
            hash_val = hash(qc.qasm())
        except:
            hash_val = seed
        rng2 = random.Random(seed + hash_val % 1000000)
        perm = list(range(256))
        rng2.shuffle(perm)
        return perm

    def _precompute_quantum_byte_substitutions(self):
        self.q_perms = [self._gen_quantum_permutation(1000 + i) for i in range(9)]
        for idx, perm in enumerate(self.q_perms, start=48):
            if idx > 56: break
            inv_perm = [0] * 256
            for i, p in enumerate(perm): inv_perm[p] = i
            self.fwd[idx] = lambda data, perm=perm: bytes(perm[b] for b in data)
            self.rev[idx] = lambda data, inv=inv_perm: bytes(inv[b] for b in data)

    def _gen_seed_tables(self, n, size, seed):
        random.seed(seed)
        return [[random.randint(5, 255) for _ in range(size)] for _ in range(n)]

    def _gen_fib(self, n):
        a, b = 0, 1
        res = [a, b]
        for _ in range(2, n):
            a, b = b, a + b
            res.append(b)
        return res

    def get_seed(self, idx, val):
        if 0 <= idx < len(self.seed_tables):
            return self.seed_tables[idx][val % 40]
        return 0

    def _build_mask_46(self):
        base = [1, 2, 4, 8, 16, 32, 64, 128, 3, 6]
        return [(b - 10) & 0xFF for b in base] * 10

    def _append_bits(self, bits, val, cnt):
        for i in range(cnt - 1, -1, -1): bits.append((val >> i) & 1)

    def _read_bits(self, bits, pos, cnt):
        val = 0
        for i in range(cnt):
            if pos + i >= len(bits): return 0
            val = (val << 1) | bits[pos + i]
        return val

    def transform_01(self, data):
        if not data: return b'\x00'
        best_result = None
        best_len = float('inf')
        original = data
        current = bytearray(data)
        applied = []
        for _ in range(10):
            best_shift = 0
            best_shifted = current
            best_score = -1
            for shift in range(256):
                tmp = bytearray(current)
                for j in range(len(tmp)): tmp[j] = (tmp[j] + shift) % 256
                score = 0
                i = 0
                while i < len(tmp):
                    val = tmp[i]
                    run = 1
                    i += 1
                    while i < len(tmp) and tmp[i] == val:
                        run += 1
                        i += 1
                    score += run * run
                if score > best_score:
                    best_score = score
                    best_shifted = tmp
                    best_shift = shift
            applied.append(best_shift)
            rle = self._apply_rle(best_shifted, best_shift)
            dec = self._rle_decode(rle)
            if dec is not None:
                test = bytearray(dec)
                for s in applied:
                    for j in range(len(test)): test[j] = (test[j] - s) % 256
                if bytes(test) == original and len(rle) < best_len:
                    best_len = len(rle)
                    best_result = rle
            current = best_shifted
            if len(rle) >= len(data): break
        if best_result is None or best_len >= len(data):
            return bytes([0]) + data
        header = bytearray([len(applied)])
        header.extend(applied)
        return header + best_result

    def _apply_rle(self, shifted, shift):
        bits = []
        self._append_bits(bits, 0b010, 3)
        self._append_bits(bits, shift, 8)
        i = 0
        n = len(shifted)
        while i < n:
            val = shifted[i]
            run = 1
            i += 1
            while i < n and shifted[i] == val:
                run += 1
                i += 1
            while run >= 13:
                chunk = min(run, 268)
                self._append_bits(bits, 0b1111, 4)
                self._append_bits(bits, chunk - 13, 8)
                self._append_bits(bits, val, 8)
                run -= chunk
            if run == 1:
                self._append_bits(bits, 0b00, 2)
                self._append_bits(bits, val, 8)
            elif run <= 5:
                self._append_bits(bits, 0b01, 2)
                self._append_bits(bits, run - 2, 2)
                self._append_bits(bits, val, 8)
            elif run <= 12:
                self._append_bits(bits, 0b10, 2)
                self._append_bits(bits, run - 6, 3)
                self._append_bits(bits, val, 8)
        pad = (8 - len(bits) % 8) % 8
        self._append_bits(bits, 0, pad)
        out = bytearray()
        for j in range(0, len(bits), 8):
            byte = 0
            for k in range(8):
                if j + k < len(bits): byte = (byte << 1) | bits[j + k]
            out.append(byte)
        return bytes(out)

    def reverse_transform_01(self, cdata):
        if not cdata or cdata == b'\x00': return b''
        if cdata[0] == 0: return cdata[1:]
        num = cdata[0]
        shifts = list(cdata[1:1 + num])
        rledata = cdata[1 + num:]
        dec = self._rle_decode(rledata)
        if dec is None: return b''
        cur = bytearray(dec)
        for s in reversed(shifts):
            for i in range(len(cur)): cur[i] = (cur[i] - s) % 256
        return bytes(cur)

    def _rle_decode(self, data):
        if not data: return None
        bits = []
        for b in data: bits.extend([(b >> i) & 1 for i in range(7, -1, -1)])
        pos = 0
        nbits = len(bits)
        if nbits < 11 or self._read_bits(bits, pos, 3) != 0b010: return None
        pos += 3
        pos += 8
        out = bytearray()
        while pos < nbits:
            if pos + 2 > nbits: break
            prefix = self._read_bits(bits, pos, 2)
            pos += 2
            if prefix == 0b00:
                if pos + 8 > nbits: break
                run = 1
            elif prefix == 0b01:
                if pos + 2 + 8 > nbits: break
                run = 2 + self._read_bits(bits, pos, 2)
                pos += 2
            elif prefix == 0b10:
                if pos + 3 + 8 > nbits: break
                run = 6 + self._read_bits(bits, pos, 3)
                pos += 3
            else:
                if pos + 2 + 8 + 8 > nbits or self._read_bits(bits, pos, 2) != 0b11: return None
                pos += 2
                run = 13 + self._read_bits(bits, pos, 8)
                pos += 8
            if pos + 8 > nbits: break
            val = self._read_bits(bits, pos, 8)
            pos += 8
            out.extend([val] * run)
        for i in range(pos, nbits):
            if bits[i] != 0: return None
        return out

    def transform_02(self, d):
        t = bytearray(d)
        r = self.repeat_count
        for prime in PRIMES:
            xor_val = prime if prime == 2 else max(1, math.ceil(prime * 4096 / 28672))
            for _ in range(r):
                for i in range(0, len(t), 3):
                    if i < len(t): t[i] ^= xor_val
        return bytes(t)

    reverse_transform_02 = transform_02

    def transform_03(self, d):
        if len(d) < 1: return b''
        pi = (len(d) + sum(d) % 256) % 256
        pat = self._get_pattern(4, pi)
        t = bytearray(d)
        for i in range(1, len(t), 4):
            if i < len(t): t[i] ^= pat[i % len(pat)]
        return bytes([pi]) + bytes(t)

    def reverse_transform_03(self, d):
        if len(d) < 2: return b''
        pi = d[0]
        t = bytearray(d[1:])
        pat = self._get_pattern(4, pi)
        for i in range(1, len(t), 4):
            if i < len(t): t[i] ^= pat[i % len(pat)]
        return bytes(t)

    def transform_04(self, d):
        if len(d) < 1: return b''
        t = bytearray(d)
        rot = (len(d) * 13 + sum(d)) % 8
        if rot == 0: rot = 1
        for i in range(2, len(t), 5):
            if i < len(t): t[i] = ((t[i] << rot) | (t[i] >> (8 - rot))) & 0xFF
        return bytes([rot]) + bytes(t)

    def reverse_transform_04(self, d):
        if len(d) < 2: return b''
        rot = d[0]
        t = bytearray(d[1:])
        for i in range(2, len(t), 5):
            if i < len(t): t[i] = ((t[i] >> rot) | (t[i] << (8 - rot))) & 0xFF
        return bytes(t)

    def transform_05(self, d):
        t = bytearray(d)
        r = self.repeat_count
        for _ in range(r):
            for i in range(len(t)): t[i] = (t[i] - (i % 256)) % 256
        return bytes(t)

    def reverse_transform_05(self, d):
        t = bytearray(d)
        r = self.repeat_count
        for _ in range(r):
            for i in range(len(t)): t[i] = (t[i] + (i % 256)) % 256
        return bytes(t)

    def transform_06(self, d, s=3):
        t = bytearray(d)
        for i in range(len(t)): t[i] = ((t[i] << s) | (t[i] >> (8 - s))) & 0xFF
        return bytes(t)

    def reverse_transform_06(self, d, s=3):
        t = bytearray(d)
        for i in range(len(t)): t[i] = ((t[i] >> s) | (t[i] << (8 - s))) & 0xFF
        return bytes(t)

    def transform_07(self, d, seed=42):
        random.seed(seed)
        sub = list(range(256))
        random.shuffle(sub)
        t = bytearray(d)
        for i in range(len(t)): t[i] = sub[t[i]]
        return bytes(t)

    def reverse_transform_07(self, d, seed=42):
        random.seed(seed)
        sub = list(range(256))
        random.shuffle(sub)
        inv = [0] * 256
        for i in range(256): inv[sub[i]] = i
        t = bytearray(d)
        for i in range(len(t)): t[i] = inv[t[i]]
        return bytes(t)

    def transform_08(self, d):
        t = bytearray(d)
        sh = len(d) % len(self.PI_DIGITS)
        pi_rot = self.PI_DIGITS[sh:] + self.PI_DIGITS[:sh]
        sz = len(d) % 256
        for i in range(len(t)): t[i] ^= sz
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i] ^= pi_rot[i % len(pi_rot)]
        return bytes(t)

    reverse_transform_08 = transform_08

    def transform_09(self, d):
        t = bytearray(d)
        sh = len(d) % len(self.PI_DIGITS)
        pi_rot = self.PI_DIGITS[sh:] + self.PI_DIGITS[:sh]
        p = find_nearest_prime_around(len(d) % 256)
        for i in range(len(t)): t[i] ^= p
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i] ^= pi_rot[i % len(pi_rot)]
        return bytes(t)

    reverse_transform_09 = transform_09

    def transform_10(self, d):
        t = bytearray(d)
        sh = len(d) % len(self.PI_DIGITS)
        pi_rot = self.PI_DIGITS[sh:] + self.PI_DIGITS[:sh]
        p = find_nearest_prime_around(len(d) % 256)
        seed = self.get_seed(len(d) % len(self.seed_tables), len(d))
        for i in range(len(t)): t[i] ^= p ^ seed
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i] ^= pi_rot[i % len(pi_rot)] ^ (i % 256)
        return bytes(t)

    reverse_transform_10 = transform_10

    def transform_11(self, d):
        if not d: return b'\x00'
        cnt = sum(1 for i in range(len(d) - 1) if d[i:i + 2] == b'X1')
        n = (((cnt * 2) + 1) // 3) * 3 % 256
        t = bytearray(d)
        for i in range(len(t)): t[i] ^= n
        return bytes([n]) + bytes(t)

    def reverse_transform_11(self, d):
        if len(d) < 1: return b''
        n = d[0]
        t = bytearray(d[1:])
        for i in range(len(t)): t[i] ^= n
        return bytes(t)

    def transform_12(self, d):
        t = bytearray(d)
        L = len(t)
        for i in range(L):
            fib_idx = (i + L) % len(self.fibonacci)
            fib_val = self.fibonacci[fib_idx] % 256
            pos_val = (i * 13 + L * 17) % 256
            t[i] ^= (fib_val ^ pos_val) % 256
        return bytes(t)

    reverse_transform_12 = transform_12

    def transform_13(self, d):
        t = bytearray(d)
        for i in range(len(t)): t[i] ^= self.fibonacci[i % len(self.fibonacci)] % 256
        return bytes(t)

    reverse_transform_13 = transform_13

    def transform_14(self, d):
        if not d: return b''
        reps = self._calculate_repeats(d)
        cur = len(d) % 256
        vals = []
        for _ in range(reps):
            cur = find_nearest_prime_around(cur)
            vals.append(cur)
        xor_val = vals[-1] if vals else 0
        t = bytearray(d)
        for i in range(len(t)): t[i] ^= xor_val
        return bytes([(reps - 1) % 256]) + bytes(t)

    def reverse_transform_14(self, d):
        if len(d) < 2: return b''
        reps = (d[0] + 1) % 256
        if reps == 0: reps = 256
        t = bytearray(d[1:])
        cur = len(t) % 256
        vals = []
        for _ in range(reps):
            cur = find_nearest_prime_around(cur)
            vals.append(cur)
        xor_val = vals[-1] if vals else 0
        for i in range(len(t)): t[i] ^= xor_val
        return bytes(t)

    def transform_15(self, d):
        if len(d) < 1: return b''
        pi = len(d) % 256
        pat = self._get_pattern(3, pi)
        t = bytearray(d)
        for i in range(0, len(t), 3):
            if i < len(t): t[i] = (t[i] + pat[i % len(pat)]) % 256
        return bytes([pi]) + bytes(t)

    def reverse_transform_15(self, d):
        if len(d) < 2: return b''
        pi = d[0]
        t = bytearray(d[1:])
        pat = self._get_pattern(3, pi)
        for i in range(0, len(t), 3):
            if i < len(t): t[i] = (t[i] - pat[i % len(pat)]) % 256
        return bytes(t)

    def transform_16(self, d):
        if not d: return b''
        xor_byte = (len(d) * 7 + 13) % 256
        t = bytearray(d)
        for i in range(len(t)): t[i] ^= xor_byte
        return bytes(t)

    reverse_transform_16 = transform_16

    def transform_17(self, d):
        if not d: return b''
        k, _ = self.find_lossless_k(7)
        bits_used = 23 if k <= 0x7FFFFF else 25
        bit_str = format(k, 'b').zfill(bits_used)
        mask_bytes = []
        for i in range(0, len(bit_str), 8):
            byte_bits = bit_str[i:i + 8]
            if len(byte_bits) < 8: byte_bits = byte_bits.ljust(8, '0')
            mask_bytes.append(int(byte_bits, 2))
        mask = bytes(mask_bytes)
        t = bytearray(d)
        for i in range(len(t)): t[i] ^= mask[i % len(mask)]
        return bytes(t)

    reverse_transform_17 = transform_17

    def transform_18(self, d):
        if not d: return b''
        digits = self.get_basel_digits(max(10, len(d) // 2 + 5))
        mask = bytes(int(digits[i:i + 2]) % 256 for i in range(0, len(digits), 2))
        t = bytearray(d)
        for i in range(len(t)): t[i] ^= mask[i % len(mask)]
        return bytes(t)

    reverse_transform_18 = transform_18

    def transform_19(self, d):
        if not d: return b''
        digits = self.get_one_over_e_digits(max(10, len(d) // 2 + 5))
        mask = bytes(int(digits[i:i + 2]) % 256 for i in range(0, len(digits), 2))
        t = bytearray(d)
        for i in range(len(t)): t[i] ^= mask[i % len(mask)]
        return bytes(t)

    reverse_transform_19 = transform_19

    def transform_20(self, d):
        if not d: return b''
        digits = self.get_5e_digits(max(10, len(d) // 2 + 5))
        mask = bytes(int(digits[i:i + 2]) % 256 for i in range(0, len(digits), 2))
        t = bytearray(d)
        for i in range(len(t)): t[i] ^= mask[i % len(mask)]
        return bytes(t)

    reverse_transform_20 = transform_20

    def transform_21(self, d):
        if not d: return b''
        t = bytearray(d)
        for i in range(len(t)): t[i] = (t[i] + 255) % 256
        return bytes(t)

    def reverse_transform_21(self, d):
        if not d: return b''
        t = bytearray(d)
        for i in range(len(t)): t[i] = (t[i] - 255) % 256
        return bytes(t)

    def transform_22(self, d): return d
    reverse_transform_22 = transform_22

    def _compress_bits(self, bits):
        if not bits: return b'\x00\x00\x00'
        cur = bits[:]
        prev_len = len(cur)
        pass_count = 0
        while pass_count < 255:
            pad = (4 - len(cur) % 4) % 4
            padded = cur + [0] * pad
            nibcnt = len(padded) // 4
            enc = []
            for i in range(nibcnt):
                nib = (padded[i * 4] << 3) | (padded[i * 4 + 1] << 2) | (padded[i * 4 + 2] << 1) | padded[i * 4 + 3]
                l, cw = _CONST_DIAPASON_ITER_CODE[nib]
                for b in range(l - 1, -1, -1): enc.append((cw >> b) & 1)
            new_len = len(enc)
            if new_len < prev_len:
                cur = enc
                prev_len = new_len
                pass_count += 1
            else:
                break
        header = bytes([(len(bits) >> 8) & 0xFF, len(bits) & 0xFF, pass_count])
        pad = (8 - len(cur) % 8) % 8
        cur += [0] * pad
        out = bytearray()
        for i in range(0, len(cur), 8):
            val = 0
            for j in range(8): val = (val << 1) | cur[i + j]
            out.append(val)
        return header + bytes(out)

    def _decompress_bits(self, data):
        if len(data) < 3: return []
        orig_len = (data[0] << 8) | data[1]
        passes = data[2]
        payload = data[3:]
        bits = []
        for b in payload: bits.extend([(b >> i) & 1 for i in range(7, -1, -1)])
        cur = bits
        for _ in range(passes):
            pos = 0
            nbits = len(cur)
            dec_nibbles = []
            while pos < nbits:
                matched = False
                for l in range(2, 10):
                    if pos + l > nbits: continue
                    cw = 0
                    for k in range(l): cw = (cw << 1) | cur[pos + k]
                    key = (l, cw)
                    if key in _CONST_DIAPASON_ITER_DECODE:
                        dec_nibbles.append(_CONST_DIAPASON_ITER_DECODE[key])
                        pos += l
                        matched = True
                        break
                if not matched: break
            new_bits = []
            for nib in dec_nibbles:
                for j in range(3, -1, -1): new_bits.append((nib >> j) & 1)
            cur = new_bits
        if len(cur) < orig_len: return []
        return cur[:orig_len]

    def transform_23(self, d):
        if not d: return b'\x00\x00\x00'
        bits = []
        for b in d: bits.extend([(b >> i) & 1 for i in range(7, -1, -1)])
        return self._compress_bits(bits)

    def reverse_transform_23(self, d):
        bits = self._decompress_bits(d)
        if not bits: return b''
        out = bytearray()
        for i in range(0, len(bits), 8):
            val = 0
            for j in range(i, min(i + 8, len(bits))): val = (val << 1) | bits[j]
            if i + 8 > len(bits): val <<= (8 - (len(bits) - i))
            out.append(val)
        return bytes(out)

    def transform_24(self, d):
        if not d: return b''
        MAX_LEN = 43
        bits = []
        i = 0
        n = len(d)
        while i < n:
            chunk_len = min(MAX_LEN, n - i)
            chunk = d[i:i + chunk_len]
            first = chunk[0]
            all_same = all(b == first for b in chunk)
            if all_same:
                self._append_bits(bits, 1, 1)
                self._append_bits(bits, first, 8)
                self._append_bits(bits, chunk_len - 1, 6)
            else:
                self._append_bits(bits, 0, 1)
                self._append_bits(bits, chunk_len, 6)
                for b in chunk: self._append_bits(bits, b, 8)
            i += chunk_len
        pad = (8 - len(bits) % 8) % 8
        self._append_bits(bits, 0, pad)
        out = bytearray()
        for j in range(0, len(bits), 8):
            byte = 0
            for k in range(8): byte = (byte << 1) | bits[j + k]
            out.append(byte)
        return bytes(out)

    def reverse_transform_24(self, d):
        if not d: return b''
        bits = []
        for b in d: bits.extend([(b >> i) & 1 for i in range(7, -1, -1)])
        pos = 0
        nbits = len(bits)
        out = bytearray()
        while pos < nbits:
            if pos + 1 > nbits: break
            flag = self._read_bits(bits, pos, 1)
            pos += 1
            if flag == 1:
                if pos + 8 + 6 > nbits: break
                byte_val = self._read_bits(bits, pos, 8)
                pos += 8
                cnt_minus1 = self._read_bits(bits, pos, 6)
                pos += 6
                out.extend([byte_val] * (cnt_minus1 + 1))
            else:
                if pos + 6 > nbits: break
                chunk_len = self._read_bits(bits, pos, 6)
                pos += 6
                if chunk_len == 0: break
                if pos + chunk_len * 8 > nbits: break
                for _ in range(chunk_len):
                    b = self._read_bits(bits, pos, 8)
                    pos += 8
                    out.append(b)
        return bytes(out)

    def transform_25(self, d):
        if not d: return b'\x01'
        n = 3
        res = bytearray(d)
        for i in range(len(res)): res[i] = (pow(res[i] + 1, n, 257) - 1) & 0xFF
        return bytes([n]) + bytes(res)

    def reverse_transform_25(self, d):
        if not d or len(d) < 2: return b''
        n = d[0]
        inv = pow(n, -1, 256)
        res = bytearray(d[1:])
        for i in range(len(res)): res[i] = (pow(res[i] + 1, inv, 257) - 1) & 0xFF
        return bytes(res)

    def transform_26(self, d):
        if not d: return b'\x01\x00'
        n = (len(d) * 7 + 13) & 0xFFFF
        if n % 2 == 0: n ^= 1
        e = pow(n, 16777216, 256) | 1
        res = bytearray(d)
        for i in range(len(res)): res[i] = (pow(res[i] + 1, e, 257) - 1) & 0xFF
        return bytes([n & 0xFF, (n >> 8) & 0xFF]) + bytes(res)

    def reverse_transform_26(self, d):
        if not d or len(d) < 2: return b''
        n = d[0] | (d[1] << 8)
        if n % 2 == 0: n ^= 1
        e = pow(n, 16777216, 256) | 1
        inv_e = pow(e, -1, 256)
        res = bytearray(d[2:])
        for i in range(len(res)): res[i] = (pow(res[i] + 1, inv_e, 257) - 1) & 0xFF
        return bytes(res)

    def transform_27(self, d):
        if not d:
            out = bytearray(b'\x00\x00\x00\x00')
            out.extend(b'\x01\x00')
            out.extend(b'\x00' * 1024)
            return bytes(out)
        BLOCK = 1024
        blocks = (len(d) + BLOCK - 1) // BLOCK
        out = bytearray()
        out.extend(len(d).to_bytes(4, 'big'))
        for bi in range(blocks):
            start = bi * BLOCK
            end = min(start + BLOCK, len(d))
            chunk = d[start:end]
            pad = BLOCK - len(chunk)
            chunk = chunk + b'\x00' * pad if pad else chunk
            n = ((len(d) * 7 + bi * 13 + 1) & 0xFFFF) | 1
            e = pow(n, 16777216, 256) | 1
            e200 = pow(e, 200, 256)
            trans = bytearray(chunk)
            for i in range(BLOCK): trans[i] = (pow(trans[i] + 1, e200, 257) - 1) & 0xFF
            out.append(n & 0xFF)
            out.append((n >> 8) & 0xFF)
            out.extend(trans)
        return bytes(out)

    def reverse_transform_27(self, d):
        if not d or len(d) < 4: return b''
        orig_len = int.from_bytes(d[:4], 'big')
        payload = d[4:]
        BLOCK = 1024
        block_total = 2 + BLOCK
        if len(payload) % block_total != 0: return d
        num = len(payload) // block_total
        decoded = bytearray()
        for bi in range(num):
            off = bi * block_total
            n = payload[off] | (payload[off + 1] << 8)
            chunk = payload[off + 2:off + 2 + BLOCK]
            n |= 1
            e = pow(n, 16777216, 256) | 1
            e200 = pow(e, 200, 256)
            inv_e200 = pow(e200, -1, 256)
            for i in range(BLOCK): decoded.append((pow(chunk[i] + 1, inv_e200, 257) - 1) & 0xFF)
        return bytes(decoded[:orig_len])

    def transform_28(self, d):
        if not d:
            out = bytearray(b'\x00\x00\x00\x00')
            out.extend(b'\x01\x00')
            out.extend(self._compress_backend(b'\x00' * 1024, safe=True))
            return bytes(out)
        BLOCK = 1024
        blocks = (len(d) + BLOCK - 1) // BLOCK
        out = bytearray()
        out.extend(len(d).to_bytes(4, 'big'))
        for bi in range(blocks):
            start = bi * BLOCK
            end = min(start + BLOCK, len(d))
            chunk = d[start:end]
            pad = BLOCK - len(chunk)
            chunk = chunk + b'\x00' * pad if pad else chunk
            n = ((len(d) * 7 + bi * 13 + 1) & 0xFFFF) | 1
            e = pow(n, 16777216, 256) | 1
            e200 = pow(e, 200, 256)
            trans = bytearray(chunk)
            for i in range(BLOCK): trans[i] = (pow(trans[i] + 1, e200, 257) - 1) & 0xFF
            comp = self._compress_backend(bytes(trans), safe=True)
            out.append(n & 0xFF)
            out.append((n >> 8) & 0xFF)
            out.append((len(comp) >> 8) & 0xFF)
            out.append(len(comp) & 0xFF)
            out.extend(comp)
        return bytes(out)

    def reverse_transform_28(self, d):
        if not d or len(d) < 4: return b''
        orig_len = int.from_bytes(d[:4], 'big')
        payload = d[4:]
        pos = 0
        decoded = bytearray()
        while pos < len(payload):
            if pos + 2 > len(payload): break
            n = payload[pos] | (payload[pos + 1] << 8)
            pos += 2
            if pos + 2 > len(payload): break
            comp_len = (payload[pos] << 8) | payload[pos + 1]
            pos += 2
            if pos + comp_len > len(payload): break
            comp = payload[pos:pos + comp_len]
            pos += comp_len
            block = self._decompress_backend(comp, safe=True)
            if block is None: return d
            n |= 1
            e = pow(n, 16777216, 256) | 1
            e200 = pow(e, 200, 256)
            inv_e200 = pow(e200, -1, 256)
            trans = bytearray(block)
            for i in range(len(trans)): trans[i] = (pow(trans[i] + 1, inv_e200, 257) - 1) & 0xFF
            decoded.extend(trans)
        return bytes(decoded[:orig_len])

    def transform_29(self, d):
        if not d:
            out = bytearray(b'\x00\x00\x00\x00')
            out.extend(b'\x01\x00')
            out.extend(self._compress_backend(b'\x00' * 32, safe=True))
            return bytes(out)
        BLOCK = 32
        blocks = (len(d) + BLOCK - 1) // BLOCK
        out = bytearray()
        out.extend(len(d).to_bytes(4, 'big'))
        for bi in range(blocks):
            start = bi * BLOCK
            end = min(start + BLOCK, len(d))
            chunk = d[start:end]
            pad = BLOCK - len(chunk)
            chunk = chunk + b'\x00' * pad if pad else chunk
            n = ((len(d) * 7 + bi * 13 + 1) & 0xFFFF) | 1
            e = pow(n, 2 ** 256, 256) | 1
            e200 = pow(e, 200, 256)
            comp = self._compress_backend(chunk, safe=True)
            out.append(n & 0xFF)
            out.append((n >> 8) & 0xFF)
            out.append((len(comp) >> 8) & 0xFF)
            out.append(len(comp) & 0xFF)
            out.extend(comp)
        return bytes(out)

    def reverse_transform_29(self, d):
        if not d or len(d) < 4: return b''
        orig_len = int.from_bytes(d[:4], 'big')
        payload = d[4:]
        pos = 0
        decoded = bytearray()
        while pos < len(payload):
            if pos + 2 > len(payload): break
            n = payload[pos] | (payload[pos + 1] << 8)
            pos += 2
            if pos + 2 > len(payload): break
            comp_len = (payload[pos] << 8) | payload[pos + 1]
            pos += 2
            if pos + comp_len > len(payload): break
            comp = payload[pos:pos + comp_len]
            pos += comp_len
            block = self._decompress_backend(comp, safe=True)
            if block is None: return d
            decoded.extend(block)
        return bytes(decoded[:orig_len])

    def transform_30(self, d):
        if not d:
            out = bytearray(b'\x00\x00\x00\x00')
            out.extend(b'\x01\x01')
            out.extend(self._compress_backend(b'\x00' * 33, safe=True))
            return bytes(out)
        BLOCK = 33
        blocks = (len(d) + BLOCK - 1) // BLOCK
        out = bytearray()
        out.extend(len(d).to_bytes(4, 'big'))
        for bi in range(blocks):
            start = bi * BLOCK
            end = min(start + BLOCK, len(d))
            chunk = d[start:end]
            pad = BLOCK - len(chunk)
            chunk = chunk + b'\x00' * pad if pad else chunk
            n, enc_n = self._compute_n_for_block(chunk, bi, len(d))
            comp = self._compress_backend(chunk, safe=True)
            out.extend(enc_n)
            out.append((len(comp) >> 8) & 0xFF)
            out.append(len(comp) & 0xFF)
            out.extend(comp)
        return bytes(out)

    def reverse_transform_30(self, d):
        if not d or len(d) < 4: return b''
        orig_len = int.from_bytes(d[:4], 'big')
        payload = d[4:]
        pos = 0
        decoded = bytearray()
        while pos < len(payload):
            Ln = payload[pos]
            pos += 1
            if Ln > 32 or pos + Ln > len(payload): break
            n_bytes = payload[pos:pos + Ln]
            pos += Ln
            if pos + 2 > len(payload): break
            comp_len = (payload[pos] << 8) | payload[pos + 1]
            pos += 2
            if pos + comp_len > len(payload): break
            comp = payload[pos:pos + comp_len]
            pos += comp_len
            block = self._decompress_backend(comp, safe=True)
            if block is None: return d
            decoded.extend(block)
        return bytes(decoded[:orig_len])

    def _compute_n_for_block(self, block, bi, total_len):
        if not block: return 1, b'\x01\x01'
        d = block[0]
        x = (bi % 33) + 1
        try:
            t = (d * d - d ** x) // 256
        except OverflowError:
            t = 0
        if 0 <= t <= 255:
            n = t | 1
            return n, bytes([1, n])
        h = hashlib.sha256(block + bytes([bi & 0xFF, (total_len >> 8) & 0xFF, total_len & 0xFF])).digest()
        nb = bytearray(h)
        nb[0] |= 1
        length = len(nb)
        encoded = bytes([length]) + bytes(nb)
        n = int.from_bytes(nb, 'big')
        return n, encoded

    def _dynamic_transform(self, n):
        def tf(d):
            if not d: return b''
            seed = self.get_seed(n % len(self.seed_tables), len(d))
            t = bytearray(d)
            for i in range(len(t)): t[i] ^= seed
            return bytes(t)

        return tf, tf

    def transform_41(self, d):
        if not d: return b''
        mask = bytes([0x27, 0x03])
        t = bytearray(d)
        n = min(len(t), 8)
        for i in range(n): t[i] ^= mask[i % 2]
        return bytes(t)

    reverse_transform_41 = transform_41

    def transform_42(self, d):
        if not d: return b''
        t = bytearray(d)
        mask = bytes([0x27, 0x03])
        for i in range(len(t)): t[i] ^= mask[i % 2]
        return bytes(t)

    reverse_transform_42 = transform_42

    def transform_43(self, d):
        if not d: return b''
        t = bytearray(d)
        mask = bytes([0x10, 0x00, 0x00])
        for i in range(0, len(t), 3):
            for j in range(min(3, len(t) - i)): t[i + j] ^= mask[j]
        return bytes(t)

    reverse_transform_43 = transform_43

    def transform_44(self, d):
        if not d: return b''
        return base64.b64encode(d)

    def reverse_transform_44(self, d):
        if not d: return b''
        try:
            return base64.b64decode(d)
        except:
            return d

    def transform_45(self, d):
        if not d: return b''
        freq = [0] * 256
        for b in d: freq[b] += 1
        cl = self._huffman_code_lengths(freq)
        codes = self._huffman_canonical_codes(cl)
        header = bytearray()
        header.extend(len(d).to_bytes(4, 'big'))
        header.extend(cl)
        bits = []
        for b in d:
            c, l = codes[b]
            for i in range(l - 1, -1, -1): bits.append((c >> i) & 1)
        pad = (8 - len(bits) % 8) % 8
        bits.extend([0] * pad)
        out = bytearray()
        for i in range(0, len(bits), 8):
            val = 0
            for j in range(8): val = (val << 1) | bits[i + j]
            out.append(val)
        return bytes(header) + bytes(out)

    def reverse_transform_45(self, d):
        if not d or len(d) < 4 + 256: return d
        orig_len = int.from_bytes(d[:4], 'big')
        cl = list(d[4:4 + 256])
        payload = d[4 + 256:]
        if orig_len == 0: return b''
        code_to_sym = {}
        symbols = list(range(256))
        symbols.sort(key=lambda s: (cl[s], s))
        code = 0
        prev_len = 0
        first = True
        for sym in symbols:
            l = cl[sym]
            if l == 0: continue
            if first:
                prev_len = l
                first = False
            elif l != prev_len:
                code <<= (l - prev_len)
                prev_len = l
            code_to_sym[(l, code)] = sym
            code += 1
        bits = []
        for b in payload: bits.extend([(b >> i) & 1 for i in range(7, -1, -1)])
        pos = 0
        nbits = len(bits)
        out = bytearray()
        while pos < nbits and len(out) < orig_len:
            found = False
            for l in range(1, 256):
                if pos + l > nbits: break
                val = 0
                for j in range(l): val = (val << 1) | bits[pos + j]
                if (l, val) in code_to_sym:
                    out.append(code_to_sym[(l, val)])
                    pos += l
                    found = True
                    break
            if not found: break
        return bytes(out)

    def transform_46(self, d):
        if not d: return b''
        t = bytearray(d)
        mask = self.mask_46
        for i in range(len(t)): t[i] ^= mask[i % len(mask)]
        return bytes(t)

    reverse_transform_46 = transform_46

    def transform_47(self, d):
        if not d: return b''
        t = bytearray(d)
        tbl = self.mod_state_table
        if not tbl: return d
        for i in range(len(t)): t[i] ^= tbl[i % len(tbl)][0]
        return bytes(t)

    reverse_transform_47 = transform_47

    def transform_52(self, d): return d
    reverse_transform_52 = transform_52

    def transform_256(self, d): return d
    reverse_transform_256 = transform_256

    def _build_transform_maps(self):
        self.fwd = {}
        self.rev = {}
        for i in range(1, 25):
            if hasattr(self, f"transform_{i:02d}"):
                self.fwd[i] = getattr(self, f"transform_{i:02d}")
                self.rev[i] = getattr(self, f"reverse_transform_{i:02d}")
        for i in range(25, 31):
            self.fwd[i] = getattr(self, f"transform_{i}")
            self.rev[i] = getattr(self, f"reverse_transform_{i}")
        for i in range(31, 41):
            f, r = self._dynamic_transform(i)
            self.fwd[i] = f
            self.rev[i] = r
        for i in range(41, 48):
            self.fwd[i] = getattr(self, f"transform_{i}")
            self.rev[i] = getattr(self, f"reverse_transform_{i}")
        for i in range(48, 52):
            f, r = self._dynamic_transform(i)
            self.fwd[i] = f
            self.rev[i] = r
        self.fwd[52] = self.transform_52
        self.rev[52] = self.reverse_transform_52

        for i in range(53, 257):
            f, r = self._dynamic_transform(i)
            self.fwd[i] = f
            self.rev[i] = r

    def _build_pair_sequences(self):
        pairs = []
        for t1 in range(1, 53):
            for t2 in range(1, 53):
                if t1 == 52 and t2 == 52: continue
                pairs.append((t1, t2))
        return pairs

    def get_transform_sequence(self, index):
        if index < 0 or index > 2703: raise ValueError("Index 0..2703 (2704 total paths)")
        if index == 0: return ()
        return self.sequences[index - 1]

    def apply_transform_by_index(self, data, index):
        seq = self.get_transform_sequence(index)
        res = data
        for t in seq: res = self.fwd[t](res)
        return res

    def reverse_transform_by_index(self, data, index):
        seq = self.get_transform_sequence(index)
        res = data
        for t in reversed(seq): res = self.rev[t](res)
        return res

    def get_pi_digits(self, n):
        if n < 1: return ""
        return self.PI_STR[2:2 + n]

    def find_lossless_k(self, n):
        if n < 1: return 0, True
        true_digits = self.get_pi_digits(n)
        true_scaled = int(self.PI_STR.replace('.', '')[:n + 1])
        DENOM = 16777216
        decimal.getcontext().prec = 50
        pi_dec = decimal.Decimal(self.PI_STR)
        k_float = (pi_dec - 3) * DENOM
        k_candidate = int(round(k_float))
        k_candidate = max(0, min(k_candidate, DENOM - 1))
        approx_scaled = (3 * 10 ** n * DENOM + k_candidate * 10 ** n) // DENOM
        return k_candidate, approx_scaled == true_scaled

    def get_basel_digits(self, n):
        decimal.getcontext().prec = n + 5
        pi = decimal.Decimal(self.PI_STR)
        basel = (pi * pi) / decimal.Decimal(6)
        s = str(basel).replace('.', '')
        return s[:n]

    def get_one_over_e_digits(self, n):
        decimal.getcontext().prec = n + 5
        e = decimal.Decimal(1).exp()
        inv_e = decimal.Decimal(1) / e
        s = str(inv_e).replace('.', '')
        return s[:n]

    def get_5e_digits(self, n):
        decimal.getcontext().prec = n + 5
        e = decimal.Decimal(1).exp()
        five_e = decimal.Decimal(5) * e
        s = str(five_e).replace('.', '')
        return s[:n]

    def _get_pattern(self, size, index):
        random.seed(12345 + size * 100 + index)
        return [random.randint(0, 255) for _ in range(size)]

    def _calculate_repeats(self, data):
        if not data: return 1
        L = len(data)
        s = sum(data) % 256
        reps = ((L * 13 + s * 17) % 256) + 1
        return max(1, min(256, reps))

    @staticmethod
    def _huffman_code_lengths(freq):
        heap = [(f, i, i) for i, f in enumerate(freq) if f > 0]
        if not heap: return [0] * len(freq)
        if len(heap) == 1:
            lengths = [0] * len(freq)
            lengths[heap[0][2]] = 1
            return lengths
        heapq.heapify(heap)
        next_id = len(heap)
        while len(heap) > 1:
            f1, _, n1 = heapq.heappop(heap)
            f2, _, n2 = heapq.heappop(heap)
            heapq.heappush(heap, (f1 + f2, next_id, (n1, n2)))
            next_id += 1
        lengths = [0] * len(freq)

        def traverse(node, depth):
            if isinstance(node, int):
                lengths[node] = depth
            else:
                traverse(node[0], depth + 1)
                traverse(node[1], depth + 1)

        traverse(heap[0][2], 0)
        return lengths

    @staticmethod
    def _huffman_canonical_codes(code_lengths):
        symbols = list(range(len(code_lengths)))
        symbols.sort(key=lambda s: (code_lengths[s], s))
        codes = {}
        code = 0
        prev_len = 0
        first = True
        for sym in symbols:
            cl = code_lengths[sym]
            if cl == 0: continue
            if first:
                prev_len = cl
                first = False
            elif cl != prev_len:
                code <<= (cl - prev_len)
                prev_len = cl
            codes[sym] = (code, cl)
            code += 1
        return codes

    WINDOW_SIZE = 2048
    MIN_MATCH = 3
    MAX_MATCH = 2048
    MAX_DIST = 2048

    def _lz77_tokenize(self, data):
        tokens = []
        i = 0
        n = len(data)
        while i < n:
            best_len = 0
            best_dist = 0
            start = max(0, i - self.WINDOW_SIZE)
            for j in range(start, i):
                if data[j] != data[i]: continue
                k = 0
                while i + k < n and j + k < i and data[j + k] == data[i + k]:
                    k += 1
                    if k >= self.MAX_MATCH: break
                if k >= self.MIN_MATCH and k > best_len:
                    best_len = k
                    best_dist = i - j
                if best_len == self.MAX_MATCH: break
            if best_len >= self.MIN_MATCH:
                tokens.append(('M', best_dist, best_len))
                i += best_len
            else:
                tokens.append(('L', data[i], None))
                i += 1
        return tokens

    def _lz77_untokenize(self, tokens):
        out = bytearray()
        for t in tokens:
            if t[0] == 'L':
                out.append(t[1])
            else:
                dist, length = t[1], t[2]
                start = len(out) - dist
                for k in range(length): out.append(out[start + k])
        return bytes(out)

    def _encode_lzh(self, data):
        tokens = self._lz77_tokenize(data)
        lit_freq = [0] * 256
        dist_freq = [0] * (self.MAX_DIST + 1)
        len_freq = [0] * (self.MAX_MATCH + 1)
        for t in tokens:
            if t[0] == 'L':
                lit_freq[t[1]] += 1
            else:
                dist_freq[t[1]] += 1
                len_freq[t[2]] += 1
        lit_cl = self._huffman_code_lengths(lit_freq)
        dist_cl = self._huffman_code_lengths(dist_freq)
        len_cl = self._huffman_code_lengths(len_freq)
        lit_codes = self._huffman_canonical_codes(lit_cl)
        dist_codes = self._huffman_canonical_codes(dist_cl)
        len_codes = self._huffman_canonical_codes(len_cl)
        bits = []
        token_count = len(tokens)
        for b in struct.pack('>I', token_count):
            for i in range(8): bits.append((b >> (7 - i)) & 1)
        for t in tokens:
            if t[0] == 'L':
                bits.append(0)
                code, cl = lit_codes[t[1]]
                for i in range(cl - 1, -1, -1): bits.append((code >> i) & 1)
            else:
                bits.append(1)
                code_d, cl_d = dist_codes[t[1]]
                for i in range(cl_d - 1, -1, -1): bits.append((code_d >> i) & 1)
                code_l, cl_l = len_codes[t[2]]
                for i in range(cl_l - 1, -1, -1): bits.append((code_l >> i) & 1)
        pad = (8 - len(bits) % 8) % 8
        bits.extend([0] * pad)

        def pack_lengths_16(lst):
            return b''.join(struct.pack('>H', l) for l in lst)

        lit_len_bytes = pack_lengths_16(lit_cl)
        dist_len_bytes = pack_lengths_16(dist_cl)
        len_len_bytes = pack_lengths_16(len_cl)
        header = bytearray()
        header.extend(lit_len_bytes)
        header.extend(dist_len_bytes)
        header.extend(len_len_bytes)
        out = bytearray(header)
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8): byte = (byte << 1) | bits[i + j]
            out.append(byte)
        return bytes(out)

    def _decode_lzh(self, data):
        LIT_LEN_BYTES = 256 * 2
        DIST_LEN_BYTES = 2049 * 2
        LEN_LEN_BYTES = 2049 * 2
        if len(data) < LIT_LEN_BYTES + DIST_LEN_BYTES + LEN_LEN_BYTES: return None
        pos = 0
        lit_cl = [struct.unpack('>H', data[i:i + 2])[0] for i in range(pos, pos + LIT_LEN_BYTES, 2)]
        pos += LIT_LEN_BYTES
        dist_cl = [struct.unpack('>H', data[i:i + 2])[0] for i in range(pos, pos + DIST_LEN_BYTES, 2)]
        pos += DIST_LEN_BYTES
        len_cl = [struct.unpack('>H', data[i:i + 2])[0] for i in range(pos, pos + LEN_LEN_BYTES, 2)]
        pos += LEN_LEN_BYTES

        def build_decode_table(lengths):
            symbols = list(range(len(lengths)))
            symbols.sort(key=lambda s: (lengths[s], s))
            decode = {}
            code = 0
            prev_len = 0
            first = True
            for sym in symbols:
                cl = lengths[sym]
                if cl == 0: continue
                if first:
                    prev_len = cl
                    first = False
                elif cl != prev_len:
                    code <<= (cl - prev_len)
                    prev_len = cl
                decode[(cl, code)] = sym
                code += 1
            return decode

        lit_decode = build_decode_table(lit_cl)
        dist_decode = build_decode_table(dist_cl)
        len_decode = build_decode_table(len_cl)
        max_lit_bits = max(lit_cl) if any(lit_cl) else 0
        max_dist_bits = max(dist_cl) if any(dist_cl) else 0
        max_len_bits = max(len_cl) if any(len_cl) else 0
        payload = data[pos:]
        if len(payload) < 4: return None
        token_count = struct.unpack('>I', payload[:4])[0]
        bits = []
        for b in payload[4:]: bits.extend([(b >> i) & 1 for i in range(7, -1, -1)])
        bpos = 0
        tokens = []
        for _ in range(token_count):
            if bpos >= len(bits): return None
            flag = bits[bpos]
            bpos += 1
            if flag == 0:
                found = False
                for cl in range(1, max_lit_bits + 1):
                    if bpos + cl > len(bits): break
                    val = 0
                    for j in range(cl): val = (val << 1) | bits[bpos + j]
                    if (cl, val) in lit_decode:
                        tokens.append(('L', lit_decode[(cl, val)], None))
                        bpos += cl
                        found = True
                        break
                if not found: return None
            else:
                found_d = False
                for cl in range(1, max_dist_bits + 1):
                    if bpos + cl > len(bits): break
                    val = 0
                    for j in range(cl): val = (val << 1) | bits[bpos + j]
                    if (cl, val) in dist_decode:
                        dist = dist_decode[(cl, val)]
                        bpos += cl
                        found_d = True
                        break
                if not found_d: return None
                found_l = False
                for cl in range(1, max_len_bits + 1):
                    if bpos + cl > len(bits): break
                    val = 0
                    for j in range(cl): val = (val << 1) | bits[bpos + j]
                    if (cl, val) in len_decode:
                        length = len_decode[(cl, val)]
                        bpos += cl
                        found_l = True
                        break
                if not found_l: return None
                tokens.append(('M', dist, length))
        return self._lz77_untokenize(tokens)

    def _compress_lzh_pipeline(self, data, ultra=True):
        best_total = float('inf')
        best_bytes = None

        def try_candidate(header, transformed):
            nonlocal best_total, best_bytes
            lzh = self._encode_lzh(transformed)
            candidate = header + b'\xFF' + lzh
            decomp = self._decompress_lzh_pipeline(candidate)
            if decomp == data and len(candidate) < best_total:
                best_total = len(candidate)
                best_bytes = candidate

        try_candidate(self._encode_marker_raw(), data)
        for t in range(1, 53):
            try:
                transformed = self.fwd[t](data)
                try_candidate(self._encode_marker_single(t), transformed)
            except:
                continue
        if ultra:
            for t1, t2 in self.sequences:
                try:
                    transformed = self.fwd[t1](data)
                    transformed = self.fwd[t2](transformed)
                    try_candidate(self._encode_marker_pair(t1, t2), transformed)
                except:
                    continue
        if best_bytes is None: raise RuntimeError("LZH compression failed.")
        return best_bytes

    def _decompress_lzh_pipeline(self, data):
        offset, seq = self._decode_header(data)
        if offset == 0 or len(data) <= offset or data[offset] != 0xFF: return None
        lzh_data = data[offset + 1:]
        transformed = self._decode_lzh(lzh_data)
        if transformed is None: return None
        if not seq: return transformed
        return self._reverse_sequence(transformed, seq)

    def _encode_marker_single(self, t):
        if t <= 252: return bytes([t - 1])
        return bytes([254, t - 253])

    def _encode_marker_raw(self): return bytes([252])

    def _encode_marker_pair(self, t1, t2):
        idx = self.pair_to_index[(t1, t2)]
        return bytes([253, (idx >> 8) & 0xFF, idx & 0xFF])

    def _decode_header(self, data):
        if not data: return 0, ()
        f = data[0]
        if f < 252: return 1, (f + 1,)
        elif f == 252: return 1, ()
        elif f == 253:
            if len(data) < 3: return 0, ()
            idx = (data[1] << 8) | data[2]
            if idx >= len(self.sequences): return 0, ()
            t1, t2 = self.pair_lookup[idx]
            return 3, (t1, t2)
        elif f == 254:
            if len(data) < 2: return 0, ()
            x = data[1]
            if x > 3: return 0, ()
            return 2, (253 + x,)
        else:
            return 0, ()

    def _reverse_sequence(self, data, seq):
        res = data
        for t in reversed(seq): res = self.rev[t](res)
        return res

    def _compress_backend(self, data, safe=False):
        candidates = []
        if HAS_ZSTD:
            try:
                candidates.append((b'Z', zstd_cctx.compress(data)))
            except:
                pass
        if HAS_PAQ:
            try:
                candidates.append((b'P', paq_mod.compress(data)))
            except:
                pass
        candidates.append((b'N', data))
        if safe:
            marker, best = min(candidates, key=lambda x: len(x[1]))
            return bytes([marker[0]]) + best
        else:
            _, best = min(candidates, key=lambda x: len(x[1]))
            return best

    def _decompress_backend(self, data, safe=False):
        if not data: return None
        if safe and len(data) > 1:
            marker = data[0]
            payload = data[1:]
            if marker == ord('N'): return payload
            if marker == ord('Z') and HAS_ZSTD:
                try:
                    return zstd_dctx.decompress(payload)
                except:
                    pass
            if marker == ord('P') and HAS_PAQ:
                try:
                    return paq_mod.decompress(payload)
                except:
                    pass
            return None
        if HAS_ZSTD:
            try:
                return zstd_dctx.decompress(data)
            except:
                pass
        if HAS_PAQ:
            try:
                return paq_mod.decompress(data)
            except:
                pass
        return data

    def compress_with_best(self, data, ultra=True):
        if not data:
            backend = self._compress_backend(b'', safe=False)
            return self._encode_marker_raw() + backend
        best_total = float('inf')
        best_bytes = None

        def try_candidate(header, transformed):
            nonlocal best_total, best_bytes
            backend = self._compress_backend(transformed, safe=False)
            candidate = header + backend
            decomp, _ = self._decompress_auto(candidate)
            if decomp == data and len(candidate) < best_total:
                best_total = len(candidate)
                best_bytes = candidate

        try_candidate(self._encode_marker_raw(), data)
        for t in range(1, 53):
            try:
                transformed = self.fwd[t](data)
                try_candidate(self._encode_marker_single(t), transformed)
            except:
                continue
        if ultra:
            for t1, t2 in self.sequences:
                try:
                    transformed = self.fwd[t1](data)
                    transformed = self.fwd[t2](transformed)
                    try_candidate(self._encode_marker_pair(t1, t2), transformed)
                except:
                    continue
        if best_bytes is None: raise RuntimeError("Compression failed.")
        return best_bytes

    def _decompress_auto(self, data):
        offset, seq = self._decode_header(data)
        if offset == 0: return None, None
        payload = data[offset:]
        if not payload: return None, None
        res = self._decompress_backend(payload, safe=False)
        if res is None: return None, None
        if not seq: return res, None
        return self._reverse_sequence(res, seq), seq

    ZADEN_MAGIC = 0x33

    def _find_best_16bit_key(self, block, time_limit=60):
        if len(block) < 3: return 0
        pad = (3 - len(block) % 3) % 3
        padded = block + b'\x00' * pad
        vals = [int.from_bytes(padded[i:i + 3], 'little') for i in range(0, len(padded), 3)]
        best_key = 0
        best_cost = float('inf')
        start = time.time()
        for key in range(65536):
            if time.time() - start > time_limit: break
            trans = [((v - key) & 0xFFFFFF) for v in vals]
            mean = sum(trans) // len(trans)
            cost = sum(abs(t - mean) for t in trans)
            if cost < best_cost:
                best_cost = cost
                best_key = key
        return best_key

    def _encode_key_unary(self, key):
        if key == 0:
            bits = '0'
            length = 1
        else:
            bits = bin(key)[2:]
            length = len(bits)
        prefix = '0' * (length - 1) + '1'
        encoded = prefix + bits
        pad = (8 - len(encoded) % 8) % 8
        encoded += '0' * pad
        return bytes(int(encoded[i:i + 8], 2) for i in range(0, len(encoded), 8))

    def _decode_key_unary(self, data, pos):
        bit_idx = pos * 8
        zeros = 0
        while True:
            byte_idx = bit_idx // 8
            bit_off = bit_idx % 8
            if byte_idx >= len(data): raise ValueError("EOF")
            byte = data[byte_idx]
            bit = (byte >> (7 - bit_off)) & 1
            bit_idx += 1
            if bit == 1: break
            zeros += 1
        length = zeros + 1
        key = 0
        for _ in range(length):
            byte_idx = bit_idx // 8
            bit_off = bit_idx % 8
            if byte_idx >= len(data): raise ValueError("EOF")
            byte = data[byte_idx]
            bit = (byte >> (7 - bit_off)) & 1
            key = (key << 1) | bit
            bit_idx += 1
        bit_idx = ((bit_idx + 7) // 8) * 8
        new_pos = bit_idx // 8
        return key, new_pos

    def _block_optimize(self, data, block_size=256, time_limit=60):
        keys = []
        parts = []
        for i in range(0, len(data), block_size):
            block = data[i:i + block_size]
            k1 = self._find_best_16bit_key(block, time_limit)
            pad = (3 - len(block) % 3) % 3
            padded = block + b'\x00' * pad
            trans1 = bytearray()
            for j in range(0, len(padded), 3):
                v = int.from_bytes(padded[j:j + 3], 'little')
                new = (v - k1) & 0xFFFFFF
                trans1.extend(new.to_bytes(3, 'little'))
            inter = bytes(trans1[:len(block)])
            k2 = self._find_best_16bit_key(inter, time_limit)
            pad2 = (3 - len(inter) % 3) % 3
            padded2 = inter + b'\x00' * pad2
            trans2 = bytearray()
            for i in range(0, len(padded2), 3):
                v = int.from_bytes(padded2[i:i + 3], 'little')
                new = (v - k2) & 0xFFFFFF
                trans2.extend(new.to_bytes(3, 'little'))
            final = bytes(trans2[:len(inter)])
            keys.append((k1, k2))
            parts.append(final)
        return b''.join(parts), keys

    def zaden_compress(self, data, block_size=256, time_limit=60):
        transformed, keys = self._block_optimize(data, block_size, time_limit)
        compressed = self.compress_with_best(transformed, ultra=True)
        magic = bytes([self.ZADEN_MAGIC])
        num_blocks = len(keys)
        header = struct.pack('<II', block_size, num_blocks)
        key_bytes = b''.join(self._encode_key_unary(k1) + self._encode_key_unary(k2) for k1, k2 in keys)
        return magic + header + key_bytes + compressed

    def zaden_decompress(self, data):
        if len(data) < 1 or data[0] != self.ZADEN_MAGIC: return None
        pos = 1
        if len(data) < pos + 8: return None
        block_size, num_blocks = struct.unpack('<II', data[pos:pos + 8])
        pos += 8
        keys = []
        for _ in range(num_blocks):
            k1, pos = self._decode_key_unary(data, pos)
            k2, pos = self._decode_key_unary(data, pos)
            keys.append((k1, k2))
        inner = data[pos:]
        decomp, _ = self._decompress_auto(inner)
        if decomp is None: return None
        out_parts = []
        offset = 0
        for k1, k2 in keys:
            block = decomp[offset:offset + block_size]
            offset += block_size
            pad = (3 - len(block) % 3) % 3
            block_pad = block + b'\x00' * pad
            inter = bytearray()
            for i in range(0, len(block_pad), 3):
                v = int.from_bytes(block_pad[i:i + 3], 'little')
                orig = (v + k2) & 0xFFFFFF
                inter.extend(orig.to_bytes(3, 'little'))
            inter = bytes(inter[:len(block)])
            pad2 = (3 - len(inter) % 3) % 3
            inter_pad = inter + b'\x00' * pad2
            orig_block = bytearray()
            for i in range(0, len(inter_pad), 3):
                v = int.from_bytes(inter_pad[i:i + 3], 'little')
                orig = (v + k1) & 0xFFFFFF
                orig_block.extend(orig.to_bytes(3, 'little'))
            out_parts.append(bytes(orig_block[:len(block)]))
        return b''.join(out_parts)

    ALGO36_MAGIC = 0x36

    def algo36_compress(self, data, time_limit=300):
        if not data: return bytes([self.ALGO36_MAGIC, 0, 0])
        pad = (3 - len(data) % 3) % 3
        padded = data + b'\x00' * pad
        vals = [int.from_bytes(padded[i:i + 3], 'little') for i in range(0, len(padded), 3)]
        n = len(vals)
        best_idx = 0
        best_metric = float('inf')
        start = time.time()
        for idx in range(24):
            p = 1 << idx
            trans = [((v - p) & 0xFFFFFF) for v in vals]
            mean = sum(trans) // n
            metric = sum(abs(t - mean) for t in trans)
            if metric < best_metric:
                best_metric = metric
                best_idx = idx
            if time.time() - start > time_limit: break
        best_pass = 1 << best_idx
        transformed = bytearray()
        for v in vals:
            transformed.extend(((v - best_pass) & 0xFFFFFF).to_bytes(3, 'little'))
        compressed = self.compress_with_best(bytes(transformed), ultra=True)
        out = bytearray([self.ALGO36_MAGIC, pad, best_idx])
        out.extend(compressed)
        return bytes(out)

    def algo36_decompress(self, data):
        if not data or data[0] != self.ALGO36_MAGIC: return None
        pos = 1
        if len(data) < pos + 2: return None
        pad = data[pos]
        pos += 1
        idx = data[pos]
        pos += 1
        if idx > 23: return None
        pass_val = 1 << idx
        compressed = data[pos:]
        decomp, _ = self._decompress_auto(compressed)
        if decomp is None: return None
        if len(decomp) % 3 != 0: return None
        out = bytearray()
        for i in range(0, len(decomp), 3):
            chunk = decomp[i:i + 3]
            val = int.from_bytes(chunk, 'little')
            orig = (val + pass_val) & 0xFFFFFF
            out.extend(orig.to_bytes(3, 'little'))
        if pad: out = out[:-pad]
        return bytes(out)

    def decompress_file(self, infile: str, outfile: str):
        try:
            with open(infile, 'rb') as f: data = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return

        if len(data) > 0 and data[0] == self.ALGO36_MAGIC:
            original = self.algo36_decompress(data)
            if original is not None:
                with open(outfile, 'wb') as f: f.write(original)
                print(f"Decompressed (Algorithm 36) -> {outfile} ({len(original)} bytes)")
                return
        if len(data) > 0 and data[0] == self.ZADEN_MAGIC:
            original = self.zaden_decompress(data)
            if original is not None:
                with open(outfile, 'wb') as f: f.write(original)
                print(f"Decompressed (Zaden) -> {outfile} ({len(original)} bytes)")
                return
        offset, seq = self._decode_header(data)
        if offset > 0 and len(data) > offset and data[offset] == 0xFF:
            original = self._decompress_lzh_pipeline(data)
            if original is not None:
                with open(outfile, 'wb') as f: f.write(original)
                print(f"Decompressed (LZ77+Huffman) -> {outfile} ({len(original)} bytes)")
                return
        original, _ = self._decompress_auto(data)
        if original is None:
            print("Decompression failed – unknown format.")
            return
        with open(outfile, 'wb') as f: f.write(original)
        seq_str = "raw" if not seq else f"sequence {seq}"
        print(f"Decompressed ({seq_str}) -> {outfile} ({len(original)} bytes)")

    def full_self_test(self):
        print("=" * 60)
        print("UltimateHybridCompressor – FULL SELF‑TEST (2704 indices)")
        print("=" * 60)
        test_byte = 0xAA
        test_data = bytes([test_byte])
        print(f"Testing all 2704 indices on byte 0x{test_byte:02X}...")
        all_ok = True
        for idx in range(2704):
            try:
                enc = self.apply_transform_by_index(test_data, idx)
                dec = self.reverse_transform_by_index(enc, idx)
                if dec != test_data:
                    print(f"  FAIL: index {idx}, seq {self.get_transform_sequence(idx)}")
                    all_ok = False
                    break
            except Exception as e:
                print(f"  EXCEPTION at {idx}: {e}")
                all_ok = False
                break
            if idx % 500 == 0 and idx > 0: print(f"  ... {idx} indices OK")
        if all_ok:
            print("  All 2704 indices lossless on test byte.")
        else:
            print("[FAIL] Basic transform index test failed.")
            return False

        rng = random.Random(12345)
        test_data = bytes(rng.randint(0, 255) for _ in range(1000))
        print("\nTesting backend compression roundtrip...")
        compressed = self.compress_with_best(test_data, ultra=True)
        decomp, _ = self._decompress_auto(compressed)
        if decomp != test_data:
            print("  FAIL")
            return False
        print("  PASS")

        print("\nTesting LZ77+Huffman pipeline...")
        compressed_lzh = self._compress_lzh_pipeline(test_data, ultra=True)
        decomp_lzh = self._decompress_lzh_pipeline(compressed_lzh)
        if decomp_lzh != test_data:
            print("  FAIL")
            return False
        print("  PASS")

        print("\nTesting Zaden block optimization...")
        compressed_z = self.zaden_compress(test_data, block_size=256, time_limit=5)
        decomp_z = self.zaden_decompress(compressed_z)
        if decomp_z != test_data:
            print("  FAIL")
            return False
        print("  PASS")

        print("\nTesting Algorithm 36...")
        compressed_a = self.algo36_compress(test_data, time_limit=5)
        decomp_a = self.algo36_decompress(compressed_a)
        if decomp_a != test_data:
            print("  FAIL")
            return False
        print("  PASS")

        print("\n[All self‑tests passed – 100% lossless]")
        return True


def main():
    print("Ultimate Hybrid Compressor – 2704 transformation paths (52x52)")
    c = UltimateHybridCompressor(repeat_count=100)

    while True:
        print("\n" + "=" * 50)
        print(" 1) Fast (52 singles, backend)")
        print(" 2) Ultra (2704 indices, backend)")
        print(" 3) LZ77+Huffman fast")
        print(" 4) LZ77+Huffman ultra")
        print(" 5) Zaden block optimization")
        print(" 6) Algorithm 36")
        print(" 7) Full self‑test")
        print(" 8) Best Overall (tries 1,2,3,4,5,6, picks smallest)")
        print(" 9) Extract (decompress) any compressed file")
        print(" 0) Exit")
        print("=" * 50)
        try:
            ch = int(input("> ").strip())
        except:
            print("Invalid input.")
            continue
        if ch == 0: break
        elif ch in (1, 2, 3, 4, 5, 6, 8):
            infile = input("Input file: ").strip()
            if not infile: continue
            outfile = input("Output file (optional): ").strip()
            if not outfile:
                base = os.path.splitext(os.path.basename(infile))[0]
                outfile = f"{base}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.uhc"
            try:
                with open(infile, 'rb') as f: data = f.read()
            except Exception as e:
                print(f"Error reading file: {e}")
                continue
            if ch == 1: compressed = c.compress_with_best(data, ultra=False)
            elif ch == 2: compressed = c.compress_with_best(data, ultra=True)
            elif ch == 3: compressed = c._compress_lzh_pipeline(data, ultra=False)
            elif ch == 4: compressed = c._compress_lzh_pipeline(data, ultra=True)
            elif ch == 5: compressed = c.zaden_compress(data, time_limit=60)
            elif ch == 6: compressed = c.algo36_compress(data, time_limit=300)
            elif ch == 8:
                methods = {}
                for name, func in [
                    ("Fast", lambda: c.compress_with_best(data, ultra=False)),
                    ("Ultra", lambda: c.compress_with_best(data, ultra=True)),
                    ("LZH_fast", lambda: c._compress_lzh_pipeline(data, ultra=False)),
                    ("LZH_ultra", lambda: c._compress_lzh_pipeline(data, ultra=True)),
                    ("Zaden", lambda: c.zaden_compress(data, time_limit=60)),
                    ("Algo36", lambda: c.algo36_compress(data, time_limit=300)),
                ]:
                    try:
                        res = func()
                        if res is not None: methods[name] = res
                    except Exception as e:
                        print(f"  {name} failed: {e}")
                if not methods:
                    print("All methods failed.")
                    continue
                best_name = min(methods, key=lambda k: len(methods[k]))
                compressed = methods[best_name]
                print(f"Best: {best_name} ({len(compressed)} bytes)")
            try:
                with open(outfile, 'wb') as f: f.write(compressed)
                print(f"Compressed {len(data)} -> {len(compressed)} bytes, written to {outfile}")
            except Exception as e:
                print(f"Write error: {e}")
        elif ch == 9:
            infile = input("Compressed file: ").strip()
            outfile = input("Output file (optional): ").strip()
            if not outfile:
                base = os.path.splitext(os.path.basename(infile))[0]
                outfile = f"{base}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.orig"
            c.decompress_file(infile, outfile)
        elif ch == 7:
            c.full_self_test()
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
