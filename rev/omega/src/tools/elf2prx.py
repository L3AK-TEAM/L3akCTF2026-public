#!/usr/bin/env python3
"""elf2prx.py -- convert a static little-endian MIPS I ELF into a PRX image."""

import argparse
import struct
import sys
from dataclasses import dataclass

import prism
import prx_mac

PRX_MAGIC = b"PRX\x00"          # e_magic: 50 52 58 00
PRX_VERSION = 1                 # e_version
HEADER_SIZE = 0x30              # 48-byte file header
PHDR_SIZE = 0x10               # 16 bytes per program header
PHDR_TABLE_OFFSET = 0x30        # table always begins right after the header
SPILLOVER_SENTINEL = 0xFFFFFFFF  # p_filesz: "map from p_offset to EOF"
FLAG_HAS_GP = 0x01             # e_flags bit 0: e_gp is valid
MAX_PHNUM = 255                # e_phnum is a single byte, and must be >= 1


ELF_MAGIC = b"\x7fELF"
ELFCLASS32 = 1
ELFDATA2LSB = 1                 # little-endian; the PRISM VM requires LE
EM_MIPS = 8
PT_LOAD = 1


class ConversionError(Exception):
    """Raised on malformed or unsupported input."""


@dataclass
class LoadSegment:
    """One PT_LOAD segment, with its bytes already sliced from the ELF."""
    vaddr: int
    filesz: int   # original ELF p_filesz (bytes actually emitted)
    memsz: int
    data: bytes   # exactly `filesz` bytes copied from the ELF


def parse_elf(buf: bytes) -> tuple[int, list[LoadSegment]]:
    """Return (e_entry, [PT_LOAD segments in program-header order])."""
    if len(buf) < 52:
        raise ConversionError("file too small to be an ELF32")
    if buf[:4] != ELF_MAGIC:
        raise ConversionError("not an ELF file (bad magic)")
    if buf[4] != ELFCLASS32:
        raise ConversionError("only ELF32 is supported")
    if buf[5] != ELFDATA2LSB:
        raise ConversionError("ELF must be little-endian (the PRISM VM is LE-only)")

    e_machine = struct.unpack_from("<H", buf, 18)[0]
    if e_machine != EM_MIPS:
        print(f"warning: e_machine={e_machine} (expected MIPS=8)", file=sys.stderr)

    e_entry, e_phoff = struct.unpack_from("<II", buf, 24)
    e_phentsize, e_phnum = struct.unpack_from("<HH", buf, 42)

    table_end = e_phoff + e_phnum * e_phentsize
    if table_end > len(buf):
        raise ConversionError("malformed program headers (table exceeds file)")

    segments: list[LoadSegment] = []
    for i in range(e_phnum):
        ph = e_phoff + i * e_phentsize
        p_type, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz = \
            struct.unpack_from("<IIIIII", buf, ph)
        if p_type != PT_LOAD:
            continue
        if p_offset + p_filesz > len(buf):
            raise ConversionError("PT_LOAD segment exceeds file")
        segments.append(LoadSegment(
            vaddr=p_vaddr,
            filesz=p_filesz,
            memsz=p_memsz,
            data=buf[p_offset:p_offset + p_filesz],
        ))

    if not segments:
        raise ConversionError("no PT_LOAD segments found")
    return e_entry, segments


def _segment_index_for_va(segments: list[LoadSegment], va: int) -> int | None:
    """Index of the segment whose file-backed range contains `va`, else None."""
    for i, seg in enumerate(segments):
        if seg.vaddr <= va < seg.vaddr + seg.filesz:
            return i
    return None

