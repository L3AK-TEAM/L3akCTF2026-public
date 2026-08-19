## Yet Another Chat Solution
### Author: aseng

Unpack the executable first, it's actually just UPX with tampered signatures, then you'll see a custom section .l3ak which holds the jumbled randomized instructions & trampolines of the real code, restore them and deobfuscate will yield the core algorithm used, which is only RC5 encryption.

Flag: `L3AK{1t_is_@ll_jU5t_4n0th3r_d30bf_uZzZc4t!0n_game_hopeyouenjoy:)_asengishere}`
