#!/usr/bin/env python3
"""prx_mac.py -- secret-prefix Merkle-Damgard MAC."""

import hashlib

MAC_OFFSET = 0x10          # e_mac field offset within the file header
MAC_SIZE = 32              # SHA-256 digest length, in bytes
MAC_COVERAGE_START = 0x30  # first authenticated byte: file[0x30 .. EOF]


def secret_prefix_mac(secret: bytes, message: bytes) -> bytes:
    """tag = SHA-256(secret || message)"""
    return hashlib.sha256(secret + message).digest()


def prx_message(prx: bytes) -> bytes:
    """The authenticated region of a PRX file: file[0x30 .. EOF]"""
    return prx[MAC_COVERAGE_START:]


def sign_prx(secret: bytes, prx: bytes) -> bytes:
    return secret_prefix_mac(secret, prx_message(prx))