def build_prx(e_entry: int, segments: list[LoadSegment], *,
              spillover: bool = True, transpile: bool = True,
              e_gp: int | None = None) -> bytes:
    """Assemble a PRX image with e_mac left zeroed."""
    phnum = len(segments)
    if not 1 <= phnum <= MAX_PHNUM:
        raise ConversionError(f"e_phnum must be 1..{MAX_PHNUM}, got {phnum}")

    if spillover and segments[-1].vaddr != max(s.vaddr for s in segments):
        print("warning: the last (spillover) segment is not the highest VA; an "
              "appended suffix may not map contiguously (prx.md sec 5)",
              file=sys.stderr)

    # Transpile the CODE segment (the one holding e_entry) from MIPS I to PRISM
    if transpile:
        code_idx = _segment_index_for_va(segments, e_entry)
        if code_idx is None:
            raise ConversionError(
                f"e_entry 0x{e_entry:08x} is not inside any PT_LOAD segment; "
                "cannot locate the code segment to transpile")
        code = segments[code_idx]
        if len(code.data) % 4 != 0:
            raise ConversionError(
                f"code segment is {len(code.data)} bytes (not a multiple of 4); "
                "cannot transpile to PRISM")
        segments = list(segments)
        segments[code_idx] = LoadSegment(
            vaddr=code.vaddr, filesz=code.filesz, memsz=code.memsz,
            data=prism.encode_bytes(code.data))

    data_start = HEADER_SIZE + phnum * PHDR_SIZE

    phdr_table = bytearray()
    segment_data = bytearray()
    cursor = data_start
    for i, seg in enumerate(segments):
        is_last = (i == phnum - 1)
        p_filesz = SPILLOVER_SENTINEL if (spillover and is_last) else seg.filesz
        phdr_table += struct.pack("<IIII", cursor, seg.vaddr, p_filesz, seg.memsz)
        segment_data += seg.data
        cursor += seg.filesz   # rebase by the real byte count, not the sentinel

    e_flags = 0
    gp_value = 0
    if e_gp is not None:
        e_flags |= FLAG_HAS_GP
        gp_value = e_gp

    header = struct.pack(
        "<4sBBBBII32s",
        PRX_MAGIC,      # e_magic
        PRX_VERSION,    # e_version
        phnum,          # e_phnum
        e_flags,        # e_flags
        0,              # e_reserved
        e_entry,        # e_entry
        gp_value,       # e_gp
        b"\x00" * prx_mac.MAC_SIZE,  # e_mac (zeroed; signed separately)
    )
    assert len(header) == HEADER_SIZE
    return bytes(header + phdr_table + segment_data)


def embed_mac(prx: bytes, tag: bytes) -> bytes:
    """Write a 32-byte MAC tag into the e_mac field (offset 0x10)."""
    if len(tag) != prx_mac.MAC_SIZE:
        raise ConversionError(f"MAC tag must be {prx_mac.MAC_SIZE} bytes, got {len(tag)}")
    out = bytearray(prx)
    out[prx_mac.MAC_OFFSET:prx_mac.MAC_OFFSET + prx_mac.MAC_SIZE] = tag
    return bytes(out)


def _parse_secret(spec: str) -> bytes:
    """A --sign-secret value: raw text, hex via 0x.../hex:..., or @file."""
    if spec.startswith("@"):
        with open(spec[1:], "rb") as f:
            return f.read()
    if spec.startswith("0x") or spec.startswith("hex:"):
        return bytes.fromhex(spec.split(":", 1)[-1].removeprefix("0x"))
    return spec.encode()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Convert a static MIPS ELF to a PRX image.")
    ap.add_argument("elf", help="input little-endian MIPS ELF32")
    ap.add_argument("-o", "--output", help="output PRX path (default: <elf>.prx)")
    ap.add_argument("--no-spillover", action="store_true",
                    help="do not mark the last segment as a spillover (non-job binary)")
    ap.add_argument("--no-transpile", action="store_true",
                    help="do not re-encode the .text segment to PRISM (emit raw MIPS I)")
    ap.add_argument("--gp", type=lambda s: int(s, 0), metavar="VALUE",
                    help="set e_gp to VALUE and the HAS_GP flag (default: -G0, no $gp)")
    ap.add_argument("--entry", type=lambda s: int(s, 0), metavar="VADDR",
                    help="override e_entry (default: the ELF entry point)")

    mac = ap.add_mutually_exclusive_group()
    mac.add_argument("--mac", metavar="HEX",
                     help="embed a precomputed 32-byte tag (64 hex chars)")
    mac.add_argument("--sign-secret", metavar="SECRET",
                     help="sign locally with SECRET (text, 0x.../hex:..., or @file); "
                          "dev convenience only -- the server owns real signing")

    args = ap.parse_args(argv)

    try:
        with open(args.elf, "rb") as f:
            elf_buf = f.read()
        e_entry, segments = parse_elf(elf_buf)
        if args.entry is not None:
            e_entry = args.entry

        prx = build_prx(e_entry, segments,
                        spillover=not args.no_spillover,
                        transpile=not args.no_transpile, e_gp=args.gp)

        if args.mac:
            prx = embed_mac(prx, bytes.fromhex(args.mac))
        elif args.sign_secret:
            tag = prx_mac.sign_prx(_parse_secret(args.sign_secret), prx)
            prx = embed_mac(prx, tag)
    except ConversionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    out_path = args.output or (args.elf.rsplit(".", 1)[0] + ".prx")
    with open(out_path, "wb") as f:
        f.write(prx)

    signed = "signed" if (args.mac or args.sign_secret) else "unsigned (e_mac=0)"
    print(f"wrote {out_path}: {len(prx)} bytes, {len(segments)} segment(s), "
          f"entry=0x{e_entry:08x}, {signed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
