#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import struct
from collections import deque
from dataclasses import dataclass
from pathlib import Path


MASK64 = (1 << 64) - 1
MASK32 = (1 << 32) - 1
MAGIC = b"\x89WWHO\r\n\x1a"
VERSION = 3
HEADER_SIZE = 64
CARD_SIZE = 12
DATA_BASE = 0x2000
INPUT_BASE = 0x0800

DOMAIN_CODE = 0x434152445F564549
DOMAIN_DATA = 0x4C45444745525F56
CARTRIDGE_SALT = 0x91E10DA5C79E7B1D

QUERY_RAW = 0
QUERY_HEX32 = 1
QUERY_HEX64 = 2
QUERY_HEX128 = 3
QUERY_DEC64 = 4

WHAT = {
    "movi": 0xA7,
    "mov": 0x39,
    "ldbx": 0xD2,
    "add": 0x4B,
    "addi": 0xF0,
    "xor": 0x16,
    "xori": 0x8D,
    "mul": 0xC3,
    "muli": 0x52,
    "andi": 0xE8,
    "shli": 0x25,
    "shri": 0xB4,
    "roli": 0x69,
    "rori": 0x9A,
    "rol32i": 0x71,
    "ror32i": 0x06,
    "cmp": 0xDD,
    "cmpi": 0x43,
    "jeq": 0xBC,
    "jne": 0x2E,
    "jmp": 0x95,
    "query": 0x5F,
    "nonce": 0xCA,
    "trail": 0x31,
    "mark": 0x7B,
    "reveal": 0xE1,
    "flip": 0x0C,
    "halt": 0xF7,
}

WHO = {
    "pushi": 0x44,
    "pushr": 0x9D,
    "popr": 0x23,
    "dup": 0xF2,
    "swap": 0x68,
    "drop": 0xB1,
    "ldb": 0x0F,
    "ld16": 0xC8,
    "ld64le": 0x75,
    "ld64be": 0xA3,
    "add": 0x37,
    "sub": 0xDE,
    "xor": 0x82,
    "mul": 0x19,
    "and": 0xEF,
    "or": 0x56,
    "shl": 0xC1,
    "shr": 0x2A,
    "rol": 0x97,
    "ror": 0x4C,
    "rol8": 0xD5,
    "mod": 0x6B,
    "eq": 0x14,
    "jz": 0xAB,
    "jnz": 0x7E,
    "jmp": 0x30,
    "flip": 0xFA,
    "halt": 0x5C,
}

STAGE1_ANSWER = "slop"
STAGE2_ANSWER = "slop_slop_slop!!"

S1_XOR = 0xC13FA9A9
S1_MUL = 0x045D9F3B
S1_ADD = 0x7F4A7C15

S4_XOR = 0x4F1BBCDCBFA54001
S4_MUL = 0xC83A91E1D74B5F27
S4_STEP = 0xB5AD4ECEDA1CE2A9
S4_ADD = 0x165667B19E3779F9

S5_XOR = 0xA0761D6478BD642F
S5_INDEX_MUL = 0xE7037ED1A0B428DB
S5_ADD = 0x8EBC6AF09C88C6E3
S5_FINAL_XOR = 0x589965CC75374CC3

T6_MUL0 = 0xD6E8FEB86659FD93
T6_ADD0 = 0xA4093822299F31D0
T6_MUL1 = 0x9E6C63D0676A9A99
T6_ADD1 = 0x13198A2E03707344
T6_ROUND_MIX = 0xC2B2AE3D27D4EB4F

STAGE6_KEYS = [
    0x15F16E2B9B9B5D3D,
    0xA7C3B29D4E1F608B,
    0xC6EF3720D4B7A931,
    0x72D5B3766FA4BC19,
    0x9C30D5392AF26013,
    0xDBE6D5D5FE4CCE2F,
    0xF1EA5EED2C3B4A57,
    0x6A09E667BB67AE85,
    0x3F84D5B5B5470917,
    0x94D049BB133111EB,
]

