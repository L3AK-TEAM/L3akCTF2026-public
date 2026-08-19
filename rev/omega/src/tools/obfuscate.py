#!/usr/bin/env python3

import argparse
import os
import random
from pathlib import Path

FIELDS = {
    'op': (31, 26),  # opcode  -- present in EVERY format
    'rs': (25, 21),
    'rt': (20, 16),
    'rd': (15, 11),
    'sh': (10, 6),   # shamt
    'fn': (5, 0),    # funct   -- only a funct when canonical opcode == 0x00
}
OP_R = 0x00          # all R-types share this opcode; funct disambiguates
MASK32 = 0xFFFFFFFF

# Canonical opcode (primary) mnemonics the VM dispatches on. Value -> NAME.
OPCODES = {
    0x00: 'SPECIAL', 0x01: 'REGIMM', 0x02: 'J', 0x03: 'JAL',
    0x04: 'BEQ', 0x05: 'BNE', 0x06: 'BLEZ', 0x07: 'BGTZ',
    0x08: 'ADDI', 0x09: 'ADDIU', 0x0a: 'SLTI', 0x0b: 'SLTIU',
    0x0c: 'ANDI', 0x0d: 'ORI', 0x0e: 'XORI', 0x0f: 'LUI',
    0x10: 'COP0', 0x11: 'COP1', 0x12: 'COP2', 0x13: 'COP3',
    0x20: 'LB', 0x21: 'LH', 0x22: 'LWL', 0x23: 'LW',
    0x24: 'LBU', 0x25: 'LHU', 0x26: 'LWR',
    0x28: 'SB', 0x29: 'SH', 0x2a: 'SWL', 0x2b: 'SW', 0x2e: 'SWR',
}

# Canonical SPECIAL funct mnemonics the VM dispatches on. Value -> NAME.
FUNCTS = {
    0x00: 'SLL', 0x02: 'SRL', 0x03: 'SRA', 0x04: 'SLLV',
    0x06: 'SRLV', 0x07: 'SRAV', 0x08: 'JR', 0x09: 'JALR',
    0x0c: 'SYSCALL', 0x0d: 'BREAK', 0x10: 'MFHI', 0x11: 'MTHI',
    0x12: 'MFLO', 0x13: 'MTLO', 0x18: 'MULT', 0x19: 'MULTU',
    0x1a: 'DIV', 0x1b: 'DIVU', 0x20: 'ADD', 0x21: 'ADDU',
    0x22: 'SUB', 0x23: 'SUBU', 0x24: 'AND', 0x25: 'OR',
    0x26: 'XOR', 0x27: 'NOR', 0x2a: 'SLT', 0x2b: 'SLTU',
}


def get_field(w, hi, lo):
    return (w >> lo) & ((1 << (hi - lo + 1)) - 1)


def set_field(w, hi, lo, v):
    width = hi - lo + 1
    m = ((1 << width) - 1) << lo
    return (w & ~m) | ((v & ((1 << width) - 1)) << lo)

def make_block_permutation(block_order):
    perm = [0] * 32
    obf_hi = 31
    for name in block_order:
        hi, lo = FIELDS[name]
        width = hi - lo + 1
        for k in range(width):
            perm[hi - k] = obf_hi - k          # MSB-aligned, order preserved
        obf_hi -= width
    assert obf_hi == -1, "block widths must sum to 32"
    assert sorted(perm) == list(range(32)), "not a permutation"
    return perm


def block_positions(block_order):
    pos, obf_hi = {}, 31
    for name in block_order:
        hi, lo = FIELDS[name]
        width = hi - lo + 1
        pos[name] = (obf_hi, obf_hi - width + 1)
        obf_hi -= width
    return pos


def invert_perm(perm):
    inv = [0] * 32
    for i, p in enumerate(perm):
        inv[p] = i
    return inv


def apply_bit_perm(w, perm):
    out = 0
    for i in range(32):
        if (w >> i) & 1:
            out |= 1 << perm[i]
    return out & MASK32


