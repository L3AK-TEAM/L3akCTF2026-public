# Immiscible Solution
### Author: Suvoni

The Unbalanced Oil & Vinegar (UOV) signature scheme in this challenge is broken because the public key does not contain oil-oil terms. Thus, if we can guess the 4 vinegar variables, every polynomial becomes linear in the 4 oil variables.

The attack is:

1. Brute-force the 4 vinegar variables over F_79. There are 79^4 = 38,950,081 possible candidates, which is very feasible to brute.
2. For each guess, convert the MQ system into a linear system in the 4 oil variables.
3. Solve the 9 x 4 linear system modulo 79 using Gaussian elimination.
4. Verify the recovered signature against the target.
5. Derive AES key = SHA256(bytes(signature)).
6. Decrypt encrypted_flag.

Flag: ``L3AK{Oil_4ND_v1N3g4r_WitH0ut_Mix1nG_Sp1LL5_eV3rYth1ng}``