STAGE6_MULTS = [
    0x2545F4914F6CDD1D,
    0x369DEA0F31A53F85,
    0xDB4F0B9175AE2165,
    0xA24BAED4963EE407,
    0x9FB21C651E98DF25,
    0xD1342543DE82EF95,
    0xF1357AEA2E62A9C5,
    0xC6BC279692B5CC83,
    0xBEA225F9EB34556D,
    0x8CB92BA72F3D8DD7,
]

STAGE6_ROTS = [7, 19, 31, 47, 11, 29, 43, 3, 23, 53]


def u64(value: int) -> int:
    return value & MASK64


def rol(value: int, count: int, width: int = 64) -> int:
    mask = (1 << width) - 1
    count %= width
    value &= mask
    if count == 0:
        return value
    return ((value << count) | (value >> (width - count))) & mask


def ror(value: int, count: int, width: int = 64) -> int:
    return rol(value, -count, width)


def avalanche(value: int) -> int:
    value &= MASK64
    value ^= value >> 28
    value = u64(value * 0xA3B195354A39B70D)
    value ^= value >> 33
    value = u64(value * 0xF1357AEA2E62A9C5)
    value ^= value >> 29
    return value & MASK64


def initial_trail(nonce: int) -> int:
    return avalanche(nonce ^ 0x57484F5F57415443)


def transcript_hash(line: bytes) -> int:
    value = 0x243F6A8885A308D3 ^ (len(line) << 48)
    for index, byte in enumerate(line):
        value ^= byte + (index + 1) * 0x9B1D2D6B42F0A7B5
        value &= MASK64
        value = rol(value, 11)
        value = u64(value * 0xD1342543DE82EF95)
        value = u64(value + 0xC6BC279692B5CC83)
    return avalanche(value)


def mark_trail(trail: int, stage: int, answer: str) -> int:
    trail ^= u64(
        transcript_hash(answer.encode("ascii"))
        + stage * 0x8CB92BA72F3D8DD7
    )
    trail = rol(trail, stage * 9 + 5)
    trail = u64(trail * 0xDB4F0B9175AE2165)
    trail ^= trail >> 27
    return trail & MASK64


def stage1_transform(value: int) -> int:
    value = (value ^ S1_XOR) & MASK32
    value = rol(value, 9, 32)
    value = (value * S1_MUL) & MASK32
    value ^= value >> 15
    value &= MASK32
    value = (value + S1_ADD) & MASK32
    return ror(value, 3, 32)


def stage4_answer(seed: int) -> str:
    state = seed ^ S4_XOR
    for index in range(0x89):
        state ^= state >> 27
        state = u64(state * S4_MUL)
        state = u64(state + rol(u64(index * S4_STEP), 31) + S4_ADD)
        state = rol(state, 23)
        state ^= state >> 31
    return str(state & MASK64)


def stage5_answer(nonce: int) -> str:
    state = nonce ^ S5_XOR
    count = 0x500 + ((nonce >> 9) & 0x3FF)
    for index in range(count):
        state ^= u64(state << 13)
        state ^= state >> 7
        state ^= u64(state << 17)
        state &= MASK64
        term = rol(u64(index * S5_INDEX_MUL), 23)
        state = u64(state + term + S5_ADD)
    state ^= rol(nonce, 29)
    state ^= S5_FINAL_XOR
    return f"{state & MASK64:016x}"


def stage6_targets(nonce: int, trail: int) -> tuple[int, int]:
    left = rol(nonce ^ trail, 17)
    left = u64(left * T6_MUL0 + T6_ADD0)

    right = rol(trail, 41)
    right ^= u64(nonce * T6_MUL1)
    right = u64(right + T6_ADD1)
    right ^= ror(left, 11)
    return left, right


def stage6_f(right: int, round_index: int, nonce: int, trail: int) -> int:
    value = right ^ STAGE6_KEYS[round_index]
    value = u64(value + nonce)
    value = rol(value, STAGE6_ROTS[round_index])
    value ^= u64(right * STAGE6_MULTS[round_index])
    value = u64(
        value
        + (trail ^ u64(round_index * T6_ROUND_MIX))
    )
    return value


