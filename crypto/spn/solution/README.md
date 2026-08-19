# spn solution
### Author: kyc

We're given an encryption cipher that uses a substitution-permutation (SP)
network.

The substitution component uses the AES SBOX, which is highly nonlinear and
should prevent differential trails.

However, the permutation component has weak diffusion. In a strong SP network,
each byte affects many bytes of the next round. But in this cipher, each round i
involves only a simple bitwise rotation by i. A change in one byte affects at
most two bytes of the next round. Sometimes that single bit doesn't affect all
bytes even after all 25 rounds, which makes this cipher very exploitable.

To actually exploit it, we can play around with the differentials. Suppose we
have two messages, M1 and M2, that differ only in the last byte:
```
M1
(byte 0)       ... (byte 15)
(b0) (b1) (b2) ... (b112) (b113) ... (b126) (b127)
0    1    1        1      0          1      0

M2
(byte 0)       ... (byte 15)
(b0) (b1) (b2) ... (b112) (b113) ... (b126) (b127)
0    1    1        1      0          0      1
                   *      *          *      *
```
(asterisks represent where bits may differ)

In the first round, the two messages are both XORed with the key, but that
doesn't change the differential - the modified messages still differ in only
the last byte. Then they go through the SBOX; they now differ in different bits
of the last byte, but still only in the last byte:
```
(byte 0)       ... (byte 14)              (byte 15)
(b0) (b1) (b2) ... (b96) (b97) ... (b111) (b112) (b113) ... (b126) (b127)
                                          *      *      ... *      *
```
Then they undergo the bit rotation by 1:
```
(byte 0)       ... (byte 14)              (byte 15)
(b0) (b1) (b2) ... (b96) (b97) ... (b111) (b112) (b113) ... (b126) (b127)
                                   *      *      *      ... *
```
They now differ in potentially one bit of byte 14, and most bits of byte 15.
With probability about 1/2, they don't actually differ at (b111). Let
D_r(M1, M2) be the number of differing bytes when the two messages M1 and M2
(which differ only in the last byte) are encrypted for r rounds. So with
probability about 1/2, D_1(M1, M2) = 1, and otherwise, D_1(M1, M2) = 2.

Unfortunately, we cannot observe D_1(M1, M2); we can only send two messages and
observe their encryptions after all 25 rounds, and find D_25(M1, M2). However,
if the differential after one round has spread to two bytes, then the
differential after 25 rounds has probably spread to relatively more bytes. If
the differential after one round consists of only one byte, then the
differential after 25 rounds has probably spread to relatively fewer bytes.
There is statistical correlation between D_1(M1, M2) and D_25(M1, M2).

There are probably many ways to take advantage of this, but my solver uses a
crude approach. Look at message pairs for which D_25(M1, M2) < 15 (so at least
2 bytes don't differ - this threshold was found empirically). For those message
pairs, there should be more that satisfy D_1(M1, M2) = 1 than D_1(M1, M2) = 2.

We can now brute force the last byte of the key. Given only the last byte, we
can compute D_1(M1, M2) for all the above message pairs. If we guess the
correct last byte X, than we'll have D_1(M1, M2) = 1 for most of the message
pairs. For any other guess, we'd expect a roughly random 50/50 distribution.

There was nothing special about the last byte here - we can start with message
pairs with a differential in any other byte as well, and do the same thing, to
get every byte of the key.

Flag: `L3AK{spicy_pork_nachos}`
