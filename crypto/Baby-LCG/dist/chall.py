import os
FLAG = b"L3AK{??????????????????????????}"
class LCG:
    def __init__(self, m):
        self.a = int.from_bytes(os.urandom(16), "big") % m
        self.c = int.from_bytes(os.urandom(16), "big") % m
        self.state = int.from_bytes(os.urandom(16), "big") % m
        self.m = m
    def next(self):
        self.state = (self.a * self.state + self.c) % self.m
        return self.state
m = 115792089237316195423570985008687907853269984665640564039457584007913129640233
rng = LCG(m)
s0 = rng.next()
s1 = rng.next()
s2 = rng.next()
key = rng.next()
flag_int = int.from_bytes(FLAG, "big")
ciphertext = flag_int ^ key
print(f"m = {m}")
print(f"s0 = {s0}")
print(f"s1 = {s1}")
print(f"s2 = {s2}")
print(f"ct = {ciphertext}")