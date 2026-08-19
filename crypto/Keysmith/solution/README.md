# Keysmith Solution

## Challenge Summary
Keysmith uses a five-round version of AES-192 as a hashing construction. The server generates a random 16-byte plaintext and asks for two different 24-byte keys that produce the same result:
```
lock(plaintext, key1, 5) == lock(plaintext, key2, 5)
```

Notice that the keys must be different, and that this process has to be done for 40 plaintexts within 40 seconds. Once all 40 rounds are completed, the server sends the flag.

## The Vulnerability

AES has a 128-bit output but AES-192 has a 192-bit key, so key collisions must exist. Finding one generically would still take around `2^64` evaluations because of the birthday bound, which is nowhere near fast enough for this challenge.

The vulnerability here is the reduced round count. Five-round AES-192 still has enough structure in the round function and key schedule to build a practical differential collision attack.

## Paper Background

The challenge is based on a recent paper I found interesting, [Practical Key Collision on AES and Kiasu-BC](https://eprint.iacr.org/2025/462). 

The relevant result is section 4.2.3, "New Fixed-target-plaintext Key Collision Attack on 5-round AES-192". This section studies target-plaintext key collisions, abbreviated TPKC. In a fixed-TPKC attack, the plaintext is fixed and the attacker finds two different keys that produce the same ciphertext. This is identical to the challenge setting.

The attack fixes a key difference `Delta K` and tries to force the two encryptions to follow the following state differences:

```text
Delta K:
313156623131562a313153623131532a0000004800000000

Round 0:
Delta x0 = 313156623131562a313153623131532a
Delta y0 = 87c0bd65da9c57943ef407fa7baecdad

Round 1:
Delta x1 = 0000f900000000868d00000000e300bd
Delta y1 = 0000ae00000000dd3e00000000050031

Round 2:
Delta x2 = 00000048000000000000000000000048
Delta y2 = 00000031000000000000000000000031

Round 3:
Delta x3 = 00000000000000480000000000000000
Delta y3 = 00000000000000310000000000000000

Round 4:
Delta x4 = 00000048000000000000000000000048
Delta y4 = 00000048000000000000000000000048
```

If the pair follows this path, the final AddRoundKey cancels the remaining difference and the ciphertexts collide.

The paper's example collision uses the all-zero plaintext but the challenge gives a fresh random plaintext each round. It turns out that this does not break the attack! The differential path fixes differences between two executions, not absolute values. When the plaintext changes, the required first round key changes by `k0 = P xor x0`. The same `Delta K`, `Delta x`, and `Delta y` path can still be used. As you can see from the solver, we can simply recompute the absolute key bytes for the new plaintext.

Going a bit more in-depth into the paper, there are 2 phases to the attack outlined, an offline phase and online phase.

### 1. Offline Phase

The attack's offline phase targets four constraints:

```text
Delta x1[8]  -> Delta y1[8]
Delta x1[13] -> Delta y1[13]
Delta x1[15] -> Delta y1[15]
Delta k2[15] -> Delta SW(k2[15])
```

Here `SW` is the SubWord S-box operation in the AES key schedule. The paper derives these key-schedule relationships:

```text
x1[8]  = k0[0] xor SW(k1[4]) xor w0[8]
x1[13] = k0[1] xor SW(k1[5]) xor k0[5] xor w0[13]
x1[15] = k0[3] xor SW(k1[7]) xor k0[7] xor w0[15]
k2[15] = k1[7] xor k1[3] xor k0[15] xor k0[11]
          xor k0[7] xor k0[3] xor SW(k1[7])
```

The attack uses the degrees of freedom in `k0` and the first bytes of `k1` to build a small table of starting points, called `Tab_pre` in the paper. The offline table is very small, only 2^5 = 32 in size.

### 2. Online Phase

The online phase uses entries from `Tab_pre` and the remaining degrees of freedom in `x0` and `x1` to satisfy later active S-boxes:

```text
Delta x2[3]  -> Delta y2[3]
Delta x2[15] -> Delta y2[15]
Delta x3[7]  -> Delta y3[7]
Delta x4[3]  -> Delta y4[3]
Delta x4[15] -> Delta y4[15]
```

So basically we iterate over `Tab_pre`, fix `x0` and partial round-key values, propagate constraints through the cipher, and verify the remaining differential conditions. The outbound phase has probability about `2^-32`, so the paper gives an attack complexity of about `2^32` iterations, with memory `2^5`.

## Solver Optimizations

The paper's complexity analysis describes the rebound attack at a higher level: after the inbound table, the outbound phase has probability around `2^-32`, so one expects about `2^32` attack iterations.

The challenge however has a tight timeout of 40 seconds, so we have to make some optimizations (this is really a programming challenge disguised as a crypto challenge, I'm sorry xd):

1. We can sample only values that already satisfy many of the S-box conditions
2. We can algebraically solve two 2nd round byte constraints instead of guessing them
3. We can combine table generation and online search instead of doing the paper's offline phase separately
4. We can stop after finding one collision since there is no reason to enumerate the rest
5. We can parallelize many independent randomized searches (multithreading!)
6. We use C instead of python :) 

So, the solver is still using the paper's differential path, but it makes many optimizations. In practice, the remaining success probability per final candidate is much better than `2^-32`, and 40 rounds can be solved within mere seconds.

Flag: ``L3AK{ThE_kEYs_t0_UnL0cK1nG_AES_M@st3rY_4RE_R3se4rCh_&_P3rs3vER4nCe}``
