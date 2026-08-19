import hashlib
import json
import random
from flag import FLAG
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

P = 79
V = 4
O = 4
M = 9
N = V + O

TARGET_MESSAGE = b"What refuses to mix will eventually reveal its boundaries"

def eval_poly(poly, x):
    total = poly["const"]

    for i, c in enumerate(poly["linear"]):
        total += c * x[i]

    for i, j, c in poly["quad"]:
        total += c * x[i] * x[j]

    return total % P

def eval_public(polys, x):
    return [eval_poly(poly, x) for poly in polys]

def make_poly():
    poly = {
        "const": random.randrange(P),
        "linear": [random.randrange(P) for _ in range(N)],
        "quad": [],
    }

    for i in range(V):
        for j in range(i, V):
            poly["quad"].append([i, j, random.randrange(P)])

    for i in range(V):
        for j in range(V, N):
            poly["quad"].append([i, j, random.randrange(P)])

    return poly

def make_public_key():
    return [make_poly() for _ in range(M)]

def aes_encrypt(flag, signature):
    key = hashlib.sha256(bytes(signature)).digest()
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(pad(flag, 16)).hex()

def main():
    polys = make_public_key()

    secret_signature = [random.randrange(P) for _ in range(N)]
    target = eval_public(polys, secret_signature)

    encrypted_flag = aes_encrypt(FLAG, secret_signature)

    public = {
        "target": target,
        "polynomials": polys,
        "encrypted_flag": encrypted_flag,
    }

    Path("public.json").write_text(
        json.dumps(public, separators=(",", ":"))
    )

if __name__ == "__main__":
    main()
