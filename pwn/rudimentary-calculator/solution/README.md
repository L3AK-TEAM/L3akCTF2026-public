## Rudimentary Calculator Solution
### Author: kyc

There is a buffer overflow bug. Because scanf can take characters after the
first '\x00', but the verification ends at the first '\x00', there can be
arbitrary bytes added after the first '\x00'. We can use that to first set
the integer length to be 103 u32s, which means that printing the integer leaks
the canary, saved rbp, and return address. We can then overwrite the return
address to point to the win function (while writing the original canary and
saved rbp) using standard ROP.

Flag: `L3AK{s3Arch_f0r_Sm0otH}`
