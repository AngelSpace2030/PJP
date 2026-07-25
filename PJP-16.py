#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===========================================================================
UNIFIED PAQJP COMPRESSOR (2 Engines in 1)
===========================================================================
Engine 1: PAQJP 9.3 – 65536 Indices + LZ77 + Huffman (2KB window)
Engine 2: Ultimate Hybrid Compressor – 2704 Paths + Quantum/Dicts/Zaden/Algo36
===========================================================================
"""

import math, random, decimal, hashlib, base64, heapq, struct, os, tempfile, time, re, urllib.request, sys, subprocess, importlib
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Callable, Any
from collections import Counter, defaultdict

# ---------- Install helpers ----------
def install_package(pkg: str) -> bool:
    print(f"Installing {pkg}...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
        print(f"Successfully installed {pkg}")
        return True
    except Exception as e:
        print(f"Failed to install {pkg}: {e}")
        return False

# ---------- Optional Quantum & Backend prompts (for Engine 2) ----------
USE_QUANTUM = False
HAS_QISKIT = False
quantum_choice = input("Enable quantum‑inspired transforms (requires Qiskit)? (y/n): ").strip().lower()
if quantum_choice == 'y':
    try:
        from qiskit import QuantumCircuit
        HAS_QISKIT = True; USE_QUANTUM = True
        print("Quantum ENABLED.")
    except ImportError:
        print("Qiskit not found. Attempting auto‑install...")
        if install_package('qiskit'):
            try:
                from qiskit import QuantumCircuit
                HAS_QISKIT = True; USE_QUANTUM = True
                print("Quantum ENABLED after install.")
            except: print("Import failed – quantum disabled.")
        else: print("Install failed – quantum disabled.")

other_choice = input("Install other backends (zstandard, paq)? (y/n): ").strip().lower()
if other_choice == 'y':
    for pkg in ['zstandard', 'paq']:
        try: importlib.import_module(pkg)
        except ImportError: install_package(pkg)

# ---------- Optional Imports ----------
try: import paq
except ImportError: paq = None
try:
    import zstandard as zstd
    zstd_cctx = zstd.ZstdCompressor(level=22)
    zstd_dctx = zstd.ZstdDecompressor()
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

if USE_QUANTUM and not HAS_QISKIT:
    try:
        from qiskit import QuantumCircuit
        HAS_QISKIT = True
    except ImportError:
        USE_QUANTUM = False; print("Quantum disabled.")

# ---------- Dictionaries (for Engine 2) ----------
DICT_DIR = "Dictionaries"
COMBINED_DICT = os.path.join(DICT_DIR, "dictionary_combined.txt")
DICT_FILES = ["generated.txt", "eng_news_2005_1M-sentences.txt", "eng_news_2005_1M-words.txt", "eng_news_2005_1M-sources.txt", "eng_news_2005_1M-co_n.txt", "eng_news_2005_1M-co_s.txt", "eng_news_2005_1M-inv_w_2.txt", "eng_news_2005_1M-inv_w_3.txt", "eng_news_2005_1M-inv_so.txt", "eng_news_2005_1M-meta.txt", "Dictionary.txt", "the-complete-reference-html-css-fifth-edition.txt"]
DICT_URLS = ["https://drive.google.com/uc?export=download&id=1u_1dCEl8hhdEug6GwkOxHAuSx_6_Pme9", "https://drive.google.com/uc?export=download&id=1pVqNN5JZ2AeOCgRaHkv4Vv6Byr4zK20e", "https://drive.google.com/uc?export=download&id=1ZSC-Tn76x8itdN0rCp-Zw17hGudxbjxo", "https://drive.google.com/uc?export=download&id=1VB_7tzngs4GxjclSRyRDnxgS8znT2w2S", "https://drive.google.com/uc?export=download&id=1KVIRgiMrhCUCqQZJ3UT67ztls2GqGJzz", "https://drive.google.com/uc?export=download&id=1Z3Lx6SqL4HWsnmbJCez4kXWRQQhUXWKL", "https://drive.google.com/uc?export=download&id=1br2bdRMkZEVVRPKYmC4IIaZuAjxFJE4N", "https://drive.google.com/uc?export=download&id=1aE6ubPZiJ8rr3lEVk8fFJYjDQ1y1rU0X", "https://drive.google.com/uc?export=download&id=1uro3TZe-t5zPx2Qu2xrTL3lU8N0melk9", "https://drive.google.com/uc?export=download&id=1HqsTH1DqpWNpGbn9VtD7-SB6wVqA90R2", "https://drive.google.com/uc?export=download&id=1zZ8iMeBC3605NZhuc4UE9jx_w_lZFg5B", "https://drive.google.com/uc?export=download&id=1dDdqYDgm7f-smS7KF70Wf0KmyFo-ft1M"]
MAX_LINE_ENTRIES = 1024

def download_and_merge_dictionaries():
    if not os.path.exists(DICT_DIR): os.makedirs(DICT_DIR, exist_ok=True)
    if os.path.exists(COMBINED_DICT):
        print(f"Combined dictionary already exists. Skipping download."); return True
    all_words = set(); success = 0
    for fname, url in zip(DICT_FILES, DICT_URLS):
        local = os.path.join(DICT_DIR, fname)
        print(f"Downloading {fname}...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                content = r.read()
            if b'<html' in content[:200].lower(): continue
            with open(local, 'wb') as f: f.write(content)
            with open(local, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    w = line.strip()
                    if not w: continue
                    try: all_words.add(base64.b64decode(w, validate=True).decode('utf-8'))
                    except: all_words.add(w)
            success += 1
        except Exception as e: print(f"  ERROR {fname}: {e}")
    if success == 0: print("No dictionaries downloaded. Continuing without."); return False
    with open(COMBINED_DICT, 'w', encoding='utf-8') as f:
        for w in sorted(all_words): f.write(w + '\n')
    print(f"Merged {len(all_words)} words."); return True

# ---------- Constants (used by both engines) ----------
PRIMES = [p for p in range(2, 256) if all(p % d for d in range(2, int(p ** 0.5) + 1))]
PI_DIGITS = [79, 17, 111]
ALPHABET_6BIT = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 \n"
CHAR_TO_6BIT = {ch: i for i, ch in enumerate(ALPHABET_6BIT)}
SIXBIT_TO_CHAR = {i: ch for ch, i in CHAR_TO_6BIT.items()}
PAQ_STATE_TABLE = [[1,2,0,0],[3,5,0,1],[4,6,2,0],[7,10,0,2],[8,12,3,0],[9,13,1,1],[11,14,0,3],[15,19,4,0],[16,23,2,1],[17,24,2,1],[18,25,2,1],[20,27,1,2],[21,28,1,2],[22,29,1,2],[26,30,0,4],[31,33,5,0],[32,34,3,1],[35,37,1,3],[36,38,1,3],[39,42,0,5],[40,43,4,1],[41,44,2,2],[45,48,1,4],[46,49,1,4],[47,50,1,4],[51,52,0,6],[53,55,6,0],[54,56,4,1],[57,59,2,3],[58,60,2,3],[61,63,0,7],[62,64,5,1],[65,66,3,2],[67,69,1,5],[68,70,1,5],[71,73,0,8],[72,74,6,1],[75,76,4,2],[77,78,2,4],[79,80,2,4],[81,82,0,9],[83,84,7,1],[85,86,5,2],[87,88,3,3],[89,90,1,6],[91,92,0,10],[93,94,8,1],[95,96,6,2],[97,98,4,3],[99,100,2,5],[101,102,0,11],[103,104,9,1],[105,106,7,2],[107,108,5,3],[109,110,3,4],[111,112,1,7],[113,114,0,12],[115,116,10,1],[117,118,8,2],[119,120,6,3],[121,122,4,4],[123,124,2,6],[125,126,0,13],[127,128,11,1],[129,130,9,2],[131,132,7,3],[133,134,5,4],[135,136,3,5],[137,138,1,8],[139,140,0,14],[141,142,12,1],[143,144,10,2],[145,146,8,3],[147,148,6,4],[149,150,4,5],[151,152,2,7],[153,154,0,15],[155,156,13,1],[157,158,11,2],[159,160,9,3],[161,162,7,4],[163,164,5,5],[165,166,3,6],[167,168,1,9],[169,170,0,16],[171,172,14,1],[173,174,12,2],[175,176,10,3],[177,178,8,4],[179,180,6,5],[181,182,4,6],[183,184,2,8],[185,186,0,17],[187,188,15,1],[189,190,13,2],[191,192,11,3],[193,194,9,4],[195,196,7,5],[197,198,5,6],[199,200,3,7],[201,202,1,10],[203,204,0,18],[205,206,16,1],[207,208,14,2],[209,210,12,3],[211,212,10,4],[213,214,8,5],[215,216,6,6],[217,218,4,7],[219,220,2,9],[221,222,0,19],[223,224,17,1],[225,226,15,2],[227,228,13,3],[229,230,11,4],[231,232,9,5],[233,234,7,6],[235,236,5,7],[237,238,3,8],[239,240,1,11],[241,242,0,20],[243,244,18,1],[245,246,16,2],[247,248,14,3],[249,250,12,4],[251,252,10,5],[253,254,8,6],[255,255,6,7]]
_CONST_DIAPASON_ITER_CODE = [(2,0b10),(2,0b11),(3,0b010),(3,0b011),(4,0b0010),(4,0b0011),(5,0b00010),(5,0b00011),(6,0b000010),(6,0b000011),(7,0b0000010),(7,0b0000011),(8,0b00000010),(8,0b00000011),(9,0b000000010),(9,0b000000011)]
_CONST_DIAPASON_ITER_DECODE = {}
for nibble, (l,b) in enumerate(_CONST_DIAPASON_ITER_CODE): _CONST_DIAPASON_ITER_DECODE[(l,b)] = nibble

def find_nearest_prime_around(n):
    o=0
    while True:
        c1,c2=n-o,n+o
        if c1>=2 and all(c1%d for d in range(2,int(c1**0.5)+1)): return c1
        if c2>=2 and all(c2%d for d in range(2,int(c2**0.5)+1)): return c2
        o+=1

# ============================================================================
# ENGINE 1: PAQJP 9.3 – 65536 Transform Paths (Indices 0-65535) + LZ77+Huffman
# ============================================================================
class PAQJPCompressorTransform65535:
    def __init__(self, repeat_count: int = 100):
        self.repeat_count = repeat_count
        self.PI_DIGITS = PI_DIGITS.copy()
        self.seed_tables = self._gen_seed_tables(num=126, size=40, seed=42)
        self.fibonacci = self._gen_fib(100)
        self.PI_STR = "3.14159265358979323846264338327950288419716939937510"
        self.mod_state_table = [[(val - 400) & 0xFF for val in row] for row in PAQ_STATE_TABLE]
        self._build_transform_maps()
        self.sequences = self._build_pair_sequences()
        self.pair_lookup = {idx: (t1, t2) for idx, (t1, t2) in enumerate(self.sequences)}
        self._build_mask_46()

    def _build_mask_46(self):
        base = [1,2,4,8,16,32,64,128,3,6]
        minus_ten = [(b - 10) & 0xFF for b in base]
        self.mask_46 = minus_ten * 10

    def get_pi_digits(self, n: int) -> str:
        if n < 1: return ""
        return self.PI_STR[2:2 + n]

    def find_lossless_k(self, n: int):
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

    def to_bin(self, value: int, bits: int) -> str: return format(value, 'b').zfill(bits)
    def get_bit_size(self, k: int) -> int: return 23 if k <= 0x7FFFFF else 25

    def transform_17(self, data: bytes) -> bytes:
        if not data: return b''
        k, _ = self.find_lossless_k(7)
        bits_used = self.get_bit_size(k)
        bit_str = self.to_bin(k, bits_used)
        mask_bytes = []
        for i in range(0, len(bit_str), 8):
            byte_bits = bit_str[i:i + 8]
            if len(byte_bits) < 8: byte_bits = byte_bits.ljust(8, '0')
            mask_bytes.append(int(byte_bits, 2))
        mask = bytes(mask_bytes)
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= mask[i % len(mask)]
        return bytes(t)
    reverse_transform_17 = transform_17

    def get_basel_digits(self, n: int) -> str:
        decimal.getcontext().prec = n + 5
        pi = decimal.Decimal(self.PI_STR)
        basel = (pi * pi) / decimal.Decimal(6)
        s = str(basel).replace('.', ''); return s[:n]
    def get_one_over_e_digits(self, n: int) -> str:
        decimal.getcontext().prec = n + 5
        e = decimal.Decimal(1).exp()
        inv_e = decimal.Decimal(1) / e
        s = str(inv_e).replace('.', ''); return s[:n]
    def get_5e_digits(self, n: int) -> str:
        decimal.getcontext().prec = n + 5
        e = decimal.Decimal(1).exp()
        five_e = decimal.Decimal(5) * e
        s = str(five_e).replace('.', ''); return s[:n]

    def _gen_seed_tables(self, num=126, size=40, seed=42):
        random.seed(seed)
        return [[random.randint(5, 255) for _ in range(size)] for _ in range(num)]
    def _gen_fib(self, n):
        a,b=0,1; res=[a,b]
        for _ in range(2,n): a,b=b,a+b; res.append(b)
        return res
    def get_seed(self, idx: int, val: int) -> int:
        if 0 <= idx < len(self.seed_tables): return self.seed_tables[idx][val % 40]
        return 0

    def _append_bits(self, bitlist: List[int], value: int, count: int):
        for i in range(count - 1, -1, -1): bitlist.append((value >> i) & 1)
    def _read_bits(self, bits: List[int], pos: int, count: int) -> int:
        val = 0
        for i in range(count):
            if pos + i >= len(bits): return 0
            val = (val << 1) | bits[pos + i]
        return val

    def transform_00(self, data: bytes) -> bytes:
        if not data: return b'\x00'
        best_result = None; best_length = float('inf'); best_shifts = []
        MAX_PASSES = 10; current = bytearray(data); applied_shifts = []; original_bytes = bytes(data)
        for _ in range(MAX_PASSES):
            best_shift = 0; best_shifted = current; best_score = float('-inf')
            for shift in range(256):
                tmp = bytearray(current)
                for j in range(len(tmp)): tmp[j] = (tmp[j] + shift) % 256
                score = 0; i = 0
                while i < len(tmp):
                    val = tmp[i]; run = 1; i += 1
                    while i < len(tmp) and tmp[i] == val: run += 1; i += 1
                    score += run * run
                if score > best_score: best_score = score; best_shifted = tmp; best_shift = shift
            applied_shifts.append(best_shift)
            rle_encoded = self._apply_rle_to_shifted(best_shifted, best_shift)
            decoded_shifted = self._rle_decode(rle_encoded)
            if decoded_shifted is not None:
                test = bytearray(decoded_shifted)
                for shift in applied_shifts:
                    for j in range(len(test)): test[j] = (test[j] - shift) % 256
                if bytes(test) == original_bytes:
                    if len(rle_encoded) < best_length:
                        best_length = len(rle_encoded); best_result = rle_encoded; best_shifts = applied_shifts.copy()
            current = best_shifted
            if len(rle_encoded) >= len(data): break
        if best_result is None or best_length >= len(data): return bytes([0]) + data
        header = bytearray([len(best_shifts)]); header.extend(best_shifts)
        return header + best_result

    def _apply_rle_to_shifted(self, shifted_data: bytearray, shift: int) -> bytes:
        bits = []
        self._append_bits(bits, 0b010, 3); self._append_bits(bits, shift, 8)
        i = 0; n = len(shifted_data)
        while i < n:
            val = shifted_data[i]; run = 1; i += 1
            while i < n and shifted_data[i] == val: run += 1; i += 1
            while run >= 13:
                chunk = min(run, 268)
                self._append_bits(bits, 0b1111, 4); self._append_bits(bits, chunk - 13, 8)
                self._append_bits(bits, val, 8); run -= chunk
            if run == 1: self._append_bits(bits, 0b00, 2); self._append_bits(bits, val, 8)
            elif run <= 5: self._append_bits(bits, 0b01, 2); self._append_bits(bits, run - 2, 2); self._append_bits(bits, val, 8)
            elif run <= 12: self._append_bits(bits, 0b10, 2); self._append_bits(bits, run - 6, 3); self._append_bits(bits, val, 8)
        pad = (8 - len(bits) % 8) % 8; self._append_bits(bits, 0, pad)
        out = bytearray()
        for j in range(0, len(bits), 8):
            byte = 0
            for k in range(8):
                if j + k < len(bits): byte = (byte << 1) | bits[j + k]
            out.append(byte)
        return bytes(out)

    def reverse_transform_00(self, cdata: bytes) -> bytes:
        if not cdata or cdata == b'\x00': return b''
        if cdata[0] == 0: return cdata[1:]
        num_passes = cdata[0]
        if num_passes == 0 or len(cdata) < 1 + num_passes: return b''
        shifts = list(cdata[1:1 + num_passes]); rle_data = cdata[1 + num_passes:]
        decoded = self._rle_decode(rle_data)
        if decoded is None: return b''
        current = bytearray(decoded)
        for shift in reversed(shifts):
            for i in range(len(current)): current[i] = (current[i] - shift) % 256
        return bytes(current)

    def _rle_decode(self, data: bytes) -> Optional[bytearray]:
        if not data: return None
        bits = []
        for b in data:
            for i in range(7, -1, -1): bits.append((b >> i) & 1)
        pos = 0; nbits = len(bits)
        if nbits < 11: return None
        marker = self._read_bits(bits, pos, 3); pos += 3
        if marker != 0b010: return None
        pos += 8
        out = bytearray()
        while pos < nbits:
            if pos + 2 > nbits: break
            prefix = self._read_bits(bits, pos, 2); pos += 2
            if prefix == 0b00:
                if pos + 8 > nbits: break; run = 1
            elif prefix == 0b01:
                if pos + 2 + 8 > nbits: break; run = 2 + self._read_bits(bits, pos, 2); pos += 2
            elif prefix == 0b10:
                if pos + 3 + 8 > nbits: break; run = 6 + self._read_bits(bits, pos, 3); pos += 3
            else:
                if pos + 2 + 8 + 8 > nbits: break
                if self._read_bits(bits, pos, 2) != 0b11: return None
                pos += 2; run = 13 + self._read_bits(bits, pos, 8); pos += 8
            if pos + 8 > nbits: break
            val = self._read_bits(bits, pos, 8); pos += 8
            out.extend([val] * run)
        for i in range(pos, nbits):
            if bits[i] != 0: return None
        return out

    def transform_01(self, d):
        t = bytearray(d); r = self.repeat_count
        for prime in PRIMES:
            xor_val = prime if prime == 2 else max(1, math.ceil(prime * 4096 / 28672))
            for _ in range(r):
                for i in range(0, len(t), 3):
                    if i < len(t): t[i] ^= xor_val
        return bytes(t)
    reverse_transform_01 = transform_01

    def transform_02(self, d):
        if len(d) < 1: return b''
        t = bytearray(d); checksum = sum(d) % 256
        pattern_index = (len(d) + checksum) % 256
        pattern_values = self._get_pattern(4, pattern_index)
        for i in range(1, len(t), 4):
            if i < len(t): t[i] ^= pattern_values[i % len(pattern_values)]
        return bytes([pattern_index]) + bytes(t)
    def reverse_transform_02(self, d):
        if len(d) < 2: return b''
        pattern_index = d[0]; t = bytearray(d[1:])
        pattern_values = self._get_pattern(4, pattern_index)
        for i in range(1, len(t), 4):
            if i < len(t): t[i] ^= pattern_values[i % len(pattern_values)]
        return bytes(t)

    def transform_03(self, d):
        if len(d) < 1: return b''
        t = bytearray(d); rotation = (len(d) * 13 + sum(d)) % 8
        if rotation == 0: rotation = 1
        for i in range(2, len(t), 5):
            if i < len(t): t[i] = ((t[i] << rotation) | (t[i] >> (8 - rotation))) & 0xFF
        return bytes([rotation]) + bytes(t)
    def reverse_transform_03(self, d):
        if len(d) < 2: return b''
        rotation = d[0]; t = bytearray(d[1:])
        for i in range(2, len(t), 5):
            if i < len(t): t[i] = ((t[i] >> rotation) | (t[i] << (8 - rotation))) & 0xFF
        return bytes(t)

    def transform_04(self, d):
        t = bytearray(d); r = self.repeat_count
        for _ in range(r):
            for i in range(len(t)): t[i] = (t[i] - (i % 256)) % 256
        return bytes(t)
    def reverse_transform_04(self, d):
        t = bytearray(d); r = self.repeat_count
        for _ in range(r):
            for i in range(len(t)): t[i] = (t[i] + (i % 256)) % 256
        return bytes(t)

    def transform_05(self, d, s=3):
        t = bytearray(d)
        for i in range(len(t)): t[i] = ((t[i] << s) | (t[i] >> (8 - s))) & 0xFF
        return bytes(t)
    def reverse_transform_05(self, d, s=3):
        t = bytearray(d)
        for i in range(len(t)): t[i] = ((t[i] >> s) | (t[i] << (8 - s))) & 0xFF
        return bytes(t)

    def transform_06(self, d, sd=42):
        random.seed(sd); sub = list(range(256)); random.shuffle(sub)
        t = bytearray(d)
        for i in range(len(t)): t[i] = sub[t[i]]
        return bytes(t)
    def reverse_transform_06(self, d, sd=42):
        random.seed(sd); sub = list(range(256)); random.shuffle(sub)
        inv = [0]*256
        for i in range(256): inv[sub[i]] = i
        t = bytearray(d)
        for i in range(len(t)): t[i] = inv[t[i]]
        return bytes(t)

    def transform_07(self, d):
        t = bytearray(d); r = self.repeat_count
        sh = len(d) % len(self.PI_DIGITS)
        pi_rot = self.PI_DIGITS[sh:] + self.PI_DIGITS[:sh]; sz = len(d) % 256
        for i in range(len(t)): t[i] ^= sz
        for _ in range(r):
            for i in range(len(t)): t[i] ^= pi_rot[i % len(pi_rot)]
        return bytes(t)
    reverse_transform_07 = transform_07

    def transform_08(self, d):
        t = bytearray(d); r = self.repeat_count
        sh = len(d) % len(self.PI_DIGITS)
        pi_rot = self.PI_DIGITS[sh:] + self.PI_DIGITS[:sh]
        p = find_nearest_prime_around(len(d) % 256)
        for i in range(len(t)): t[i] ^= p
        for _ in range(r):
            for i in range(len(t)): t[i] ^= pi_rot[i % len(pi_rot)]
        return bytes(t)
    reverse_transform_08 = transform_08

    def transform_09(self, d):
        t = bytearray(d); r = self.repeat_count
        sh = len(d) % len(self.PI_DIGITS)
        pi_rot = self.PI_DIGITS[sh:] + self.PI_DIGITS[:sh]
        p = find_nearest_prime_around(len(d) % 256)
        seed = self.get_seed(len(d) % len(self.seed_tables), len(d))
        for i in range(len(t)): t[i] ^= p ^ seed
        for _ in range(r):
            for i in range(len(t)): t[i] ^= pi_rot[i % len(pi_rot)] ^ (i % 256)
        return bytes(t)
    reverse_transform_09 = transform_09

    def transform_10(self, data: bytes) -> bytes:
        if not data: return b'\x00'
        cnt = sum(1 for i in range(len(data)-1) if data[i:i+2] == b'X1')
        n = (((cnt * 2) + 1) // 3) * 3 % 256
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= n
        return bytes([n]) + bytes(t)
    def reverse_transform_10(self, data: bytes) -> bytes:
        if len(data) < 1: return b''
        n = data[0]; t = bytearray(data[1:])
        for i in range(len(t)): t[i] ^= n
        return bytes(t)

    def transform_11(self, data: bytes) -> bytes:
        if not data: return b''
        t = bytearray(data); length = len(t)
        for i in range(length):
            fib_idx = (i + length) % len(self.fibonacci)
            fib_val = self.fibonacci[fib_idx] % 256
            pos_val = (i * 13 + length * 17) % 256
            key = (fib_val ^ pos_val) % 256
            t[i] ^= key
        return bytes(t)
    reverse_transform_11 = transform_11

    def transform_12(self, data: bytes) -> bytes:
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= self.fibonacci[i % len(self.fibonacci)] % 256
        return bytes(t)
    reverse_transform_12 = transform_12

    def transform_13(self, d):
        if not d: return b''
        repeats = self._calculate_repeats(d)
        current_value = len(d) % 256; prime_values = []; count = 0
        while count < repeats:
            current_value = find_nearest_prime_around(current_value)
            prime_values.append(current_value); count += 1
        t = bytearray(d)
        xor_value = prime_values[-1] if prime_values else 0
        for i in range(len(t)): t[i] ^= xor_value
        repeat_byte = (repeats - 1) % 256
        return bytes([repeat_byte]) + bytes(t)
    def reverse_transform_13(self, d):
        if len(d) < 2: return b''
        repeat_byte = d[0]
        repeats = (repeat_byte + 1) % 256
        if repeats == 0: repeats = 256
        t = bytearray(d[1:])
        current_value = len(t) % 256; prime_values = []; count = 0
        while count < repeats:
            current_value = find_nearest_prime_around(current_value)
            prime_values.append(current_value); count += 1
        xor_value = prime_values[-1] if prime_values else 0
        for i in range(len(t)): t[i] ^= xor_value
        return bytes(t)

    def transform_14(self, d):
        if not d: return b'\x00'
        checksum = sum(d) % 256
        return d + bytes([checksum])
    def reverse_transform_14(self, d):
        if not d: return b''
        return d[:-1]

    def transform_15(self, d):
        if len(d) < 1: return b''
        t = bytearray(d); pattern_index = len(d) % 256
        pattern_values = self._get_pattern(3, pattern_index)
        for i in range(0, len(t), 3):
            if i < len(t): t[i] = (t[i] + pattern_values[i % len(pattern_values)]) % 256
        return bytes([pattern_index]) + bytes(t)
    def reverse_transform_15(self, d):
        if len(d) < 2: return b''
        pattern_index = d[0]; t = bytearray(d[1:])
        pattern_values = self._get_pattern(3, pattern_index)
        for i in range(0, len(t), 3):
            if i < len(t): t[i] = (t[i] - pattern_values[i % len(pattern_values)]) % 256
        return bytes(t)

    def transform_16(self, data: bytes) -> bytes:
        if not data: return b''
        xor_byte = (len(data) * 7 + 13) % 256
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= xor_byte
        return bytes(t)
    reverse_transform_16 = transform_16

    def transform_18(self, data: bytes) -> bytes:
        if not data: return b''
        digits = self.get_basel_digits(max(10, len(data)//2 + 5))
        mask = bytes(int(digits[i:i+2]) % 256 for i in range(0, len(digits), 2))
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= mask[i % len(mask)]
        return bytes(t)
    reverse_transform_18 = transform_18

    def transform_19(self, data: bytes) -> bytes:
        if not data: return b''
        digits = self.get_one_over_e_digits(max(10, len(data)//2 + 5))
        mask = bytes(int(digits[i:i+2]) % 256 for i in range(0, len(digits), 2))
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= mask[i % len(mask)]
        return bytes(t)
    reverse_transform_19 = transform_19

    def transform_20(self, data: bytes) -> bytes:
        if not data: return b''
        digits = self.get_5e_digits(max(10, len(data)//2 + 5))
        mask = bytes(int(digits[i:i+2]) % 256 for i in range(0, len(digits), 2))
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= mask[i % len(mask)]
        return bytes(t)
    reverse_transform_20 = transform_20

    def transform_21(self, data: bytes) -> bytes:
        if not data: return b''
        shift = 255; t = bytearray(data)
        for i in range(len(t)): t[i] = (t[i] + shift) % 256
        return bytes(t)
    def reverse_transform_21(self, data: bytes) -> bytes:
        if not data: return b''
        shift = 255; t = bytearray(data)
        for i in range(len(t)): t[i] = (t[i] - shift) % 256
        return bytes(t)

    def _compress_bits(self, bits: List[int]) -> bytes:
        orig_bit_len = len(bits)
        if orig_bit_len == 0: return b'\x00\x00\x00'
        current_bits = bits[:]; prev_len = orig_bit_len; pass_count = 0
        while pass_count < 255:
            pad_len = (4 - len(current_bits) % 4) % 4
            padded = current_bits + [0] * pad_len
            nibble_count = len(padded) // 4
            encoded_bits = []
            for i in range(nibble_count):
                nibble = (padded[i*4]<<3)|(padded[i*4+1]<<2)|(padded[i*4+2]<<1)|padded[i*4+3]
                length, codeword = _CONST_DIAPASON_ITER_CODE[nibble]
                for b in range(length-1, -1, -1): encoded_bits.append((codeword >> b) & 1)
            new_len = len(encoded_bits)
            if new_len < prev_len:
                current_bits = encoded_bits; prev_len = new_len; pass_count += 1
            else: break
        header = bytes([(orig_bit_len >> 8) & 0xFF, orig_bit_len & 0xFF, pass_count])
        pad = (8 - len(current_bits) % 8) % 8
        current_bits += [0] * pad
        out_bytes = bytearray()
        for i in range(0, len(current_bits), 8):
            val = 0
            for j in range(8): val = (val << 1) | current_bits[i+j]
            out_bytes.append(val)
        return header + bytes(out_bytes)

    def _decompress_bits(self, data: bytes) -> List[int]:
        if len(data) < 3: return []
        orig_bit_len = (data[0] << 8) | data[1]
        pass_count = data[2]; payload = data[3:]
        bits = []
        for byte in payload:
            for i in range(7, -1, -1): bits.append((byte >> i) & 1)
        current_bits = bits
        for _ in range(pass_count):
            pos = 0; nbits = len(current_bits); decoded_nibbles = []
            while pos < nbits:
                matched = False
                for length in range(2, 10):
                    if pos + length > nbits: continue
                    codeword = 0
                    for k in range(length): codeword = (codeword << 1) | current_bits[pos + k]
                    key = (length, codeword)
                    if key in _CONST_DIAPASON_ITER_DECODE:
                        decoded_nibbles.append(_CONST_DIAPASON_ITER_DECODE[key])
                        pos += length; matched = True; break
                if not matched: break
            new_bits = []
            for nibble in decoded_nibbles:
                for j in range(3, -1, -1): new_bits.append((nibble >> j) & 1)
            current_bits = new_bits
        if len(current_bits) < orig_bit_len: return []
        return current_bits[:orig_bit_len]

    def transform_23(self, data: bytes) -> bytes:
        if not data: return b'\x00\x00\x00'
        bits = []
        for byte in data:
            for i in range(7, -1, -1): bits.append((byte >> i) & 1)
        return self._compress_bits(bits)

    def reverse_transform_23(self, data: bytes) -> bytes:
        bits = self._decompress_bits(data)
        if not bits: return b''
        out_bytes = bytearray()
        for i in range(0, len(bits), 8):
            val = 0
            for j in range(i, min(i+8, len(bits))): val = (val << 1) | bits[j]
            if i+8 > len(bits): val <<= (8 - (len(bits) - i))
            out_bytes.append(val)
        return bytes(out_bytes)

    def transform_24(self, data: bytes) -> bytes:
        if not data: return b''
        MAX_LEN = 43; bits = []; i = 0; n = len(data)
        while i < n:
            chunk_len = min(MAX_LEN, n - i)
            chunk = data[i:i+chunk_len]; first = chunk[0]
            all_same = all(b == first for b in chunk)
            if all_same:
                self._append_bits(bits, 1, 1); self._append_bits(bits, first, 8); self._append_bits(bits, chunk_len - 1, 6)
            else:
                self._append_bits(bits, 0, 1); self._append_bits(bits, chunk_len, 6)
                for b in chunk: self._append_bits(bits, b, 8)
            i += chunk_len
        pad = (8 - len(bits) % 8) % 8; self._append_bits(bits, 0, pad)
        out = bytearray()
        for j in range(0, len(bits), 8):
            byte = 0
            for k in range(8): byte = (byte << 1) | bits[j+k]
            out.append(byte)
        return bytes(out)

    def reverse_transform_24(self, data: bytes) -> bytes:
        if not data: return b''
        bits = []
        for byte in data:
            for i in range(7, -1, -1): bits.append((byte >> i) & 1)
        pos = 0; nbits = len(bits); out = bytearray()
        while pos < nbits:
            if pos + 1 > nbits: break
            flag = self._read_bits(bits, pos, 1); pos += 1
            if flag == 1:
                if pos + 8 + 6 > nbits: break
                byte_val = self._read_bits(bits, pos, 8); pos += 8
                count_minus1 = self._read_bits(bits, pos, 6); pos += 6
                run_len = count_minus1 + 1
                out.extend([byte_val] * run_len)
            else:
                if pos + 6 > nbits: break
                chunk_len = self._read_bits(bits, pos, 6); pos += 6
                if chunk_len == 0: break
                if pos + chunk_len * 8 > nbits: break
                for _ in range(chunk_len):
                    b = self._read_bits(bits, pos, 8); pos += 8; out.append(b)
        return bytes(out)

    def transform_25(self, data: bytes) -> bytes:
        if not data: return b'\x01'
        n = 3; res = bytearray(data)
        for i in range(len(res)): res[i] = (pow(res[i] + 1, n, 257) - 1) & 0xFF
        return bytes([n]) + bytes(res)
    def reverse_transform_25(self, data: bytes) -> bytes:
        if not data or len(data) < 2: return b''
        n = data[0]; inv = pow(n, -1, 256); res = bytearray(data[1:])
        for i in range(len(res)): res[i] = (pow(res[i] + 1, inv, 257) - 1) & 0xFF
        return bytes(res)

    def transform_26(self, data: bytes) -> bytes:
        if not data: return b'\x01\x00'
        n = (len(data) * 7 + 13) & 0xFFFF
        if n % 2 == 0: n ^= 1
        e = pow(n, 16777216, 256) | 1
        res = bytearray(data)
        for i in range(len(res)): res[i] = (pow(res[i] + 1, e, 257) - 1) & 0xFF
        return bytes([n & 0xFF, (n >> 8) & 0xFF]) + bytes(res)
    def reverse_transform_26(self, data: bytes) -> bytes:
        if not data or len(data) < 2: return b''
        n = data[0] | (data[1] << 8)
        if n % 2 == 0: n ^= 1
        e = pow(n, 16777216, 256) | 1
        inv_e = pow(e, -1, 256)
        res = bytearray(data[2:])
        for i in range(len(res)): res[i] = (pow(res[i] + 1, inv_e, 257) - 1) & 0xFF
        return bytes(res)

    def transform_27(self, data: bytes) -> bytes:
        if not data:
            out = bytearray(b'\x00\x00\x00\x00'); out.extend(b'\x01\x00'); out.extend(b'\x00' * 1024)
            return bytes(out)
        BLOCK_SIZE = 1024
        total_blocks = (len(data) + BLOCK_SIZE - 1) // BLOCK_SIZE
        out = bytearray(); out.extend(len(data).to_bytes(4, 'big'))
        for block_idx in range(total_blocks):
            start = block_idx * BLOCK_SIZE; end = min(start + BLOCK_SIZE, len(data)); chunk = data[start:end]
            pad_len = BLOCK_SIZE - len(chunk)
            if pad_len: chunk = chunk + b'\x00' * pad_len
            n = ((len(data) * 7 + block_idx * 13 + 1) & 0xFFFF) | 1
            e = pow(n, 16777216, 256) | 1; e200 = pow(e, 200, 256)
            transformed = bytearray(chunk)
            for i in range(BLOCK_SIZE): transformed[i] = (pow(transformed[i] + 1, e200, 257) - 1) & 0xFF
            out.append(n & 0xFF); out.append((n >> 8) & 0xFF); out.extend(transformed)
        return bytes(out)
    def reverse_transform_27(self, data: bytes) -> bytes:
        if not data or len(data) < 4: return b''
        orig_len = int.from_bytes(data[:4], 'big'); payload = data[4:]
        BLOCK_SIZE = 1024; block_total_len = 2 + BLOCK_SIZE
        if len(payload) % block_total_len != 0: return data
        num_blocks = len(payload) // block_total_len; decoded = bytearray()
        for block_idx in range(num_blocks):
            offset = block_idx * block_total_len
            if offset + 2 > len(payload): break
            n = payload[offset] | (payload[offset+1] << 8)
            chunk = payload[offset+2:offset+2+BLOCK_SIZE]
            if len(chunk) < BLOCK_SIZE: break
            n |= 1
            e = pow(n, 16777216, 256) | 1; e200 = pow(e, 200, 256); inv_e200 = pow(e200, -1, 256)
            for i in range(BLOCK_SIZE): decoded.append((pow(chunk[i] + 1, inv_e200, 257) - 1) & 0xFF)
        return bytes(decoded[:orig_len])

    def transform_28(self, data: bytes) -> bytes:
        if not data:
            out = bytearray(b'\x00\x00\x00\x00'); out.extend(b'\x01\x00'); out.extend(self._compress_backend(b'\x00' * 1024))
            return bytes(out)
        BLOCK_SIZE = 1024
        total_blocks = (len(data) + BLOCK_SIZE - 1) // BLOCK_SIZE
        out = bytearray(); out.extend(len(data).to_bytes(4, 'big'))
        for block_idx in range(total_blocks):
            start = block_idx * BLOCK_SIZE; end = min(start + BLOCK_SIZE, len(data)); chunk = data[start:end]
            pad_len = BLOCK_SIZE - len(chunk)
            if pad_len: chunk = chunk + b'\x00' * pad_len
            n = ((len(data) * 7 + block_idx * 13 + 1) & 0xFFFF) | 1
            e = pow(n, 16777216, 256) | 1; e200 = pow(e, 200, 256)
            transformed = bytearray(chunk)
            for i in range(BLOCK_SIZE): transformed[i] = (pow(transformed[i] + 1, e200, 257) - 1) & 0xFF
            compressed_block = self._compress_backend(bytes(transformed))
            out.append(n & 0xFF); out.append((n >> 8) & 0xFF)
            L = len(compressed_block)
            out.append((L >> 8) & 0xFF); out.append(L & 0xFF); out.extend(compressed_block)
        return bytes(out)
    def reverse_transform_28(self, data: bytes) -> bytes:
        if not data or len(data) < 4: return b''
        orig_len = int.from_bytes(data[:4], 'big'); payload = data[4:]; pos = 0; decoded = bytearray()
        while pos < len(payload):
            if pos + 2 > len(payload): break
            n = payload[pos] | (payload[pos+1] << 8); pos += 2
            if pos + 2 > len(payload): break
            comp_len = (payload[pos] << 8) | payload[pos+1]; pos += 2
            if pos + comp_len > len(payload): break
            comp_block = payload[pos:pos+comp_len]; pos += comp_len
            block = self._decompress_backend(comp_block)
            if block is None: return data
            n |= 1
            e = pow(n, 16777216, 256) | 1; e200 = pow(e, 200, 256); inv_e200 = pow(e200, -1, 256)
            transformed = bytearray(block)
            for i in range(len(transformed)): transformed[i] = (pow(transformed[i] + 1, inv_e200, 257) - 1) & 0xFF
            decoded.extend(transformed)
        return bytes(decoded[:orig_len])

    def transform_29(self, data: bytes) -> bytes:
        if not data:
            out = bytearray(b'\x00\x00\x00\x00'); out.extend(b'\x01\x00'); out.extend(self._compress_backend(b'\x00' * 32))
            return bytes(out)
        BLOCK_SIZE = 32
        total_blocks = (len(data) + BLOCK_SIZE - 1) // BLOCK_SIZE
        out = bytearray(); out.extend(len(data).to_bytes(4, 'big'))
        for block_idx in range(total_blocks):
            start = block_idx * BLOCK_SIZE; end = min(start + BLOCK_SIZE, len(data)); chunk = data[start:end]
            pad_len = BLOCK_SIZE - len(chunk)
            if pad_len: chunk = chunk + b'\x00' * pad_len
            n = ((len(data) * 7 + block_idx * 13 + 1) & 0xFFFF) | 1
            e = pow(n, 2**256, 256) | 1; e200 = pow(e, 200, 256)
            transformed = bytearray(chunk)
            compressed_block = self._compress_backend(bytes(transformed))
            out.append(n & 0xFF); out.append((n >> 8) & 0xFF)
            L = len(compressed_block)
            out.append((L >> 8) & 0xFF); out.append(L & 0xFF); out.extend(compressed_block)
        return bytes(out)
    def reverse_transform_29(self, data: bytes) -> bytes:
        if not data or len(data) < 4: return b''
        orig_len = int.from_bytes(data[:4], 'big'); payload = data[4:]; pos = 0; decoded = bytearray()
        while pos < len(payload):
            if pos + 2 > len(payload): break
            n = payload[pos] | (payload[pos+1] << 8); pos += 2
            if pos + 2 > len(payload): break
            comp_len = (payload[pos] << 8) | payload[pos+1]; pos += 2
            if pos + comp_len > len(payload): break
            comp_block = payload[pos:pos+comp_len]; pos += comp_len
            block = self._decompress_backend(comp_block)
            if block is None: return data
            decoded.extend(block)
        return bytes(decoded[:orig_len])

    def _compute_n_for_block(self, block: bytes, block_idx: int, total_len: int) -> Tuple[int, bytes]:
        if not block: return (1, b'\x01\x01')
        d = block[0]; x = (block_idx % 33) + 1
        try: t = (d*d - d**x) // 256
        except OverflowError: t = 0
        if 0 <= t <= 255: n = t | 1; return (n, bytes([1, n]))
        h = hashlib.sha256(block + bytes([block_idx & 0xFF, (total_len>>8)&0xFF, total_len&0xFF])).digest()
        n_bytes = bytearray(h); n_bytes[0] |= 1
        length = len(n_bytes); encoded = bytes([length]) + bytes(n_bytes)
        n = int.from_bytes(n_bytes, 'big')
        return (n, encoded)

    def transform_30(self, data: bytes) -> bytes:
        if not data:
            out = bytearray(b'\x00\x00\x00\x00'); out.extend(b'\x01\x01'); out.extend(self._compress_backend(b'\x00' * 33))
            return bytes(out)
        BLOCK_SIZE = 33
        total_blocks = (len(data) + BLOCK_SIZE - 1) // BLOCK_SIZE
        out = bytearray(); out.extend(len(data).to_bytes(4, 'big'))
        for block_idx in range(total_blocks):
            start = block_idx * BLOCK_SIZE; end = min(start + BLOCK_SIZE, len(data)); chunk = data[start:end]
            pad_len = BLOCK_SIZE - len(chunk)
            if pad_len: chunk = chunk + b'\x00' * pad_len
            n, enc_n = self._compute_n_for_block(chunk, block_idx, len(data))
            transformed = chunk
            compressed_block = self._compress_backend(transformed)
            out.extend(enc_n)
            L = len(compressed_block); out.append((L >> 8) & 0xFF); out.append(L & 0xFF); out.extend(compressed_block)
        return bytes(out)
    def reverse_transform_30(self, data: bytes) -> bytes:
        if not data or len(data) < 4: return b''
        orig_len = int.from_bytes(data[:4], 'big'); payload = data[4:]; pos = 0; decoded = bytearray()
        while pos < len(payload):
            if pos >= len(payload): break
            Ln = payload[pos]; pos += 1
            if Ln > 32 or pos + Ln > len(payload): break
            n_bytes = payload[pos:pos+Ln]; pos += Ln
            if pos + 2 > len(payload): break
            comp_len = (payload[pos] << 8) | payload[pos+1]; pos += 2
            if pos + comp_len > len(payload): break
            comp_block = payload[pos:pos+comp_len]; pos += comp_len
            block = self._decompress_backend(comp_block)
            if block is None: return data
            decoded.extend(block)
        return bytes(decoded[:orig_len])

    def transform_41(self, data: bytes) -> bytes:
        if not data: return b''
        mask = bytes([0x27, 0x03]); t = bytearray(data); n = min(len(t), 8)
        for i in range(n): t[i] ^= mask[i % 2]
        return bytes(t)
    reverse_transform_41 = transform_41

    def transform_42(self, data: bytes) -> bytes:
        if not data: return b''
        t = bytearray(data); mask = bytes([0x27, 0x03])
        for i in range(len(t)): t[i] ^= mask[i % 2]
        return bytes(t)
    reverse_transform_42 = transform_42

    def transform_43(self, data: bytes) -> bytes:
        if not data: return b''
        t = bytearray(data); mask = bytes([0x10, 0x00, 0x00])
        for i in range(0, len(t), 3):
            for j in range(min(3, len(t) - i)): t[i + j] ^= mask[j]
        return bytes(t)
    reverse_transform_43 = transform_43

    def transform_44(self, data: bytes) -> bytes:
        if not data: return b''
        b64_str = base64.b64encode(data).decode('ascii')
        return b64_str.encode('ascii')
    def reverse_transform_44(self, data: bytes) -> bytes:
        if not data: return b''
        try:
            b64_str = data.decode('ascii')
            return base64.b64decode(b64_str)
        except (ValueError, UnicodeDecodeError): return data

    @staticmethod
    def _huffman_code_lengths(freq: List[int]) -> List[int]:
        heap = [(f, i, i) for i, f in enumerate(freq) if f > 0]
        if not heap: return [0] * len(freq)
        if len(heap) == 1:
            lengths = [0] * len(freq); lengths[heap[0][2]] = 1; return lengths
        heapq.heapify(heap); next_id = len(heap)
        while len(heap) > 1:
            f1, _, n1 = heapq.heappop(heap); f2, _, n2 = heapq.heappop(heap)
            heapq.heappush(heap, (f1 + f2, next_id, (n1, n2))); next_id += 1
        lengths = [0] * len(freq)
        def traverse(node, depth):
            if isinstance(node, int): lengths[node] = depth
            else: left, right = node; traverse(left, depth + 1); traverse(right, depth + 1)
        _, _, root = heap[0]; traverse(root, 0)
        return lengths

    @staticmethod
    def _huffman_canonical_codes(code_lengths: List[int]) -> Dict[int, Tuple[int, int]]:
        symbols = list(range(len(code_lengths))); symbols.sort(key=lambda s: (code_lengths[s], s))
        codes = {}; code = 0; prev_len = 0; first = True
        for sym in symbols:
            cl = code_lengths[sym]
            if cl == 0: continue
            if first: prev_len = cl; first = False
            elif cl != prev_len: code <<= (cl - prev_len); prev_len = cl
            codes[sym] = (code, cl); code += 1
        return codes

    def transform_45(self, data: bytes) -> bytes:
        if not data: return b''
        freq = [0]*256
        for b in data: freq[b] += 1
        code_lengths = self._huffman_code_lengths(freq)
        codes = self._huffman_canonical_codes(code_lengths)
        header = bytearray(); header.extend(len(data).to_bytes(4, 'big')); header.extend(code_lengths)
        bits = []
        for b in data:
            c, cl = codes[b]
            for i in range(cl - 1, -1, -1): bits.append((c >> i) & 1)
        pad = (8 - len(bits) % 8) % 8; bits.extend([0] * pad)
        out_bytes = bytearray()
        for i in range(0, len(bits), 8):
            val = 0
            for j in range(8): val = (val << 1) | bits[i + j]
            out_bytes.append(val)
        return bytes(header) + bytes(out_bytes)

    def reverse_transform_45(self, data: bytes) -> bytes:
        if not data: return b''
        if len(data) < 4 + 256: return data
        original_len = int.from_bytes(data[:4], 'big')
        code_lengths = list(data[4:4+256]); payload = data[4+256:]
        if original_len == 0: return b''
        code_to_sym = {}
        symbols = list(range(256)); symbols.sort(key=lambda s: (code_lengths[s], s))
        code = 0; prev_len = 0; first = True
        for sym in symbols:
            cl = code_lengths[sym]
            if cl == 0: continue
            if first: prev_len = cl; first = False
            elif cl != prev_len: code <<= (cl - prev_len); prev_len = cl
            code_to_sym[(cl, code)] = sym; code += 1
        bits = []
        for byte in payload:
            for i in range(7, -1, -1): bits.append((byte >> i) & 1)
        pos = 0; nbits = len(bits); out = bytearray()
        while pos < nbits and len(out) < original_len:
            found = False
            for cl in range(1, 256):
                if pos + cl > nbits: break
                val = 0
                for j in range(cl): val = (val << 1) | bits[pos + j]
                if (cl, val) in code_to_sym:
                    sym = code_to_sym[(cl, val)]
                    out.append(sym); pos += cl; found = True; break
            if not found: break
        return bytes(out)

    def transform_46(self, data: bytes) -> bytes:
        if not data: return b''
        t = bytearray(data); mask = self.mask_46
        for i in range(len(t)): t[i] ^= mask[i % len(mask)]
        return bytes(t)
    reverse_transform_46 = transform_46

    def transform_47(self, data: bytes) -> bytes:
        if not data: return b''
        t = bytearray(data); table_len = len(self.mod_state_table)
        if table_len == 0: return data
        for i in range(len(t)):
            row = self.mod_state_table[i % table_len]; t[i] ^= row[0]
        return bytes(t)
    reverse_transform_47 = transform_47

    def _dynamic_transform(self, n: int):
        def tf(data: bytes):
            if not data: return b''
            seed = self.get_seed(n % len(self.seed_tables), len(data))
            t = bytearray(data)
            for i in range(len(t)): t[i] ^= seed
            return bytes(t)
        return tf, tf

    def transform_256(self, d: bytes) -> bytes: return d
    reverse_transform_256 = transform_256

    def _get_pattern(self, size: int, index: int):
        random.seed(12345 + size * 100 + index)
        return [random.randint(0, 255) for _ in range(size)]

    def _calculate_repeats(self, data: bytes) -> int:
        if not data: return 1
        length = len(data); byte_sum = sum(data) % 256
        repeats = ((length * 13 + byte_sum * 17) % 256) + 1
        return max(1, min(256, repeats))

    def _build_transform_maps(self):
        self.fwd_transforms: Dict[int, Callable] = {}; self.rev_transforms: Dict[int, Callable] = {}
        self.fwd_transforms[1] = self.transform_00; self.rev_transforms[1] = self.reverse_transform_00
        self.fwd_transforms[2] = self.transform_01; self.rev_transforms[2] = self.reverse_transform_01
        self.fwd_transforms[3] = self.transform_02; self.rev_transforms[3] = self.reverse_transform_02
        self.fwd_transforms[4] = self.transform_03; self.rev_transforms[4] = self.reverse_transform_03
        self.fwd_transforms[5] = self.transform_04; self.rev_transforms[5] = self.reverse_transform_04
        self.fwd_transforms[6] = self.transform_05; self.rev_transforms[6] = self.reverse_transform_05
        self.fwd_transforms[7] = self.transform_06; self.rev_transforms[7] = self.reverse_transform_06
        self.fwd_transforms[8] = self.transform_07; self.rev_transforms[8] = self.reverse_transform_07
        self.fwd_transforms[9] = self.transform_08; self.rev_transforms[9] = self.reverse_transform_08
        self.fwd_transforms[10] = self.transform_09; self.rev_transforms[10] = self.reverse_transform_09
        self.fwd_transforms[11] = self.transform_10; self.rev_transforms[11] = self.reverse_transform_10
        self.fwd_transforms[12] = self.transform_11; self.rev_transforms[12] = self.reverse_transform_11
        self.fwd_transforms[13] = self.transform_12; self.rev_transforms[13] = self.reverse_transform_12
        self.fwd_transforms[14] = self.transform_13; self.rev_transforms[14] = self.reverse_transform_13
        self.fwd_transforms[15] = self.transform_14; self.rev_transforms[15] = self.reverse_transform_14
        self.fwd_transforms[16] = self.transform_15; self.rev_transforms[16] = self.reverse_transform_15
        self.fwd_transforms[17] = self.transform_16; self.rev_transforms[17] = self.reverse_transform_16
        self.fwd_transforms[18] = self.transform_17; self.rev_transforms[18] = self.reverse_transform_17
        self.fwd_transforms[19] = self.transform_18; self.rev_transforms[19] = self.reverse_transform_18
        self.fwd_transforms[20] = self.transform_19; self.rev_transforms[20] = self.reverse_transform_19
        self.fwd_transforms[21] = self.transform_20; self.rev_transforms[21] = self.reverse_transform_20
        self.fwd_transforms[22] = self.transform_21; self.rev_transforms[22] = self.reverse_transform_21
        self.fwd_transforms[23] = self.transform_23; self.rev_transforms[23] = self.reverse_transform_23
        self.fwd_transforms[24] = self.transform_24; self.rev_transforms[24] = self.reverse_transform_24
        self.fwd_transforms[25] = self.transform_25; self.rev_transforms[25] = self.reverse_transform_25
        self.fwd_transforms[26] = self.transform_26; self.rev_transforms[26] = self.reverse_transform_26
        self.fwd_transforms[27] = self.transform_27; self.rev_transforms[27] = self.reverse_transform_27
        self.fwd_transforms[28] = self.transform_28; self.rev_transforms[28] = self.reverse_transform_28
        self.fwd_transforms[29] = self.transform_29; self.rev_transforms[29] = self.reverse_transform_29
        self.fwd_transforms[30] = self.transform_30; self.rev_transforms[30] = self.reverse_transform_30
        for i in range(31, 41):
            fwd, rev = self._dynamic_transform(i)
            self.fwd_transforms[i] = fwd; self.rev_transforms[i] = rev
        self.fwd_transforms[41] = self.transform_41; self.rev_transforms[41] = self.reverse_transform_41
        self.fwd_transforms[42] = self.transform_42; self.rev_transforms[42] = self.reverse_transform_42
        self.fwd_transforms[43] = self.transform_43; self.rev_transforms[43] = self.reverse_transform_43
        self.fwd_transforms[44] = self.transform_44; self.rev_transforms[44] = self.reverse_transform_44
        self.fwd_transforms[45] = self.transform_45; self.rev_transforms[45] = self.reverse_transform_45
        self.fwd_transforms[46] = self.transform_46; self.rev_transforms[46] = self.reverse_transform_46
        self.fwd_transforms[47] = self.transform_47; self.rev_transforms[47] = self.reverse_transform_47
        for i in range(48, 256):
            fwd, rev = self._dynamic_transform(i)
            self.fwd_transforms[i] = fwd; self.rev_transforms[i] = rev
        self.fwd_transforms[256] = self.transform_256; self.rev_transforms[256] = self.reverse_transform_256
        for i in range(1, 257):
            if i not in self.fwd_transforms: raise RuntimeError(f"Transform {i} missing!")

    def _build_pair_sequences(self) -> List[Tuple[int, int]]:
        pairs = []
        for t1 in range(1, 257):
            for t2 in range(1, 257):
                if t1 == 256 and t2 == 256: continue
                pairs.append((t1, t2))
        return pairs

    def get_transform_sequence(self, index: int) -> Tuple[int, ...]:
        if index < 0 or index > 65535: raise ValueError("Index must be 0..65535")
        if index == 0: return ()
        if index - 1 >= len(self.sequences): raise IndexError(f"Sequence index {index-1} out of range")
        return self.sequences[index - 1]

    def apply_transform_by_index(self, data: bytes, index: int) -> bytes:
        seq = self.get_transform_sequence(index)
        if not seq: return data
        result = data
        for t in seq:
            if t not in self.fwd_transforms: raise KeyError(f"Transform {t} not defined")
            result = self.fwd_transforms[t](result)
        return result

    def reverse_transform_by_index(self, data: bytes, index: int) -> bytes:
        seq = self.get_transform_sequence(index)
        if not seq: return data
        result = data
        for t in reversed(seq):
            if t not in self.rev_transforms: raise KeyError(f"Reverse transform {t} not defined")
            result = self.rev_transforms[t](result)
        return result

    def _compress_backend(self, data: bytes) -> bytes:
        candidates = []
        if HAS_ZSTD:
            try: candidates.append(zstd_cctx.compress(data))
            except: pass
        if paq is not None:
            try: candidates.append(paq.compress(data))
            except: pass
        candidates.append(data)
        return min(candidates, key=len)

    def _decompress_backend(self, data: bytes) -> Optional[bytes]:
        if len(data) == 0: return b''
        if HAS_ZSTD:
            try: return zstd_dctx.decompress(data)
            except: pass
        if paq is not None:
            try: return paq.decompress(data)
            except: pass
        return data

    # --- LZ77+Huffman (2 KB window) ---
    WINDOW_SIZE = 2048; MIN_MATCH = 3; MAX_MATCH = 2048; MAX_DIST = 2048

    def _lz77_tokenize(self, data: bytes) -> List[Tuple]:
        tokens = []; i = 0; n = len(data)
        while i < n:
            best_len = 0; best_dist = 0; start_window = max(0, i - self.WINDOW_SIZE)
            for j in range(start_window, i):
                if data[j] != data[i]: continue
                k = 0
                while i + k < n and j + k < i and data[j + k] == data[i + k]:
                    k += 1
                    if k >= self.MAX_MATCH: break
                if k >= self.MIN_MATCH and k > best_len:
                    best_len = k; best_dist = i - j
                    if best_len == self.MAX_MATCH: break
            if best_len >= self.MIN_MATCH:
                tokens.append(('M', best_dist, best_len)); i += best_len
            else:
                tokens.append(('L', data[i], None)); i += 1
        return tokens

    def _lz77_untokenize(self, tokens: List[Tuple]) -> bytes:
        out = bytearray()
        for t in tokens:
            if t[0] == 'L': out.append(t[1])
            else:
                dist, length = t[1], t[2]
                start = len(out) - dist
                for k in range(length): out.append(out[start + k])
        return bytes(out)

    def _encode_lzh(self, data: bytes) -> bytes:
        tokens = self._lz77_tokenize(data)
        lit_freq = [0] * 256; dist_freq = [0] * (self.MAX_DIST + 1); len_freq = [0] * (self.MAX_MATCH + 1)
        for t in tokens:
            if t[0] == 'L': lit_freq[t[1]] += 1
            else: dist_freq[t[1]] += 1; len_freq[t[2]] += 1
        lit_cl = self._huffman_code_lengths(lit_freq)
        dist_cl = self._huffman_code_lengths(dist_freq)
        len_cl = self._huffman_code_lengths(len_freq)
        lit_codes = self._huffman_canonical_codes(lit_cl)
        dist_codes = self._huffman_canonical_codes(dist_cl)
        len_codes = self._huffman_canonical_codes(len_cl)
        bits = []; token_count = len(tokens)
        for b in struct.pack('>I', token_count):
            for i in range(8): bits.append((b >> (7-i)) & 1)
        for t in tokens:
            if t[0] == 'L':
                bits.append(0); code, cl = lit_codes[t[1]]
                for i in range(cl-1, -1, -1): bits.append((code >> i) & 1)
            else:
                bits.append(1); code_d, cl_d = dist_codes[t[1]]
                for i in range(cl_d-1, -1, -1): bits.append((code_d >> i) & 1)
                code_l, cl_l = len_codes[t[2]]
                for i in range(cl_l-1, -1, -1): bits.append((code_l >> i) & 1)
        pad = (8 - len(bits) % 8) % 8; bits.extend([0] * pad)
        def pack_lengths_16(lengths: List[int]) -> bytes:
            return b''.join(struct.pack('>H', l) for l in lengths)
        lit_len_bytes = pack_lengths_16(lit_cl)
        dist_len_bytes = pack_lengths_16(dist_cl)
        len_len_bytes = pack_lengths_16(len_cl)
        header = bytearray(); header.extend(lit_len_bytes); header.extend(dist_len_bytes); header.extend(len_len_bytes)
        out = bytearray(header)
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8): byte = (byte << 1) | bits[i+j]
            out.append(byte)
        return bytes(out)

    def _decode_lzh(self, data: bytes) -> Optional[bytes]:
        LIT_LEN_BYTES = 256 * 2; DIST_LEN_BYTES = 2049 * 2; LEN_LEN_BYTES = 2049 * 2
        if len(data) < LIT_LEN_BYTES + DIST_LEN_BYTES + LEN_LEN_BYTES: return None
        pos = 0
        lit_cl = [struct.unpack('>H', data[i:i+2])[0] for i in range(pos, pos+LIT_LEN_BYTES, 2)]; pos += LIT_LEN_BYTES
        dist_cl = [struct.unpack('>H', data[i:i+2])[0] for i in range(pos, pos+DIST_LEN_BYTES, 2)]; pos += DIST_LEN_BYTES
        len_cl = [struct.unpack('>H', data[i:i+2])[0] for i in range(pos, pos+LEN_LEN_BYTES, 2)]; pos += LEN_LEN_BYTES
        def build_decode_table(lengths: List[int]) -> Dict[Tuple[int, int], int]:
            symbols = list(range(len(lengths))); symbols.sort(key=lambda s: (lengths[s], s))
            decode = {}; code = 0; prev_len = 0; first = True
            for sym in symbols:
                cl = lengths[sym]
                if cl == 0: continue
                if first: prev_len = cl; first = False
                elif cl != prev_len: code <<= (cl - prev_len); prev_len = cl
                decode[(cl, code)] = sym; code += 1
            return decode
        lit_decode = build_decode_table(lit_cl); dist_decode = build_decode_table(dist_cl); len_decode = build_decode_table(len_cl)
        max_lit_bits = max(lit_cl) if any(lit_cl) else 0
        max_dist_bits = max(dist_cl) if any(dist_cl) else 0
        max_len_bits = max(len_cl) if any(len_cl) else 0
        payload = data[pos:]
        if len(payload) < 4: return None
        token_count = struct.unpack('>I', payload[:4])[0]
        bits = []
        for byte in payload[4:]:
            for i in range(7, -1, -1): bits.append((byte >> i) & 1)
        bpos = 0; tokens = []
        for _ in range(token_count):
            if bpos >= len(bits): return None
            flag = bits[bpos]; bpos += 1
            if flag == 0:
                found = False
                for cl in range(1, max_lit_bits + 1):
                    if bpos + cl > len(bits): break
                    val = 0
                    for j in range(cl): val = (val << 1) | bits[bpos + j]
                    if (cl, val) in lit_decode:
                        lit = lit_decode[(cl, val)]; tokens.append(('L', lit, None))
                        bpos += cl; found = True; break
                if not found: return None
            else:
                found_d = False
                for cl in range(1, max_dist_bits + 1):
                    if bpos + cl > len(bits): break
                    val = 0
                    for j in range(cl): val = (val << 1) | bits[bpos + j]
                    if (cl, val) in dist_decode:
                        dist = dist_decode[(cl, val)]; bpos += cl; found_d = True; break
                if not found_d: return None
                found_l = False
                for cl in range(1, max_len_bits + 1):
                    if bpos + cl > len(bits): break
                    val = 0
                    for j in range(cl): val = (val << 1) | bits[bpos + j]
                    if (cl, val) in len_decode:
                        length = len_decode[(cl, val)]; bpos += cl; found_l = True; break
                if not found_l: return None
                tokens.append(('M', dist, length))
        return self._lz77_untokenize(tokens)

    def compress_with_lzh(self, data: bytes, ultra: bool = True) -> bytes:
        best_total = float('inf'); best_bytes = None
        def try_candidate(transform_header: bytes, transformed_data: bytes):
            nonlocal best_total, best_bytes
            lzh = self._encode_lzh(transformed_data)
            candidate = transform_header + b'\xFF' + lzh
            decomp = self._decompress_lzh_pipeline(candidate)
            if decomp == data and len(candidate) < best_total:
                best_total = len(candidate); best_bytes = candidate
        try_candidate(self._encode_marker_raw(), data)
        for t in range(1, 257):
            try:
                transformed = self.fwd_transforms[t](data)
                try_candidate(self._encode_marker_single(t), transformed)
            except: continue
        if ultra:
            for t1, t2 in self.sequences:
                try:
                    transformed = self.fwd_transforms[t1](data)
                    transformed = self.fwd_transforms[t2](transformed)
                    try_candidate(self._encode_marker_pair(t1, t2), transformed)
                except: continue
        if best_bytes is None: raise RuntimeError("Cannot compress with LZH pipeline.")
        return best_bytes

    def _decompress_lzh_pipeline(self, data: bytes) -> Optional[bytes]:
        offset, seq = self._decode_header(data)
        if offset == 0: return None
        if len(data) <= offset or data[offset] != 0xFF: return None
        lzh_data = data[offset+1:]; transformed = self._decode_lzh(lzh_data)
        if transformed is None: return None
        if not seq: return transformed
        try: return self._reverse_sequence(transformed, seq)
        except: return None

    def _encode_marker_single(self, t: int) -> bytes:
        if t <= 252: return bytes([t - 1])
        return bytes([254, t - 253])
    def _encode_marker_raw(self) -> bytes: return bytes([252])
    def _encode_marker_pair(self, t1: int, t2: int) -> bytes:
        idx = (t1 - 1) * 256 + (t2 - 1)
        if t1 == 256 and t2 == 256: raise ValueError("Identity pair excluded")
        return bytes([253, (idx >> 8) & 0xFF, idx & 0xFF])

    def _decode_header(self, data: bytes):
        if len(data) < 1: return 0, ()
        f = data[0]
        if f < 252: return 1, (f + 1,)
        elif f == 252: return 1, ()
        elif f == 253:
            if len(data) < 3: return 0, ()
            idx = (data[1] << 8) | data[2]
            if idx >= len(self.sequences): return 0, ()
            t1, t2 = self.pair_lookup[idx]; return 3, (t1, t2)
        elif f == 254:
            if len(data) < 2: return 0, ()
            x = data[1]
            if x > 3: return 0, ()
            return 2, (253 + x,)
        else: return 0, ()

    def compress_with_best(self, data: bytes, ultra: bool = True) -> bytes:
        if not data:
            backend = self._compress_backend(b'')
            return self._encode_marker_raw() + backend
        best_total = float('inf'); best_bytes = None
        def try_candidate(transform_header: bytes, transformed_data: bytes):
            nonlocal best_total, best_bytes
            backend = self._compress_backend(transformed_data)
            candidate = transform_header + backend
            decomp, _ = self._decompress_auto(candidate)
            if decomp == data and len(candidate) < best_total:
                best_total = len(candidate); best_bytes = candidate
        try_candidate(self._encode_marker_raw(), data)
        for t in range(1, 257):
            try:
                transformed = self.fwd_transforms[t](data)
                header = self._encode_marker_single(t)
                try_candidate(header, transformed)
            except: continue
        if ultra:
            for t1, t2 in self.sequences:
                try:
                    transformed = self.fwd_transforms[t1](data)
                    transformed = self.fwd_transforms[t2](transformed)
                    header = self._encode_marker_pair(t1, t2)
                    try_candidate(header, transformed)
                except: continue
        if best_bytes is None: raise RuntimeError("Cannot compress in strict marker‑free mode.")
        return best_bytes

    def _decompress_auto(self, data: bytes) -> Tuple[bytes, Optional[Tuple[int, ...]]]:
        offset, seq = self._decode_header(data)
        if offset == 0: return b'', None
        payload = data[offset:]
        if not payload: return b'', None
        res = self._decompress_backend(payload)
        if res is None: return b'', None
        try:
            if not seq: result = res
            else: result = self._reverse_sequence(res, seq)
        except: return b'', None
        return result, seq

    def _reverse_sequence(self, data: bytes, seq: Tuple[int, ...]) -> bytes:
        result = data
        for t in reversed(seq): result = self.rev_transforms[t](result)
        return result

    def full_self_test(self) -> bool:
        print("="*60); print("PAQJP 9.3 – Transform65535 CHECK (0-65535)"); print("="*60)
        test_byte = 0xAA; test_data = bytes([test_byte])
        print(f"Testing all 65536 transformation indices on byte 0x{test_byte:02X} ...")
        all_ok = True
        for index in range(65536):
            try:
                transformed = self.apply_transform_by_index(test_data, index)
                restored = self.reverse_transform_by_index(transformed, index)
                if restored != test_data:
                    print(f"  FAIL: index {index}, seq {self.get_transform_sequence(index)}")
                    all_ok = False; break
            except Exception as e:
                print(f"  EXCEPTION at index {index}: {e}"); all_ok = False; break
            if index % 10000 == 0 and index > 0: print(f"  ... {index} indices tested OK")
        if all_ok: print("  All 65536 transformations are lossless on test byte.")
        else: print("\n[FAIL] Check failed."); return False

        print("\nRandom 1000‑byte pipeline test (LZH backend)...")
        rng = random.Random(12345); test_data = bytes(rng.randint(0, 255) for _ in range(1000))
        try:
            compressed = self.compress_with_lzh(test_data, ultra=True)
            decompressed = self._decompress_lzh_pipeline(compressed)
            if decompressed != test_data: print("  FAIL: LZH pipeline mismatch"); return False
            print("  PASS")
        except RuntimeError as e: print(f"  Could not compress (rare): {e}"); return False

        print("\n[All checks passed – 100% lossless]"); return True

    def _atomic_write(self, path: str, data: bytes):
        dirname = os.path.dirname(path) or '.'; basename = os.path.basename(path)
        fd, tmpname = tempfile.mkstemp(prefix=basename + '.tmp', dir=dirname)
        try: os.write(fd, data); os.fsync(fd)
        finally: os.close(fd)
        os.replace(tmpname, path)

    def _auto_output_name(self, infile: str, suffix: str = ".pjp") -> str:
        base = os.path.basename(infile); name, _ = os.path.splitext(base)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{name}.{ts}{suffix}"

    def compress_file(self, infile: str, outfile: str = "", ultra: bool = True, use_lzh: bool = False):
        try:
            with open(infile, 'rb') as f: data = f.read()
        except Exception as e: print(f"Error reading file: {e}"); return
        try:
            if use_lzh:
                compressed = self.compress_with_lzh(data, ultra=ultra)
                default_suffix = ".pjp.lzh"
            else:
                compressed = self.compress_with_best(data, ultra=ultra)
                default_suffix = ".pjp"
        except RuntimeError as e: print(f"Compression failed: {e}"); return
        if not outfile: outfile = self._auto_output_name(infile, default_suffix)
        try: self._atomic_write(outfile, compressed)
        except Exception as e: print(f"Error writing output file: {e}"); return
        print(f"Compressed {len(data)} → {len(compressed)} bytes → {outfile}")

    def decompress_file(self, infile: str, outfile: str = ""):
        try:
            with open(infile, 'rb') as f: data = f.read()
        except Exception as e: print(f"Error reading file: {e}"); return
        offset, seq = self._decode_header(data)
        if offset == 0: print("Decompression failed: invalid header."); return
        if offset < len(data) and data[offset] == 0xFF:
            original = self._decompress_lzh_pipeline(data)
        else:
            original, _ = self._decompress_auto(data)
        if original is None or original == b'' and seq is None:
            print("Decompression failed."); return
        if not outfile:
            base = os.path.basename(infile); name, _ = os.path.splitext(base)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            outfile = f"{name}.{ts}.orig"
        try: self._atomic_write(outfile, original)
        except Exception as e: print(f"Error writing output file: {e}"); return
        seq_str = "raw" if not seq else f"sequence {seq}"
        print(f"Decompressed ({seq_str}) → {outfile} ({len(original)} bytes)")

    def analyze_constant_diapason(self, filepath: str):
        with open(filepath, 'rb') as f: data = f.read()
        bits = []
        for byte in data:
            for i in range(7, -1, -1): bits.append((byte >> i) & 1)
        orig_len = len(bits); ones = sum(bits); zeros = orig_len - ones
        print(f"File: {filepath} ({len(data)} bytes, {orig_len} bits)"); print(f"Ones: {ones}, Zeros: {zeros}\n")
        current_bits = bits[:]; prev_len = orig_len; pass_num = 0; best_pass = 0; best_len = orig_len
        print("Round‑by‑round sizes:")
        while pass_num < 255:
            pad_len = (4 - len(current_bits) % 4) % 4
            padded = current_bits + [0] * pad_len; nibble_count = len(padded) // 4; encoded_bits = []
            for i in range(nibble_count):
                nibble = (padded[i*4]<<3)|(padded[i*4+1]<<2)|(padded[i*4+2]<<1)|padded[i*4+3]
                length, codeword = _CONST_DIAPASON_ITER_CODE[nibble]
                for b in range(length-1, -1, -1): encoded_bits.append((codeword >> b) & 1)
            new_len = len(encoded_bits)
            if new_len < prev_len:
                current_bits = encoded_bits; prev_len = new_len; pass_num += 1
                if new_len < best_len: best_len = new_len; best_pass = pass_num
                print(f"  Pass {pass_num}: {new_len} bits  (delta {new_len - orig_len:+d})")
            else:
                print(f"  Pass {pass_num+1}: {new_len} bits (expansion) – stopping"); break
        if pass_num == 0: print("  (no pass reduced size)")
        print(f"\nBest: {best_len} bits after {best_pass} passes")
        if best_pass == 0: print("Best is to keep original (no compression).")
        print("\nComparison with standard compressors (on original file):")
        orig_bytes = data
        if HAS_ZSTD:
            try: zstd_bytes = zstd_cctx.compress(orig_bytes); print(f"  Zstandard –22: {len(zstd_bytes)} bytes")
            except: print("  Zstandard –22: error")
        else: print("  Zstandard not available.")
        if paq is not None:
            try: paq_bytes = paq.compress(orig_bytes); print(f"  PAQ: {len(paq_bytes)} bytes")
            except: print("  PAQ: error")
        else: print("  PAQ not available.")
        print(f"  Raw (no compress): {len(orig_bytes)} bytes")

    def transform_23_blocks_compress(self, data: bytes, block_bits: int) -> bytes:
        if not data: return self.transform_23(data)
        total_bits = len(data) * 8
        if block_bits == 0 or block_bits >= total_bits: return self.transform_23(data)
        bits = []
        for byte in data:
            for i in range(7, -1, -1): bits.append((byte >> i) & 1)
        out = bytearray()
        for start in range(0, total_bits, block_bits):
            chunk = bits[start:start+block_bits]
            compressed = self._compress_bits(chunk); orig_bit_len = len(chunk)
            out.append((orig_bit_len >> 8) & 0xFF); out.append(orig_bit_len & 0xFF)
            L = len(compressed); out.append((L >> 8) & 0xFF); out.append(L & 0xFF); out.extend(compressed)
        return bytes(out)

    def transform_23_blocks_decompress(self, data: bytes) -> bytes:
        if not data: return b''
        pos = 0; all_bits = []
        try:
            while pos + 2 <= len(data):
                orig_bit_len = (data[pos] << 8) | data[pos+1]; pos += 2
                if pos + 2 > len(data): break
                L = (data[pos] << 8) | data[pos+1]; pos += 2
                if pos + L > len(data): break
                block_data = data[pos:pos+L]; pos += L
                bits = self._decompress_bits(block_data)
                if len(bits) != orig_bit_len: raise ValueError("Block bit length mismatch")
                all_bits.extend(bits)
            if all_bits:
                out_bytes = bytearray()
                for i in range(0, len(all_bits), 8):
                    val = 0
                    for j in range(i, min(i+8, len(all_bits))): val = (val << 1) | all_bits[j]
                    if i+8 > len(all_bits): val <<= (8 - (len(all_bits) - i))
                    out_bytes.append(val)
                return bytes(out_bytes)
        except: pass
        return self.reverse_transform_23(data)

    def find_best_block_size_transform23(self, filepath: str):
        with open(filepath, 'rb') as f: data = f.read()
        if not data: print("Empty file – no block size test meaningful."); return
        total_bits = len(data) * 8
        print(f"File: {filepath}  ({len(data)} bytes, {total_bits} bits)")
        print("Scanning block sizes 0 … 8191 bits …")
        best_size = None; best_block_bits = -1
        for block_bits in range(0, 8192):
            if block_bits == 0: compressed = self.transform_23(data)
            else: compressed = self.transform_23_blocks_compress(data, block_bits)
            L = len(compressed)
            if best_size is None or L < best_size:
                best_size = L; best_block_bits = block_bits
            if block_bits % 1024 == 0:
                print(f"  {block_bits} bits → {L} bytes (best so far: {best_block_bits} bits → {best_size} bytes)")
        print("\nBest block size: {} bits → {} bytes".format(best_block_bits, best_size))
        if best_block_bits == 0: compressed = self.transform_23(data); recovered = self.reverse_transform_23(compressed)
        else: compressed = self.transform_23_blocks_compress(data, best_block_bits); recovered = self.transform_23_blocks_decompress(compressed)
        if recovered == data: print("Lossless check: OK")
        else: print("Lossless check: FAILED")
        return best_block_bits, best_size


# ============================================================================
# ENGINE 2: Ultimate Hybrid Compressor – 2704 Paths + Dicts/Zaden/Algo36/Quantum
# ============================================================================
class UltimateHybridCompressor:
    def __init__(self, repeat_count=100):
        self.repeat_count = repeat_count
        self.PI_DIGITS = PI_DIGITS.copy()
        self.seed_tables = self._gen_seed_tables(126,40,42)
        self.fibonacci = self._gen_fib(100)
        self.PI_STR = "3.14159265358979323846264338327950288419716939937510"
        self.mask_46 = self._build_mask_46()
        self.mod_state_table = [[(v-400)&0xFF for v in row] for row in PAQ_STATE_TABLE]
        download_and_merge_dictionaries()
        self.static_dict, self.word_to_index = self._load_static_dict()
        self.line_dict, self.line_to_index = self._load_line_dict()
        self._build_transform_maps()
        self.sequences = self._build_pair_sequences()
        self.pair_lookup = {idx:(t1,t2) for idx,(t1,t2) in enumerate(self.sequences)}
        self.pair_to_index = {seq:idx for idx,seq in enumerate(self.sequences)}
        if USE_QUANTUM and HAS_QISKIT: self._precompute_quantum_byte_substitutions()

    def _gen_quantum_permutation(self, seed):
        from qiskit import QuantumCircuit
        qc = QuantumCircuit(8); rng = random.Random(seed)
        for i in range(8): qc.h(i); qc.rz(rng.random()*2*math.pi,i); qc.rx(rng.random()*2*math.pi,i)
        for _ in range(8):
            for i in range(7): qc.cx(i,i+1)
            qc.barrier()
            for i in range(8): qc.rz(rng.random()*2*math.pi,i); qc.rx(rng.random()*2*math.pi,i)
        try: hash_val = hash(qc.qasm())
        except: hash_val = seed
        rng2 = random.Random(seed+hash_val%1000000)
        perm = list(range(256)); rng2.shuffle(perm)
        return perm

    def _precompute_quantum_byte_substitutions(self):
        self.q_perms = [self._gen_quantum_permutation(1000+i) for i in range(9)]
        for idx, perm in enumerate(self.q_perms, start=48):
            if idx > 56: break
            inv_perm = [0]*256
            for i,p in enumerate(perm): inv_perm[p] = i
            self.fwd[idx] = lambda data, perm=perm: bytes(perm[b] for b in data)
            self.rev[idx] = lambda data, inv=inv_perm: bytes(inv[b] for b in data)

    def _load_static_dict(self):
        if not os.path.exists(COMBINED_DICT): return [],[]
        words=set()
        with open(COMBINED_DICT,'r',encoding='utf-8',errors='ignore') as f:
            for line in f: w=line.strip(); 
            if w: words.add(w)
        sorted_words=sorted(words); w2i={w:i for i,w in enumerate(sorted_words)}
        return sorted_words, w2i

    def _load_line_dict(self):
        if not os.path.exists(COMBINED_DICT): return [],[]
        lines=[]
        with open(COMBINED_DICT,'r',encoding='utf-8',errors='ignore') as f:
            for raw in f:
                phrase=raw.strip()
                if phrase and phrase not in lines: lines.append(phrase)
                if len(lines)>=MAX_LINE_ENTRIES: break
        if not lines: return [],[]
        lines.sort(key=len, reverse=True); l2i={p:i for i,p in enumerate(lines)}
        return lines, l2i

    def _gen_seed_tables(self,n,size,seed):
        random.seed(seed); return [[random.randint(5,255) for _ in range(size)] for _ in range(n)]
    def _gen_fib(self,n):
        a,b=0,1; res=[a,b]
        for _ in range(2,n): a,b=b,a+b; res.append(b)
        return res
    def get_seed(self,idx,val):
        if 0<=idx<len(self.seed_tables): return self.seed_tables[idx][val%40]
        return 0
    def _build_mask_46(self):
        base=[1,2,4,8,16,32,64,128,3,6]; return [(b-10)&0xFF for b in base]*10

    def _append_bits(self,bits,val,cnt):
        for i in range(cnt-1,-1,-1): bits.append((val>>i)&1)
    def _read_bits(self,bits,pos,cnt):
        val=0
        for i in range(cnt):
            if pos+i>=len(bits): return 0
            val=(val<<1)|bits[pos+i]
        return val

    def transform_01(self, data):
        if not data: return b'\x00'
        best_result=None; best_len=float('inf'); original=data
        current=bytearray(data); applied=[]
        for _ in range(10):
            best_shift=0; best_shifted=current; best_score=-1
            for shift in range(256):
                tmp=bytearray(current)
                for j in range(len(tmp)): tmp[j]=(tmp[j]+shift)%256
                score=0; i=0
                while i<len(tmp):
                    val=tmp[i]; run=1; i+=1
                    while i<len(tmp) and tmp[i]==val: run+=1; i+=1
                    score+=run*run
                if score>best_score: best_score=score; best_shifted=tmp; best_shift=shift
            applied.append(best_shift)
            rle=self._apply_rle(best_shifted, best_shift)
            dec=self._rle_decode(rle)
            if dec is not None:
                test=bytearray(dec)
                for s in applied:
                    for j in range(len(test)): test[j]=(test[j]-s)%256
                if bytes(test)==original and len(rle)<best_len:
                    best_len=len(rle); best_result=rle
            current=best_shifted
            if len(rle)>=len(data): break
        if best_result is None or best_len>=len(data): return bytes([0])+data
        header=bytearray([len(applied)]); header.extend(applied)
        return header+best_result

    def _apply_rle(self, shifted, shift):
        bits=[]; self._append_bits(bits,0b010,3); self._append_bits(bits,shift,8)
        i=0; n=len(shifted)
        while i<n:
            val=shifted[i]; run=1; i+=1
            while i<n and shifted[i]==val: run+=1; i+=1
            while run>=13:
                chunk=min(run,268); self._append_bits(bits,0b1111,4); self._append_bits(bits,chunk-13,8)
                self._append_bits(bits,val,8); run-=chunk
            if run==1: self._append_bits(bits,0b00,2); self._append_bits(bits,val,8)
            elif run<=5: self._append_bits(bits,0b01,2); self._append_bits(bits,run-2,2); self._append_bits(bits,val,8)
            elif run<=12: self._append_bits(bits,0b10,2); self._append_bits(bits,run-6,3); self._append_bits(bits,val,8)
        pad=(8-len(bits)%8)%8; self._append_bits(bits,0,pad)
        out=bytearray()
        for j in range(0,len(bits),8):
            byte=0
            for k in range(8):
                if j+k<len(bits): byte=(byte<<1)|bits[j+k]
            out.append(byte)
        return bytes(out)

    def reverse_transform_01(self, cdata):
        if not cdata or cdata==b'\x00': return b''
        if cdata[0]==0: return cdata[1:]
        num=cdata[0]; shifts=list(cdata[1:1+num]); rledata=cdata[1+num:]
        dec=self._rle_decode(rledata)
        if dec is None: return b''
        cur=bytearray(dec)
        for s in reversed(shifts):
            for i in range(len(cur)): cur[i]=(cur[i]-s)%256
        return bytes(cur)

    def _rle_decode(self, data):
        if not data: return None
        bits=[]
        for b in data: bits.extend([(b>>i)&1 for i in range(7,-1,-1)])
        pos=0; nbits=len(bits)
        if nbits<11 or self._read_bits(bits,pos,3)!=0b010: return None
        pos+=3; pos+=8; out=bytearray()
        while pos<nbits:
            if pos+2>nbits: break
            prefix=self._read_bits(bits,pos,2); pos+=2
            if prefix==0b00:
                if pos+8>nbits: break; run=1
            elif prefix==0b01:
                if pos+2+8>nbits: break; run=2+self._read_bits(bits,pos,2); pos+=2
            elif prefix==0b10:
                if pos+3+8>nbits: break; run=6+self._read_bits(bits,pos,3); pos+=3
            else:
                if pos+2+8+8>nbits or self._read_bits(bits,pos,2)!=0b11: return None
                pos+=2; run=13+self._read_bits(bits,pos,8); pos+=8
            if pos+8>nbits: break; val=self._read_bits(bits,pos,8); pos+=8
            out.extend([val]*run)
        for i in range(pos,nbits):
            if bits[i]!=0: return None
        return out

    def transform_02(self,d):
        t=bytearray(d); r=self.repeat_count
        for prime in PRIMES:
            xor_val=prime if prime==2 else max(1,math.ceil(prime*4096/28672))
            for _ in range(r):
                for i in range(0,len(t),3):
                    if i<len(t): t[i]^=xor_val
        return bytes(t)
    reverse_transform_02=transform_02

    def transform_03(self,d):
        if len(d)<1: return b''
        pi=(len(d)+sum(d)%256)%256; pat=self._get_pattern(4,pi); t=bytearray(d)
        for i in range(1,len(t),4):
            if i<len(t): t[i]^=pat[i%len(pat)]
        return bytes([pi])+bytes(t)
    def reverse_transform_03(self,d):
        if len(d)<2: return b''
        pi=d[0]; t=bytearray(d[1:]); pat=self._get_pattern(4,pi)
        for i in range(1,len(t),4):
            if i<len(t): t[i]^=pat[i%len(pat)]
        return bytes(t)

    def transform_04(self,d):
        if len(d)<1: return b''
        t=bytearray(d); rot=(len(d)*13+sum(d))%8
        if rot==0: rot=1
        for i in range(2,len(t),5):
            if i<len(t): t[i]=((t[i]<<rot)|(t[i]>>(8-rot)))&0xFF
        return bytes([rot])+bytes(t)
    def reverse_transform_04(self,d):
        if len(d)<2: return b''
        rot=d[0]; t=bytearray(d[1:])
        for i in range(2,len(t),5):
            if i<len(t): t[i]=((t[i]>>rot)|(t[i]<<(8-rot)))&0xFF
        return bytes(t)

    def transform_05(self,d):
        t=bytearray(d); r=self.repeat_count
        for _ in range(r):
            for i in range(len(t)): t[i]=(t[i]-(i%256))%256
        return bytes(t)
    def reverse_transform_05(self,d):
        t=bytearray(d); r=self.repeat_count
        for _ in range(r):
            for i in range(len(t)): t[i]=(t[i]+(i%256))%256
        return bytes(t)

    def transform_06(self,d,s=3):
        t=bytearray(d)
        for i in range(len(t)): t[i]=((t[i]<<s)|(t[i]>>(8-s)))&0xFF
        return bytes(t)
    def reverse_transform_06(self,d,s=3):
        t=bytearray(d)
        for i in range(len(t)): t[i]=((t[i]>>s)|(t[i]<<(8-s)))&0xFF
        return bytes(t)

    def transform_07(self,d,seed=42):
        random.seed(seed); sub=list(range(256)); random.shuffle(sub)
        t=bytearray(d)
        for i in range(len(t)): t[i]=sub[t[i]]
        return bytes(t)
    def reverse_transform_07(self,d,seed=42):
        random.seed(seed); sub=list(range(256)); random.shuffle(sub); inv=[0]*256
        for i in range(256): inv[sub[i]]=i
        t=bytearray(d)
        for i in range(len(t)): t[i]=inv[t[i]]
        return bytes(t)

    def transform_08(self,d):
        t=bytearray(d); sh=len(d)%len(self.PI_DIGITS)
        pi_rot=self.PI_DIGITS[sh:]+self.PI_DIGITS[:sh]; sz=len(d)%256
        for i in range(len(t)): t[i]^=sz
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i]^=pi_rot[i%len(pi_rot)]
        return bytes(t)
    reverse_transform_08=transform_08

    def transform_09(self,d):
        t=bytearray(d); sh=len(d)%len(self.PI_DIGITS)
        pi_rot=self.PI_DIGITS[sh:]+self.PI_DIGITS[:sh]; p=find_nearest_prime_around(len(d)%256)
        for i in range(len(t)): t[i]^=p
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i]^=pi_rot[i%len(pi_rot)]
        return bytes(t)
    reverse_transform_09=transform_09

    def transform_10(self,d):
        t=bytearray(d); sh=len(d)%len(self.PI_DIGITS)
        pi_rot=self.PI_DIGITS[sh:]+self.PI_DIGITS[:sh]; p=find_nearest_prime_around(len(d)%256)
        seed=self.get_seed(len(d)%len(self.seed_tables),len(d))
        for i in range(len(t)): t[i]^=p^seed
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i]^=pi_rot[i%len(pi_rot)]^(i%256)
        return bytes(t)
    reverse_transform_10=transform_10

    def transform_11(self,d):
        if not d: return b'\x00'
        cnt=sum(1 for i in range(len(d)-1) if d[i:i+2]==b'X1')
        n=(((cnt*2)+1)//3)*3%256; t=bytearray(d)
        for i in range(len(t)): t[i]^=n
        return bytes([n])+bytes(t)
    def reverse_transform_11(self,d):
        if len(d)<1: return b''
        n=d[0]; t=bytearray(d[1:])
        for i in range(len(t)): t[i]^=n
        return bytes(t)

    def transform_12(self,d):
        t=bytearray(d); L=len(t)
        for i in range(L):
            fib_idx=(i+L)%len(self.fibonacci); fib_val=self.fibonacci[fib_idx]%256
            pos_val=(i*13+L*17)%256; t[i]^=(fib_val^pos_val)%256
        return bytes(t)
    reverse_transform_12=transform_12

    def transform_13(self,d):
        t=bytearray(d)
        for i in range(len(t)): t[i]^=self.fibonacci[i%len(self.fibonacci)]%256
        return bytes(t)
    reverse_transform_13=transform_13

    def transform_14(self,d):
        if not d: return b''
        reps=self._calculate_repeats(d); cur=len(d)%256; vals=[]
        for _ in range(reps):
            cur=find_nearest_prime_around(cur); vals.append(cur)
        xor_val=vals[-1] if vals else 0; t=bytearray(d)
        for i in range(len(t)): t[i]^=xor_val
        return bytes([(reps-1)%256])+bytes(t)
    def reverse_transform_14(self,d):
        if len(d)<2: return b''
        reps=(d[0]+1)%256
        if reps==0: reps=256
        t=bytearray(d[1:]); cur=len(t)%256; vals=[]
        for _ in range(reps):
            cur=find_nearest_prime_around(cur); vals.append(cur)
        xor_val=vals[-1] if vals else 0
        for i in range(len(t)): t[i]^=xor_val
        return bytes(t)

    def transform_15(self,d):
        if len(d)<1: return b''
        pi=len(d)%256; pat=self._get_pattern(3,pi); t=bytearray(d)
        for i in range(0,len(t),3):
            if i<len(t): t[i]=(t[i]+pat[i%len(pat)])%256
        return bytes([pi])+bytes(t)
    def reverse_transform_15(self,d):
        if len(d)<2: return b''
        pi=d[0]; t=bytearray(d[1:]); pat=self._get_pattern(3,pi)
        for i in range(0,len(t),3):
            if i<len(t): t[i]=(t[i]-pat[i%len(pat)])%256
        return bytes(t)

    def transform_16(self,d):
        if not d: return b''
        xor_byte=(len(d)*7+13)%256; t=bytearray(d)
        for i in range(len(t)): t[i]^=xor_byte
        return bytes(t)
    reverse_transform_16=transform_16

    def transform_17(self,d):
        if not d: return b''
        k,_=self.find_lossless_k(7); bits_used=23 if k<=0x7FFFFF else 25
        bit_str=format(k,'b').zfill(bits_used)
        mask_bytes=[]
        for i in range(0,len(bit_str),8):
            byte_bits=bit_str[i:i+8]
            if len(byte_bits)<8: byte_bits=byte_bits.ljust(8,'0')
            mask_bytes.append(int(byte_bits,2))
        mask=bytes(mask_bytes); t=bytearray(d)
        for i in range(len(t)): t[i]^=mask[i%len(mask)]
        return bytes(t)
    reverse_transform_17=transform_17

    def transform_18(self,d):
        if not d: return b''
        digits=self.get_basel_digits(max(10,len(d)//2+5))
        mask=bytes(int(digits[i:i+2])%256 for i in range(0,len(digits),2))
        t=bytearray(d)
        for i in range(len(t)): t[i]^=mask[i%len(mask)]
        return bytes(t)
    reverse_transform_18=transform_18

    def transform_19(self,d):
        if not d: return b''
        digits=self.get_one_over_e_digits(max(10,len(d)//2+5))
        mask=bytes(int(digits[i:i+2])%256 for i in range(0,len(digits),2))
        t=bytearray(d)
        for i in range(len(t)): t[i]^=mask[i%len(mask)]
        return bytes(t)
    reverse_transform_19=transform_19

    def transform_20(self,d):
        if not d: return b''
        digits=self.get_5e_digits(max(10,len(d)//2+5))
        mask=bytes(int(digits[i:i+2])%256 for i in range(0,len(digits),2))
        t=bytearray(d)
        for i in range(len(t)): t[i]^=mask[i%len(mask)]
        return bytes(t)
    reverse_transform_20=transform_20

    def transform_21(self,d):
        if not d: return b''
        t=bytearray(d)
        for i in range(len(t)): t[i]=(t[i]+255)%256
        return bytes(t)
    def reverse_transform_21(self,d):
        if not d: return b''
        t=bytearray(d)
        for i in range(len(t)): t[i]=(t[i]-255)%256
        return bytes(t)

    def transform_22(self,d): return d
    reverse_transform_22=transform_22

    def _compress_bits(self,bits):
        if not bits: return b'\x00\x00\x00'
        cur=bits[:]; prev_len=len(cur); pass_count=0
        while pass_count<255:
            pad=(4-len(cur)%4)%4; padded=cur+[0]*pad; nibcnt=len(padded)//4
            enc=[]
            for i in range(nibcnt):
                nib=(padded[i*4]<<3)|(padded[i*4+1]<<2)|(padded[i*4+2]<<1)|padded[i*4+3]
                l,cw=_CONST_DIAPASON_ITER_CODE[nib]
                for b in range(l-1,-1,-1): enc.append((cw>>b)&1)
            new_len=len(enc)
            if new_len<prev_len: cur=enc; prev_len=new_len; pass_count+=1
            else: break
        header=bytes([(len(bits)>>8)&0xFF, len(bits)&0xFF, pass_count])
        pad=(8-len(cur)%8)%8; cur+=[0]*pad
        out=bytearray()
        for i in range(0,len(cur),8):
            val=0
            for j in range(8): val=(val<<1)|cur[i+j]
            out.append(val)
        return header+bytes(out)

    def _decompress_bits(self,data):
        if len(data)<3: return []
        orig_len=(data[0]<<8)|data[1]; passes=data[2]; payload=data[3:]
        bits=[]
        for b in payload: bits.extend([(b>>i)&1 for i in range(7,-1,-1)])
        cur=bits
        for _ in range(passes):
            pos=0; nbits=len(cur); dec_nibbles=[]
            while pos<nbits:
                matched=False
                for l in range(2,10):
                    if pos+l>nbits: continue
                    cw=0
                    for k in range(l): cw=(cw<<1)|cur[pos+k]
                    key=(l,cw)
                    if key in _CONST_DIAPASON_ITER_DECODE:
                        dec_nibbles.append(_CONST_DIAPASON_ITER_DECODE[key]); pos+=l; matched=True; break
                if not matched: break
            new_bits=[]
            for nib in dec_nibbles:
                for j in range(3,-1,-1): new_bits.append((nib>>j)&1)
            cur=new_bits
        if len(cur)<orig_len: return []
        return cur[:orig_len]

    def transform_23(self,d):
        if not d: return b'\x00\x00\x00'
        bits=[]
        for b in d: bits.extend([(b>>i)&1 for i in range(7,-1,-1)])
        return self._compress_bits(bits)
    def reverse_transform_23(self,d):
        bits=self._decompress_bits(d)
        if not bits: return b''
        out=bytearray()
        for i in range(0,len(bits),8):
            val=0
            for j in range(i,min(i+8,len(bits))): val=(val<<1)|bits[j]
            if i+8>len(bits): val<<=(8-(len(bits)-i))
            out.append(val)
        return bytes(out)

    def transform_24(self,d):
        if not d: return b''
        MAX_LEN=43; bits=[]; i=0; n=len(d)
        while i<n:
            chunk_len=min(MAX_LEN,n-i); chunk=d[i:i+chunk_len]; first=chunk[0]
            all_same=all(b==first for b in chunk)
            if all_same:
                self._append_bits(bits,1,1); self._append_bits(bits,first,8); self._append_bits(bits,chunk_len-1,6)
            else:
                self._append_bits(bits,0,1); self._append_bits(bits,chunk_len,6)
                for b in chunk: self._append_bits(bits,b,8)
            i+=chunk_len
        pad=(8-len(bits)%8)%8; self._append_bits(bits,0,pad)
        out=bytearray()
        for j in range(0,len(bits),8):
            byte=0
            for k in range(8): byte=(byte<<1)|bits[j+k]
            out.append(byte)
        return bytes(out)

    def reverse_transform_24(self,d):
        if not d: return b''
        bits=[]
        for b in d: bits.extend([(b>>i)&1 for i in range(7,-1,-1)])
        pos=0; nbits=len(bits); out=bytearray()
        while pos<nbits:
            if pos+1>nbits: break
            flag=self._read_bits(bits,pos,1); pos+=1
            if flag==1:
                if pos+8+6>nbits: break
                byte_val=self._read_bits(bits,pos,8); pos+=8; cnt_minus1=self._read_bits(bits,pos,6); pos+=6
                out.extend([byte_val]*(cnt_minus1+1))
            else:
                if pos+6>nbits: break
                chunk_len=self._read_bits(bits,pos,6); pos+=6
                if chunk_len==0: break
                if pos+chunk_len*8>nbits: break
                for _ in range(chunk_len):
                    b=self._read_bits(bits,pos,8); pos+=8; out.append(b)
        return bytes(out)

    def transform_25(self,d):
        if not d: return b'\x01'
        n=3; res=bytearray(d)
        for i in range(len(res)): res[i]=(pow(res[i]+1,n,257)-1)&0xFF
        return bytes([n])+bytes(res)
    def reverse_transform_25(self,d):
        if not d or len(d)<2: return b''
        n=d[0]; inv=pow(n,-1,256); res=bytearray(d[1:])
        for i in range(len(res)): res[i]=(pow(res[i]+1,inv,257)-1)&0xFF
        return bytes(res)

    def transform_26(self,d):
        if not d: return b'\x01\x00'
        n=(len(d)*7+13)&0xFFFF
        if n%2==0: n^=1
        e=pow(n,16777216,256)|1; res=bytearray(d)
        for i in range(len(res)): res[i]=(pow(res[i]+1,e,257)-1)&0xFF
        return bytes([n&0xFF,(n>>8)&0xFF])+bytes(res)
    def reverse_transform_26(self,d):
        if not d or len(d)<2: return b''
        n=d[0]|(d[1]<<8)
        if n%2==0: n^=1
        e=pow(n,16777216,256)|1; inv_e=pow(e,-1,256); res=bytearray(d[2:])
        for i in range(len(res)): res[i]=(pow(res[i]+1,inv_e,257)-1)&0xFF
        return bytes(res)

    def transform_27(self,d):
        if not d:
            out=bytearray(b'\x00\x00\x00\x00'); out.extend(b'\x01\x00'); out.extend(b'\x00'*1024)
            return bytes(out)
        BLOCK=1024; blocks=(len(d)+BLOCK-1)//BLOCK; out=bytearray(); out.extend(len(d).to_bytes(4,'big'))
        for bi in range(blocks):
            start=bi*BLOCK; end=min(start+BLOCK,len(d)); chunk=d[start:end]
            pad=BLOCK-len(chunk); chunk=chunk+b'\x00'*pad if pad else chunk
            n=((len(d)*7+bi*13+1)&0xFFFF)|1; e=pow(n,16777216,256)|1; e200=pow(e,200,256)
            trans=bytearray(chunk)
            for i in range(BLOCK): trans[i]=(pow(trans[i]+1,e200,257)-1)&0xFF
            out.append(n&0xFF); out.append((n>>8)&0xFF); out.extend(trans)
        return bytes(out)
    def reverse_transform_27(self,d):
        if not d or len(d)<4: return b''
        orig_len=int.from_bytes(d[:4],'big'); payload=d[4:]; BLOCK=1024; block_total=2+BLOCK
        if len(payload)%block_total!=0: return d
        num=len(payload)//block_total; decoded=bytearray()
        for bi in range(num):
            off=bi*block_total; n=payload[off]|(payload[off+1]<<8); chunk=payload[off+2:off+2+BLOCK]
            n|=1; e=pow(n,16777216,256)|1; e200=pow(e,200,256); inv_e200=pow(e200,-1,256)
            for i in range(BLOCK): decoded.append((pow(chunk[i]+1,inv_e200,257)-1)&0xFF)
        return bytes(decoded[:orig_len])

    def transform_28(self,d):
        if not d:
            out=bytearray(b'\x00\x00\x00\x00'); out.extend(b'\x01\x00'); out.extend(self._compress_backend(b'\x00'*1024,safe=True))
            return bytes(out)
        BLOCK=1024; blocks=(len(d)+BLOCK-1)//BLOCK; out=bytearray(); out.extend(len(d).to_bytes(4,'big'))
        for bi in range(blocks):
            start=bi*BLOCK; end=min(start+BLOCK,len(d)); chunk=d[start:end]
            pad=BLOCK-len(chunk); chunk=chunk+b'\x00'*pad if pad else chunk
            n=((len(d)*7+bi*13+1)&0xFFFF)|1; e=pow(n,16777216,256)|1; e200=pow(e,200,256)
            trans=bytearray(chunk)
            for i in range(BLOCK): trans[i]=(pow(trans[i]+1,e200,257)-1)&0xFF
            comp=self._compress_backend(bytes(trans),safe=True)
            out.append(n&0xFF); out.append((n>>8)&0xFF)
            out.append((len(comp)>>8)&0xFF); out.append(len(comp)&0xFF); out.extend(comp)
        return bytes(out)
    def reverse_transform_28(self,d):
        if not d or len(d)<4: return b''
        orig_len=int.from_bytes(d[:4],'big'); payload=d[4:]; pos=0; decoded=bytearray()
        while pos<len(payload):
            if pos+2>len(payload): break
            n=payload[pos]|(payload[pos+1]<<8); pos+=2
            if pos+2>len(payload): break
            comp_len=(payload[pos]<<8)|payload[pos+1]; pos+=2
            if pos+comp_len>len(payload): break
            comp=payload[pos:pos+comp_len]; pos+=comp_len
            block=self._decompress_backend(comp,safe=True)
            if block is None: return d
            n|=1; e=pow(n,16777216,256)|1; e200=pow(e,200,256); inv_e200=pow(e200,-1,256)
            trans=bytearray(block)
            for i in range(len(trans)): trans[i]=(pow(trans[i]+1,inv_e200,257)-1)&0xFF
            decoded.extend(trans)
        return bytes(decoded[:orig_len])

    def transform_29(self,d):
        if not d:
            out=bytearray(b'\x00\x00\x00\x00'); out.extend(b'\x01\x00'); out.extend(self._compress_backend(b'\x00'*32,safe=True))
            return bytes(out)
        BLOCK=32; blocks=(len(d)+BLOCK-1)//BLOCK; out=bytearray(); out.extend(len(d).to_bytes(4,'big'))
        for bi in range(blocks):
            start=bi*BLOCK; end=min(start+BLOCK,len(d)); chunk=d[start:end]
            pad=BLOCK-len(chunk); chunk=chunk+b'\x00'*pad if pad else chunk
            n=((len(d)*7+bi*13+1)&0xFFFF)|1; e=pow(n,2**256,256)|1; e200=pow(e,200,256)
            comp=self._compress_backend(chunk,safe=True)
            out.append(n&0xFF); out.append((n>>8)&0xFF)
            out.append((len(comp)>>8)&0xFF); out.append(len(comp)&0xFF); out.extend(comp)
        return bytes(out)
    def reverse_transform_29(self,d):
        if not d or len(d)<4: return b''
        orig_len=int.from_bytes(d[:4],'big'); payload=d[4:]; pos=0; decoded=bytearray()
        while pos<len(payload):
            if pos+2>len(payload): break
            n=payload[pos]|(payload[pos+1]<<8); pos+=2
            if pos+2>len(payload): break
            comp_len=(payload[pos]<<8)|payload[pos+1]; pos+=2
            if pos+comp_len>len(payload): break
            comp=payload[pos:pos+comp_len]; pos+=comp_len
            block=self._decompress_backend(comp,safe=True)
            if block is None: return d
            decoded.extend(block)
        return bytes(decoded[:orig_len])

    def transform_30(self,d):
        if not d:
            out=bytearray(b'\x00\x00\x00\x00'); out.extend(b'\x01\x01'); out.extend(self._compress_backend(b'\x00'*33,safe=True))
            return bytes(out)
        BLOCK=33; blocks=(len(d)+BLOCK-1)//BLOCK; out=bytearray(); out.extend(len(d).to_bytes(4,'big'))
        for bi in range(blocks):
            start=bi*BLOCK; end=min(start+BLOCK,len(d)); chunk=d[start:end]
            pad=BLOCK-len(chunk); chunk=chunk+b'\x00'*pad if pad else chunk
            n,enc_n=self._compute_n_for_block(chunk,bi,len(d))
            comp=self._compress_backend(chunk,safe=True)
            out.extend(enc_n); out.append((len(comp)>>8)&0xFF); out.append(len(comp)&0xFF); out.extend(comp)
        return bytes(out)
    def reverse_transform_30(self,d):
        if not d or len(d)<4: return b''
        orig_len=int.from_bytes(d[:4],'big'); payload=d[4:]; pos=0; decoded=bytearray()
        while pos<len(payload):
            Ln=payload[pos]; pos+=1
            if Ln>32 or pos+Ln>len(payload): break
            n_bytes=payload[pos:pos+Ln]; pos+=Ln
            if pos+2>len(payload): break
            comp_len=(payload[pos]<<8)|payload[pos+1]; pos+=2
            if pos+comp_len>len(payload): break
            comp=payload[pos:pos+comp_len]; pos+=comp_len
            block=self._decompress_backend(comp,safe=True)
            if block is None: return d
            decoded.extend(block)
        return bytes(decoded[:orig_len])

    def _compute_n_for_block(self,block,bi,total_len):
        if not block: return 1,b'\x01\x01'
        d=block[0]; x=(bi%33)+1
        try: t=(d*d - d**x)//256
        except OverflowError: t=0
        if 0<=t<=255: n=t|1; return n,bytes([1,n])
        h=hashlib.sha256(block+bytes([bi&0xFF,(total_len>>8)&0xFF,total_len&0xFF])).digest()
        nb=bytearray(h); nb[0]|=1; length=len(nb); encoded=bytes([length])+bytes(nb)
        n=int.from_bytes(nb,'big'); return n,encoded

    def _dynamic_transform(self,n):
        def tf(d):
            if not d: return b''
            seed=self.get_seed(n%len(self.seed_tables),len(d)); t=bytearray(d)
            for i in range(len(t)): t[i]^=seed
            return bytes(t)
        return tf,tf

    def transform_41(self,d):
        if not d: return b''
        mask=bytes([0x27,0x03]); t=bytearray(d); n=min(len(t),8)
        for i in range(n): t[i]^=mask[i%2]
        return bytes(t)
    reverse_transform_41=transform_41

    def transform_42(self,d):
        if not d: return b''
        t=bytearray(d); mask=bytes([0x27,0x03])
        for i in range(len(t)): t[i]^=mask[i%2]
        return bytes(t)
    reverse_transform_42=transform_42

    def transform_43(self,d):
        if not d: return b''
        t=bytearray(d); mask=bytes([0x10,0x00,0x00])
        for i in range(0,len(t),3):
            for j in range(min(3,len(t)-i)): t[i+j]^=mask[j]
        return bytes(t)
    reverse_transform_43=transform_43

    def transform_44(self,d):
        if not d: return b''
        return base64.b64encode(d)
    def reverse_transform_44(self,d):
        if not d: return b''
        try: return base64.b64decode(d)
        except: return d

    def transform_45(self,d):
        if not d: return b''
        freq=[0]*256
        for b in d: freq[b]+=1
        cl=self._huffman_code_lengths(freq); codes=self._huffman_canonical_codes(cl)
        header=bytearray(); header.extend(len(d).to_bytes(4,'big')); header.extend(cl)
        bits=[]
        for b in d:
            c,l=codes[b]
            for i in range(l-1,-1,-1): bits.append((c>>i)&1)
        pad=(8-len(bits)%8)%8; bits.extend([0]*pad)
        out=bytearray()
        for i in range(0,len(bits),8):
            val=0
            for j in range(8): val=(val<<1)|bits[i+j]
            out.append(val)
        return bytes(header)+bytes(out)
    def reverse_transform_45(self,d):
        if not d or len(d)<4+256: return d
        orig_len=int.from_bytes(d[:4],'big'); cl=list(d[4:4+256]); payload=d[4+256:]
        if orig_len==0: return b''
        code_to_sym={}; symbols=list(range(256)); symbols.sort(key=lambda s:(cl[s],s))
        code=0; prev_len=0; first=True
        for sym in symbols:
            l=cl[sym]
            if l==0: continue
            if first: prev_len=l; first=False
            elif l!=prev_len: code<<=(l-prev_len); prev_len=l
            code_to_sym[(l,code)]=sym; code+=1
        bits=[]
        for b in payload: bits.extend([(b>>i)&1 for i in range(7,-1,-1)])
        pos=0; nbits=len(bits); out=bytearray()
        while pos<nbits and len(out)<orig_len:
            found=False
            for l in range(1,256):
                if pos+l>nbits: break
                val=0
                for j in range(l): val=(val<<1)|bits[pos+j]
                if (l,val) in code_to_sym:
                    out.append(code_to_sym[(l,val)]); pos+=l; found=True; break
            if not found: break
        return bytes(out)

    def transform_46(self,d):
        if not d: return b''
        t=bytearray(d); mask=self.mask_46
        for i in range(len(t)): t[i]^=mask[i%len(mask)]
        return bytes(t)
    reverse_transform_46=transform_46

    def transform_47(self,d):
        if not d: return b''
        t=bytearray(d); tbl=self.mod_state_table
        if not tbl: return d
        for i in range(len(t)): t[i]^=tbl[i%len(tbl)][0]
        return bytes(t)
    reverse_transform_47=transform_47

    def transform_256(self,d): return d
    reverse_transform_256=transform_256

    def _build_transform_maps(self):
        self.fwd={}; self.rev={}
        self.fwd[1]=self.transform_01; self.rev[1]=self.reverse_transform_01
        self.fwd[2]=self.transform_02; self.rev[2]=self.reverse_transform_02
        self.fwd[3]=self.transform_03; self.rev[3]=self.reverse_transform_03
        self.fwd[4]=self.transform_04; self.rev[4]=self.reverse_transform_04
        self.fwd[5]=self.transform_05; self.rev[5]=self.reverse_transform_05
        self.fwd[6]=self.transform_06; self.rev[6]=self.reverse_transform_06
        self.fwd[7]=self.transform_07; self.rev[7]=self.reverse_transform_07
        self.fwd[8]=self.transform_08; self.rev[8]=self.reverse_transform_08
        self.fwd[9]=self.transform_09; self.rev[9]=self.reverse_transform_09
        self.fwd[10]=self.transform_10; self.rev[10]=self.reverse_transform_10
        self.fwd[11]=self.transform_11; self.rev[11]=self.reverse_transform_11
        self.fwd[12]=self.transform_12; self.rev[12]=self.reverse_transform_12
        self.fwd[13]=self.transform_13; self.rev[13]=self.reverse_transform_13
        self.fwd[14]=self.transform_14; self.rev[14]=self.reverse_transform_14
        self.fwd[15]=self.transform_15; self.rev[15]=self.reverse_transform_15
        self.fwd[16]=self.transform_16; self.rev[16]=self.reverse_transform_16
        self.fwd[17]=self.transform_17; self.rev[17]=self.reverse_transform_17
        self.fwd[18]=self.transform_18; self.rev[18]=self.reverse_transform_18
        self.fwd[19]=self.transform_19; self.rev[19]=self.reverse_transform_19
        self.fwd[20]=self.transform_20; self.rev[20]=self.reverse_transform_20
        self.fwd[21]=self.transform_21; self.rev[21]=self.reverse_transform_21
        self.fwd[22]=self.transform_22; self.rev[22]=self.reverse_transform_22
        self.fwd[23]=self.transform_23; self.rev[23]=self.reverse_transform_23
        self.fwd[24]=self.transform_24; self.rev[24]=self.reverse_transform_24
        self.fwd[25]=self.transform_25; self.rev[25]=self.reverse_transform_25
        self.fwd[26]=self.transform_26; self.rev[26]=self.reverse_transform_26
        self.fwd[27]=self.transform_27; self.rev[27]=self.reverse_transform_27
        self.fwd[28]=self.transform_28; self.rev[28]=self.reverse_transform_28
        self.fwd[29]=self.transform_29; self.rev[29]=self.reverse_transform_29
        self.fwd[30]=self.transform_30; self.rev[30]=self.reverse_transform_30
        for i in range(31,41):
            f,r=self._dynamic_transform(i); self.fwd[i]=f; self.rev[i]=r
        self.fwd[41]=self.transform_41; self.rev[41]=self.reverse_transform_41
        self.fwd[42]=self.transform_42; self.rev[42]=self.reverse_transform_42
        self.fwd[43]=self.transform_43; self.rev[43]=self.reverse_transform_43
        self.fwd[44]=self.transform_44; self.rev[44]=self.reverse_transform_44
        self.fwd[45]=self.transform_45; self.rev[45]=self.reverse_transform_45
        self.fwd[46]=self.transform_46; self.rev[46]=self.reverse_transform_46
        self.fwd[47]=self.transform_47; self.rev[47]=self.reverse_transform_47
        for i in range(48,256):
            f,r=self._dynamic_transform(i); self.fwd[i]=f; self.rev[i]=r
        self.fwd[256]=self.transform_256; self.rev[256]=self.reverse_transform_256
        for i in range(1,257):
            if i not in self.fwd: raise RuntimeError(f"Transform {i} missing!")

    def _build_pair_sequences(self):
        pairs=[]
        for t1 in range(1,257):
            for t2 in range(1,257):
                if t1==256 and t2==256: continue
                pairs.append((t1,t2))
        return pairs

    def get_transform_sequence(self, index):
        if index<0 or index>65535: raise ValueError("Index 0..65535")
        if index==0: return ()
        return self.sequences[index-1]

    def apply_transform_by_index(self, data, index):
        seq=self.get_transform_sequence(index)
        res=data
        for t in seq: res=self.fwd[t](res)
        return res

    def reverse_transform_by_index(self, data, index):
        seq=self.get_transform_sequence(index)
        res=data
        for t in reversed(seq): res=self.rev[t](res)
        return res

    def get_pi_digits(self,n):
        if n<1: return ""
        return self.PI_STR[2:2+n]
    def find_lossless_k(self,n):
        if n<1: return 0,True
        true_digits=self.get_pi_digits(n); true_scaled=int(self.PI_STR.replace('.','')[:n+1])
        DENOM=16777216; decimal.getcontext().prec=50; pi_dec=decimal.Decimal(self.PI_STR)
        k_float=(pi_dec-3)*DENOM; k_candidate=int(round(k_float)); k_candidate=max(0,min(k_candidate,DENOM-1))
        approx_scaled=(3*10**n*DENOM+k_candidate*10**n)//DENOM
        return k_candidate, approx_scaled==true_scaled
    def get_basel_digits(self,n):
        decimal.getcontext().prec=n+5; pi=decimal.Decimal(self.PI_STR)
        basel=(pi*pi)/decimal.Decimal(6); s=str(basel).replace('.',''); return s[:n]
    def get_one_over_e_digits(self,n):
        decimal.getcontext().prec=n+5; e=decimal.Decimal(1).exp()
        inv_e=decimal.Decimal(1)/e; s=str(inv_e).replace('.',''); return s[:n]
    def get_5e_digits(self,n):
        decimal.getcontext().prec=n+5; e=decimal.Decimal(1).exp()
        five_e=decimal.Decimal(5)*e; s=str(five_e).replace('.',''); return s[:n]
    def _get_pattern(self,size,index):
        random.seed(12345+size*100+index); return [random.randint(0,255) for _ in range(size)]
    def _calculate_repeats(self,data):
        if not data: return 1
        L=len(data); s=sum(data)%256; reps=((L*13+s*17)%256)+1; return max(1,min(256,reps))

    @staticmethod
    def _huffman_code_lengths(freq):
        heap=[(f,i,i) for i,f in enumerate(freq) if f>0]
        if not heap: return [0]*len(freq)
        if len(heap)==1: lengths=[0]*len(freq); lengths[heap[0][2]]=1; return lengths
        heapq.heapify(heap); next_id=len(heap)
        while len(heap)>1:
            f1,_,n1=heapq.heappop(heap); f2,_,n2=heapq.heappop(heap)
            heapq.heappush(heap,(f1+f2,next_id,(n1,n2))); next_id+=1
        lengths=[0]*len(freq)
        def traverse(node,depth):
            if isinstance(node,int): lengths[node]=depth
            else: traverse(node[0],depth+1); traverse(node[1],depth+1)
        traverse(heap[0][2],0)
        return lengths

    @staticmethod
    def _huffman_canonical_codes(code_lengths):
        symbols=list(range(len(code_lengths))); symbols.sort(key=lambda s:(code_lengths[s],s))
        codes={}; code=0; prev_len=0; first=True
        for sym in symbols:
            cl=code_lengths[sym]
            if cl==0: continue
            if first: prev_len=cl; first=False
            elif cl!=prev_len: code<<=(cl-prev_len); prev_len=cl
            codes[sym]=(code,cl); code+=1
        return codes

    WINDOW_SIZE=2048; MIN_MATCH=3; MAX_MATCH=2048; MAX_DIST=2048
    def _lz77_tokenize(self,data):
        tokens=[]; i=0; n=len(data)
        while i<n:
            best_len=0; best_dist=0; start=max(0,i-self.WINDOW_SIZE)
            for j in range(start,i):
                if data[j]!=data[i]: continue
                k=0
                while i+k<n and j+k<i and data[j+k]==data[i+k]:
                    k+=1
                    if k>=self.MAX_MATCH: break
                if k>=self.MIN_MATCH and k>best_len: best_len=k; best_dist=i-j
                if best_len==self.MAX_MATCH: break
            if best_len>=self.MIN_MATCH:
                tokens.append(('M',best_dist,best_len)); i+=best_len
            else:
                tokens.append(('L',data[i],None)); i+=1
        return tokens

    def _lz77_untokenize(self,tokens):
        out=bytearray()
        for t in tokens:
            if t[0]=='L': out.append(t[1])
            else:
                dist,length=t[1],t[2]; start=len(out)-dist
                for k in range(length): out.append(out[start+k])
        return bytes(out)

    def _encode_lzh(self,data):
        tokens=self._lz77_tokenize(data)
        lit_freq=[0]*256; dist_freq=[0]*(self.MAX_DIST+1); len_freq=[0]*(self.MAX_MATCH+1)
        for t in tokens:
            if t[0]=='L': lit_freq[t[1]]+=1
            else: dist_freq[t[1]]+=1; len_freq[t[2]]+=1
        lit_cl=self._huffman_code_lengths(lit_freq); dist_cl=self._huffman_code_lengths(dist_freq); len_cl=self._huffman_code_lengths(len_freq)
        lit_codes=self._huffman_canonical_codes(lit_cl); dist_codes=self._huffman_canonical_codes(dist_cl); len_codes=self._huffman_canonical_codes(len_cl)
        bits=[]; token_count=len(tokens)
        for b in struct.pack('>I',token_count):
            for i in range(8): bits.append((b>>(7-i))&1)
        for t in tokens:
            if t[0]=='L':
                bits.append(0); code,cl=lit_codes[t[1]]
                for i in range(cl-1,-1,-1): bits.append((code>>i)&1)
            else:
                bits.append(1); code_d,cl_d=dist_codes[t[1]]
                for i in range(cl_d-1,-1,-1): bits.append((code_d>>i)&1)
                code_l,cl_l=len_codes[t[2]]
                for i in range(cl_l-1,-1,-1): bits.append((code_l>>i)&1)
        pad=(8-len(bits)%8)%8; bits.extend([0]*pad)
        def pack_lengths_16(lst):
            return b''.join(struct.pack('>H',l) for l in lst)
        lit_len_bytes=pack_lengths_16(lit_cl); dist_len_bytes=pack_lengths_16(dist_cl); len_len_bytes=pack_lengths_16(len_cl)
        header=bytearray(); header.extend(lit_len_bytes); header.extend(dist_len_bytes); header.extend(len_len_bytes)
        out=bytearray(header)
        for i in range(0,len(bits),8):
            byte=0
            for j in range(8): byte=(byte<<1)|bits[i+j]
            out.append(byte)
        return bytes(out)

    def _decode_lzh(self,data):
        LIT_LEN_BYTES=256*2; DIST_LEN_BYTES=2049*2; LEN_LEN_BYTES=2049*2
        if len(data)<LIT_LEN_BYTES+DIST_LEN_BYTES+LEN_LEN_BYTES: return None
        pos=0
        lit_cl=[struct.unpack('>H',data[i:i+2])[0] for i in range(pos,pos+LIT_LEN_BYTES,2)]; pos+=LIT_LEN_BYTES
        dist_cl=[struct.unpack('>H',data[i:i+2])[0] for i in range(pos,pos+DIST_LEN_BYTES,2)]; pos+=DIST_LEN_BYTES
        len_cl=[struct.unpack('>H',data[i:i+2])[0] for i in range(pos,pos+LEN_LEN_BYTES,2)]; pos+=LEN_LEN_BYTES
        def build_decode_table(lengths):
            symbols=list(range(len(lengths))); symbols.sort(key=lambda s:(lengths[s],s))
            decode={}; code=0; prev_len=0; first=True
            for sym in symbols:
                cl=lengths[sym]
                if cl==0: continue
                if first: prev_len=cl; first=False
                elif cl!=prev_len: code<<=(cl-prev_len); prev_len=cl
                decode[(cl,code)]=sym; code+=1
            return decode
        lit_decode=build_decode_table(lit_cl); dist_decode=build_decode_table(dist_cl); len_decode=build_decode_table(len_cl)
        max_lit_bits=max(lit_cl) if any(lit_cl) else 0
        max_dist_bits=max(dist_cl) if any(dist_cl) else 0
        max_len_bits=max(len_cl) if any(len_cl) else 0
        payload=data[pos:]
        if len(payload)<4: return None
        token_count=struct.unpack('>I',payload[:4])[0]
        bits=[]
        for b in payload[4:]: bits.extend([(b>>i)&1 for i in range(7,-1,-1)])
        bpos=0; tokens=[]
        for _ in range(token_count):
            if bpos>=len(bits): return None
            flag=bits[bpos]; bpos+=1
            if flag==0:
                found=False
                for cl in range(1,max_lit_bits+1):
                    if bpos+cl>len(bits): break
                    val=0
                    for j in range(cl): val=(val<<1)|bits[bpos+j]
                    if (cl,val) in lit_decode:
                        tokens.append(('L',lit_decode[(cl,val)],None)); bpos+=cl; found=True; break
                if not found: return None
            else:
                found_d=False
                for cl in range(1,max_dist_bits+1):
                    if bpos+cl>len(bits): break
                    val=0
                    for j in range(cl): val=(val<<1)|bits[bpos+j]
                    if (cl,val) in dist_decode:
                        dist=dist_decode[(cl,val)]; bpos+=cl; found_d=True; break
                if not found_d: return None
                found_l=False
                for cl in range(1,max_len_bits+1):
                    if bpos+cl>len(bits): break
                    val=0
                    for j in range(cl): val=(val<<1)|bits[bpos+j]
                    if (cl,val) in len_decode:
                        length=len_decode[(cl,val)]; bpos+=cl; found_l=True; break
                if not found_l: return None
                tokens.append(('M',dist,length))
        return self._lz77_untokenize(tokens)

    def _compress_lzh_pipeline(self,data,ultra=True):
        best_total=float('inf'); best_bytes=None
        def try_candidate(header,transformed):
            nonlocal best_total,best_bytes
            lzh=self._encode_lzh(transformed); candidate=header+b'\xFF'+lzh
            decomp=self._decompress_lzh_pipeline(candidate)
            if decomp==data and len(candidate)<best_total:
                best_total=len(candidate); best_bytes=candidate
        try_candidate(self._encode_marker_raw(),data)
        for t in range(1,257):
            try: transformed=self.fwd[t](data); try_candidate(self._encode_marker_single(t),transformed)
            except: continue
        if ultra:
            for t1,t2 in self.sequences:
                try:
                    transformed=self.fwd[t1](data); transformed=self.fwd[t2](transformed)
                    try_candidate(self._encode_marker_pair(t1,t2),transformed)
                except: continue
        if best_bytes is None: raise RuntimeError("LZH compression failed.")
        return best_bytes

    def _decompress_lzh_pipeline(self,data):
        offset,seq=self._decode_header(data)
        if offset==0 or len(data)<=offset or data[offset]!=0xFF: return None
        lzh_data=data[offset+1:]; transformed=self._decode_lzh(lzh_data)
        if transformed is None: return None
        if not seq: return transformed
        return self._reverse_sequence(transformed,seq)

    def _encode_marker_single(self,t):
        if t<=252: return bytes([t-1])
        return bytes([254, t-253])
    def _encode_marker_raw(self): return bytes([252])
    def _encode_marker_pair(self,t1,t2):
        idx=self.pair_to_index[(t1,t2)]
        return bytes([253, (idx>>8)&0xFF, idx&0xFF])
    def _decode_header(self,data):
        if not data: return 0,()
        f=data[0]
        if f<252: return 1,(f+1,)
        elif f==252: return 1,()
        elif f==253:
            if len(data)<3: return 0,()
            idx=(data[1]<<8)|data[2]
            if idx>=len(self.sequences): return 0,()
            t1,t2=self.pair_lookup[idx]; return 3,(t1,t2)
        elif f==254:
            if len(data)<2: return 0,()
            x=data[1]
            if x>3: return 0,()
            return 2,(253+x,)
        else: return 0,()

    def _reverse_sequence(self,data,seq):
        res=data
        for t in reversed(seq): res=self.rev[t](res)
        return res

    def _compress_backend(self,data,safe=False):
        candidates=[]
        if HAS_ZSTD:
            try: candidates.append((b'Z', zstd_cctx.compress(data)))
            except: pass
        if paq is not None:
            try: candidates.append((b'P', paq_mod.compress(data)))
            except: pass
        candidates.append((b'N', data))
        if safe:
            marker,best=min(candidates, key=lambda x:len(x[1]))
            return bytes([marker[0]])+best
        else:
            _,best=min(candidates, key=lambda x:len(x[1]))
            return best

    def _decompress_backend(self,data,safe=False):
        if not data: return None
        if safe and len(data)>1:
            marker=data[0]; payload=data[1:]
            if marker==ord('N'): return payload
            if marker==ord('Z') and HAS_ZSTD:
                try: return zstd_dctx.decompress(payload)
                except: pass
            if marker==ord('P') and paq is not None:
                try: return paq_mod.decompress(payload)
                except: pass
            return None
        if HAS_ZSTD:
            try: return zstd_dctx.decompress(data)
            except: pass
        if paq is not None:
            try: return paq_mod.decompress(data)
            except: pass
        return data

    def compress_with_best(self,data,ultra=True):
        if not data:
            backend=self._compress_backend(b'', safe=False)
            return self._encode_marker_raw()+backend
        best_total=float('inf'); best_bytes=None
        def try_candidate(header,transformed):
            nonlocal best_total,best_bytes
            backend=self._compress_backend(transformed, safe=False)
            candidate=header+backend
            decomp,_=self._decompress_auto(candidate)
            if decomp==data and len(candidate)<best_total:
                best_total=len(candidate); best_bytes=candidate
        try_candidate(self._encode_marker_raw(),data)
        for t in range(1,257):
            try: transformed=self.fwd[t](data); try_candidate(self._encode_marker_single(t),transformed)
            except: continue
        if ultra:
            for t1,t2 in self.sequences:
                try:
                    transformed=self.fwd[t1](data); transformed=self.fwd[t2](transformed)
                    try_candidate(self._encode_marker_pair(t1,t2),transformed)
                except: continue
        if best_bytes is None: raise RuntimeError("Compression failed.")
        return best_bytes

    def _decompress_auto(self,data):
        offset,seq=self._decode_header(data)
        if offset==0: return None,None
        payload=data[offset:]
        if not payload: return None,None
        res=self._decompress_backend(payload, safe=False)
        if res is None: return None,None
        if not seq: return res,None
        return self._reverse_sequence(res,seq),seq

    MAGIC_DICT = b'DICT'; MAGIC_LINE = b'LINE'

    def _tokenize_with_static_dict(self, data):
        try: text=data.decode('utf-8')
        except: return None
        pattern=r'([A-Za-z0-9_]+)'; tokens=re.split(pattern,text)
        stream=bytearray()
        for i,tok in enumerate(tokens):
            if i%2==1:
                idx=self.word_to_index.get(tok)
                if idx is not None:
                    stream+=b'\x01'+struct.pack('>I',idx)
                else:
                    wb=tok.encode('utf-8')
                    stream+=b'\x02'+struct.pack('>H',len(wb))+wb
            else:
                if tok:
                    sep=tok.encode('utf-8')
                    stream+=b'\x00'+struct.pack('>H',len(sep))+sep
        return bytes(stream)

    def _detokenize_static_dict(self, ts):
        if not ts: return b''
        out=bytearray(); pos=0
        while pos<len(ts):
            if pos>=len(ts): break
            typ=ts[pos]; pos+=1
            if typ==1:
                if pos+4>len(ts): break
                idx=struct.unpack('>I',ts[pos:pos+4])[0]; pos+=4
                if idx<len(self.static_dict): out+=self.static_dict[idx].encode('utf-8')
                else: return None
            elif typ==2:
                if pos+2>len(ts): break
                wlen=struct.unpack('>H',ts[pos:pos+2])[0]; pos+=2
                if pos+wlen>len(ts): break
                out+=ts[pos:pos+wlen]; pos+=wlen
            elif typ==0:
                if pos+2>len(ts): break
                slen=struct.unpack('>H',ts[pos:pos+2])[0]; pos+=2
                if pos+slen>len(ts): break
                out+=ts[pos:pos+slen]; pos+=slen
            else: break
        return bytes(out)

    def _compress_static_dict(self, data):
        ts=self._tokenize_with_static_dict(data)
        if ts is None: return None
        compressed=self._compress_backend(ts, safe=True)
        return self.MAGIC_DICT + b'\x01' + compressed

    def _decompress_static_dict(self, compressed):
        if not compressed.startswith(self.MAGIC_DICT+b'\x01'): return None
        payload=compressed[len(self.MAGIC_DICT)+1:]
        ts=self._decompress_backend(payload, safe=True)
        if ts is None: return None
        return self._detokenize_static_dict(ts)

    def _tokenize_with_line_dict(self, data):
        if not self.line_dict: return None
        try: text=data.decode('utf-8')
        except: return None
        pos=0; token_list=[]
        while pos<len(text):
            earliest_pos=len(text)+1; earliest_len=0; earliest_idx=-1
            for idx,phrase in enumerate(self.line_dict):
                p=text.find(phrase,pos)
                if p!=-1 and (p<earliest_pos or (p==earliest_pos and len(phrase)>earliest_len)):
                    earliest_pos=p; earliest_len=len(phrase); earliest_idx=idx
            if earliest_idx!=-1:
                if earliest_pos>pos:
                    token_list.append((False, text[pos:earliest_pos].encode('utf-8')))
                token_list.append((True, earliest_idx))
                pos=earliest_pos+earliest_len
            else:
                token_list.append((False, text[pos:].encode('utf-8')))
                break
        out=bytearray()
        for is_index, payload in token_list:
            if is_index:
                out+=b'\x01'+struct.pack('>Q',payload)
            else:
                out+=b'\x00'+struct.pack('>H',len(payload))+payload
        return bytes(out)

    def _detokenize_line_dict(self, ts):
        if not ts: return b''
        out=bytearray(); pos=0
        while pos<len(ts):
            if pos>=len(ts): break
            typ=ts[pos]; pos+=1
            if typ==1:
                if pos+8>len(ts): return None
                idx=struct.unpack('>Q',ts[pos:pos+8])[0]; pos+=8
                if idx<len(self.line_dict): out+=self.line_dict[idx].encode('utf-8')
                else: return None
            elif typ==0:
                if pos+2>len(ts): return None
                raw_len=struct.unpack('>H',ts[pos:pos+2])[0]; pos+=2
                if pos+raw_len>len(ts): return None
                out+=ts[pos:pos+raw_len]; pos+=raw_len
            else: return None
        return bytes(out)

    def _compress_line_dict(self, data):
        ts=self._tokenize_with_line_dict(data)
        if ts is None: return None
        compressed=self._compress_backend(ts, safe=True)
        return self.MAGIC_LINE + compressed

    def _decompress_line_dict(self, compressed):
        if not compressed.startswith(self.MAGIC_LINE): return None
        payload=compressed[len(self.MAGIC_LINE):]
        ts=self._decompress_backend(payload, safe=True)
        if ts is None: return None
        return self._detokenize_line_dict(ts)

    def _tokenize_with_dynamic_dict(self, data):
        try: text=data.decode('utf-8')
        except: return None
        chunks=[]; paragraphs=re.split(r'(\n\n)',text)
        for i,para in enumerate(paragraphs):
            if i%2==1: chunks.append(para); continue
            lines=re.split(r'(\n)',para)
            for j,line in enumerate(lines):
                if j%2==1: chunks.append(line); continue
                sentences=re.split(r'([.!?]+)',line)
                for k,sent in enumerate(sentences):
                    if k%2==1: chunks.append(sent); continue
                    words=re.split(r'(\s+|\b)',sent)
                    chunks.extend(words)
        freq=Counter(chunks)
        sorted_chunks=sorted(freq.keys(), key=lambda x:(-freq[x],-len(x),x))
        c2i={ch:i for i,ch in enumerate(sorted_chunks)}
        num_entries=len(sorted_chunks)
        header=bytearray()
        header.append(3)
        header.extend(struct.pack('>I',num_entries))
        for ch in sorted_chunks:
            chb=ch.encode('utf-8')
            header.extend(struct.pack('>I',len(chb))); header.extend(chb)
        token_stream=bytearray()
        for ch in chunks:
            idx=c2i[ch]; token_stream+=struct.pack('>I',idx)[1:4]
        return bytes(header)+bytes(token_stream)

    def _detokenize_dynamic_dict(self, data):
        if not data: return b''
        if data[0]==0: return data[1:]
        pos=1
        if pos+4>len(data): return None
        num_entries=struct.unpack('>I',data[pos:pos+4])[0]; pos+=4
        dictionary=[]
        for _ in range(num_entries):
            if pos+4>len(data): return None
            chunk_len=struct.unpack('>I',data[pos:pos+4])[0]; pos+=4
            if pos+chunk_len>len(data): return None
            chunk=data[pos:pos+chunk_len].decode('utf-8'); pos+=chunk_len
            dictionary.append(chunk)
        tokens=[]
        while pos<len(data):
            if pos+3>len(data): break
            idx_bytes=b'\x00'+data[pos:pos+3]; idx=struct.unpack('>I',idx_bytes)[0]; pos+=3
            if idx<len(dictionary): tokens.append(dictionary[idx])
            else: return None
        return ''.join(tokens).encode('utf-8')

    def _compress_dynamic_dict(self, data):
        ts=self._tokenize_with_dynamic_dict(data)
        if ts is None: return None
        compressed=self._compress_backend(ts, safe=True)
        return self.MAGIC_DICT + b'\x02' + compressed

    def _decompress_dynamic_dict(self, compressed):
        if not compressed.startswith(self.MAGIC_DICT+b'\x02'): return None
        payload=compressed[len(self.MAGIC_DICT)+1:]
        ts=self._decompress_backend(payload, safe=True)
        if ts is None: return None
        return self._detokenize_dynamic_dict(ts)

    ZADEN_MAGIC=0x33
    def _find_best_16bit_key(self,block,time_limit=60):
        if len(block)<3: return 0
        pad=(3-len(block)%3)%3; padded=block+b'\x00'*pad
        vals=[int.from_bytes(padded[i:i+3],'little') for i in range(0,len(padded),3)]
        best_key=0; best_cost=float('inf'); start=time.time()
        for key in range(65536):
            if time.time()-start>time_limit: break
            trans=[((v-key)&0xFFFFFF) for v in vals]
            mean=sum(trans)//len(trans); cost=sum(abs(t-mean) for t in trans)
            if cost<best_cost: best_cost=cost; best_key=key
        return best_key

    def _encode_key_unary(self,key):
        if key==0: bits='0'; length=1
        else: bits=bin(key)[2:]; length=len(bits)
        prefix='0'*(length-1)+'1'; encoded=prefix+bits
        pad=(8-len(encoded)%8)%8; encoded+='0'*pad
        return bytes(int(encoded[i:i+8],2) for i in range(0,len(encoded),8))

    def _decode_key_unary(self,data,pos):
        bit_idx=pos*8
        zeros=0
        while True:
            byte_idx=bit_idx//8; bit_off=bit_idx%8
            if byte_idx>=len(data): raise ValueError("EOF")
            byte=data[byte_idx]; bit=(byte>>(7-bit_off))&1; bit_idx+=1
            if bit==1: break
            zeros+=1
        length=zeros+1; key=0
        for _ in range(length):
            byte_idx=bit_idx//8; bit_off=bit_idx%8
            if byte_idx>=len(data): raise ValueError("EOF")
            byte=data[byte_idx]; bit=(byte>>(7-bit_off))&1; key=(key<<1)|bit; bit_idx+=1
        bit_idx=((bit_idx+7)//8)*8; new_pos=bit_idx//8
        return key,new_pos

    def _block_optimize(self,data,block_size=256,time_limit=60):
        keys=[]; parts=[]
        for i in range(0,len(data),block_size):
            block=data[i:i+block_size]
            k1=self._find_best_16bit_key(block,time_limit)
            pad=(3-len(block)%3)%3; padded=block+b'\x00'*pad
            trans1=bytearray()
            for j in range(0,len(padded),3):
                v=int.from_bytes(padded[j:j+3],'little'); new=(v-k1)&0xFFFFFF
                trans1.extend(new.to_bytes(3,'little'))
            inter=bytes(trans1[:len(block)])
            k2=self._find_best_16bit_key(inter,time_limit)
            pad2=(3-len(inter)%3)%3; padded2=inter+b'\x00'*pad2
            trans2=bytearray()
            for j in range(0,len(padded2),3):
                v=int.from_bytes(padded2[j:j+3],'little'); new=(v-k2)&0xFFFFFF
                trans2.extend(new.to_bytes(3,'little'))
            final=bytes(trans2[:len(inter)])
            keys.append((k1,k2)); parts.append(final)
        return b''.join(parts), keys

    def zaden_compress(self,data,block_size=256,time_limit=60):
        transformed, keys = self._block_optimize(data, block_size, time_limit)
        compressed = self.compress_with_best(transformed, ultra=True)
        magic = bytes([self.ZADEN_MAGIC]); num_blocks = len(keys)
        header = struct.pack('<II', block_size, num_blocks)
        key_bytes = b''.join(self._encode_key_unary(k1)+self._encode_key_unary(k2) for k1,k2 in keys)
        return magic + header + key_bytes + compressed

    def zaden_decompress(self,data):
        if len(data)<1 or data[0]!=self.ZADEN_MAGIC: return None
        pos=1
        if len(data)<pos+8: return None
        block_size, num_blocks = struct.unpack('<II', data[pos:pos+8]); pos+=8
        keys=[]
        for _ in range(num_blocks):
            k1,pos=self._decode_key_unary(data,pos); k2,pos=self._decode_key_unary(data,pos)
            keys.append((k1,k2))
        inner=data[pos:]
        decomp,_=self._decompress_auto(inner)
        if decomp is None: return None
        out_parts=[]; offset=0
        for k1,k2 in keys:
            block=decomp[offset:offset+block_size]; offset+=block_size
            pad=(3-len(block)%3)%3; block_pad=block+b'\x00'*pad
            inter=bytearray()
            for i in range(0,len(block_pad),3):
                v=int.from_bytes(block_pad[i:i+3],'little'); orig=(v+k2)&0xFFFFFF
                inter.extend(orig.to_bytes(3,'little'))
            inter=bytes(inter[:len(block)])
            pad2=(3-len(inter)%3)%3; inter_pad=inter+b'\x00'*pad2
            orig_block=bytearray()
            for i in range(0,len(inter_pad),3):
                v=int.from_bytes(inter_pad[i:i+3],'little'); orig=(v+k1)&0xFFFFFF
                orig_block.extend(orig.to_bytes(3,'little'))
            out_parts.append(bytes(orig_block[:len(block)]))
        return b''.join(out_parts)

    ALGO36_MAGIC=0x36
    def algo36_compress(self,data,time_limit=300):
        if not data: return bytes([self.ALGO36_MAGIC,0,0])
        pad=(3-len(data)%3)%3; padded=data+b'\x00'*pad
        vals=[int.from_bytes(padded[i:i+3],'little') for i in range(0,len(padded),3)]
        n=len(vals)
        best_idx=0; best_metric=float('inf'); start=time.time()
        for idx in range(24):
            p=1<<idx
            trans=[((v-p)&0xFFFFFF) for v in vals]
            mean=sum(trans)//n; metric=sum(abs(t-mean) for t in trans)
            if metric<best_metric: best_metric=metric; best_idx=idx
            if time.time()-start>time_limit: break
        best_pass=1<<best_idx
        transformed=bytearray()
        for v in vals: transformed.extend(((v-best_pass)&0xFFFFFF).to_bytes(3,'little'))
        compressed=self.compress_with_best(bytes(transformed), ultra=True)
        out=bytearray([self.ALGO36_MAGIC, pad, best_idx]); out.extend(compressed)
        return bytes(out)

    def algo36_decompress(self,data):
        if not data or data[0]!=self.ALGO36_MAGIC: return None
        pos=1
        if len(data)<pos+2: return None
        pad=data[pos]; pos+=1; idx=data[pos]; pos+=1
        if idx>23: return None
        pass_val=1<<idx
        compressed=data[pos:]
        decomp,_=self._decompress_auto(compressed)
        if decomp is None: return None
        if len(decomp)%3!=0: return None
        out=bytearray()
        for i in range(0,len(decomp),3):
            chunk=decomp[i:i+3]; val=int.from_bytes(chunk,'little')
            orig=(val+pass_val)&0xFFFFFF; out.extend(orig.to_bytes(3,'little'))
        if pad: out=out[:-pad]
        return bytes(out)

    def decompress_file(self, infile: str, outfile: str):
        try: with open(infile, 'rb') as f: data = f.read()
        except Exception as e: print(f"Error reading file: {e}"); return
        if len(data) > 0 and data[0] == self.ALGO36_MAGIC:
            original = self.algo36_decompress(data)
            if original is not None:
                with open(outfile, 'wb') as f: f.write(original)
                print(f"Decompressed (Algorithm 36) -> {outfile} ({len(original)} bytes)"); return
        if len(data) > 0 and data[0] == self.ZADEN_MAGIC:
            original = self.zaden_decompress(data)
            if original is not None:
                with open(outfile, 'wb') as f: f.write(original)
                print(f"Decompressed (Zaden) -> {outfile} ({len(original)} bytes)"); return
        offset, seq = self._decode_header(data)
        if offset>0 and len(data)>offset and data[offset]==0xFF:
            original = self._decompress_lzh_pipeline(data)
            if original is not None:
                with open(outfile, 'wb') as f: f.write(original)
                print(f"Decompressed (LZ77+Huffman) -> {outfile} ({len(original)} bytes)"); return
        if data.startswith(self.MAGIC_DICT+b'\x01'):
            original = self._decompress_static_dict(data)
            if original is not None:
                with open(outfile, 'wb') as f: f.write(original)
                print(f"Decompressed (Static‑Word Dict) -> {outfile} ({len(original)} bytes)"); return
        if data.startswith(self.MAGIC_DICT+b'\x02'):
            original = self._decompress_dynamic_dict(data)
            if original is not None:
                with open(outfile, 'wb') as f: f.write(original)
                print(f"Decompressed (Dynamic Dict) -> {outfile} ({len(original)} bytes)"); return
        if data.startswith(self.MAGIC_LINE):
            original = self._decompress_line_dict(data)
            if original is not None:
                with open(outfile, 'wb') as f: f.write(original)
                print(f"Decompressed (Line Dict) -> {outfile} ({len(original)} bytes)"); return
        original, _ = self._decompress_auto(data)
        if original is None: print("Decompression failed – unknown format."); return
        with open(outfile, 'wb') as f: f.write(original)
        seq_str = "raw" if not seq else f"sequence {seq}"
        print(f"Decompressed ({seq_str}) -> {outfile} ({len(original)} bytes)")

    def full_self_test(self):
        print("="*60); print("UltimateHybridCompressor – FULL SELF‑TEST (65536 indices)"); print("="*60)
        test_byte=0xAA; test_data=bytes([test_byte])
        print(f"Testing all 65536 indices on byte 0x{test_byte:02X}...")
        all_ok=True
        for idx in range(65536):
            try:
                enc=self.apply_transform_by_index(test_data, idx)
                dec=self.reverse_transform_by_index(enc, idx)
                if dec!=test_data:
                    print(f"  FAIL: index {idx}, seq {self.get_transform_sequence(idx)}")
                    all_ok=False; break
            except Exception as e:
                print(f"  EXCEPTION at {idx}: {e}"); all_ok=False; break
            if idx%10000==0 and idx>0: print(f"  ... {idx} indices OK")
        if all_ok: print("  All 65536 indices lossless on test byte.")
        else: print("[FAIL] Basic transform index test failed."); return False

        rng=random.Random(12345); test_data=bytes(rng.randint(0,255) for _ in range(1000))
        print("\nTesting backend compression roundtrip...")
        compressed=self.compress_with_best(test_data, ultra=True)
        decomp,_=self._decompress_auto(compressed)
        if decomp!=test_data: print("  FAIL"); return False
        print("  PASS")

        print("\nTesting LZ77+Huffman pipeline...")
        compressed_lzh=self._compress_lzh_pipeline(test_data, ultra=True)
        decomp_lzh=self._decompress_lzh_pipeline(compressed_lzh)
        if decomp_lzh!=test_data: print("  FAIL"); return False
        print("  PASS")

        print("\nTesting Zaden block optimization...")
        compressed_z=self.zaden_compress(test_data, block_size=256, time_limit=5)
        decomp_z=self.zaden_decompress(compressed_z)
        if decomp_z!=test_data: print("  FAIL"); return False
        print("  PASS")

        print("\nTesting Algorithm 36...")
        compressed_a=self.algo36_compress(test_data, time_limit=5)
        decomp_a=self.algo36_decompress(compressed_a)
        if decomp_a!=test_data: print("  FAIL"); return False
        print("  PASS")

        print("\nTesting static dictionary...")
        sample=b"The quick brown fox jumps over the lazy dog."
        comp=self._compress_static_dict(sample)
        if comp:
            decomp=self._decompress_static_dict(comp)
            if decomp!=sample: print("  FAIL"); return False
            else: print("  PASS")
        else: print("  Dictionary not loaded, skip.")

        print("\n[All self‑tests passed – 100% lossless]")
        return True


# ============================================================================
# UNIFIED MAIN MENU
# ============================================================================
def main():
    print("="*60)
    print("UNIFIED PAQJP COMPRESSOR – CHOOSE YOUR ENGINE")
    print("="*60)
    print("1) Engine 1: PAQJP 9.3 – 65536 Indices + LZ77/Huffman (2KB window)")
    print("2) Engine 2: Ultimate Hybrid – 65536 Indices + Quantum/Zaden/Algo36/Dicts")
    print("0) Exit")
    print("="*60)

    while True:
        try:
            eng_choice = input("Select engine (0-2): ").strip()
            if eng_choice == "0": break
            if eng_choice == "1":
                c = PAQJPCompressorTransform65535(repeat_count=100)
                print(f"\n{PROGNAME} – Engine 1 selected.")
                sub_menu_engine1(c)
            elif eng_choice == "2":
                c = UltimateHybridCompressor(repeat_count=100)
                print(f"\n{PROGNAME} – Engine 2 selected.")
                sub_menu_engine2(c)
            else:
                print("Invalid selection.")
        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

def sub_menu_engine1(c):
    while True:
        print("\n" + "="*50)
        print("ENGINE 1 MENU (PAQJP 9.3 – 65536 LZH)")
        print("1) Compress (Zstd/PAQ)")
        print("2) Decompress")
        print("3) Full self‑test (all 0‑65535)")
        print("4) Analyze bit‑string")
        print("5) Test transformation by index")
        print("6) Find optimal block size for Transform 23")
        print("7) Compress (LZ77+Huffman)")
        print("0) Return to Engine Selection")
        print("="*50)
        choice = input("> ").strip()
        if choice == "0": break
        elif choice == "1":
            i = input("Input file: ").strip()
            mode = input("Choose mode: 1) Fast (256)  2) Ultra (65535 pairs)\n> ").strip()
            ultra = True if mode == "2" else False
            c.compress_file(i, "", ultra=ultra, use_lzh=False)
        elif choice == "2":
            i = input("Compressed file: ").strip()
            o = input("Output file (enter for auto-name): ").strip()
            c.decompress_file(i, o)
        elif choice == "3": c.full_self_test()
        elif choice == "4":
            fpath = input("File to analyze: ").strip()
            c.analyze_constant_diapason(fpath)
        elif choice == "5":
            try: idx = int(input("Transformation index (0‑65535): ").strip())
            except ValueError: print("Invalid number."); continue
            if idx < 0 or idx > 65535: print("Index out of range."); continue
            seq = c.get_transform_sequence(idx)
            print(f"Sequence: {seq if seq else '(raw)'}")
            test_bytes = bytes([0x00, 0xFF, 0x55, 0xAA])
            print("Testing on bytes 0x00 0xFF 0x55 0xAA ...")
            for b in test_bytes:
                data = bytes([b]); enc = c.apply_transform_by_index(data, idx)
                dec = c.reverse_transform_by_index(enc, idx)
                if dec == data: print(f"  0x{b:02X}: OK")
                else: print(f"  0x{b:02X}: FAIL (got {dec.hex()})")
        elif choice == "6":
            fpath = input("File to test: ").strip()
            c.find_best_block_size_transform23(fpath)
        elif choice == "7":
            i = input("Input file: ").strip()
            mode = input("Choose mode: 1) Fast (256)  2) Ultra (65535 pairs)\n> ").strip()
            ultra = True if mode == "2" else False
            c.compress_file(i, "", ultra=ultra, use_lzh=True)
        else: print("Invalid choice.")

def sub_menu_engine2(c):
    while True:
        print("\n" + "="*50)
        print("ENGINE 2 MENU (Ultimate Hybrid)")
        print(" 1) Fast (256 singles, backend)")
        print(" 2) Ultra (65536 indices, backend)")
        print(" 3) LZ77+Huffman fast")
        print(" 4) LZ77+Huffman ultra")
        print(" 5) Hybrid dictionary + Ultra backend")
        print(" 6) Zaden block optimization")
        print(" 7) Algorithm 36")
        print(" 8) Full self‑test")
        print(" 9) Best Overall (tries 1,2,3,4,5,6,7, picks smallest)")
        print("10) Extract (decompress) any compressed file")
        print(" 0) Return to Engine Selection")
        print("="*50)
        try: ch = int(input("> ").strip())
        except: print("Invalid input."); continue
        if ch == 0: break
        elif ch in (1,2,3,4,5,6,7,9):
            infile = input("Input file: ").strip()
            if not infile: continue
            outfile = input("Output file (optional): ").strip()
            if not outfile:
                base = os.path.splitext(os.path.basename(infile))[0]
                outfile = f"{base}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.uhc"
            try: with open(infile,'rb') as f: data=f.read()
            except Exception as e: print(f"Error reading file: {e}"); continue
            if ch == 1: compressed=c.compress_with_best(data, ultra=False)
            elif ch == 2: compressed=c.compress_with_best(data, ultra=True)
            elif ch == 3: compressed=c._compress_lzh_pipeline(data, ultra=False)
            elif ch == 4: compressed=c._compress_lzh_pipeline(data, ultra=True)
            elif ch == 5:
                methods={}
                for name, func in [("StaticDict", lambda: c._compress_static_dict(data)),("DynamicDict", lambda: c._compress_dynamic_dict(data)),("LineDict", lambda: c._compress_line_dict(data)),("Ultra", lambda: c.compress_with_best(data, ultra=True))]:
                    try: res=func()
                    except: continue
                    if res is not None: methods[name]=res
                if methods: compressed = min(methods.values(), key=len); print(f"Chosen method: {min(methods, key=lambda k: len(methods[k]))}")
                else: print("All dict methods failed, falling back to Ultra."); compressed = c.compress_with_best(data, ultra=True)
            elif ch == 6: compressed=c.zaden_compress(data, time_limit=60)
            elif ch == 7: compressed=c.algo36_compress(data, time_limit=300)
            elif ch == 9:
                methods={}
                for name,func in [("Fast",lambda: c.compress_with_best(data,ultra=False)),("Ultra",lambda: c.compress_with_best(data,ultra=True)),("LZH_fast",lambda: c._compress_lzh_pipeline(data,ultra=False)),("LZH_ultra",lambda: c._compress_lzh_pipeline(data,ultra=True)),("StaticDict",lambda: c._compress_static_dict(data)),("DynamicDict",lambda: c._compress_dynamic_dict(data)),("LineDict",lambda: c._compress_line_dict(data)),("Zaden",lambda: c.zaden_compress(data, time_limit=60)),("Algo36",lambda: c.algo36_compress(data, time_limit=300))]:
                    try: res=func()
                    except Exception as e: print(f"  {name} failed: {e}")
                    if res is not None: methods[name]=res
                if not methods: print("All methods failed."); continue
                best_name=min(methods, key=lambda k:len(methods[k])); compressed=methods[best_name]
                print(f"Best: {best_name} ({len(compressed)} bytes)")
            try: with open(outfile,'wb') as f: f.write(compressed)
            except Exception as e: print(f"Write error: {e}")
            print(f"Compressed {len(data)} -> {len(compressed)} bytes, written to {outfile}")
        elif ch == 10:
            infile=input("Compressed file: ").strip()
            outfile=input("Output file (optional): ").strip()
            if not outfile:
                base=os.path.splitext(os.path.basename(infile))[0]
                outfile=f"{base}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.orig"
            c.decompress_file(infile, outfile)
        elif ch == 8: c.full_self_test()
        else: print("Invalid choice.")

if __name__ == "__main__":
    main()
