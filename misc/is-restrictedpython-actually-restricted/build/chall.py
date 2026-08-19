#!/usr/local/bin/python3
from __future__ import annotations

import base64
import binascii
import os
from pathlib import Path
import sys
import warnings

from RestrictedPython import PrintCollector
from RestrictedPython import compile_restricted
from RestrictedPython import safe_globals
from RestrictedPython.Eval import default_guarded_getitem
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import full_write_guard
from RestrictedPython.Guards import guarded_iter_unpack_sequence
from RestrictedPython.Guards import guarded_unpack_sequence
from RestrictedPython.Guards import safer_getattr


MAX_SOURCE_BYTES = 8 * 1024
MAX_WIRE_BYTES = 12 * 1024
TERMINATOR = b"EOL"


def read_source() -> tuple[str, bytes]:
    print(
        "Submit one base64-encoded Python program, then EOL:",
        flush=True,
    )
    wire = sys.stdin.buffer.readline(MAX_WIRE_BYTES + 1)
    if not wire or len(wire) > MAX_WIRE_BYTES:
        raise SystemExit("invalid submission")

    marker = sys.stdin.buffer.readline(len(TERMINATOR) + 3)
    if marker.strip() != TERMINATOR:
        raise SystemExit("expected EOL")

    encoded = wire.rstrip(b"\r\n")
    remainder = len(encoded) % 4
    if not encoded or remainder == 1:
        raise SystemExit("invalid submission")
    padded = encoded + (b"=" * ((4 - remainder) % 4))

    try:
        raw = base64.b64decode(padded, validate=True)
        source = raw.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        raise SystemExit("invalid submission") from None

    if len(raw) > MAX_SOURCE_BYTES:
        raise SystemExit("program too large")
    return source, raw


def get_submission_path() -> Path:
    if len(sys.argv) == 1:
        os.chdir(os.environ.get("CHALLENGE_WORKDIR", "."))
        sys.argv.append("submission.py")
    elif len(sys.argv) != 2:
        raise SystemExit("service misconfigured")

    path = Path(sys.argv[1])
    if path.is_absolute() or path.name != str(path) or path.suffix != ".py":
        raise SystemExit("service misconfigured")
    sys.path.insert(0, str(Path.cwd()))
    return path


def execute(source: str, filename: str) -> None:
    namespace = safe_globals.copy()
    namespace.update({
        "__name__": "0x1622",
        "__metaclass__": type,
        "_getattr_": safer_getattr,
        "_getitem_": default_guarded_getitem,
        "_getiter_": default_guarded_getiter,
        "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
        "_print_": PrintCollector,
        "_unpack_sequence_": guarded_unpack_sequence,
        "_write_": full_write_guard,
    })

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        try:
            code = compile_restricted(
                source,
                filename=filename,
                mode="exec",
            )
        except SyntaxError:
            print("Wrong!", flush=True)
            return
    exec(code, namespace, namespace)

    collector = namespace.get("_print")
    output = collector() if isinstance(collector, PrintCollector) else ""

    flag_path = Path("/flag.txt")
    if not flag_path.is_file():
        flag_path = Path(__file__).resolve().with_name("flag.txt")
    flag = flag_path.read_text(encoding="utf-8").strip()

    if flag and flag in output.splitlines():
        print(flag, flush=True)
    else:
        wrong_responses = (
            "Wrong!"
        )
        print(wrong_responses, flush=True)


def main() -> None:
    source, raw = read_source()
    path = get_submission_path()
    path.write_bytes(raw)
    execute(source, str(path))


if __name__ == "__main__":
    main()