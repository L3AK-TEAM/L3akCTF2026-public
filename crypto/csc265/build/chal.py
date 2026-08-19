from Crypto.Cipher import AES
from Crypto.Util.number import *
from hashlib import sha256
import os
from sage.all import *
from secrets import randbelow, choice

#https://std.neuromancer.sk/nist/P-256
p = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
K = GF(p)
a = K(0xffffffff00000001000000000000000000000000fffffffffffffffffffffffc)
b = K(0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b)
E = EllipticCurve(K, (a, b))
G = E(0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296, 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5)
E.set_order(0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551 * 0x1)

ln2 = 0.69314718056


N = 32
M = 12*32
k = int(round(ln2*12))
SHARES_NEEDED = M//4
alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
SECRET = ''.join([choice(alphabet) for i in range(N)]).encode()

def hash_index(m, ind, mod=M):
    return bytes_to_long(sha256(str(ind).encode()+m).digest())%mod

def get_indices(m):
    available = list(range(M))
    res = []
    for i in range(k):
        j = hash_index(m, i, len(available))
        res.append(available.pop(j))
    return res

def hash_element(m):
    return sha256(m).digest()[:16]

def xor(a, b):
    assert len(a)==len(b)
    return bytes([i^j for i, j in zip(a, b)])

class SSS():
    def __init__(self, sk):
        self.p = 0x100000000000000000000000000000033
        self.sk = sk
        self.shares_needed = SHARES_NEEDED
        self.poly = [bytes_to_long(sk)]+[bytes_to_long(os.urandom(16)) for i in range(self.shares_needed-1)]
        self.counter = 0
    def get_share(self):
        self.counter+=1
        return long_to_bytes(sum(pow(self.counter, i, self.p)*self.poly[i] for i in range(len(self.poly)))%self.p, blocksize=16)

class GBF():
    def __init__(self, S):
        self.S = S
        self.master_key = os.urandom(16)
        self.cipher = AES.new(self.master_key, AES.MODE_ECB)
        self.gbf = [None]*M
        self.decrypted = {}
        for x in S:
            #print(x)
            emptySlot = None
            finalShare = self.cipher.encrypt(hash_element(x))
            decryptedShare = hash_element(x)
            indices = get_indices(x)
            for i in range(k):
                j = indices[i]
                #print(j)
                if self.gbf[j] is None:
                    if emptySlot is None:
                        emptySlot = j
                    else:
                        self.gbf[j] = os.urandom(16)
                        finalShare = xor(finalShare, self.gbf[j])
                        decryptedShare = xor(decryptedShare, self.gbf[j])
                else:
                    #print("Encountered already seen item!")
                    finalShare = xor(finalShare, self.gbf[j])
                    if j in self.decrypted:
                        decryptedShare = xor(decryptedShare, self.decrypted[j])
                    else:
                        decryptedShare =  xor(decryptedShare, self.gbf[j])

            self.gbf[emptySlot] = finalShare
            self.decrypted[emptySlot] = decryptedShare
        for i in range(M):
            if self.gbf[i] is None:
                self.gbf[i] = os.urandom(16)
        for cnt, x in enumerate(self.S):
            t = bytes(16)
            indices = get_indices(x)
            for i in range(k):
                j = indices[i]
                t = xor(t, self.gbf[j])
            #print(t, self.cipher.encrypt(hash_element(x)))
            assert t==self.cipher.encrypt(hash_element(x)), f"Got: {t.hex()}, Expected: {self.cipher.encrypt(hash_element(x)).hex()}, at index {cnt}."
    def print_gbf(self):
        print("Printing GBF:")
        for row in self.gbf:
            print(row.hex())
    def initiate_intersection(self):
        self.temp_key = os.urandom(16)
        self.temp_cipher = AES.new(self.temp_key, AES.MODE_ECB)
        self.sss = SSS(self.temp_key)
        self.edited = {}
        print("Follow M oblivious transfers:")
        for z in range(M):
            c = E.random_element()
            print(*c.xy())
            pk0 = E(list(map(int, input("pk0: ").split())))
            pk1 = E(list(map(int, input("pk1: ").split())))
            assert pk0+pk1==c
            r0 = randbelow(E.order())
            r1 = randbelow(E.order())
            x0, x1 = self.get_vals_for_OT(z)
            c0 = ((r0*G).xy(), xor(hash_element(str(r0*pk0).encode()), x0).hex())
            c1 = ((r1*G).xy(), xor(hash_element(str(r1*pk1).encode()), x1).hex())
            print(c0)
            print(c1)


    def get_vals_for_OT(self, index):
        x0 = self.sss.get_share()
        if index in self.decrypted:
            x1 = self.decrypted[index]
        else:
            x1 = self.gbf[index]
        x1 = self.temp_cipher.encrypt(x1)
        return (x0, x1)

    def assert_decryption(self):
        self.temp_key = os.urandom(16)
        self.temp_cipher = AES.new(self.temp_key, AES.MODE_ECB)
        self.sss = SSS(self.temp_key)
        self.edited = {}
        gbf = [self.temp_cipher.decrypt(self.get_vals_for_OT(index)[1]) for index in range(M)]
        for x in self.S:
            indices = get_indices(x)
            t = bytes(16)
            for i in range(k):
                j = indices[i]
                t = xor(t, gbf[j])
            assert t==hash_element(x)


def main():
    nonce = os.urandom(32)
    S = [str((nonce, i, SECRET[i])).encode() for i in range(len(SECRET))]
    gbf = GBF(S)
    gbf.print_gbf()
    gbf.assert_decryption()
    gbf.initiate_intersection()

    print("Here's a little hint:", hash_element(SECRET).hex(), nonce.hex())
    guess = input("What's my secret: ")
    if guess==SECRET.decode():
        print(open("flag.txt").read().strip())

if __name__=="__main__":
    main()