def invert_box(box):
    inv = [0] * len(box)
    for x, y in enumerate(box):
        inv[y] = x
    return inv

def obfuscate(word, perm, op_box, fn_box):
    op = get_field(word, *FIELDS['op'])
    w = set_field(word, *FIELDS['op'], op_box[op])
    if op == OP_R:                                   # funct is meaningful
        fn = get_field(word, *FIELDS['fn'])
        w = set_field(w, *FIELDS['fn'], fn_box[fn])
    return apply_bit_perm(w, perm)


def deobfuscate(obf, inv_perm, op_inv, fn_inv):
    w = apply_bit_perm(obf, inv_perm)
    op = op_inv[get_field(w, *FIELDS['op'])]
    w = set_field(w, *FIELDS['op'], op)
    if op == OP_R:
        fn = fn_inv[get_field(w, *FIELDS['fn'])]
        w = set_field(w, *FIELDS['fn'], fn)
    return w

class Instance:
    def __init__(self, seed: bytes):
        self.seed = seed
        r = random.Random(seed)
        # (1) field block order, MSB->LSB in the PRISM word.
        self.block_order = list(FIELDS.keys())
        r.shuffle(self.block_order)
        # the opcode block must NOT stay at the canonical MSB position
        assert self.block_order[0] != 'op', \
            "degenerate instance: opcode block left at canonical MSB position"
        # (2) opcode + funct S-boxes (random LUTs, 6-bit).
        self.op_box = list(range(64)); r.shuffle(self.op_box)
        self.fn_box = list(range(64)); r.shuffle(self.fn_box)
        # derived
        self.op_inv = invert_box(self.op_box)
        self.fn_inv = invert_box(self.fn_box)
        self.perm = make_block_permutation(self.block_order)
        self.inv_perm = invert_perm(self.perm)
        self.pos = block_positions(self.block_order)

    def encode(self, word):
        return obfuscate(word, self.perm, self.op_box, self.fn_box)

    def decode(self, obf):
        return deobfuscate(obf, self.inv_perm, self.op_inv, self.fn_inv)

    def selftest(self, rounds=200000):
        for w, _ in _EXAMPLES:
            assert self.decode(self.encode(w)) == w
        rng = random.Random()
        for _ in range(rounds):
            w = rng.getrandbits(32)
            assert self.decode(self.encode(w)) == w


_EXAMPLES = [
    (0x02324020, "add  $t0,$s1,$s2"),
    (0x00094100, "sll  $t0,$t1,4"),
    (0x22100001, "addi $s0,$s0,1"),
    (0xAFA80008, "sw   $t0,8($sp)"),
    (0x12110003, "beq  $s0,$s1,L"),
    (0x08100009, "j    0x00400024"),
]