def stage6_answer(nonce: int, trail: int) -> str:
    left, right = stage6_targets(nonce, trail)
    for round_index in range(9, -1, -1):
        old_right = left
        old_left = right ^ stage6_f(old_right, round_index, nonce, trail)
        left, right = old_left & MASK64, old_right & MASK64
    return left.to_bytes(8, "big").hex() + right.to_bytes(8, "big").hex()


class DataBuilder:
    def __init__(self) -> None:
        self.data = bytearray()
        self.labels: dict[str, int] = {}

    def add(
        self, label: str, value: bytes, *, alignment: int = 1, nul: bool = False
    ) -> int:
        if label in self.labels:
            raise ValueError(f"duplicate data label: {label}")
        while len(self.data) % alignment:
            self.data.append(0)
        address = DATA_BASE + len(self.data)
        self.labels[label] = address
        self.data.extend(value)
        if nul:
            self.data.append(0)
        return address

    def __getitem__(self, label: str) -> int:
        return self.labels[label]


@dataclass
class Card:
    face: str
    mnemonic: str
    glyph: int
    x: int = 0
    y: int = 0
    z: int = 0
    arg: int | str = 0


class Assembler:
    def __init__(self) -> None:
        self.cards: list[Card] = []
        self.labels: dict[str, int] = {}
        self.face = "what"

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"duplicate code label: {name}")
        self.labels[name] = len(self.cards)

    def w(
        self, mnemonic: str, *, x: int = 0, y: int = 0, z: int = 0,
        arg: int | str = 0
    ) -> None:
        if self.face != "what":
            raise ValueError(f"WHAT card emitted while face is {self.face}")
        self.cards.append(Card("what", mnemonic, WHAT[mnemonic], x, y, z, arg))
        if mnemonic == "flip":
            self.face = "who"

    def h(
        self, mnemonic: str, *, x: int = 0, y: int = 0, z: int = 0,
        arg: int | str = 0
    ) -> None:
        if self.face != "who":
            raise ValueError(f"WHO card emitted while face is {self.face}")
        self.cards.append(Card("who", mnemonic, WHO[mnemonic], x, y, z, arg))
        if mnemonic == "flip":
            self.face = "what"

    def encode(self) -> bytes:
        encoded = bytearray()
        for card in self.cards:
            arg = card.arg
            if isinstance(arg, str):
                if arg not in self.labels:
                    raise ValueError(f"unresolved label: {arg}")
                arg = self.labels[arg]
            if not 0 <= int(arg) <= MASK64:
                raise ValueError(f"card immediate outside u64: {card}")
            encoded.extend(
                struct.pack(
                    "<BBBBQ",
                    card.glyph,
                    card.x,
                    card.y,
                    card.z,
                    int(arg),
                )
            )
        return bytes(encoded)


