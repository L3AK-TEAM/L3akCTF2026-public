import json
import hashlib
import itertools
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

def inv_mod(a, p):
    return pow(a % p, -1, p)

def eval_poly(poly, x, p):
    total = poly["const"]

    for i, c in enumerate(poly["linear"]):
        total += c * x[i]

    for i, j, c in poly["quad"]:
        total += c * x[i] * x[j]

    return total % p

def eval_public(polys, x, p):
    return [eval_poly(poly, x, p) for poly in polys]

def solve_linear_mod(A, b, p):
    """
    Solve A x = b mod p.
    Supports rectangular overdetermined systems.
    Returns one solution, or None if inconsistent.
    """
    m = len(A)
    n = len(A[0])

    M = [row[:] + [rhs % p] for row, rhs in zip(A, b)]

    row = 0
    pivots = []

    for col in range(n):
        pivot = None

        for r in range(row, m):
            if M[r][col] % p != 0:
                pivot = r
                break

        if pivot is None:
            continue

        M[row], M[pivot] = M[pivot], M[row]

        inv = inv_mod(M[row][col], p)
        M[row] = [(x * inv) % p for x in M[row]]

        for r in range(m):
            if r != row and M[r][col] % p != 0:
                factor = M[r][col]
                M[r] = [
                    (M[r][c] - factor * M[row][c]) % p
                    for c in range(n + 1)
                ]

        pivots.append(col)
        row += 1

        if row == m:
            break

    # Check inconsistency: 0 = nonzero.
    for r in range(row, m):
        if all(M[r][c] % p == 0 for c in range(n)) and M[r][n] % p != 0:
            return None

    # Require unique oil solution for this vinegar guess.
    if len(pivots) < n:
        return None

    sol = [0] * n
    for r, col in enumerate(pivots):
        sol[col] = M[r][n] % p

    return sol

def build_linear_system(polys, vinegar, target, p, v, o):
    """
    Once vinegar variables are fixed, each polynomial becomes linear in oils.
    """
    A = []
    b = []

    base_x = list(vinegar) + [0] * o

    for poly, y in zip(polys, target):
        const_part = eval_poly(poly, base_x, p)

        coeffs = []

        for oil_idx in range(o):
            test_x = base_x[:]
            test_x[v + oil_idx] = 1

            val = eval_poly(poly, test_x, p)
            coeff = (val - const_part) % p
            coeffs.append(coeff)

        A.append(coeffs)
        b.append((y - const_part) % p)

    return A, b

def decrypt_flag(encrypted_flag, signature):
    key = hashlib.sha256(bytes(signature)).digest()
    cipher = AES.new(key, AES.MODE_ECB)
    return unpad(cipher.decrypt(bytes.fromhex(encrypted_flag)), 16)

def main():

    pub = json.loads(Path("public.json").read_text())

    p = 79
    v = 4
    o = 4
    m = 9
    n = v + o

    target = pub["target"]
    polys = pub["polynomials"]
    encrypted_flag = pub["encrypted_flag"]

    guesses = 0

    print("Brute forcing vinegar variables...")

    for vinegar in itertools.product(range(p), repeat=v):
        guesses += 1

        if guesses % 1000 == 0:
            print(f"Tried {guesses:,} vinegar guesses...")

        A, b = build_linear_system(polys, vinegar, target, p, v, o)
        oils = solve_linear_mod(A, b, p)

        if oils is None:
            continue

        sig = list(vinegar) + oils

        if len(sig) != n:
            continue

        if eval_public(polys, sig, p) != target:
            continue

        try:
            flag = decrypt_flag(encrypted_flag, sig)
        except ValueError:
            continue

        if flag.startswith(b"L3AK{") and flag.endswith(b"}"):
            print("Found valid unique signature:")
            print(sig)
            print(f"Guesses tried: {guesses:,}")
            print("Flag:")
            print(flag.decode())
            return

    print("No valid signature found")

if __name__ == "__main__":
    main()
