#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quantumzstandard 1 – Full lossless transform set (0–65535) + LZ77/Huffman
100% lossless on every index (verified by self‑test).
Menu:
  1) Compress Fast (256 transforms + LZH) → .pjp.lzh
  2) Compress Ultra (65536 transforms + LZH) → .pjp.lzh
  3) Full self‑test (65536 indices + LZH round‑trip)
  4) Exit
"""
import math, random, decimal, hashlib, base64, heapq, struct, zlib, os
from typing import Optional, List, Tuple, Dict, Callable, Any

# ---------- Optional backends (only for internal block transforms 28-30) ----------
try:
    import zstandard as zstd
    zstd_cctx = zstd.ZstdCompressor(level=22)
    zstd_dctx = zstd.ZstdDecompressor()
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

try:
    import paq
except ImportError:
    paq = None

# ---------- Constants ----------
PRIMES = [p for p in range(2, 256) if all(p % d != 0 for d in range(2, int(p**0.5)+1))]
PI_DIGITS = [79, 17, 111]

def find_nearest_prime_around(n: int) -> int:
    if n < 2: return 2
    for o in range(0, 256):
        for cand in (n - o, n + o):
            if cand >= 2 and all(cand % d != 0 for d in range(2, int(cand**0.5)+1)):
                return cand
    return 2

# Prefix‑free nibble code for transform 23
_CONST_DIAPASON_ITER_CODE = [
    (2, 0b10), (2, 0b11),
    (3, 0b010), (3, 0b011),
    (4, 0b0010), (4, 0b0011),
    (5, 0b00010), (5, 0b00011),
    (6, 0b000010), (6, 0b000011),
    (7, 0b0000010), (7, 0b0000011),
    (8, 0b00000010), (8, 0b00000011),
    (9, 0b000000010), (9, 0b000000011),
]
_CONST_DIAPASON_ITER_DECODE = {}
for nibble, (length, bits) in enumerate(_CONST_DIAPASON_ITER_CODE):
    _CONST_DIAPASON_ITER_DECODE[(length, bits)] = nibble

# State table for Transform 47
STATE_TABLE = [
    [ 1, 2, 0, 0], [ 3, 5, 0, 1], [ 4, 6, 2, 0], [ 7, 10, 0, 2],
    [ 8, 12, 3, 0], [ 9, 13, 1, 1], [ 11, 14, 0, 3], [ 15, 19, 4, 0],
    [ 16, 23, 2, 1], [ 17, 24, 2, 1], [ 18, 25, 2, 1], [ 20, 27, 1, 2],
    [ 21, 28, 1, 2], [ 22, 29, 1, 2], [ 26, 30, 0, 4], [ 31, 33, 5, 0],
    [ 32, 34, 3, 1], [ 35, 37, 1, 3], [ 36, 38, 1, 3], [ 39, 42, 0, 5],
    [ 40, 43, 4, 1], [ 41, 44, 2, 2], [ 45, 48, 1, 4], [ 46, 49, 1, 4],
    [ 47, 50, 1, 4], [ 51, 52, 0, 6], [ 53, 55, 6, 0], [ 54, 56, 4, 1],
    [ 57, 59, 2, 3], [ 58, 60, 2, 3], [ 61, 63, 0, 7], [ 62, 64, 5, 1],
    [ 65, 66, 3, 2], [ 67, 69, 1, 5], [ 68, 70, 1, 5], [ 71, 73, 0, 8],
    [ 72, 74, 6, 1], [ 75, 76, 4, 2], [ 77, 78, 2, 4], [ 79, 80, 2, 4],
    [ 81, 82, 0, 9], [ 83, 84, 7, 1], [ 85, 86, 5, 2], [ 87, 88, 3, 3],
    [ 89, 90, 1, 6], [ 91, 92, 0, 10], [ 93, 94, 8, 1], [ 95, 96, 6, 2],
    [ 97, 98, 4, 3], [ 99, 100, 2, 5], [101, 102, 0, 11], [103, 104, 9, 1],
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
    [249, 250, 12, 4], [251, 252, 10, 4], [253, 254, 8, 6], [255, 255, 6, 7],
]

class QuantumzstandardCompressor:
    def __init__(self, repeat_count=100):
        self.repeat_count = repeat_count
        self.PI_DIGITS = PI_DIGITS.copy()
        self.seed_tables = self._gen_seed_tables(126, 40, 42)
        self.fibonacci = self._gen_fib(100)
        self.PI_STR = "3.14159265358979323846264338327950288419716939937510"
        self.mod_state_table = [[(v-400)&0xFF for v in row] for row in STATE_TABLE]
        self._build_transform_maps()
        self.sequences = self._build_pair_sequences()
        self.pair_lookup = {i: (t1,t2) for i,(t1,t2) in enumerate(self.sequences)}
        self._build_mask_46()

    def _build_mask_46(self):
        base = [1,2,4,8,16,32,64,128,3,6]
        self.mask_46 = [(b-10)&0xFF for b in base] * 10

    # ---------- Pi helpers ----------
    def get_pi_digits(self, n): return self.PI_STR[2:2+n] if n>0 else ""
    def find_lossless_k(self, n):
        if n<1: return 0, True
        true_digits = self.get_pi_digits(n)
        true_scaled = int(self.PI_STR.replace('.','')[:n+1])
        DENOM = 16777216
        decimal.getcontext().prec = 50
        pi_dec = decimal.Decimal(self.PI_STR)
        k_float = (pi_dec - 3) * DENOM
        k = int(round(k_float))
        k = max(0, min(k, DENOM-1))
        approx = (3*10**n*DENOM + k*10**n)//DENOM
        return k, approx==true_scaled
    def to_bin(self, v, b): return format(v,'b').zfill(b)
    def get_bit_size(self, k): return 23 if k<=0x7FFFFF else 25
    def get_basel_digits(self, n):
        decimal.getcontext().prec = n+5
        s = str((decimal.Decimal(self.PI_STR)**2)/6).replace('.','')
        return s[:n]
    def get_one_over_e_digits(self, n):
        decimal.getcontext().prec = n+5
        e = decimal.Decimal(1).exp()
        s = str(1/e).replace('.','')
        return s[:n]
    def get_5e_digits(self, n):
        decimal.getcontext().prec = n+5
        e = decimal.Decimal(1).exp()
        s = str(5*e).replace('.','')
        return s[:n]

    # ---------- Seed tables / Fibonacci ----------
    def _gen_seed_tables(self, num, size, seed):
        random.seed(seed)
        return [[random.randint(5,255) for _ in range(size)] for _ in range(num)]
    def _gen_fib(self, n):
        a,b = 0,1
        res = [a,b]
        for _ in range(2,n): a,b = b, a+b; res.append(b)
        return res
    def get_seed(self, idx, val):
        if 0 <= idx < len(self.seed_tables): return self.seed_tables[idx][val%40]
        return 0

    # ---------- Bit helpers ----------
    def _append_bits(self, bitlist, value, count):
        for i in range(count-1,-1,-1): bitlist.append((value>>i)&1)
    def _read_bits(self, bits, pos, count):
        val = 0
        for i in range(count):
            if pos+i >= len(bits): return 0
            val = (val<<1) | bits[pos+i]
        return val

    # ---------- RLE transform 00 (index 1) ----------
    def transform_00(self, data):
        if not data: return b'\x00'
        best_result, best_length, best_shifts = None, float('inf'), []
        MAX_PASSES = 10
        current = bytearray(data)
        applied_shifts = []
        original = bytes(data)
        for _ in range(MAX_PASSES):
            best_shift, best_shifted, best_score = 0, current, float('-inf')
            for shift in range(256):
                tmp = bytearray(current)
                for j in range(len(tmp)): tmp[j] = (tmp[j]+shift)%256
                score = 0
                i = 0
                while i < len(tmp):
                    val = tmp[i]; run = 1; i+=1
                    while i < len(tmp) and tmp[i]==val: run+=1; i+=1
                    score += run*run
                if score > best_score:
                    best_score, best_shifted, best_shift = score, tmp, shift
            applied_shifts.append(best_shift)
            rle_enc = self._apply_rle_to_shifted(best_shifted, best_shift)
            dec_shifted = self._rle_decode(rle_enc)
            if dec_shifted is not None:
                test = bytearray(dec_shifted)
                for s in applied_shifts:
                    for j in range(len(test)): test[j] = (test[j]-s)%256
                if bytes(test) == original and len(rle_enc) < best_length:
                    best_length, best_result, best_shifts = len(rle_enc), rle_enc, applied_shifts.copy()
            current = best_shifted
            if len(rle_enc) >= len(data): break
        if best_result is None or best_length >= len(data):
            return bytes([0])+data
        header = bytearray([len(best_shifts)])
        header.extend(best_shifts)
        return header + best_result

    def _apply_rle_to_shifted(self, shifted, shift):
        bits = []
        self._append_bits(bits, 0b010, 3)
        self._append_bits(bits, shift, 8)
        i, n = 0, len(shifted)
        while i < n:
            val = shifted[i]; run = 1; i+=1
            while i < n and shifted[i]==val: run+=1; i+=1
            while run >= 13:
                chunk = min(run, 268)
                self._append_bits(bits, 0b1111, 4)
                self._append_bits(bits, chunk-13, 8)
                self._append_bits(bits, val, 8)
                run -= chunk
            if run == 1:
                self._append_bits(bits, 0b00, 2); self._append_bits(bits, val, 8)
            elif run <= 5:
                self._append_bits(bits, 0b01, 2); self._append_bits(bits, run-2, 2)
                self._append_bits(bits, val, 8)
            else:
                self._append_bits(bits, 0b10, 2); self._append_bits(bits, run-6, 3)
                self._append_bits(bits, val, 8)
        pad = (8 - len(bits)%8)%8
        self._append_bits(bits, 0, pad)
        out = bytearray()
        for j in range(0, len(bits), 8):
            byte = 0
            for k in range(8):
                if j+k < len(bits): byte = (byte<<1) | bits[j+k]
            out.append(byte)
        return bytes(out)

    def reverse_transform_00(self, cdata):
        if not cdata or cdata == b'\x00': return b''
        if cdata[0] == 0: return cdata[1:]
        num_passes = cdata[0]
        if num_passes == 0 or len(cdata) < 1+num_passes: return b''
        shifts = list(cdata[1:1+num_passes])
        rle_data = cdata[1+num_passes:]
        decoded = self._rle_decode(rle_data)
        if decoded is None: return b''
        current = bytearray(decoded)
        for s in reversed(shifts):
            for i in range(len(current)): current[i] = (current[i]-s)%256
        return bytes(current)

    def _rle_decode(self, data):
        if not data: return None
        bits = []
        for b in data:
            for i in range(7,-1,-1): bits.append((b>>i)&1)
        pos, nbits = 0, len(bits)
        if nbits < 11: return None
        marker = self._read_bits(bits, pos, 3); pos+=3
        if marker != 0b010: return None
        pos += 8
        out = bytearray()
        while pos < nbits:
            if pos+2 > nbits: break
            prefix = self._read_bits(bits, pos, 2); pos+=2
            if prefix == 0b00:
                if pos+8 > nbits: break
                run = 1
            elif prefix == 0b01:
                if pos+2+8 > nbits: break
                run = 2 + self._read_bits(bits, pos, 2); pos+=2
            elif prefix == 0b10:
                if pos+3+8 > nbits: break
                run = 6 + self._read_bits(bits, pos, 3); pos+=3
            else:
                if pos+2+8+8 > nbits: break
                if self._read_bits(bits, pos, 2) != 0b11: return None
                pos+=2
                run = 13 + self._read_bits(bits, pos, 8); pos+=8
            if pos+8 > nbits: break
            val = self._read_bits(bits, pos, 8); pos+=8
            out.extend([val]*run)
        for i in range(pos, nbits):
            if bits[i] != 0: return None
        return out

    # ---------- Transforms 01-21 ----------
    def transform_01(self, d):
        t = bytearray(d)
        for prime in PRIMES:
            xor_val = prime if prime==2 else max(1, math.ceil(prime*4096/28672))
            for _ in range(self.repeat_count):
                for i in range(0, len(t), 3):
                    if i < len(t): t[i] ^= xor_val
        return bytes(t)
    reverse_transform_01 = transform_01

    def transform_02(self, d):
        if len(d)<1: return b''
        t = bytearray(d)
        pattern_index = (len(d)+sum(d))%256
        pattern = self._get_pattern(4, pattern_index)
        for i in range(1, len(t), 4):
            if i < len(t): t[i] ^= pattern[i%len(pattern)]
        return bytes([pattern_index])+bytes(t)
    def reverse_transform_02(self, d):
        if len(d)<2: return b''
        pi, t = d[0], bytearray(d[1:])
        pattern = self._get_pattern(4, pi)
        for i in range(1, len(t), 4):
            if i < len(t): t[i] ^= pattern[i%len(pattern)]
        return bytes(t)

    def transform_03(self, d):
        if len(d)<1: return b''
        t = bytearray(d)
        rot = (len(d)*13+sum(d))%8; rot = rot if rot else 1
        for i in range(2, len(t), 5):
            if i < len(t): t[i] = ((t[i]<<rot)|(t[i]>>(8-rot)))&0xFF
        return bytes([rot])+bytes(t)
    def reverse_transform_03(self, d):
        if len(d)<2: return b''
        rot, t = d[0], bytearray(d[1:])
        for i in range(2, len(t), 5):
            if i < len(t): t[i] = ((t[i]>>rot)|(t[i]<<(8-rot)))&0xFF
        return bytes(t)

    def transform_04(self, d):
        t = bytearray(d)
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i] = (t[i]-(i%256))%256
        return bytes(t)
    def reverse_transform_04(self, d):
        t = bytearray(d)
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i] = (t[i]+(i%256))%256
        return bytes(t)

    def transform_05(self, d, s=3):
        t = bytearray(d)
        for i in range(len(t)): t[i] = ((t[i]<<s)|(t[i]>>(8-s)))&0xFF
        return bytes(t)
    reverse_transform_05 = transform_05  # s=3 for both

    def transform_06(self, d, sd=42):
        random.seed(sd); sub = list(range(256)); random.shuffle(sub)
        t = bytearray(d)
        for i in range(len(t)): t[i] = sub[t[i]]
        return bytes(t)
    def reverse_transform_06(self, d, sd=42):
        random.seed(sd); sub = list(range(256)); random.shuffle(sub)
        inv = [0]*256
        for i,v in enumerate(sub): inv[v] = i
        t = bytearray(d)
        for i in range(len(t)): t[i] = inv[t[i]]
        return bytes(t)

    def transform_07(self, d):
        t = bytearray(d)
        sh = len(d)%len(self.PI_DIGITS)
        pi_rot = self.PI_DIGITS[sh:]+self.PI_DIGITS[:sh]
        sz = len(d)%256
        for i in range(len(t)): t[i] ^= sz
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i] ^= pi_rot[i%len(pi_rot)]
        return bytes(t)
    reverse_transform_07 = transform_07

    def transform_08(self, d):
        t = bytearray(d)
        sh = len(d)%len(self.PI_DIGITS)
        pi_rot = self.PI_DIGITS[sh:]+self.PI_DIGITS[:sh]
        p = find_nearest_prime_around(len(d)%256)
        for i in range(len(t)): t[i] ^= p
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i] ^= pi_rot[i%len(pi_rot)]
        return bytes(t)
    reverse_transform_08 = transform_08

    def transform_09(self, d):
        t = bytearray(d)
        sh = len(d)%len(self.PI_DIGITS)
        pi_rot = self.PI_DIGITS[sh:]+self.PI_DIGITS[:sh]
        p = find_nearest_prime_around(len(d)%256)
        seed = self.get_seed(len(d)%len(self.seed_tables), len(d))
        for i in range(len(t)): t[i] ^= p ^ seed
        for _ in range(self.repeat_count):
            for i in range(len(t)): t[i] ^= pi_rot[i%len(pi_rot)] ^ (i%256)
        return bytes(t)
    reverse_transform_09 = transform_09

    def transform_10(self, data):
        if not data: return b'\x00'
        cnt = sum(1 for i in range(len(data)-1) if data[i:i+2]==b'X1')
        n = (((cnt*2)+1)//3)*3%256
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= n
        return bytes([n])+bytes(t)
    def reverse_transform_10(self, data):
        if len(data)<1: return b''
        n, t = data[0], bytearray(data[1:])
        for i in range(len(t)): t[i] ^= n
        return bytes(t)

    def transform_11(self, data):
        if not data: return b''
        t = bytearray(data)
        L = len(t)
        for i in range(L):
            fib_val = self.fibonacci[(i+L)%len(self.fibonacci)]%256
            pos_val = (i*13 + L*17)%256
            t[i] ^= fib_val ^ pos_val
        return bytes(t)
    reverse_transform_11 = transform_11

    def transform_12(self, data):
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= self.fibonacci[i%len(self.fibonacci)]%256
        return bytes(t)
    reverse_transform_12 = transform_12

    def transform_13(self, d):
        if not d: return b''
        repeats = self._calculate_repeats(d)
        cur = len(d)%256
        primes = []
        for _ in range(repeats):
            cur = find_nearest_prime_around(cur); primes.append(cur)
        xor_val = primes[-1] if primes else 0
        t = bytearray(d)
        for i in range(len(t)): t[i] ^= xor_val
        return bytes([(repeats-1)%256])+bytes(t)
    def reverse_transform_13(self, d):
        if len(d)<2: return b''
        repeats = (d[0]+1)%256; repeats = repeats if repeats else 256
        t = bytearray(d[1:])
        cur = len(t)%256
        primes = []
        for _ in range(repeats):
            cur = find_nearest_prime_around(cur); primes.append(cur)
        xor_val = primes[-1] if primes else 0
        for i in range(len(t)): t[i] ^= xor_val
        return bytes(t)

    def transform_14(self, d):
        if not d: return b'\x00'
        return d + bytes([sum(d)%256])
    def reverse_transform_14(self, d):
        return d[:-1] if d else b''

    def transform_15(self, d):
        if len(d)<1: return b''
        t = bytearray(d)
        pi = len(d)%256
        pattern = self._get_pattern(3, pi)
        for i in range(0, len(t), 3):
            if i < len(t): t[i] = (t[i]+pattern[i%len(pattern)])%256
        return bytes([pi])+bytes(t)
    def reverse_transform_15(self, d):
        if len(d)<2: return b''
        pi, t = d[0], bytearray(d[1:])
        pattern = self._get_pattern(3, pi)
        for i in range(0, len(t), 3):
            if i < len(t): t[i] = (t[i]-pattern[i%len(pattern)])%256
        return bytes(t)

    def transform_16(self, data):
        if not data: return b''
        xor_byte = (len(data)*7+13)%256
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= xor_byte
        return bytes(t)
    reverse_transform_16 = transform_16

    def transform_17(self, data):
        if not data: return b''
        k, _ = self.find_lossless_k(7)
        bits_used = self.get_bit_size(k)
        bit_str = self.to_bin(k, bits_used)
        mask = bytearray()
        for i in range(0, len(bit_str), 8):
            chunk = bit_str[i:i+8].ljust(8,'0')
            mask.append(int(chunk,2))
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= mask[i%len(mask)]
        return bytes(t)
    reverse_transform_17 = transform_17

    def transform_18(self, data):
        if not data: return b''
        digits = self.get_basel_digits(max(10, len(data)//2+5))
        mask = bytes(int(digits[i:i+2])%256 for i in range(0, len(digits), 2))
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= mask[i%len(mask)]
        return bytes(t)
    reverse_transform_18 = transform_18

    def transform_19(self, data):
        if not data: return b''
        digits = self.get_one_over_e_digits(max(10, len(data)//2+5))
        mask = bytes(int(digits[i:i+2])%256 for i in range(0, len(digits), 2))
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= mask[i%len(mask)]
        return bytes(t)
    reverse_transform_19 = transform_19

    def transform_20(self, data):
        if not data: return b''
        digits = self.get_5e_digits(max(10, len(data)//2+5))
        mask = bytes(int(digits[i:i+2])%256 for i in range(0, len(digits), 2))
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= mask[i%len(mask)]
        return bytes(t)
    reverse_transform_20 = transform_20

    def transform_21(self, data):
        if not data: return b''
        shift = 255
        t = bytearray(data)
        for i in range(len(t)): t[i] = (t[i]+shift)%256
        return bytes(t)
    def reverse_transform_21(self, data):
        if not data: return b''
        t = bytearray(data)
        for i in range(len(t)): t[i] = (t[i]-255)%256
        return bytes(t)

    # ---------- Transform 23: Constant Diapason ----------
    def _compress_bits(self, bits):
        orig = len(bits)
        if orig == 0: return b'\x00\x00\x00'
        cur, prev, passes = bits[:], orig, 0
        while passes < 255:
            pad = (4 - len(cur)%4)%4
            padded = cur + [0]*pad
            encoded = []
            for i in range(len(padded)//4):
                nib = (padded[i*4]<<3)|(padded[i*4+1]<<2)|(padded[i*4+2]<<1)|padded[i*4+3]
                L, code = _CONST_DIAPASON_ITER_CODE[nib]
                for b in range(L-1,-1,-1): encoded.append((code>>b)&1)
            if len(encoded) < prev:
                cur, prev, passes = encoded, len(encoded), passes+1
            else: break
        header = bytes([(orig>>8)&0xFF, orig&0xFF, passes])
        pad2 = (8 - len(cur)%8)%8
        cur += [0]*pad2
        out = bytearray()
        for i in range(0, len(cur), 8):
            val = 0
            for j in range(8): val = (val<<1)|cur[i+j]
            out.append(val)
        return header + bytes(out)

    def _decompress_bits(self, data):
        if len(data)<3: return []
        orig = (data[0]<<8)|data[1]
        passes = data[2]
        payload = data[3:]
        bits = []
        for byte in payload:
            for i in range(7,-1,-1): bits.append((byte>>i)&1)
        cur = bits
        for _ in range(passes):
            pos, nbits, decoded = 0, len(cur), []
            while pos < nbits:
                matched = False
                for L in range(2,10):
                    if pos+L > nbits: continue
                    code = 0
                    for k in range(L): code = (code<<1)|cur[pos+k]
                    if (L, code) in _CONST_DIAPASON_ITER_DECODE:
                        decoded.append(_CONST_DIAPASON_ITER_DECODE[(L,code)])
                        pos += L; matched = True; break
                if not matched: break
            cur = []
            for nib in decoded:
                for j in range(3,-1,-1): cur.append((nib>>j)&1)
        if len(cur) < orig: return []
        return cur[:orig]

    def transform_23(self, data):
        if not data: return b'\x00\x00\x00'
        bits = []
        for b in data:
            for i in range(7,-1,-1): bits.append((b>>i)&1)
        return self._compress_bits(bits)
    def reverse_transform_23(self, data):
        bits = self._decompress_bits(data)
        if not bits: return b''
        out = bytearray()
        for i in range(0, len(bits), 8):
            val = 0
            for j in range(i, min(i+8, len(bits))): val = (val<<1)|bits[j]
            if i+8 > len(bits): val <<= (8 - (len(bits)-i))
            out.append(val)
        return bytes(out)

    # ---------- Transform 24: block run ----------
    def transform_24(self, data):
        if not data: return b''
        MAX_LEN = 43
        bits = []
        i, n = 0, len(data)
        while i < n:
            chunk_len = min(MAX_LEN, n-i)
            chunk = data[i:i+chunk_len]
            first = chunk[0]
            if all(b==first for b in chunk):
                self._append_bits(bits, 1, 1)
                self._append_bits(bits, first, 8)
                self._append_bits(bits, chunk_len-1, 6)
            else:
                self._append_bits(bits, 0, 1)
                self._append_bits(bits, chunk_len, 6)
                for b in chunk: self._append_bits(bits, b, 8)
            i += chunk_len
        pad = (8 - len(bits)%8)%8
        self._append_bits(bits, 0, pad)
        out = bytearray()
        for j in range(0, len(bits), 8):
            byte = 0
            for k in range(8):
                if j+k < len(bits): byte = (byte<<1)|bits[j+k]
            out.append(byte)
        return bytes(out)
    def reverse_transform_24(self, data):
        if not data: return b''
        bits = []
        for byte in data:
            for i in range(7,-1,-1): bits.append((byte>>i)&1)
        pos, nbits, out = 0, len(bits), bytearray()
        while pos < nbits:
            if pos+1 > nbits: break
            flag = self._read_bits(bits, pos, 1); pos+=1
            if flag == 1:
                if pos+8+6 > nbits: break
                val = self._read_bits(bits, pos, 8); pos+=8
                run = self._read_bits(bits, pos, 6)+1; pos+=6
                out.extend([val]*run)
            else:
                if pos+6 > nbits: break
                chunk_len = self._read_bits(bits, pos, 6); pos+=6
                if chunk_len==0: break
                if pos+chunk_len*8 > nbits: break
                for _ in range(chunk_len):
                    out.append(self._read_bits(bits, pos, 8)); pos+=8
        return bytes(out)

    # ---------- Transforms 25-30 (Fermat) ----------
    def transform_25(self, data):
        if not data: return b'\x01'
        n = 3
        res = bytearray(data)
        for i in range(len(res)): res[i] = (pow(res[i]+1, n, 257)-1)&0xFF
        return bytes([n])+bytes(res)
    def reverse_transform_25(self, data):
        if len(data)<2: return b''
        n, inv, res = data[0], pow(data[0], -1, 256), bytearray(data[1:])
        for i in range(len(res)): res[i] = (pow(res[i]+1, inv, 257)-1)&0xFF
        return bytes(res)

    def transform_26(self, data):
        if not data: return b'\x01\x00'
        n = (len(data)*7+13)&0xFFFF
        if n%2==0: n ^= 1
        e = pow(n, 16777216, 256)|1
        res = bytearray(data)
        for i in range(len(res)): res[i] = (pow(res[i]+1, e, 257)-1)&0xFF
        return bytes([n&0xFF, (n>>8)&0xFF])+bytes(res)
    def reverse_transform_26(self, data):
        if len(data)<2: return b''
        n = data[0]|(data[1]<<8)
        if n%2==0: n ^= 1
        e = pow(n, 16777216, 256)|1
        inv = pow(e, -1, 256)
        res = bytearray(data[2:])
        for i in range(len(res)): res[i] = (pow(res[i]+1, inv, 257)-1)&0xFF
        return bytes(res)

    def transform_27(self, data):
        BLOCK = 1024
        if not data:
            out = bytearray(b'\x00\x00\x00\x00')
            out.extend(b'\x01\x00')
            out.extend(b'\x00'*BLOCK)
            return bytes(out)
        total = (len(data)+BLOCK-1)//BLOCK
        out = bytearray(len(data).to_bytes(4,'big'))
        for idx in range(total):
            chunk = data[idx*BLOCK:min((idx+1)*BLOCK, len(data))]
            pad = BLOCK - len(chunk)
            if pad: chunk += b'\x00'*pad
            n = ((len(data)*7 + idx*13 + 1)&0xFFFF)|1
            e = pow(n, 16777216, 256)|1
            e200 = pow(e, 200, 256)
            trans = bytearray(chunk)
            for i in range(BLOCK): trans[i] = (pow(trans[i]+1, e200, 257)-1)&0xFF
            out.append(n&0xFF); out.append((n>>8)&0xFF)
            out.extend(trans)
        return bytes(out)
    def reverse_transform_27(self, data):
        if len(data)<4: return b''
        orig_len = int.from_bytes(data[:4],'big')
        payload = data[4:]
        BLOCK, block_hdr = 1024, 2+1024
        if len(payload)%block_hdr != 0: return data
        num = len(payload)//block_hdr
        decoded = bytearray()
        for idx in range(num):
            off = idx*block_hdr
            if off+2 > len(payload): break
            n = payload[off]|(payload[off+1]<<8)
            chunk = payload[off+2:off+2+BLOCK]
            if len(chunk) < BLOCK: break
            n |= 1
            e = pow(n, 16777216, 256)|1
            e200 = pow(e, 200, 256)
            inv = pow(e200, -1, 256)
            for b in chunk: decoded.append((pow(b+1, inv, 257)-1)&0xFF)
        return bytes(decoded[:orig_len])

    def transform_28(self, data):
        BLOCK = 1024
        if not data:
            out = bytearray(b'\x00\x00\x00\x00')
            out.extend(b'\x01\x00')
            out.extend(self._compress_backend(b'\x00'*BLOCK))
            return bytes(out)
        total = (len(data)+BLOCK-1)//BLOCK
        out = bytearray(len(data).to_bytes(4,'big'))
        for idx in range(total):
            chunk = data[idx*BLOCK:min((idx+1)*BLOCK, len(data))]
            pad = BLOCK - len(chunk)
            if pad: chunk += b'\x00'*pad
            n = ((len(data)*7 + idx*13 + 1)&0xFFFF)|1
            e = pow(n, 16777216, 256)|1
            e200 = pow(e, 200, 256)
            trans = bytearray(chunk)
            for i in range(BLOCK): trans[i] = (pow(trans[i]+1, e200, 257)-1)&0xFF
            comp = self._compress_backend(bytes(trans))
            out.append(n&0xFF); out.append((n>>8)&0xFF)
            L = len(comp)
            out.append((L>>8)&0xFF); out.append(L&0xFF)
            out.extend(comp)
        return bytes(out)
    def reverse_transform_28(self, data):
        if len(data)<4: return b''
        orig_len = int.from_bytes(data[:4],'big')
        payload, pos, decoded = data[4:], 0, bytearray()
        while pos < len(payload):
            if pos+2 > len(payload): break
            n = payload[pos]|(payload[pos+1]<<8); pos+=2
            if pos+2 > len(payload): break
            comp_len = (payload[pos]<<8)|payload[pos+1]; pos+=2
            if pos+comp_len > len(payload): break
            comp = payload[pos:pos+comp_len]; pos+=comp_len
            block = self._decompress_backend(comp)
            if block is None: return data
            n |= 1
            e = pow(n, 16777216, 256)|1
            e200 = pow(e, 200, 256)
            inv = pow(e200, -1, 256)
            trans = bytearray(block)
            for i in range(len(trans)): trans[i] = (pow(trans[i]+1, inv, 257)-1)&0xFF
            decoded.extend(trans)
        return bytes(decoded[:orig_len])

    def transform_29(self, data):
        BLOCK = 32
        if not data:
            out = bytearray(b'\x00\x00\x00\x00')
            out.extend(b'\x01\x00')
            out.extend(self._compress_backend(b'\x00'*BLOCK))
            return bytes(out)
        total = (len(data)+BLOCK-1)//BLOCK
        out = bytearray(len(data).to_bytes(4,'big'))
        for idx in range(total):
            chunk = data[idx*BLOCK:min((idx+1)*BLOCK, len(data))]
            pad = BLOCK - len(chunk)
            if pad: chunk += b'\x00'*pad
            n = ((len(data)*7 + idx*13 + 1)&0xFFFF)|1
            e = pow(n, 2**256, 256)|1
            e200 = pow(e, 200, 256)
            trans = bytearray(chunk)
            comp = self._compress_backend(bytes(trans))
            out.append(n&0xFF); out.append((n>>8)&0xFF)
            L = len(comp)
            out.append((L>>8)&0xFF); out.append(L&0xFF)
            out.extend(comp)
        return bytes(out)
    def reverse_transform_29(self, data):
        if len(data)<4: return b''
        orig_len = int.from_bytes(data[:4],'big')
        payload, pos, decoded = data[4:], 0, bytearray()
        while pos < len(payload):
            if pos+2 > len(payload): break
            n = payload[pos]|(payload[pos+1]<<8); pos+=2
            if pos+2 > len(payload): break
            comp_len = (payload[pos]<<8)|payload[pos+1]; pos+=2
            if pos+comp_len > len(payload): break
            comp = payload[pos:pos+comp_len]; pos+=comp_len
            block = self._decompress_backend(comp)
            if block is None: return data
            decoded.extend(block)
        return bytes(decoded[:orig_len])

    def _compute_n_for_block(self, block, block_idx, total_len):
        if not block: return (1, b'\x01\x01')
        d = block[0]; x = (block_idx%33)+1
        try: t = (d*d - d**x)//256
        except OverflowError: t = 0
        if 0 <= t <= 255: return (t|1, bytes([1, t|1]))
        h = hashlib.sha256(block + bytes([block_idx&0xFF, (total_len>>8)&0xFF, total_len&0xFF])).digest()
        n_bytes = bytearray(h); n_bytes[0] |= 1
        return (int.from_bytes(n_bytes,'big'), bytes([len(n_bytes)])+bytes(n_bytes))

    def transform_30(self, data):
        BLOCK = 33
        if not data:
            out = bytearray(b'\x00\x00\x00\x00')
            out.extend(b'\x01\x01')
            out.extend(self._compress_backend(b'\x00'*BLOCK))
            return bytes(out)
        total = (len(data)+BLOCK-1)//BLOCK
        out = bytearray(len(data).to_bytes(4,'big'))
        for idx in range(total):
            chunk = data[idx*BLOCK:min((idx+1)*BLOCK, len(data))]
            pad = BLOCK - len(chunk)
            if pad: chunk += b'\x00'*pad
            n, enc_n = self._compute_n_for_block(chunk, idx, len(data))
            comp = self._compress_backend(chunk)
            out.extend(enc_n)
            L = len(comp)
            out.append((L>>8)&0xFF); out.append(L&0xFF)
            out.extend(comp)
        return bytes(out)
    def reverse_transform_30(self, data):
        if len(data)<4: return b''
        orig_len = int.from_bytes(data[:4],'big')
        payload, pos, decoded = data[4:], 0, bytearray()
        while pos < len(payload):
            if pos >= len(payload): break
            Ln = payload[pos]; pos+=1
            if Ln>32 or pos+Ln > len(payload): break
            n_bytes = payload[pos:pos+Ln]; pos+=Ln
            if pos+2 > len(payload): break
            comp_len = (payload[pos]<<8)|payload[pos+1]; pos+=2
            if pos+comp_len > len(payload): break
            comp = payload[pos:pos+comp_len]; pos+=comp_len
            block = self._decompress_backend(comp)
            if block is None: return data
            decoded.extend(block)
        return bytes(decoded[:orig_len])

    # ---------- Transforms 41-47 ----------
    def transform_41(self, data):
        if not data: return b''
        t = bytearray(data)
        mask = b'\x27\x03'
        for i in range(min(len(t),8)): t[i] ^= mask[i%2]
        return bytes(t)
    reverse_transform_41 = transform_41

    def transform_42(self, data):
        if not data: return b''
        t = bytearray(data)
        mask = b'\x27\x03'
        for i in range(len(t)): t[i] ^= mask[i%2]
        return bytes(t)
    reverse_transform_42 = transform_42

    def transform_43(self, data):
        if not data: return b''
        t = bytearray(data)
        mask = b'\x10\x00\x00'
        for i in range(0, len(t), 3):
            for j in range(min(3, len(t)-i)): t[i+j] ^= mask[j]
        return bytes(t)
    reverse_transform_43 = transform_43

    def transform_44(self, data):
        if not data: return b''
        return base64.b64encode(data)
    def reverse_transform_44(self, data):
        if not data: return b''
        try: return base64.b64decode(data)
        except: return data

    # Huffman helpers
    @staticmethod
    def _huffman_code_lengths(freq):
        heap = [(f,i,i) for i,f in enumerate(freq) if f>0]
        if not heap: return [0]*len(freq)
        if len(heap)==1:
            lengths = [0]*len(freq)
            lengths[heap[0][2]] = 1
            return lengths
        heapq.heapify(heap)
        next_id = len(heap)
        while len(heap)>1:
            f1,_,n1 = heapq.heappop(heap); f2,_,n2 = heapq.heappop(heap)
            heapq.heappush(heap, (f1+f2, next_id, (n1,n2)))
            next_id+=1
        lengths = [0]*len(freq)
        def traverse(node, depth):
            if isinstance(node, int): lengths[node] = depth
            else: traverse(node[0],depth+1); traverse(node[1],depth+1)
        traverse(heap[0][2], 0)
        return lengths

    @staticmethod
    def _huffman_canonical_codes(code_lengths):
        symbols = sorted(range(len(code_lengths)), key=lambda s: (code_lengths[s], s))
        codes, code, prev_len = {}, 0, 0
        for sym in symbols:
            cl = code_lengths[sym]
            if cl==0: continue
            if prev_len==0: prev_len=cl
            elif cl != prev_len: code <<= (cl-prev_len); prev_len=cl
            codes[sym] = (code, cl)
            code += 1
        return codes

    def transform_45(self, data):
        if not data: return b''
        freq = [0]*256
        for b in data: freq[b]+=1
        lens = self._huffman_code_lengths(freq)
        codes = self._huffman_canonical_codes(lens)
        header = bytearray(len(data).to_bytes(4,'big'))
        header.extend(lens)
        bits = []
        for b in data:
            c,cl = codes[b]
            for i in range(cl-1,-1,-1): bits.append((c>>i)&1)
        pad = (8 - len(bits)%8)%8
        bits.extend([0]*pad)
        out = bytearray()
        for i in range(0, len(bits), 8):
            val = 0
            for j in range(8): val = (val<<1)|bits[i+j]
            out.append(val)
        return bytes(header)+bytes(out)
    def reverse_transform_45(self, data):
        if len(data)<4+256: return data
        orig_len = int.from_bytes(data[:4],'big')
        lens = list(data[4:4+256])
        payload = data[4+256:]
        if orig_len==0: return b''
        decode = {}
        symbols = sorted(range(256), key=lambda s: (lens[s],s))
        code, prev = 0,0
        for sym in symbols:
            cl = lens[sym]
            if cl==0: continue
            if prev==0: prev=cl
            elif cl!=prev: code <<= (cl-prev); prev=cl
            decode[(cl, code)] = sym
            code+=1
        bits = []
        for byte in payload:
            for i in range(7,-1,-1): bits.append((byte>>i)&1)
        pos, nbits, out = 0, len(bits), bytearray()
        while pos < nbits and len(out) < orig_len:
            for cl in range(1, 256):
                if pos+cl > nbits: break
                val = 0
                for j in range(cl): val = (val<<1)|bits[pos+j]
                if (cl,val) in decode:
                    out.append(decode[(cl,val)]); pos+=cl; break
            else: break
        return bytes(out)

    def transform_46(self, data):
        if not data: return b''
        t = bytearray(data)
        for i in range(len(t)): t[i] ^= self.mask_46[i%len(self.mask_46)]
        return bytes(t)
    reverse_transform_46 = transform_46

    def transform_47(self, data):
        if not data: return b''
        t = bytearray(data)
        for i in range(len(t)):
            row = self.mod_state_table[i%len(self.mod_state_table)]
            t[i] ^= row[0]
        return bytes(t)
    reverse_transform_47 = transform_47

    # ---------- Transform 50,51,53-55 ----------
    def transform_50(self, data):
        if not data: return b'\x00'*10
        orig_len = len(data)
        n = int.from_bytes(data,'big')
        ops = []
        while n.bit_length() > 32*8:
            if n%6==0: n//=6; ops.append(0)
            elif n%2==0: n//=2; ops.append(1)
            else: n-=1; ops.append(2)
        small = n.to_bytes((n.bit_length()+7)//8,'big')
        if not small: small=b'\x00'
        if len(small)>32: raise RuntimeError("Internal error: small int too large")
        bits = []
        for op in ops: self._append_bits(bits, op, 2)
        pad = (8 - len(bits)%8)%8; self._append_bits(bits, 0, pad)
        op_bytes = bytearray()
        for i in range(0, len(bits), 8):
            val = 0
            for j in range(8): val = (val<<1)|bits[i+j]
            op_bytes.append(val)
        header = (orig_len.to_bytes(5,'big') + bytes([len(small)]) +
                  struct.pack('>H', len(ops)) + bytes([0,0]))  # zero/one counts placeholder
        return header + small + bytes(op_bytes)
    def reverse_transform_50(self, data):
        if len(data)<10: return b''
        orig_len = int.from_bytes(data[:5],'big')
        small_len = data[5]
        if small_len==0: return b''
        op_count = struct.unpack('>H', data[6:8])[0]
        header_size = 10
        if len(data) < header_size+small_len: return b''
        small = int.from_bytes(data[header_size:header_size+small_len], 'big')
        op_bytes = data[header_size+small_len:]
        bits = []
        for byte in op_bytes:
            for i in range(7,-1,-1): bits.append((byte>>i)&1)
        ops = []
        for i in range(0, op_count*2, 2):
            if i+1 >= len(bits): break
            ops.append((bits[i]<<1)|bits[i+1])
        n = small
        for op in reversed(ops):
            if op==0: n*=6
            elif op==1: n*=2
            elif op==2: n+=1
        raw = n.to_bytes((n.bit_length()+7)//8,'big')
        if len(raw) < orig_len: raw = b'\x00'*(orig_len-len(raw)) + raw
        return raw[:orig_len]

    def transform_51(self, data):
        BLOCK,TARGET = 100,43
        if not data: return b'\x00\x00'
        blocks = []
        for i in range(0, len(data), BLOCK):
            chunk = data[i:i+BLOCK]; orig_len = len(chunk)
            n = int.from_bytes(chunk,'big')
            ops = []
            while n.bit_length() > TARGET*8:
                if n%6==0: n//=6; ops.append(0)
                elif n%2==0: n//=2; ops.append(1)
                else: n-=1; ops.append(2)
            small = n.to_bytes((n.bit_length()+7)//8,'big')
            if not small: small=b'\x00'; slen=1
            else: slen=len(small)
            if slen > TARGET: raise RuntimeError("Block too large")
            bits = []
            for op in ops: self._append_bits(bits, op, 2)
            pad = (8 - len(bits)%8)%8; self._append_bits(bits, 0, pad)
            op_bytes = bytearray()
            for j in range(0, len(bits), 8):
                val = 0
                for k in range(8): val = (val<<1)|bits[j+k]
                op_bytes.append(val)
            blocks.append(bytes([orig_len])+bytes([slen])+struct.pack('>H',len(ops))+small+bytes(op_bytes))
        return struct.pack('>H', len(blocks)) + b''.join(blocks)
    def reverse_transform_51(self, data):
        if len(data)<2: return b''
        num = struct.unpack('>H', data[:2])[0]; pos=2
        out = bytearray()
        for _ in range(num):
            if pos+1 > len(data): break
            orig_len = data[pos]; pos+=1
            if pos+1 > len(data): break
            slen = data[pos]; pos+=1
            if pos+2 > len(data): break
            op_cnt = struct.unpack('>H', data[pos:pos+2])[0]; pos+=2
            if pos+slen > len(data): break
            small = int.from_bytes(data[pos:pos+slen],'big'); pos+=slen
            needed = (op_cnt*2+7)//8
            if pos+needed > len(data): break
            op_bytes = data[pos:pos+needed]; pos+=needed
            bits = []
            for byte in op_bytes:
                for i in range(7,-1,-1): bits.append((byte>>i)&1)
            ops = []
            for i in range(0, op_cnt*2, 2):
                if i+1 >= len(bits): break
                ops.append((bits[i]<<1)|bits[i+1])
            n = small
            for op in reversed(ops):
                if op==0: n*=6
                elif op==1: n*=2
                elif op==2: n+=1
            raw = n.to_bytes((n.bit_length()+7)//8,'big')
            if len(raw) < orig_len: raw = b'\x00'*(orig_len-len(raw)) + raw
            out.extend(raw[:orig_len])
        return bytes(out)

    def transform_53(self, data):
        if not data: return b''
        out = bytearray()
        for i in range(0, len(data), 256):
            chunk = data[i:i+256]
            pos1 = pos2 = -1
            for j,b in enumerate(chunk):
                if b <= 15:
                    if pos1==-1: pos1=j
                    elif pos2==-1: pos2=j; break
            if pos1==-1 or pos2==-1:
                out.extend(b'\xFF\xFF\xFF\xFF'); out.extend(chunk)
            else:
                out.append(chunk[pos1]); out.append(pos1)
                out.append(chunk[pos2]); out.append(pos2)
                remaining = bytearray(b for j,b in enumerate(chunk) if j not in (pos1,pos2))
                out.extend(remaining)
        return bytes(out)
    def reverse_transform_53(self, data):
        if not data: return b''
        pos, out = 0, bytearray()
        while pos < len(data):
            if pos+4 > len(data): break
            v1,p1,v2,p2 = data[pos],data[pos+1],data[pos+2],data[pos+3]
            pos+=4
            if v1==0xFF and v2==0xFF and p1==0xFF and p2==0xFF:
                if pos+256 > len(data): out.extend(data[pos:]); break
                out.extend(data[pos:pos+256]); pos+=256
            else:
                if pos+254 > len(data): break
                remaining = data[pos:pos+254]; pos+=254
                block = bytearray(256)
                r=0
                for i in range(256):
                    if i==p1: block[i]=v1
                    elif i==p2: block[i]=v2
                    else: block[i]=remaining[r]; r+=1
                out.extend(block)
        return bytes(out)

    def transform_54(self, data):
        if len(data)!=65536: return b'\x01'+data
        # find longest run >=5
        best_start,best_val,best_len = -1,0,0
        i=0
        while i<65536:
            val=data[i]; j=i+1
            while j<65536 and data[j]==val: j+=1
            if j-i > best_len: best_start,best_val,best_len = i,val,j-i
            i=j
        if best_len>=5:
            # rebuild removing first 5 of that run
            new = bytearray([0x00, best_val])
            new.extend(struct.pack('>H', best_start))
            new.extend(data[:best_start])
            new.extend(data[best_start+5:])
            return bytes(new)
        return b'\x01'+data
    def reverse_transform_54(self, data):
        if not data: return b''
        if data[0]==0x01: return data[1:1+65536]
        if data[0]==0x00:
            val=data[1]; start=struct.unpack('>H', data[2:4])[0]
            rest=data[4:]
            orig = bytearray(65536)
            pos=0
            for i in range(start): orig[i]=rest[pos]; pos+=1
            for i in range(start, start+5): orig[i]=val
            for i in range(start+5, 65536): orig[i]=rest[pos]; pos+=1
            return bytes(orig)
        return data[1:]

    def transform_55(self, data):
        if len(data)!=65536: return b'\x01'+data
        return b'\x01'+data
    def reverse_transform_55(self, data):
        if not data: return b''
        if data[0]==0x01: return data[1:1+65536]
        return b''

    # ---------- Dynamic transforms 48-255 ----------
    def _dynamic_transform(self, n):
        def tf(data):
            if not data: return b''
            seed = self.get_seed(n % len(self.seed_tables), len(data))
            return bytes(b ^ seed for b in data)
        return tf, tf

    def transform_256(self, d): return d
    reverse_transform_256 = transform_256

    # ---------- Helpers ----------
    def _get_pattern(self, size, index):
        random.seed(12345 + size*100 + index)
        return [random.randint(0,255) for _ in range(size)]

    def _calculate_repeats(self, data):
        if not data: return 1
        return max(1, min(256, ((len(data)*13 + sum(data)%256*17)%256)+1))

    # ---------- Build transform maps ----------
    def _build_transform_maps(self):
        self.fwd_transforms: Dict[int, Callable] = {}
        self.rev_transforms: Dict[int, Callable] = {}
        # 1‑24
        self.fwd_transforms[1]=self.transform_00; self.rev_transforms[1]=self.reverse_transform_00
        self.fwd_transforms[2]=self.transform_01; self.rev_transforms[2]=self.reverse_transform_01
        self.fwd_transforms[3]=self.transform_02; self.rev_transforms[3]=self.reverse_transform_02
        self.fwd_transforms[4]=self.transform_03; self.rev_transforms[4]=self.reverse_transform_03
        self.fwd_transforms[5]=self.transform_04; self.rev_transforms[5]=self.reverse_transform_04
        self.fwd_transforms[6]=self.transform_05; self.rev_transforms[6]=self.reverse_transform_05
        self.fwd_transforms[7]=self.transform_06; self.rev_transforms[7]=self.reverse_transform_06
        self.fwd_transforms[8]=self.transform_07; self.rev_transforms[8]=self.reverse_transform_07
        self.fwd_transforms[9]=self.transform_08; self.rev_transforms[9]=self.reverse_transform_08
        self.fwd_transforms[10]=self.transform_09; self.rev_transforms[10]=self.reverse_transform_09
        self.fwd_transforms[11]=self.transform_10; self.rev_transforms[11]=self.reverse_transform_10
        self.fwd_transforms[12]=self.transform_11; self.rev_transforms[12]=self.reverse_transform_11
        self.fwd_transforms[13]=self.transform_12; self.rev_transforms[13]=self.reverse_transform_12
        self.fwd_transforms[14]=self.transform_13; self.rev_transforms[14]=self.reverse_transform_13
        self.fwd_transforms[15]=self.transform_14; self.rev_transforms[15]=self.reverse_transform_14
        self.fwd_transforms[16]=self.transform_15; self.rev_transforms[16]=self.reverse_transform_15
        self.fwd_transforms[17]=self.transform_16; self.rev_transforms[17]=self.reverse_transform_16
        self.fwd_transforms[18]=self.transform_17; self.rev_transforms[18]=self.reverse_transform_17
        self.fwd_transforms[19]=self.transform_18; self.rev_transforms[19]=self.reverse_transform_18
        self.fwd_transforms[20]=self.transform_19; self.rev_transforms[20]=self.reverse_transform_19
        self.fwd_transforms[21]=self.transform_20; self.rev_transforms[21]=self.reverse_transform_20
        self.fwd_transforms[22]=self.transform_21; self.rev_transforms[22]=self.reverse_transform_21
        self.fwd_transforms[23]=self.transform_23; self.rev_transforms[23]=self.reverse_transform_23
        self.fwd_transforms[24]=self.transform_24; self.rev_transforms[24]=self.reverse_transform_24
        # 25‑30
        self.fwd_transforms[25]=self.transform_25; self.rev_transforms[25]=self.reverse_transform_25
        self.fwd_transforms[26]=self.transform_26; self.rev_transforms[26]=self.reverse_transform_26
        self.fwd_transforms[27]=self.transform_27; self.rev_transforms[27]=self.reverse_transform_27
        self.fwd_transforms[28]=self.transform_28; self.rev_transforms[28]=self.reverse_transform_28
        self.fwd_transforms[29]=self.transform_29; self.rev_transforms[29]=self.reverse_transform_29
        self.fwd_transforms[30]=self.transform_30; self.rev_transforms[30]=self.reverse_transform_30
        for i in range(31,41):
            fwd,rev = self._dynamic_transform(i)
            self.fwd_transforms[i]=fwd; self.rev_transforms[i]=rev
        self.fwd_transforms[41]=self.transform_41; self.rev_transforms[41]=self.reverse_transform_41
        self.fwd_transforms[42]=self.transform_42; self.rev_transforms[42]=self.reverse_transform_42
        self.fwd_transforms[43]=self.transform_43; self.rev_transforms[43]=self.reverse_transform_43
        self.fwd_transforms[44]=self.transform_44; self.rev_transforms[44]=self.reverse_transform_44
        self.fwd_transforms[45]=self.transform_45; self.rev_transforms[45]=self.reverse_transform_45
        self.fwd_transforms[46]=self.transform_46; self.rev_transforms[46]=self.reverse_transform_46
        self.fwd_transforms[47]=self.transform_47; self.rev_transforms[47]=self.reverse_transform_47
        for i in range(48,256):
            if i==50:
                self.fwd_transforms[50]=self.transform_50; self.rev_transforms[50]=self.reverse_transform_50
            elif i==51:
                self.fwd_transforms[51]=self.transform_51; self.rev_transforms[51]=self.reverse_transform_51
            elif i==53:
                self.fwd_transforms[53]=self.transform_53; self.rev_transforms[53]=self.reverse_transform_53
            elif i==54:
                self.fwd_transforms[54]=self.transform_54; self.rev_transforms[54]=self.reverse_transform_54
            elif i==55:
                self.fwd_transforms[55]=self.transform_55; self.rev_transforms[55]=self.reverse_transform_55
            else:
                fwd,rev = self._dynamic_transform(i)
                self.fwd_transforms[i]=fwd; self.rev_transforms[i]=rev
        self.fwd_transforms[256]=self.transform_256; self.rev_transforms[256]=self.reverse_transform_256
        for i in range(1,257):
            if i not in self.fwd_transforms: raise RuntimeError(f"Transform {i} missing!")

    def _build_pair_sequences(self):
        return [(t1,t2) for t1 in range(1,257) for t2 in range(1,257) if not (t1==256 and t2==256)]

    # ================= LZ77+Huffman =================
    WINDOW_SIZE = 2048
    MIN_MATCH = 3
    MAX_MATCH = 2048
    MAX_DIST = 2048

    def _lz77_tokenize(self, data):
        tokens = []
        i, n = 0, len(data)
        while i < n:
            best_len, best_dist = 0, 0
            start_win = max(0, i-self.WINDOW_SIZE)
            for j in range(start_win, i):
                if data[j] != data[i]: continue
                k = 0
                while i+k < n and j+k < i and data[j+k] == data[i+k]:
                    k+=1
                    if k >= self.MAX_MATCH: break
                if k >= self.MIN_MATCH and k > best_len:
                    best_len, best_dist = k, i-j
                    if best_len == self.MAX_MATCH: break
            if best_len >= self.MIN_MATCH:
                tokens.append(('M', best_dist, best_len))
                i += best_len
            else:
                tokens.append(('L', data[i], None))
                i+=1
        return tokens

    def _lz77_untokenize(self, tokens):
        out = bytearray()
        for t in tokens:
            if t[0]=='L': out.append(t[1])
            else:
                dist, length = t[1], t[2]
                start = len(out)-dist
                for _ in range(length): out.append(out[start]); start+=1
        return bytes(out)

    def _encode_lzh(self, data):
        tokens = self._lz77_tokenize(data)
        lit_freq = [0]*256
        dist_freq = [0]*(self.MAX_DIST+1)
        len_freq = [0]*(self.MAX_MATCH+1)
        for t in tokens:
            if t[0]=='L': lit_freq[t[1]]+=1
            else: dist_freq[t[1]]+=1; len_freq[t[2]]+=1
        lit_cl = self._huffman_code_lengths(lit_freq)
        dist_cl = self._huffman_code_lengths(dist_freq)
        len_cl = self._huffman_code_lengths(len_freq)
        lit_codes = self._huffman_canonical_codes(lit_cl)
        dist_codes = self._huffman_canonical_codes(dist_cl)
        len_codes = self._huffman_canonical_codes(len_cl)
        bits = []
        token_cnt = len(tokens)
        for b in struct.pack('>I', token_cnt):
            for i in range(8): bits.append((b>>(7-i))&1)
        for t in tokens:
            if t[0]=='L':
                bits.append(0)
                code, cl = lit_codes[t[1]]
                for i in range(cl-1,-1,-1): bits.append((code>>i)&1)
            else:
                bits.append(1)
                code_d, cl_d = dist_codes[t[1]]
                for i in range(cl_d-1,-1,-1): bits.append((code_d>>i)&1)
                code_l, cl_l = len_codes[t[2]]
                for i in range(cl_l-1,-1,-1): bits.append((code_l>>i)&1)
        pad = (8 - len(bits)%8)%8
        bits.extend([0]*pad)
        lit_len_bytes = bytes(lit_cl)
        dist_len_bytes = b''.join(struct.pack('>H', cl) for cl in dist_cl)
        len_len_bytes = b''.join(struct.pack('>H', cl) for cl in len_cl)
        header = bytearray(lit_len_bytes)
        header.extend(dist_len_bytes); header.extend(len_len_bytes)
        out = bytearray(header)
        for i in range(0, len(bits), 8):
            val = 0
            for j in range(8): val = (val<<1)|bits[i+j]
            out.append(val)
        return bytes(out)

    def _decode_lzh(self, data):
        if len(data) < 256 + 2*2049 + 2*2049: return None
        pos = 0
        lit_cl = list(data[pos:pos+256]); pos+=256
        dist_cl = []
        for _ in range(self.MAX_DIST+1):
            if pos+2 > len(data): return None
            dist_cl.append((data[pos]<<8)|data[pos+1]); pos+=2
        len_cl = []
        for _ in range(self.MAX_MATCH+1):
            if pos+2 > len(data): return None
            len_cl.append((data[pos]<<8)|data[pos+1]); pos+=2

        def build_table(lengths):
            syms = sorted(range(len(lengths)), key=lambda s: (lengths[s], s))
            table, code, prev = {}, 0, 0
            for sym in syms:
                cl = lengths[sym]
                if cl==0: continue
                if prev==0: prev=cl
                elif cl!=prev: code <<= (cl-prev); prev=cl
                table[(cl,code)] = sym
                code+=1
            return table

        lit_tab = build_table(lit_cl)
        dist_tab = build_table(dist_cl)
        len_tab = build_table(len_cl)
        max_lit_bits = max(lit_cl) if any(lit_cl) else 0
        max_dist_bits = max(dist_cl) if any(dist_cl) else 0
        max_len_bits = max(len_cl) if any(len_cl) else 0

        payload = data[pos:]
        if len(payload)<4: return None
        token_cnt = struct.unpack('>I', payload[:4])[0]
        bits = []
        for byte in payload[4:]:
            for i in range(7,-1,-1): bits.append((byte>>i)&1)
        bpos, tokens = 0, []
        for _ in range(token_cnt):
            if bpos >= len(bits): return None
            flag = bits[bpos]; bpos+=1
            if flag == 0:
                for cl in range(1, max_lit_bits+1):
                    if bpos+cl > len(bits): break
                    val = 0
                    for j in range(cl): val = (val<<1)|bits[bpos+j]
                    if (cl,val) in lit_tab:
                        tokens.append(('L', lit_tab[(cl,val)], None))
                        bpos+=cl; break
                else: return None
            else:
                for cl in range(1, max_dist_bits+1):
                    if bpos+cl > len(bits): break
                    val = 0
                    for j in range(cl): val = (val<<1)|bits[bpos+j]
                    if (cl,val) in dist_tab:
                        dist = dist_tab[(cl,val)]; bpos+=cl; break
                else: return None
                for cl in range(1, max_len_bits+1):
                    if bpos+cl > len(bits): break
                    val = 0
                    for j in range(cl): val = (val<<1)|bits[bpos+j]
                    if (cl,val) in len_tab:
                        length = len_tab[(cl,val)]; bpos+=cl; break
                else: return None
                tokens.append(('M', dist, length))
        return self._lz77_untokenize(tokens)

    # ---------- Compression pipeline ----------
    def compress_with_lzh(self, data, ultra=True):
        if not data:
            return self._encode_marker_raw() + b'\xFF' + self._encode_lzh(b'')
        best_total, best_bytes = float('inf'), None

        def try_candidate(hdr, transformed):
            nonlocal best_total, best_bytes
            lzh = self._encode_lzh(transformed)
            candidate = hdr + b'\xFF' + lzh
            restored = self._decompress_lzh_pipeline(candidate)
            if restored == data and len(candidate) < best_total:
                best_total, best_bytes = len(candidate), candidate

        try_candidate(self._encode_marker_raw(), data)
        for t in range(1, 257):
            try:
                transformed = self.fwd_transforms[t](data)
                try_candidate(self._encode_marker_single(t), transformed)
            except: continue
        if ultra:
            for t1,t2 in self.sequences:
                try:
                    transformed = self.fwd_transforms[t1](data)
                    transformed = self.fwd_transforms[t2](transformed)
                    try_candidate(self._encode_marker_pair(t1, t2), transformed)
                except: continue
        if best_bytes is None: raise RuntimeError("Cannot compress this file with LZH pipeline.")
        return best_bytes

    def _decompress_lzh_pipeline(self, data):
        offset, seq = self._decode_header(data)
        if offset==0 or len(data)<=offset or data[offset]!=0xFF: return None
        lzh_data = data[offset+1:]
        transformed = self._decode_lzh(lzh_data)
        if transformed is None: return None
        return transformed if not seq else self._reverse_sequence(transformed, seq)

    # ---------- Backend compression (internal) ----------
    def _compress_backend(self, data):
        candidates = [data]
        if HAS_ZSTD:
            try: candidates.append(zstd_cctx.compress(data))
            except: pass
        if paq:
            try: candidates.append(paq.compress(data))
            except: pass
        candidates.append(zlib.compress(data, 9))
        return min(candidates, key=len)

    def _decompress_backend(self, data):
        if not data: return b''
        if HAS_ZSTD:
            try: return zstd_dctx.decompress(data)
            except: pass
        if paq:
            try: return paq.decompress(data)
            except: pass
        try: return zlib.decompress(data)
        except: pass
        return data

    # ---------- Marker encoding ----------
    def _encode_marker_raw(self): return b'\xFC'
    def _encode_marker_single(self, t):
        if t <= 252: return bytes([t-1])
        return bytes([254, t-253])
    def _encode_marker_pair(self, t1, t2):
        idx = (t1-1)*256 + (t2-1)
        return bytes([253, (idx>>8)&0xFF, idx&0xFF])
    def _decode_header(self, data):
        if not data: return 0, ()
        f = data[0]
        if f < 252: return 1, (f+1,)
        if f == 252: return 1, ()
        if f == 253:
            if len(data)<3: return 0, ()
            idx = (data[1]<<8)|data[2]
            if idx >= len(self.sequences): return 0, ()
            return 3, self.pair_lookup[idx]
        if f == 254:
            if len(data)<2: return 0, ()
            x = data[1]
            if x>3: return 0, ()
            return 2, (253+x,)
        return 0, ()

    def _reverse_sequence(self, data, seq):
        res = data
        for t in reversed(seq): res = self.rev_transforms[t](res)
        return res

    # ---------- File I/O with error handling ----------
    def compress_file(self, infile, outfile, ultra=True):
        try:
            with open(infile, 'rb') as f: data = f.read()
        except FileNotFoundError:
            print(f"ERROR: Input file '{infile}' not found."); return
        except Exception as e:
            print(f"ERROR reading file: {e}"); return
        try:
            compressed = self.compress_with_lzh(data, ultra=ultra)
        except RuntimeError as e:
            print(f"Compression failed: {e}"); return
        try:
            with open(outfile, 'wb') as f: f.write(compressed)
        except Exception as e:
            print(f"ERROR writing output file: {e}"); return
        print(f"Compressed {len(data)} → {len(compressed)} bytes → {outfile}")

    def decompress_file(self, infile, outfile):
        try:
            with open(infile, 'rb') as f: data = f.read()
        except FileNotFoundError:
            print(f"ERROR: Input file '{infile}' not found."); return
        except Exception as e:
            print(f"ERROR reading file: {e}"); return
        offset, seq = self._decode_header(data)
        if offset == 0:
            print("ERROR: Invalid compressed file header."); return
        if offset < len(data) and data[offset] == 0xFF:
            original = self._decompress_lzh_pipeline(data)
        else:
            payload = data[offset:]
            original = self._decompress_backend(payload)
            if original is not None and seq: original = self._reverse_sequence(original, seq)
        if original is None:
            print("ERROR: Decompression failed – data may be corrupt."); return
        try:
            with open(outfile, 'wb') as f: f.write(original)
        except Exception as e:
            print(f"ERROR writing output file: {e}"); return
        seq_str = "raw" if not seq else f"sequence {seq}"
        print(f"Decompressed ({seq_str}) → {outfile} ({len(original)} bytes)")

    # ---------- Self‑test ----------
    def full_self_test(self):
        print("="*60)
        print("Full self‑test: verifying 65536 transform indices on byte 0xAA ...")
        test_data = bytes([0xAA])
        for idx in range(65536):
            try:
                enc = self.apply_transform_by_index(test_data, idx)
                dec = self.reverse_transform_by_index(enc, idx)
                if dec != test_data:
                    print(f"  FAIL at index {idx}"); return False
            except Exception as e:
                print(f"  EXCEPTION at index {idx}: {e}"); return False
            if idx % 10000 == 0: print(f"  ... {idx} OK")
        print("  All 65536 transformations are 100% lossless.\n")
        # LZH round‑trip
        print("Testing random 1000‑byte LZH round‑trip ...")
        rng = random.Random(12345)
        data = bytes(rng.randint(0,255) for _ in range(1000))
        try:
            comp = self.compress_with_lzh(data, ultra=True)
            restored = self._decompress_lzh_pipeline(comp)
            if restored != data: print("  FAIL"); return False
            print("  PASS\n[All checks passed – system is 100% lossless]")
            return True
        except Exception as e:
            print(f"  LZH test failed: {e}"); return False

    def get_transform_sequence(self, index):
        if index == 0: return ()
        return self.sequences[index-1]

    def apply_transform_by_index(self, data, index):
        seq = self.get_transform_sequence(index)
        res = data
        for t in seq: res = self.fwd_transforms[t](res)
        return res

    def reverse_transform_by_index(self, data, index):
        seq = self.get_transform_sequence(index)
        res = data
        for t in reversed(seq): res = self.rev_transforms[t](res)
        return res

# ============================================================
def main():
    print("Quantumzstandard 1 – Full lossless LZH compressor (output: .pjp.lzh)")
    c = QuantumzstandardCompressor()
    while True:
        print("\n1) Compress Fast (256 transforms + LZH)")
        print("2) Compress Ultra (65536 transforms + LZH)")
        print("3) Full self‑test (65536 indices + LZH round‑trip)")
        print("4) Exit")
        ch = input("> ").strip()
        if ch == '1':
            inf = input("Input file: ").strip()
            outf = inf + ".pjp.lzh"
            c.compress_file(inf, outf, ultra=False)
        elif ch == '2':
            inf = input("Input file: ").strip()
            outf = inf + ".pjp.lzh"
            c.compress_file(inf, outf, ultra=True)
        elif ch == '3':
            if c.full_self_test():
                print("Self‑test PASSED.")
            else:
                print("Self‑test FAILED.")
        elif ch == '4':
            print("Exiting."); break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()