def emit_prism_h(inst: Instance) -> str:
    pos = inst.pos
    # canonical-field bit position of each block's LSB in the PRISM word.
    lo = {name: pos[name][1] for name in FIELDS}
    L = []
    L.append("/* prism.h - PRISM ISA decode tables (AUTO-GENERATED by obfuscate.py). */")
    L.append("#ifndef PRISM_H")
    L.append("#define PRISM_H")
    L.append("")
    L.append("#include <stdint.h>")
    L.append("")
    L.append("/* ---- field extraction: canonical field <- its permuted PRISM offset ---- */")
    L.append(f"#define PRISM_OP(w)   (((w) >> {lo['op']:2}) & 0x3f)")
    L.append(f"#define PRISM_RS(w)   (((w) >> {lo['rs']:2}) & 0x1f)")
    L.append(f"#define PRISM_RT(w)   (((w) >> {lo['rt']:2}) & 0x1f)")
    L.append(f"#define PRISM_RD(w)   (((w) >> {lo['rd']:2}) & 0x1f)")
    L.append(f"#define PRISM_SA(w)   (((w) >> {lo['sh']:2}) & 0x1f)")
    L.append(f"#define PRISM_FN(w)   (((w) >> {lo['fn']:2}) & 0x3f)")
    L.append("")
    L.append("/* Canonical immediate/target reassembled from the scattered field values:")
    L.append(" *   imm    = rd:sh:fn  (canonical bits 15..0)")
    L.append(" *   target = rs:rt:rd:sh:fn  (canonical bits 25..0) */")
    L.append("#define PRISM_IMM(w)    ((PRISM_RD(w) << 11) | (PRISM_SA(w) << 6) | PRISM_FN(w))")
    L.append("#define PRISM_SIMM(w)   ((int32_t)(int16_t)PRISM_IMM(w))")
    L.append("#define PRISM_TARGET(w) ((PRISM_RS(w) << 21) | (PRISM_RT(w) << 16) | PRISM_IMM(w))")
    L.append("")
    L.append("/* ---- substituted PRIMARY opcodes (canonical mnemonic -> PRISM value) ---- */")
    for val, name in OPCODES.items():
        L.append(f"#define PRISM_OP_{name:<8} 0x{inst.op_box[val]:02X}  /* MIPS op  0x{val:02X} */")
    L.append("")
    L.append("/* ---- substituted SPECIAL funct codes (canonical mnemonic -> PRISM value) ---- */")
    for val, name in FUNCTS.items():
        L.append(f"#define PRISM_FN_{name:<8} 0x{inst.fn_box[val]:02X}  /* MIPS funct 0x{val:02X} */")
    L.append("")
    L.append("#endif /* PRISM_H */")
    return "\n".join(L) + "\n"


def emit_prism_py(inst: Instance) -> str:
    L = []
    L.append('#!/usr/bin/env python3')
    L.append('"""prism.py -- PRISM codec (AUTO-GENERATED by obfuscate.py)."""')
    L.append('')
    L.append('import struct')
    L.append('')
    L.append(f'SEED = bytes.fromhex("{inst.seed.hex()}")')
    L.append('')
    L.append('# Canonical MIPS-I field positions (hi, lo), MSB = bit 31.')
    L.append('FIELDS = {')
    for name, (hi, loo) in FIELDS.items():
        L.append(f'    {name!r}: ({hi}, {loo}),')
    L.append('}')
    L.append('OP_R = 0x00')
    L.append('')
    L.append(f'BLOCK_ORDER = {inst.block_order!r}  # MSB->LSB in the PRISM word')
    L.append(f'OP_BOX = {inst.op_box!r}')
    L.append(f'FN_BOX = {inst.fn_box!r}')
    L.append('OP_INV = [0] * 64')
    L.append('FN_INV = [0] * 64')
    L.append('for _x, _y in enumerate(OP_BOX): OP_INV[_y] = _x')
    L.append('for _x, _y in enumerate(FN_BOX): FN_INV[_y] = _x')
    L.append('')
    L.append('')
    L.append('def _perm():')
    L.append('    perm = [0] * 32')
    L.append('    obf_hi = 31')
    L.append('    for name in BLOCK_ORDER:')
    L.append('        hi, lo = FIELDS[name]')
    L.append('        for k in range(hi - lo + 1):')
    L.append('            perm[hi - k] = obf_hi - k')
    L.append('        obf_hi -= (hi - lo + 1)')
    L.append('    return perm')
    L.append('')
    L.append('')
    L.append('PERM = _perm()')
    L.append('INV_PERM = [0] * 32')
    L.append('for _i, _p in enumerate(PERM): INV_PERM[_p] = _i')
    L.append('')
    L.append('')
    L.append('def _get(w, hi, lo): return (w >> lo) & ((1 << (hi - lo + 1)) - 1)')
    L.append('')
    L.append('')
    L.append('def _set(w, hi, lo, v):')
    L.append('    width = hi - lo + 1')
    L.append('    m = ((1 << width) - 1) << lo')
    L.append('    return (w & ~m) | ((v & ((1 << width) - 1)) << lo)')
    L.append('')
    L.append('')
    L.append('def _permute(w, perm):')
    L.append('    out = 0')
    L.append('    for i in range(32):')
    L.append('        if (w >> i) & 1:')
    L.append('            out |= 1 << perm[i]')
    L.append('    return out & 0xFFFFFFFF')
    L.append('')
    L.append('')
    L.append('def encode_word(word):')
    L.append('    """MIPS I instruction word -> PRISM instruction word."""')
    L.append('    word &= 0xFFFFFFFF')
    L.append("    op = _get(word, *FIELDS['op'])")
    L.append("    w = _set(word, *FIELDS['op'], OP_BOX[op])")
    L.append('    if op == OP_R:')
    L.append("        w = _set(w, *FIELDS['fn'], FN_BOX[_get(word, *FIELDS['fn'])])")
    L.append('    return _permute(w, PERM)')
    L.append('')
    L.append('')
    L.append('def decode_word(obf):')
    L.append('    """PRISM instruction word -> MIPS I instruction word."""')
    L.append('    w = _permute(obf & 0xFFFFFFFF, INV_PERM)')
    L.append("    op = OP_INV[_get(w, *FIELDS['op'])]")
    L.append("    w = _set(w, *FIELDS['op'], op)")
    L.append('    if op == OP_R:')
    L.append("        w = _set(w, *FIELDS['fn'], FN_INV[_get(w, *FIELDS['fn'])])")
    L.append('    return w')
    L.append('')
    L.append('')
    L.append('def encode_bytes(blob):')
    L.append('    """Re-encode a little-endian stream of 4-byte MIPS words to PRISM."""')
    L.append('    if len(blob) % 4:')
    L.append('        raise ValueError("instruction stream must be a multiple of 4 bytes")')
    L.append('    out = bytearray()')
    L.append('    for off in range(0, len(blob), 4):')
    L.append('        (w,) = struct.unpack_from("<I", blob, off)')
    L.append('        out += struct.pack("<I", encode_word(w))')
    L.append('    return bytes(out)')
    L.append('')
    return "\n".join(L) + "\n"


