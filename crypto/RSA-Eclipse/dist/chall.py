from Crypto.Util.number import bytes_to_long
from secret import p, q, FLAG

assert p.bit_length() == 607
assert q.bit_length() == 521

def encrypt():
    N = p * q
    e = 65537

    m = bytes_to_long(FLAG)
    c = pow(m, e, N)

    with open("output.txt", "w") as f:
        f.write(f"N = {N}\n")
        f.write(f"e = {e}\n")
        f.write(f"c = {c}\n")

if __name__ == "__main__":
    encrypt()