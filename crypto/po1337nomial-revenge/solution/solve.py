import json
from pwn import *

# Un-shuffle the scrambled outputs of Python MT19937 PRNG

N = 1337

def untemper(x):
    x = x ^ (x >> 18)
    x = x ^ ((x << 15) & 0xEFC60000)
    for i in range(7, 32):
        x ^= (x << 7) & (1 << i) & 0x9D2C5680
    for i in range(20, -1, -1):
        x ^= (x >> 11) & (1 << i)
    return x & 0xFFFFFFFF

# After 624 outputs, the RNG will replace each x_i with twist(x_i, x_{i+1}, x_{i+397})
def twist(x, y, z):
    return (((x & 0x80000000) ^ (y & 0x7FFFFFFE)) >> 1) ^ ((y & 1) * 0x9908B0DF) ^ z

while True:
    io = remote('localhost', 10028)

    io.sendline(b'1')
    io.recvuntil(b's: ')
    tempered_nums = json.loads(io.recvline())

    nums = set([untemper(num) for num in tempered_nums])
    assert len(nums) == N

    # There is an XOR relationship between terms a_i, a_{i+396}, and a_{i+623} in a sequence output by MT19937.
    # We don't know the order, but we can find all such relationships.
    # The relationship between a_{i+396} and a_{i+623} are symmetric, so we don't know the order between the two.
    relationships = set()
    for up in nums:
        for down1 in nums:
            for down2 in twist(0, up, down1), twist(0x80000000, up, down1):
                if down2 in nums:
                    relationships.add((up, frozenset([down1, down2])))

    # We expect N+1-624 relationships: (0, 396, 623), (1, 397, 624), ... (N-624, N-228, N-1)
    # If there are more (coincidental ones), try again
    if len(relationships) != N + 1 - 624:
        io.close()
        continue

    # Repeatedly filter down possible options for the indices.
    # For an up value, make sure i+396 and i+623 are possible options for the down values.
    # For a down value, make sure the option i is either 396 or 623 more than an option for the up value.
    # Repeat until there is only one possible n for each of the first 624 indices.
    options = {n: set(range(N)) for n in nums}
    while not all(sum(i in ops for ops in options.values()) == 1 for i in range(624)):
        for up, (down1, down2) in relationships:
            up_options = set(i for i in options[up]
                             if (i + 396 in options[down1] and i + 623 in options[down2])
                             or (i + 396 in options[down2] and i + 623 in options[down1]))
            options[up] &= up_options

            down_options = set(i + d for i in options[up] for d in (396, 623))
            options[down1] &= down_options
            options[down2] &= down_options

    state = [-1] * 624
    for n, (index, *_) in options.items():
        if index < 624:
            state[index] = n
    r = random.Random()
    r.setstate((3, tuple(state + [0]), None))

    a = [r.getrandbits(32) for _ in range(N)]
    assert set(a) == set(tempered_nums)
    r.shuffle(a.copy())
    randbytes = r.randbytes(N).hex()

    io.sendline(b'3')
    io.recvuntil(b'k: ')
    io.sendline(randbytes.encode())
    print(io.recvline().decode())

    io.sendline(b'quit')
    break
