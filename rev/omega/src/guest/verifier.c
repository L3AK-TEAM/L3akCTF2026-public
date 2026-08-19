/* verifier.c -- in-VM PRX MAC verifier. */
#include "sha256.h"
#include "syscall.h"

#define STDIN 0
#define MAX_SECRET 256
#define CHUNK 512

#define EXIT_VALID 0
#define EXIT_INVALID 1
#define EXIT_MALFORMED 2

/* Read exactly n bytes from stdin; -1 if EOF arrives first. */
static int read_full(void *buf, uint32_t n) {
    uint8_t *p = (uint8_t *)buf;
    uint32_t got = 0;
    while (got < n) {
        long r = _syscall(SYS_read, STDIN, (long)(void *)(p + got), n - got);
        if (r <= 0)
            return -1;
        got += (uint32_t)r;
    }
    return 0;
}

static uint32_t le32(const uint8_t b[4]) {
    return (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) |
           ((uint32_t)b[3] << 24);
}

static int verify(void) {
    uint8_t lenbuf[4];
    uint8_t secret[MAX_SECRET];
    uint8_t chunk[CHUNK];
    uint8_t expect[32];
    uint8_t tag[32];

    /* secret */
    if (read_full(lenbuf, 4))
        return EXIT_MALFORMED;
    uint32_t slen = le32(lenbuf);
    if (slen > MAX_SECRET || read_full(secret, slen))
        return EXIT_MALFORMED;

    /* Stream SHA256(secret || message) without buffering the whole message. */
    sha256_ctx ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, secret, slen);

    if (read_full(lenbuf, 4))
        return EXIT_MALFORMED;
    for (uint32_t mlen = le32(lenbuf); mlen;) {
        uint32_t take = mlen < CHUNK ? mlen : CHUNK;
        if (read_full(chunk, take))
            return EXIT_MALFORMED;
        sha256_update(&ctx, chunk, take);
        mlen -= take;
    }
    sha256_final(&ctx, expect);

    if (read_full(tag, 32))
        return EXIT_MALFORMED;

    uint8_t diff = 0;
    for (int i = 0; i < 32; i++)
        diff |= (uint8_t)(expect[i] ^ tag[i]);
    return diff ? EXIT_INVALID : EXIT_VALID;
}

void _exit(int code) {
    _syscall(SYS_exit, code);
}

void _start(void) {
    _exit(verify());
}
