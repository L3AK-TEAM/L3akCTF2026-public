from scapy.all import IP, TCP, rdpcap
from struct import pack, unpack

r = 12
p = 0xB7E15163
q = 0x9E3779B9
xk = bytes([0xEB, 0xDA, 0x20, 0x75, 0xDE, 0x70, 0xE3, 0x10,0xE0, 0x4B, 0x46, 0x7B, 0x75, 0x8C, 0x6D, 0x04])
def u(x):
    return x & 0xFFFFFFFF

def rol(x, n):
    n &= 31
    return u((x << n) | (x >> ((32 - n) & 31)))

def ror(x, n):
    n &= 31
    return u((x >> n) | (x << ((32 - n) & 31)))

def ks(k):
    l = list(unpack("<IIII", k))
    s = [p]
    for _ in range(1, 2 * (r + 1)):
        s.append(u(s[-1] + q))

    a = b = i = j = 0
    for _ in range(3 * len(s)):
        a = s[i] = rol(u(s[i] + a + b), 3)
        b = l[j] = rol(u(l[j] + a + b), a + b)
        i = (i + 1) % len(s)
        j = (j + 1) % len(l)
    return s

def rc5(x, s):
    a, b = unpack("<II", x)
    for i in range(r, 0, -1):
        b = ror(u(b - s[2 * i + 1]), a) ^ a
        a = ror(u(a - s[2 * i]), b) ^ b
    return pack("<II", u(a - s[0]), u(b - s[1]))

def xtea(x):
    a, b = unpack(">II", x)
    k = list(unpack(">IIII", xk))
    d = 0x9E3779B9
    sm = 0xC6EF3720
    for _ in range(32):
        b = u(b - (u(((a << 4) ^ (a >> 5)) + a) ^ u(sm + k[(sm >> 11) & 3])))
        sm = u(sm - d)
        a = u(a - (u(((b << 4) ^ (b >> 5)) + b) ^ u(sm + k[sm & 3])))
    return pack(">II", a, b)

def dec(x):
    k = x[:16]
    c = bytearray(x[16:])
    for i in range(0, len(c), 8):
        c[i:i + 8] = xtea(c[i:i + 8])

    s = ks(k)
    m = bytearray()
    for i in range(0, len(c), 8):
        m += rc5(c[i:i + 8], s)

    n = m[-1]
    return bytes(m[:-n]).decode()

buf = {}
for pkt in rdpcap("sniffed_chat.pcap"):
    if IP not in pkt or TCP not in pkt:
        continue

    ip = pkt[IP]
    tcp = pkt[TCP]
    data = bytes(tcp.payload)

    if not data or (tcp.sport != 13371 and tcp.dport != 13371):
        continue

    sk = (ip.src, tcp.sport, ip.dst, tcp.dport)
    if sk not in buf:
        buf[sk] = [bytearray(), set()]
    b = buf[sk][0]
    seen = buf[sk][1]
    sig = (tcp.seq, len(data), data[:16])
    if sig in seen:
        continue

    seen.add(sig)
    b += data

    while len(b) >= 4:
        n = unpack(">I", b[:4])[0]
        if n < 24 or n > 4096:
            del b[0]
            continue
        if len(b) < n + 4:
            break

        msg = dec(bytes(b[4:n + 4]))
        b[:n + 4] = b""
        print(f"{msg}")