# ==========================================================================
# CLI
# ==========================================================================
def main(argv=None):
    repo = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser(description="Generate / freeze a PRISM instance.")
    ap.add_argument("--seed", metavar="HEX",
                    help="reproduce a specific instance (default: fresh os.urandom(32))")
    ap.add_argument("--emit", action="store_true",
                    help="write src/host/vm/prism.h, src/tools/prism.py, build/prism.seed")
    ap.add_argument("--rounds", type=int, default=200000,
                    help="random round-trip rounds for the self-test")
    args = ap.parse_args(argv)

    if args.seed:
        # Reproduce a specific instance; the disguise assertion validates it.
        inst = Instance(bytes.fromhex(args.seed))
    else:
        # Draw fresh seeds until one satisfies the disguise invariant.
        while True:
            try:
                inst = Instance(os.urandom(32))
                break
            except AssertionError:
                continue
    seed = inst.seed

    print(f"[*] PRISM instance seed: {seed.hex()}")
    print(f"[*] field order (MSB->LSB): {' '.join(inst.block_order)}")
    inst.selftest(args.rounds)
    print(f"[+] bijection holds over {args.rounds} random words + cheat-sheet examples")

    if args.emit:
        h_path = repo / "src" / "host" / "vm" / "prism.h"
        py_path = repo / "src" / "tools" / "prism.py"
        seed_path = repo / "build" / "prism.seed"
        h_path.write_text(emit_prism_h(inst))
        py_path.write_text(emit_prism_py(inst))
        seed_path.write_text(seed.hex() + "\n")
        print(f"[+] wrote {h_path.relative_to(repo)}")
        print(f"[+] wrote {py_path.relative_to(repo)}")
        print(f"[+] wrote {seed_path.relative_to(repo)} (provenance)")
    else:
        print("[i] re-run with --emit to freeze src/host/vm/prism.h + src/tools/prism.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
