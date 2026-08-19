# L3aky Canvas

### Author: NeX

## TL;DR

This challenge has 2 bugs. A path-traversal file read and a one-byte arbitrary write. Use them together to patch the login check inside the running server. First read `/proc/self/maps` to beat ASLR, patch the `sete` in `auth_check` to `setne` through `/proc/self/mem` with a single byte write, then log in with any credentials. The moderator page then lists the rooms and reveals the flag's randomly named file. Use the same file read to finally read the flag.

## The two primitives

**Read:** `GET /canvas?room=<path>` joins the path with `PathBuf::push`, so an absolute `room` escapes `/srv/rooms` and any file is rendered back as a grayscale BMP (`offset` pages through it). That's enough to read `/proc/self/maps`.

**Write:** `POST /pixel` checks `(x as u8) < 64` but builds the write offset from the full 64-bit `x` and `y`, so the "pixel" is really a one-byte write to any offset. Point `room` at `/proc/self/mem` and it writes into the process itself.

## Solution

`auth_check` is a "login" funcion and the login always returns false. The decision compiles to a single `sete al`, and turning it into `setne` makes every login succeed.

1. Read `/proc/self/maps` via `/canvas` and grab the base of the `r-xp` mapping of `l3aky-canvas`.
2. In your copy of the binary, find `auth_check`'s tail `3B 4C 24 FC 0F 94 C0 C3` (it's unique) and take the offset of the `0F 94`.
3. Turn that file offset into a runtime address using the `r-xp` segment.
4. Write `0x95` there with `POST /pixel room=/proc/self/mem`, using `y` in `0..3` and `x = addr - 64*y` so both low bytes stay under 64 and the check passes.
5. `POST /login` with anything. The reply lists the folder `/srv/rooms`, including `flag-<hex>.bin`.
6. `GET /canvas?room=flag-<hex>.bin` and decode it.

The room named `flag` is a decoy. It shows a fake `L4AK{...}`. Notice the 4 instead of 3 in the flag format. And stores the same text as plain bytes for `strings`. The real flag is the random file.


## Flag

```
L3AK{0n3_byt3_t0_rul3_th3m_4ll}
```