def deterministic_maze() -> tuple[bytes, str, int, int, list[str]]:
    width = height = 17
    grid = [["#"] * width for _ in range(height)]
    start = (1, 1)
    grid[start[1]][start[0]] = "."
    stack = [start]
    state = 0x57484F

    while stack:
        x, y = stack[-1]
        directions = [(0, -2), (2, 0), (0, 2), (-2, 0)]
        for index in range(3, 0, -1):
            state = (state * 1664525 + 1013904223) & MASK32
            other = state % (index + 1)
            directions[index], directions[other] = (
                directions[other],
                directions[index],
            )
        candidates = []
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if (
                1 <= nx < width - 1
                and 1 <= ny < height - 1
                and grid[ny][nx] == "#"
            ):
                candidates.append((dx, dy))
        if not candidates:
            stack.pop()
            continue
        dx, dy = candidates[0]
        grid[y + dy // 2][x + dx // 2] = "."
        grid[y + dy][x + dx] = "."
        stack.append((x + dx, y + dy))

    queue = deque([start])
    distance = {start: 0}
    previous: dict[tuple[int, int], tuple[tuple[int, int], str]] = {}
    steps = [("N", (0, -1)), ("E", (1, 0)), ("S", (0, 1)), ("W", (-1, 0))]
    while queue:
        point = queue.popleft()
        for letter, (dx, dy) in steps:
            nxt = (point[0] + dx, point[1] + dy)
            if grid[nxt[1]][nxt[0]] != "#" and nxt not in distance:
                distance[nxt] = distance[point] + 1
                previous[nxt] = (point, letter)
                queue.append(nxt)

    end = max(distance, key=distance.get)
    cursor = end
    route = []
    while cursor != start:
        cursor, letter = previous[cursor]
        route.append(letter)
    route.reverse()

    grid[start[1]][start[0]] = "S"
    grid[end[1]][end[0]] = "E"
    rendered = ["".join(row) for row in grid]
    packed = bytes(0 if cell == "#" else 1 for row in grid for cell in row)
    return (
        packed,
        "".join(route),
        start[1] * width + start[0],
        end[1] * width + end[0],
        rendered,
    )


def stage2_vectors() -> tuple[bytes, bytes, bytes, bytes]:
    keys = bytes(((0x31 + i * 73) ^ (i * i * 11 + 0xA6)) & 0xFF for i in range(16))
    rotations = bytes((i % 7) + 1 for i in range(16))
    post = bytes((0xA7 + i * 11) & 0xFF for i in range(16))

    state = 0x5A
    expected = bytearray()
    for index, char in enumerate(STAGE2_ANSWER.encode("ascii")):
        value = ((char ^ state) + keys[index]) & 0xFF
        value = rol(value, rotations[index], 8)
        value ^= post[index]
        expected.append(value)
        state = (state + value + char + 0x13) & 0xFF
    return keys, rotations, post, bytes(expected)


def build_data() -> tuple[DataBuilder, dict[str, object]]:
    data = DataBuilder()
    data.add(
        "prompt1",
        b"Question 1 - Did you remember the password? ",
        nul=True,
    )
    data.add(
        "prompt2",
        b"Question 2 - What is today's special? ",
        nul=True,
    )
    data.add(
        "prompt3",
        b"Question 3 - Which way now? ",
        nul=True,
    )
    data.add(
        "prompt4",
        b"Question 4 - Can you guess the number i am thinking? ",
        nul=True,
    )
    data.add(
        "prompt5",
        b"Question 5 - Is your clock running? ",
        nul=True,
    )
    data.add(
        "prompt6",
        b"Question 6 - Who is asking? ",
        nul=True,
    )

    s2_key, s2_rot, s2_post, s2_expected = stage2_vectors()
    data.add("s2_key", s2_key)
    data.add("s2_rot", s2_rot)
    data.add("s2_post", s2_post)
    data.add("s2_expected", s2_expected)

    maze, route, start_index, end_index, rendered = deterministic_maze()
    data.add("maze", maze)

    data.add(
        "s6_keys",
        b"".join(struct.pack("<Q", value) for value in STAGE6_KEYS),
        alignment=8,
    )
    data.add(
        "s6_mults",
        b"".join(struct.pack("<Q", value) for value in STAGE6_MULTS),
        alignment=8,
    )
    data.add("s6_rots", bytes(STAGE6_ROTS))

    metadata: dict[str, object] = {
        "route": route,
        "maze_start": start_index,
        "maze_end": end_index,
        "maze_rendered": rendered,
    }
    return data, metadata


def emit_stack_address(asm: Assembler, base: int, index_register: int) -> None:
    asm.h("pushi", arg=base)
    asm.h("pushr", x=index_register)
    asm.h("add")


def build_program(data: DataBuilder, metadata: dict[str, object]) -> Assembler:
    asm = Assembler()
    s1_target = stage1_transform(
        int.from_bytes(STAGE1_ANSWER.encode("ascii"), "big")
    )
    route = str(metadata["route"])

    # Gate 1: pack four raw bytes, then apply an invertible 32-bit verifier.
    asm.label("start")
    asm.w("query", x=7, y=QUERY_RAW, z=4, arg=data["prompt1"])
    asm.w("cmpi", x=7, arg=4)
    asm.w("jne", arg="fail")
    asm.w("movi", x=0, arg=0)
    asm.w("movi", x=1, arg=0)
    asm.label("stage1_pack")
    asm.w("ldbx", x=2, y=1, arg=INPUT_BASE)
    asm.w("shli", x=0, arg=8)
    asm.w("add", x=0, y=2)
    asm.w("addi", x=1, arg=1)
    asm.w("cmpi", x=1, arg=4)
    asm.w("jne", arg="stage1_pack")
    asm.w("xori", x=0, arg=S1_XOR)
    asm.w("rol32i", x=0, arg=9)
    asm.w("muli", x=0, arg=S1_MUL)
    asm.w("andi", x=0, arg=MASK32)
    asm.w("mov", x=1, y=0)
    asm.w("shri", x=1, arg=15)
    asm.w("xor", x=0, y=1)
    asm.w("andi", x=0, arg=MASK32)
    asm.w("addi", x=0, arg=S1_ADD)
    asm.w("andi", x=0, arg=MASK32)
    asm.w("ror32i", x=0, arg=3)
    asm.w("cmpi", x=0, arg=s1_target)
    asm.w("jne", arg="fail")
    asm.w("mark", arg=1)

    # Gate 2: a stateful byte transducer expressed as postfix WHO cards.
    asm.w("query", x=0, y=QUERY_RAW, z=16, arg=data["prompt2"])
    asm.w("cmpi", x=0, arg=16)
    asm.w("jne", arg="fail")
    asm.w("flip")
    asm.h("pushi", arg=0)
    asm.h("popr", x=1)  # index
    asm.h("pushi", arg=0x5A)
    asm.h("popr", x=2)  # state
    asm.label("stage2_loop")
    emit_stack_address(asm, INPUT_BASE, 1)
    asm.h("ldb")
    asm.h("popr", x=3)  # character

    asm.h("pushr", x=3)
    asm.h("pushr", x=2)
    asm.h("xor")
    emit_stack_address(asm, data["s2_key"], 1)
    asm.h("ldb")
    asm.h("add")
    asm.h("pushi", arg=0xFF)
    asm.h("and")
    emit_stack_address(asm, data["s2_rot"], 1)
    asm.h("ldb")
    asm.h("rol8")
    emit_stack_address(asm, data["s2_post"], 1)
    asm.h("ldb")
    asm.h("xor")
    asm.h("popr", x=4)  # transformed byte

    asm.h("pushr", x=4)
    emit_stack_address(asm, data["s2_expected"], 1)
    asm.h("ldb")
    asm.h("eq")
    asm.h("jz", arg="who_fail")

    asm.h("pushr", x=2)
    asm.h("pushr", x=4)
    asm.h("add")
    asm.h("pushr", x=3)
    asm.h("add")
    asm.h("pushi", arg=0x13)
    asm.h("add")
    asm.h("pushi", arg=0xFF)
    asm.h("and")
    asm.h("popr", x=2)

    asm.h("pushr", x=1)
    asm.h("pushi", arg=1)
    asm.h("add")
    asm.h("popr", x=1)
    asm.h("pushr", x=1)
    asm.h("pushi", arg=16)
    asm.h("eq")
    asm.h("jz", arg="stage2_loop")
    asm.h("flip")
    asm.w("mark", arg=2)

    # Gate 3: walk a perfect maze stored as a one-byte occupancy plane.
    asm.w("query", x=0, y=QUERY_RAW, z=120, arg=data["prompt3"])
    asm.w("cmpi", x=0, arg=len(route))
    asm.w("jne", arg="fail")
    asm.w("movi", x=1, arg=0)  # route index
    asm.w("movi", x=2, arg=int(metadata["maze_start"]))
    asm.label("stage3_loop")
    asm.w("ldbx", x=3, y=1, arg=INPUT_BASE)
    asm.w("cmpi", x=3, arg=ord("N"))
    asm.w("jeq", arg="move_north")
    asm.w("cmpi", x=3, arg=ord("E"))
    asm.w("jeq", arg="move_east")
    asm.w("cmpi", x=3, arg=ord("S"))
    asm.w("jeq", arg="move_south")
    asm.w("cmpi", x=3, arg=ord("W"))
    asm.w("jeq", arg="move_west")
    asm.w("jmp", arg="fail")
    asm.label("move_north")
    asm.w("addi", x=2, arg=u64(-17))
    asm.w("jmp", arg="moved")
    asm.label("move_east")
    asm.w("addi", x=2, arg=1)
    asm.w("jmp", arg="moved")
    asm.label("move_south")
    asm.w("addi", x=2, arg=17)
    asm.w("jmp", arg="moved")
    asm.label("move_west")
    asm.w("addi", x=2, arg=u64(-1))
    asm.label("moved")
    asm.w("ldbx", x=4, y=2, arg=data["maze"])
    asm.w("cmpi", x=4, arg=1)
    asm.w("jne", arg="fail")
    asm.w("addi", x=1, arg=1)
    asm.w("cmpi", x=1, arg=len(route))
    asm.w("jne", arg="stage3_loop")
    asm.w("cmpi", x=2, arg=int(metadata["maze_end"]))
    asm.w("jne", arg="fail")
    asm.w("mark", arg=3)

    # Gate 4: predict a per-instance 64-bit number from the displayed seed.
    asm.w("nonce", x=0)
    asm.w("mov", x=1, y=0)
    asm.w("xori", x=1, arg=S4_XOR)
    asm.w("movi", x=2, arg=0x89)
    asm.w("movi", x=3, arg=0)
    asm.label("stage4_round")
    asm.w("mov", x=4, y=1)
    asm.w("shri", x=4, arg=27)
    asm.w("xor", x=1, y=4)
    asm.w("muli", x=1, arg=S4_MUL)
    asm.w("mov", x=4, y=3)
    asm.w("muli", x=4, arg=S4_STEP)
    asm.w("roli", x=4, arg=31)
    asm.w("add", x=1, y=4)
    asm.w("addi", x=1, arg=S4_ADD)
    asm.w("roli", x=1, arg=23)
    asm.w("mov", x=4, y=1)
    asm.w("shri", x=4, arg=31)
    asm.w("xor", x=1, y=4)
    asm.w("addi", x=3, arg=1)
    asm.w("cmp", x=3, y=2)
    asm.w("jne", arg="stage4_round")
    asm.w(
        "query",
        x=5,
        y=QUERY_DEC64,
        z=20,
        arg=data["prompt4"],
    )
    asm.w("cmp", x=5, y=1)
    asm.w("jne", arg="fail")
    asm.w("mark", arg=4)

    # Gate 5: a second per-connection recurrence keyed by the displayed seed.
    asm.w("nonce", x=0)
    asm.w("mov", x=1, y=0)
    asm.w("xori", x=1, arg=S5_XOR)
    asm.w("mov", x=2, y=0)
    asm.w("shri", x=2, arg=9)
    asm.w("andi", x=2, arg=0x3FF)
    asm.w("addi", x=2, arg=0x500)
    asm.w("movi", x=3, arg=0)
    asm.label("stage5_loop")
    asm.w("mov", x=4, y=1)
    asm.w("shli", x=4, arg=13)
    asm.w("xor", x=1, y=4)
    asm.w("mov", x=4, y=1)
    asm.w("shri", x=4, arg=7)
    asm.w("xor", x=1, y=4)
    asm.w("mov", x=4, y=1)
    asm.w("shli", x=4, arg=17)
    asm.w("xor", x=1, y=4)
    asm.w("mov", x=4, y=3)
    asm.w("muli", x=4, arg=S5_INDEX_MUL)
    asm.w("roli", x=4, arg=23)
    asm.w("add", x=1, y=4)
    asm.w("addi", x=1, arg=S5_ADD)
    asm.w("addi", x=3, arg=1)
    asm.w("cmp", x=3, y=2)
    asm.w("jne", arg="stage5_loop")
    asm.w("mov", x=4, y=0)
    asm.w("roli", x=4, arg=29)
    asm.w("xor", x=1, y=4)
    asm.w("xori", x=1, arg=S5_FINAL_XOR)
    asm.w("query", x=5, y=QUERY_HEX64, z=16, arg=data["prompt5"])
    asm.w("cmp", x=5, y=1)
    asm.w("jne", arg="fail")
    asm.w("mark", arg=5)

    # Gate 6: derive two targets from seed+transcript, then invert a
    # ten-round Feistel construction to obtain the required identity seal.
    asm.w("nonce", x=0)
    asm.w("trail", x=1)
    asm.w("mov", x=2, y=0)
    asm.w("xor", x=2, y=1)
    asm.w("roli", x=2, arg=17)
    asm.w("muli", x=2, arg=T6_MUL0)
    asm.w("addi", x=2, arg=T6_ADD0)
    asm.w("mov", x=3, y=1)
    asm.w("roli", x=3, arg=41)
    asm.w("mov", x=4, y=0)
    asm.w("muli", x=4, arg=T6_MUL1)
    asm.w("xor", x=3, y=4)
    asm.w("addi", x=3, arg=T6_ADD1)
    asm.w("mov", x=4, y=2)
    asm.w("rori", x=4, arg=11)
    asm.w("xor", x=3, y=4)
    asm.w("query", x=6, y=QUERY_HEX128, z=32, arg=data["prompt6"])
    asm.w("flip")

    asm.h("pushi", arg=INPUT_BASE)
    asm.h("ld64be")
    asm.h("popr", x=4)  # left
    asm.h("pushi", arg=INPUT_BASE + 8)
    asm.h("ld64be")
    asm.h("popr", x=5)  # right
    asm.h("pushi", arg=0)
    asm.h("popr", x=6)  # round
    asm.label("stage6_round")

    asm.h("pushr", x=5)
    asm.h("pushi", arg=data["s6_keys"])
    asm.h("pushr", x=6)
    asm.h("pushi", arg=8)
    asm.h("mul")
    asm.h("add")
    asm.h("ld64le")
    asm.h("xor")
    asm.h("pushr", x=0)
    asm.h("add")
    asm.h("pushi", arg=data["s6_rots"])
    asm.h("pushr", x=6)
    asm.h("add")
    asm.h("ldb")
    asm.h("rol")

    asm.h("pushr", x=5)
    asm.h("pushi", arg=data["s6_mults"])
    asm.h("pushr", x=6)
    asm.h("pushi", arg=8)
    asm.h("mul")
    asm.h("add")
    asm.h("ld64le")
    asm.h("mul")
    asm.h("xor")

    asm.h("pushr", x=1)
    asm.h("pushr", x=6)
    asm.h("pushi", arg=T6_ROUND_MIX)
    asm.h("mul")
    asm.h("xor")
    asm.h("add")
    asm.h("popr", x=7)

    asm.h("pushr", x=4)
    asm.h("pushr", x=7)
    asm.h("xor")
    asm.h("pushr", x=5)
    asm.h("popr", x=4)
    asm.h("popr", x=5)

    asm.h("pushr", x=6)
    asm.h("pushi", arg=1)
    asm.h("add")
    asm.h("popr", x=6)
    asm.h("pushr", x=6)
    asm.h("pushi", arg=10)
    asm.h("eq")
    asm.h("jz", arg="stage6_round")

    asm.h("pushr", x=4)
    asm.h("pushr", x=2)
    asm.h("eq")
    asm.h("jz", arg="who_fail")
    asm.h("pushr", x=5)
    asm.h("pushr", x=3)
    asm.h("eq")
    asm.h("jz", arg="who_fail")
    asm.h("flip")
    asm.w("mark", arg=6)
    asm.w("reveal")
    asm.w("halt")

    # Architecture-correct failure trampoline for branches taken under WHO.
    # This first FLIP is unreachable by fallthrough because success halted.
    # It only establishes the face of the card at the branch destination.
    asm.w("flip")
    asm.label("who_fail")
    asm.h("flip")
    asm.w("jmp", arg="fail")
    asm.label("fail")
    asm.w("halt")
    return asm


def veil_byte(byte: int, salt: int, position: int, domain: int) -> int:
    lane = salt ^ domain
    lane ^= u64((position + 1) * 0xA24BAED4963EE407)
    lane &= MASK64
    lane ^= lane >> 27
    lane = u64(lane * 0x3C79AC492BA7B653)
    lane ^= lane >> 33
    lane = u64(lane * 0x1C69B3F74AC4AE35)
    lane ^= lane >> 27
    key = (lane >> ((position * 5) & 56)) & 0xFF
    rotation = (salt + position * 3 + domain) & 7
    bias = (position * 29 + (salt >> 16) + (domain >> 8)) & 0xFF
    return ror((byte + bias) & 0xFF, rotation, 8) ^ key


def seal(blob: bytes, domain: int) -> int:
    value = domain ^ u64(len(blob) * 0x9E6C63D0676A9A99)
    for index, byte in enumerate(blob):
        value ^= u64(byte + (index + 1) * 0x6A09E667F3BCC909)
        value &= MASK64
        value = rol(value, 13)
        value = u64(value * 0xD6E8FEB86659FD93)
        value ^= value >> 29
    value ^= value >> 32
    value = u64(value * 0xBEA225F9EB34556D)
    value ^= value >> 31
    value = u64(value * 0x94D049BB133111EB)
    value ^= value >> 30
    return value & MASK64


def encrypt(blob: bytes, salt: int, domain: int) -> bytes:
    return bytes(veil_byte(byte, salt, index, domain) for index, byte in enumerate(blob))


def write_outputs(
    output: Path, answers_path: Path | None, maze_path: Path | None
) -> None:
    data, metadata = build_data()
    asm = build_program(data, metadata)
    code = asm.encode()
    if len(code) != len(asm.cards) * CARD_SIZE:
        raise AssertionError("bad card serialization")

    code_seal = seal(code, DOMAIN_CODE)
    data_blob = bytes(data.data)
    data_seal = seal(data_blob, DOMAIN_DATA)
    cartridge_id = bytes.fromhex("1e8f4a71c09d52b63a7742ed950cb184")
    header = struct.pack(
        "<8sHHIIIQQQ16s",
        MAGIC,
        VERSION,
        HEADER_SIZE,
        len(asm.cards),
        len(data_blob),
        asm.labels["start"],
        CARTRIDGE_SALT,
        code_seal,
        data_seal,
        cartridge_id,
    )
    if len(header) != HEADER_SIZE:
        raise AssertionError("bad header size")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(
        header
        + encrypt(code, CARTRIDGE_SALT, DOMAIN_CODE)
        + encrypt(data_blob, CARTRIDGE_SALT, DOMAIN_DATA)
    )

    route = str(metadata["route"])
    demo_seed = 0x0123456789ABCDEF
    answers = [
        STAGE1_ANSWER,
        STAGE2_ANSWER,
        route,
        stage4_answer(demo_seed),
        stage5_answer(demo_seed),
    ]
    trail = initial_trail(demo_seed)
    for stage, answer in enumerate(answers, 1):
        trail = mark_trail(trail, stage, answer)
    demo_stage6 = stage6_answer(demo_seed, trail)

    manifest = {
        "stage1": STAGE1_ANSWER,
        "stage2": STAGE2_ANSWER,
        "stage3": route,
        "demo_seed": f"{demo_seed:016x}",
        "demo_stage4": answers[3],
        "demo_stage5": answers[4],
        "demo_stage6": demo_stage6,
        "card_count": len(asm.cards),
        "data_size": len(data_blob),
    }
    if answers_path is not None:
        answers_path.parent.mkdir(parents=True, exist_ok=True)
        answers_path.write_text(json.dumps(manifest, indent=2) + "\n")
    if maze_path is not None:
        maze_path.parent.mkdir(parents=True, exist_ok=True)
        maze_path.write_text("\n".join(metadata["maze_rendered"]) + "\n")

    print(
        f"wrote {output} ({len(asm.cards)} cards, {len(data_blob)} data bytes)"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--answers", type=Path)
    parser.add_argument("--maze", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    options = parse_args()
    write_outputs(options.output, options.answers, options.maze)
