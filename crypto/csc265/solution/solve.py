from Crypto.Cipher import AES
from Crypto.Util.number import *
from hashlib import sha256
import os
from sage.all import *
from secrets import randbelow
from pwn import *
import pdb
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
SHARES_NEEDED = M//4
k = int(round(ln2*12))
alphabet = b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

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


def enumerate_secrets2(nonce, E, F, M, I, fixed, known_empty, empty_slots_curr=[], index=0, seq = b''):
    print(index, seq.hex(), end='                                    \r')
    #if index==0:
    #    pdb.set_trace()
    if index==32:
        return [seq]
    if index in fixed:
        new_I = list(I)
        c, indices = fixed[index]
        seq = seq+c
        for i in indices:
            if I[i]==0:
                empty = i
                break
        else:
            return []
        if empty not in known_empty: # means that we didn't properly set up for this.
            return []
        for i in indices:
            new_I[i] = 1
        new_empty_slots_curr = list(empty_slots_curr)
        new_empty_slots_curr.append(empty)
        return enumerate_secrets2(nonce, E, F, M, new_I, fixed, known_empty, new_empty_slots_curr, index+1, seq)
    res = []
    for s in alphabet:
        x = str((nonce, index, s)).encode()
        indices = get_indices(x)
        for i in indices:
            if I[i]==0:
                empty = i
                break
        else:
            continue
        if empty in E and empty not in known_empty:
            previous_indices = indices[:indices.index(empty)]
            if any(i in empty_slots_curr for i in previous_indices):
                new_I = list(I)
                for i in indices:
                    new_I[i] = 1
                res.extend(enumerate_secrets2(nonce, E, F, M, new_I, fixed, known_empty, empty_slots_curr+[empty], index+1, seq+bytes([s])))
        elif empty in M:
            new_empty_slots_curr = list(empty_slots_curr)
            new_empty_slots_curr.append(empty)
            if not any(ind not in new_empty_slots_curr and ind in known_empty for ind in indices):
                new_I = list(I)
                for i in indices:
                    new_I[i] = 1
                res.extend(enumerate_secrets2(nonce, E, F, M, new_I, fixed, known_empty, new_empty_slots_curr, index+1, seq+bytes([s])))
    return res






def main(r):
    #r = process(['python3', './chal.py'])
    #actual = r.readline()
    #print(actual)
    print(r.readline())
    first_gbf = []
    for i in range(M):
        first_gbf.append(bytes.fromhex(r.readline().decode().strip()))
    print(r.readline())
    second_gbf = []
    shares = []
    for i in range(SHARES_NEEDED):
        c = E(list(map(int, r.readline().decode().strip().split())))
        sk = randbelow(E.order())
        pk0 = sk*G
        pk1 = c-pk0
        r.recvuntil(b'pk0: ')
        r.sendline((' '.join(list(map(str, pk0.xy())))).encode())
        r.recvuntil(b'pk1: ')
        r.sendline((' '.join(list(map(str, pk1.xy())))).encode())
        c0 = eval(r.readline().decode().strip())
        c1 = eval(r.readline().decode().strip())
        v1, v2 = c0
        shares.append(bytes_to_long(xor(bytes.fromhex(v2), hash_element(str(E(v1)*sk).encode()))))
    PR = GF(0x100000000000000000000000000000033)['x']
    poly = PR.lagrange_polynomial(list(zip(range(1, SHARES_NEEDED+1), shares)))
    cipher = AES.new(long_to_bytes(int(poly[0]), blocksize=16), AES.MODE_ECB)
    for i in range(M-SHARES_NEEDED):
        c = E(list(map(int, r.readline().decode().strip().split())))
        sk = randbelow(E.order())
        pk1 = sk*G
        pk0 = c-pk1
        r.recvuntil(b'pk0: ')
        r.sendline((' '.join(list(map(str, pk0.xy())))).encode())
        r.recvuntil(b'pk1: ')
        r.sendline((' '.join(list(map(str, pk1.xy())))).encode())
        c0 = eval(r.readline().decode().strip())
        c1 = eval(r.readline().decode().strip())
        v1, v2 = c1
        second_gbf.append(cipher.decrypt(xor(bytes.fromhex(v2), hash_element(str(E(v1)*sk).encode()))))
    definitely_empty = set()
    definitely_not_empty = set()
    for i in range(M-SHARES_NEEDED):
        if second_gbf[i]!=first_gbf[i+SHARES_NEEDED]:
            print(i, second_gbf[i].hex(), first_gbf[i+SHARES_NEEDED].hex())
            definitely_empty.add(i+SHARES_NEEDED)
        else:
            definitely_not_empty.add(i+SHARES_NEEDED)
    print(len(definitely_empty))
    r.recvuntil(b'hint: ')
    hsh, nonce = list(map(bytes.fromhex, r.readline().strip().decode().split()))
    print(hsh.hex())
    print(nonce.hex())
    fixed_indices = {}
    known_empty = {}
    for i in range(32):
        for s in alphabet:
            x = str((nonce, i, s)).encode()
            #print(x)
            h = hash_element(x)
            t = bytes(16)
            indices = get_indices(x)
            empty = None
            for z in range(k):
                j = indices[z]
                if j<SHARES_NEEDED:
                    t = xor(t, first_gbf[j])
                else:
                    t = xor(t, second_gbf[j-SHARES_NEEDED])
                    if second_gbf[j-SHARES_NEEDED]!=first_gbf[j]:
                        empty = j
                        known_empty[empty] = True
            else:
                if t==h:
                    fixed_indices[i] = bytes([s]), indices
                    for j in indices:
                        if j<SHARES_NEEDED:
                            definitely_not_empty.add(j)

    print(len(fixed_indices))
    if len(fixed_indices)<25:
        r.close()
        return False
    print(len(definitely_empty))

    print(len(definitely_not_empty))
    secrets = enumerate_secrets2(nonce, definitely_empty, definitely_not_empty, set(range(SHARES_NEEDED))-definitely_not_empty, [0]*M, fixed_indices, known_empty)
    print()
    print(secrets)
    print(len(secrets))
    SECRET = None
    for s in secrets:
        if hash_element(s)==hsh:
            SECRET=s
            break
    else:
        r.close()
        return False
    print(SECRET)
    r.sendline(SECRET)
    r.interactive()
    r.close()
    return True

if __name__=="__main__":
    while True:
        r = remote('localhost', 1337)
        try:
            if main(r):
                break
        except Exception:
            r.interactive()
