# What-Who Solution
### Author: 0x1622

## First layer: cartridge and VM

The header is 64 bytes and contains the card count, data length, entry card,
salt, and separate 64-bit seals for code and data. Each plaintext card is:

```c
struct card {
    uint8_t glyph;
    uint8_t x;
    uint8_t y;
    uint8_t z;
    uint64_t argument;
} __attribute__((packed));
```

The interpreter unveils every code and data byte, verifies both seals, loads
data at virtual address `0x2000`, and starts in the WHAT face. Reversing the two
glyph switches yields a disassembler. The only architecture transition is a
FLIP glyph, so face recovery is a control-flow/state problem.

## Question 1

The query accepts exactly four raw bytes. The WHAT cards pack them in
big-endian order into a 32-bit word and transform that word:

```text
x ^= c13fa9a9
x = rol32(x, 9)
x = x * 045d9f3b
x ^= x >> 15
x += 7f4a7c15
x = ror32(x, 3)
```

The target is `fb5647da`. Reverse the rotate/add/xorshift/multiplication
operations. The odd multiplier has an inverse modulo `2^32`.

Answer:

```text
slop
```

## Question 2

The WHO program maintains an eight-bit state. For character `i`:

```text
y = ((character[i] XOR state) + key[i]) mod 256
y = rol8(y, (i mod 7) + 1)
y = y XOR ((a7 + 11*i) mod 256)
state = (state + y + character[i] + 13) mod 256
```

Each `y` is compared immediately with a 16-byte vector in cartridge data. The
map is bijective once the prior state is known, so solve from left to right.

Answer:

```text
slop_slop_slop!!
```

## Question 3

The data section contains 289 consecutive bytes interpreted as a 17x17
occupancy grid. The VM starts at flattened cell 18, applies `N/E/S/W` deltas,
rejects walls, requires exactly 102 moves, and finishes at cell 96.

Rendered organizer maze:

```text
#################
#S..#.......#...#
###.#.#####.###.#
#.#...#...#...#.#
#.#####.#.###.#.#
#.......#.#E#...#
#.#######.#.###.#
#...#.....#.#...#
###.#.#####.#.###
#...#.......#...#
#.#########.###.#
#...#...#...#...#
#.#.#.#.###.#.###
#.#...#...#.#...#
#.#######.#####.#
#.......#.......#
#################
```

Because this is a perfect maze, the shortest route is unique:

```text
EESSEENNEEEEEESSEESSEESSWWSSEESSWWSSEESSWWWWWWNNWWNNWWSSWWNNWWNNEENNWWNNEEEEEENNEESSSSWWWWSSEEEEEENNNN
```

## Question 4

Read the connection's 64-bit seed from the banner. The native query handler
parses this answer as an unsigned decimal integer. The WHAT code then runs this
custom mixer, with every operation reduced modulo `2^64`:

```text
state = seed XOR 4f1bbcdcbfa54001

for i in range(0x89):
    state ^= state >> 27
    state *= c83a91e1d74b5f27
    state += rol64(i * b5ad4eceda1ce2a9, 31)
    state += 165667b19e3779f9
    state = rol64(state, 23)
    state ^= state >> 31
```

Every individual operation is invertible on 64-bit words (including the odd
multiplication and right-xorshifts), so the complete mixer is a permutation:
different seeds always produce different answers. Submit `state` in unsigned
decimal.

## Question 5

Read the same 64-bit connection seed from the banner. All operations below wrap
modulo `2^64`:

```text
state = seed XOR a0761d6478bd642f
count = 0x500 + ((seed >> 9) AND 0x3ff)

for i in range(count):
    state ^= state << 13
    state ^= state >> 7
    state ^= state << 17
    state += rol64(i * e7037ed1a0b428db, 23)
    state += 8ebc6af09c88c6e3

state ^= rol64(seed, 29)
state ^= 589965cc75374cc3
```

Submit `state` as 16 lowercase hexadecimal digits.

## Transcript commitment

After every accepted answer, native code hashes its exact text and updates a
hidden 64-bit `trail`. Question 6 reads this value, so solvers must model all
five updates. All operations below wrap modulo `2^64`:

```text
avalanche(x):
    x ^= x >> 28
    x *= a3b195354a39b70d
    x ^= x >> 33
    x *= f1357aea2e62a9c5
    x ^= x >> 29
    return x

trail = avalanche(seed XOR 57484f5f57415443)

transcript_hash(answer):
    h = 243f6a8885a308d3 XOR (len(answer) << 48)
    for i, byte in enumerate(answer):
        h ^= byte + (i + 1) * 9b1d2d6b42f0a7b5
        h = rol64(h, 11)
        h *= d1342543de82ef95
        h += c6bc279692b5cc83
    return avalanche(h)

for stage, answer in enumerate(answers_1_through_5, start=1):
    trail ^= transcript_hash(answer) + stage * 8cb92ba72f3d8dd7
    trail = rol64(trail, stage * 9 + 5)
    trail *= db4f0b9175ae2165
    trail ^= trail >> 27
```

## Question 6

The VM derives a 128-bit target from `seed` and `trail`, decodes the submitted
32 hexadecimal digits into two big-endian 64-bit halves, and applies ten
Feistel rounds:

```text
F(R, i) =
    rol64((R XOR key[i]) + seed, rotation[i])
    XOR (R * multiplier[i])
    + (trail XOR (i * c2b2ae3d27d4eb4f))

(L, R) = (R, L XOR F(R, i))
```

Given the target halves, reverse rounds 9 through 0:

```text
old_R = new_L
old_L = new_R XOR F(old_R, i)
```

The resulting two big-endian halves form the unique 32-digit answer for that
connection.

The round parameters, indexed from 0 through 9, are:

```text
key = [
    15f16e2b9b9b5d3d, a7c3b29d4e1f608b,
    c6ef3720d4b7a931, 72d5b3766fa4bc19,
    9c30d5392af26013, dbe6d5d5fe4cce2f,
    f1ea5eed2c3b4a57, 6a09e667bb67ae85,
    3f84d5b5b5470917, 94d049bb133111eb
]

multiplier = [
    2545f4914f6cdd1d, 369dea0f31a53f85,
    db4f0b9175ae2165, a24baed4963ee407,
    9fb21c651e98df25, d1342543de82ef95,
    f1357aea2e62a9c5, c6bc279692b5cc83,
    bea225f9eb34556d, 8cb92ba72f3d8dd7
]

rotation = [7, 19, 31, 47, 11, 29, 43, 3, 23, 53]
```

The target halves fed into the reverse rounds are:

```text
target_L = rol64(seed XOR trail, 17)
target_L = target_L * d6e8feb86659fd93 + a4093822299f31d0

target_R = rol64(trail, 41)
target_R ^= seed * 9e6c63d0676a9a99
target_R += 13198a2e03707344
target_R ^= ror64(target_L, 11)
```

For the deterministic test seed `0123456789abcdef`:

```text
Question 4: 2347727620915961940
Question 5: 0f1b54eadb90271e
Question 6: cc5e42fcde3381f38fd61e51578ff02e
```
