#!/usr/bin/env python3
"""Decrypt DPAPI-NG/CNG blobs with an already-decrypted raw DPAPI masterkey.

The normal offline flow is:
  1. decrypt the user's DPAPI masterkey by other means;
  2. pass that raw masterkey and a raw DPAPI-NG blob to this utility.

This handles the common NCryptProtectSecret/CNG DPAPI blob shape where an
embedded classic DPAPI blob decrypts to a KEK, which unwraps the AES-GCM
content key.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import struct
import sys
from dataclasses import dataclass
from typing import Iterator

from Crypto.Cipher import AES, DES3


ALG_CRYPT = {
    0x6603: ("3DES", 24, 8, 8),
    0x6611: ("AES", 16, 16, 16),
    0x660E: ("AES", 16, 16, 16),
    0x660F: ("AES", 24, 16, 16),
    0x6610: ("AES", 32, 16, 16),
}

ALG_HASH = {
    0x8003: ("md5", 16, 64),
    0x8004: ("sha1", 20, 64),
    0x8009: ("sha1", 20, 64),
    0x800C: ("sha256", 32, 64),
    0x800D: ("sha384", 48, 128),
    0x800E: ("sha512", 64, 128),
}


class DPAPINGError(Exception):
    pass


@dataclass
class ASN1Node:
    tag: int
    value: bytes
    children: list["ASN1Node"]


@dataclass
class DPAPIBlob:
    alg_crypt: int
    salt: bytes
    hmac_key: bytes
    alg_hash: int
    hmac2_key: bytes
    data: bytes
    to_sign: bytes
    sign: bytes


def read_exact(reader: io.BytesIO, size: int, what: str) -> bytes:
    data = reader.read(size)
    if len(data) != size:
        raise DPAPINGError(f"truncated {what}")
    return data


def read_u32(reader: io.BytesIO, what: str) -> int:
    return struct.unpack("<I", read_exact(reader, 4, what))[0]


def parse_asn1(data: bytes, offset: int = 0, end: int | None = None) -> tuple[ASN1Node, int]:
    if end is None:
        end = len(data)
    if offset >= end:
        raise DPAPINGError("empty ASN.1 input")

    start = offset
    tag = data[offset]
    offset += 1
    if offset >= end:
        raise DPAPINGError("truncated ASN.1 length")

    first_len = data[offset]
    offset += 1
    if first_len & 0x80:
        count = first_len & 0x7F
        if count == 0:
            raise DPAPINGError("indefinite ASN.1 lengths are not supported")
        if offset + count > end:
            raise DPAPINGError("truncated ASN.1 long length")
        length = int.from_bytes(data[offset : offset + count], "big")
        offset += count
    else:
        length = first_len

    value_start = offset
    value_end = offset + length
    if value_end > end:
        raise DPAPINGError("ASN.1 length exceeds input")

    value = data[value_start:value_end]
    children: list[ASN1Node] = []
    if tag & 0x20:
        child_offset = value_start
        while child_offset < value_end:
            child, child_offset = parse_asn1(data, child_offset, value_end)
            children.append(child)
        if child_offset != value_end:
            raise DPAPINGError("ASN.1 child parser did not consume container")

    return ASN1Node(tag=tag, value=value, children=children), value_end


def walk_asn1(node: ASN1Node) -> Iterator[ASN1Node]:
    yield node
    for child in node.children:
        yield from walk_asn1(child)


def extract_cng_fields_from_der(
    blob_data: bytes, allow_trailer: bool = False
) -> tuple[bytes, bytes, bytes, bytes]:
    root, consumed = parse_asn1(blob_data)
    if consumed != len(blob_data) and not allow_trailer:
        raise DPAPINGError("trailing data after ASN.1 blob")
    trailer = blob_data[consumed:]
    nodes = list(walk_asn1(root))
    try:
        dpapi_blob = nodes[9].value
        wrapped_key = nodes[21].value
        nonce = nodes[27].value
        encrypted_data = nodes[29].value
    except IndexError:
        dpapi_blob, wrapped_key, nonce, encrypted_data = discover_cng_fields(nodes, trailer)

    if not dpapi_blob.startswith(b"\x01\x00\x00\x00"):
        raise DPAPINGError("embedded DPAPI blob was not found at the expected ASN.1 position")
    if len(wrapped_key) < 24 or len(wrapped_key) % 8:
        raise DPAPINGError("wrapped content key length is invalid")
    if len(nonce) != 12:
        raise DPAPINGError(f"expected 12-byte AES-GCM nonce, got {len(nonce)} bytes")
    if len(encrypted_data) < 16:
        raise DPAPINGError("AES-GCM ciphertext is too short to include a tag")

    return dpapi_blob, wrapped_key, nonce, encrypted_data


def discover_cng_fields(nodes: list[ASN1Node], trailer: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    octets = [(index, node.value) for index, node in enumerate(nodes) if node.tag == 0x04]
    dpapi_entries = [
        (index, value) for index, value in octets if value.startswith(b"\x01\x00\x00\x00")
    ]
    if not dpapi_entries:
        raise DPAPINGError("embedded DPAPI blob was not found in the ASN.1 data")

    dpapi_index, dpapi_blob = dpapi_entries[0]
    later_octets = [(index, value) for index, value in octets if index > dpapi_index]

    wrapped_entries = [
        (index, value) for index, value in later_octets if len(value) >= 24 and len(value) % 8 == 0
    ]
    if not wrapped_entries:
        raise DPAPINGError("wrapped content key was not found in the ASN.1 data")
    wrapped_index, wrapped_key = wrapped_entries[0]

    nonce_entries = [
        (index, value) for index, value in later_octets if index > wrapped_index and len(value) == 12
    ]
    if not nonce_entries:
        raise DPAPINGError("AES-GCM nonce was not found in the ASN.1 data")
    nonce_index, nonce = nonce_entries[0]

    encrypted_entries = [
        value for index, value in later_octets if index > nonce_index and len(value) >= 16
    ]
    if encrypted_entries:
        encrypted_data = encrypted_entries[0]
    elif len(trailer) >= 16:
        encrypted_data = trailer
    else:
        raise DPAPINGError("AES-GCM ciphertext/tag was not found in the ASN.1 data or trailer")

    return dpapi_blob, wrapped_key, nonce, encrypted_data


def iter_der_sequence_candidates(data: bytes) -> Iterator[tuple[int, bytes]]:
    for offset, byte in enumerate(data):
        if byte != 0x30:
            continue
        try:
            parse_asn1(data, offset)
        except DPAPINGError:
            continue
        yield offset, data[offset:]


def extract_cng_fields(blob_data: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    try:
        return extract_cng_fields_from_der(blob_data, allow_trailer=True)
    except DPAPINGError as original_exc:
        original_error = str(original_exc)

    # Clipboard pinned data can wrap a DPAPI-NG ASN.1 blob with non-ASN.1
    # metadata or append record data after the DER object. Use the first
    # embedded SEQUENCE that matches the expected CNG layout.
    for _offset, candidate in iter_der_sequence_candidates(blob_data):
        try:
            return extract_cng_fields_from_der(candidate, allow_trailer=True)
        except DPAPINGError:
            continue

    raise DPAPINGError(original_error)


def parse_dpapi_blob(data: bytes) -> DPAPIBlob:
    reader = io.BytesIO(data)
    read_u32(reader, "DPAPI version")
    read_exact(reader, 16, "provider GUID")
    read_u32(reader, "masterkey version")
    read_exact(reader, 16, "masterkey GUID")
    read_u32(reader, "flags")

    description_len = read_u32(reader, "description length")
    read_exact(reader, description_len, "description")

    alg_crypt = read_u32(reader, "cipher algorithm")
    read_u32(reader, "cipher algorithm length")

    salt_len = read_u32(reader, "salt length")
    salt = read_exact(reader, salt_len, "salt")

    hmac_key_len = read_u32(reader, "HMAC key length")
    hmac_key = read_exact(reader, hmac_key_len, "HMAC key")

    alg_hash = read_u32(reader, "hash algorithm")
    read_u32(reader, "hash algorithm length")

    hmac2_key_len = read_u32(reader, "HMAC2 key length")
    hmac2_key = read_exact(reader, hmac2_key_len, "HMAC2 key")

    data_len = read_u32(reader, "encrypted data length")
    encrypted = read_exact(reader, data_len, "encrypted data")

    to_sign_len = 60 + description_len + salt_len + hmac_key_len + hmac2_key_len + data_len
    if 20 + to_sign_len > len(data):
        raise DPAPINGError("DPAPI signature coverage exceeds blob length")
    to_sign = data[20 : 20 + to_sign_len]

    sign_len = read_u32(reader, "signature length")
    sign = read_exact(reader, sign_len, "signature")
    if not sign:
        raise DPAPINGError("DPAPI blob has no signature")

    return DPAPIBlob(
        alg_crypt=alg_crypt,
        salt=salt,
        hmac_key=hmac_key,
        alg_hash=alg_hash,
        hmac2_key=hmac2_key,
        data=encrypted,
        to_sign=to_sign,
        sign=sign,
    )


def xor_bytes(value: int, data: bytes) -> bytes:
    return bytes(byte ^ value for byte in data)


def fix_des_parity(key: bytes) -> bytes:
    fixed = bytearray()
    for byte in key:
        high_seven = byte & 0xFE
        parity_bit = 0 if bin(high_seven).count("1") % 2 else 1
        fixed.append(high_seven | parity_bit)
    return bytes(fixed)


def pkcs7_unpad(data: bytes, block_size: int) -> bytes:
    if not data:
        raise DPAPINGError("decrypted DPAPI payload is empty")
    pad = data[-1]
    if pad == 0 or pad > block_size:
        return data
    if data[-pad:] != bytes([pad]) * pad:
        return data
    return data[:-pad]


def decrypt_dpapi_blob(dpapi_blob: bytes, masterkey: bytes, entropy: bytes = b"") -> bytes:
    blob = parse_dpapi_blob(dpapi_blob)
    if blob.alg_hash not in ALG_HASH:
        raise DPAPINGError(f"unsupported DPAPI hash algorithm 0x{blob.alg_hash:08x}")
    if blob.alg_crypt not in ALG_CRYPT:
        raise DPAPINGError(f"unsupported DPAPI cipher algorithm 0x{blob.alg_crypt:08x}")

    hash_name, _digest_len, hash_block_size = ALG_HASH[blob.alg_hash]
    cipher_name, key_len, iv_len, block_size = ALG_CRYPT[blob.alg_crypt]

    key_hash = hashlib.sha1(masterkey).digest()
    session_msg = blob.salt + entropy
    session_key = hmac.new(key_hash, session_msg, hash_name).digest()
    derived_key = (
        hmac.new(session_key, b"", hash_name).digest()
        if len(session_key) > hash_block_size
        else session_key
    )

    if len(derived_key) < key_len:
        padded = derived_key + bytes(hash_block_size)
        ipad = xor_bytes(0x36, padded)[:hash_block_size]
        opad = xor_bytes(0x5C, padded)[:hash_block_size]
        derived_key = fix_des_parity(
            hashlib.new(hash_name, ipad).digest() + hashlib.new(hash_name, opad).digest()
        )

    key = derived_key[:key_len]
    iv = bytes(iv_len)
    if cipher_name == "AES":
        cipher = AES.new(key, AES.MODE_CBC, iv)
    elif cipher_name == "3DES":
        cipher = DES3.new(key, DES3.MODE_CBC, iv)
    else:
        raise DPAPINGError(f"unsupported DPAPI cipher {cipher_name}")

    cleartext = pkcs7_unpad(cipher.decrypt(blob.data), block_size)

    ipad = xor_bytes(0x36, key_hash + bytes(hash_block_size))[:hash_block_size]
    opad = xor_bytes(0x5C, key_hash + bytes(hash_block_size))[:hash_block_size]
    hmac1_data = (
        hashlib.new(hash_name, ipad + blob.hmac2_key).digest()
        + entropy
        + blob.to_sign
    )
    hmac1 = hashlib.new(hash_name, opad + hmac1_data).digest()
    hmac3 = hmac.new(key_hash, blob.hmac2_key + entropy + blob.to_sign, hash_name).digest()

    if not (hmac.compare_digest(hmac1, blob.sign) or hmac.compare_digest(hmac3, blob.sign)):
        raise DPAPINGError("embedded DPAPI blob HMAC check failed")

    return cleartext


def decrypt_dpapi_ng(blob_data: bytes, masterkey: bytes, entropy: bytes = b"") -> bytes:
    dpapi_blob, wrapped_key, nonce, encrypted_data = extract_cng_fields(blob_data)
    kek = decrypt_dpapi_blob(dpapi_blob, masterkey, entropy)
    content_key = AES.new(kek, AES.MODE_KW).unseal(wrapped_key)
    cipher = AES.new(content_key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = encrypted_data[:-16], encrypted_data[-16:]
    return cipher.decrypt_and_verify(ciphertext, tag)


def read_input(path_or_hex: str, is_hex: bool) -> bytes:
    if is_hex:
        try:
            return bytes.fromhex(path_or_hex)
        except ValueError as exc:
            raise DPAPINGError(f"invalid hex input: {exc}") from exc
    with open(path_or_hex, "rb") as handle:
        return handle.read()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Decrypt a raw DPAPI-NG/CNG blob with a raw decrypted DPAPI masterkey."
    )
    parser.add_argument("masterkey", help="raw decrypted masterkey file, or hex with --masterkey-hex")
    parser.add_argument("blob", help="raw DPAPI-NG blob file, or hex with --blob-hex")
    parser.add_argument("-o", "--out", help="write raw plaintext to this file instead of stdout")
    parser.add_argument("--entropy", default="", help="optional entropy file, or hex with --entropy-hex")
    parser.add_argument("--masterkey-hex", action="store_true", help="treat masterkey argument as hex")
    parser.add_argument("--blob-hex", action="store_true", help="treat blob argument as hex")
    parser.add_argument("--entropy-hex", action="store_true", help="treat entropy argument as hex")
    parser.add_argument("--print-hex", action="store_true", help="print plaintext as hex text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        masterkey = read_input(args.masterkey, args.masterkey_hex)
        blob = read_input(args.blob, args.blob_hex)
        entropy = read_input(args.entropy, args.entropy_hex) if args.entropy else b""
        plaintext = decrypt_dpapi_ng(blob, masterkey, entropy)
    except (OSError, ValueError, DPAPINGError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = plaintext.hex().encode("ascii") + b"\n" if args.print_hex else plaintext
    if args.out:
        with open(args.out, "wb") as handle:
            handle.write(output)
    else:
        sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
