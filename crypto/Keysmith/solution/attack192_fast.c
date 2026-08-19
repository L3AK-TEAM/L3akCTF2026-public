#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static const uint8_t SBOX[256] = {
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16
};

static const uint8_t MASTER_DIFF[24] = {
    0x31,0x31,0x56,0x62,0x31,0x31,0x56,0x2a,0x31,0x31,0x53,0x62,
    0x31,0x31,0x53,0x2a,0x00,0x00,0x00,0x48,0x00,0x00,0x00,0x00
};

static const uint8_t DX0[16] = {0x31,0x31,0x56,0x62,0x31,0x31,0x56,0x2a,0x31,0x31,0x53,0x62,0x31,0x31,0x53,0x2a};
static const uint8_t DY0[16] = {0x87,0xc0,0xbd,0x65,0xda,0x9c,0x57,0x94,0x3e,0xf4,0x07,0xfa,0x7b,0xae,0xcd,0xad};
static const uint8_t DX1[16] = {0x00,0x00,0xf9,0x00,0x00,0x00,0x00,0x86,0x8d,0x00,0x00,0x00,0x00,0xe3,0x00,0xbd};
static const uint8_t DY1[16] = {0x00,0x00,0xae,0x00,0x00,0x00,0x00,0xdd,0x3e,0x00,0x00,0x00,0x00,0x05,0x00,0x31};

typedef struct {
    uint8_t v[256];
    int n;
} list_t;

static uint8_t INV_SBOX[256];
static uint8_t INV_GMUL3[256];
static list_t X0C[16], X1_2, X1_7, X1_8, X1_13, X1_15, K2_15_SW, X2_3, X2_15;

static inline uint8_t xtime8(uint8_t x) {
    return (uint8_t)((x << 1) ^ ((x & 0x80) ? 0x1b : 0));
}

static inline uint8_t gmul2(uint8_t x) {
    return xtime8(x);
}

static inline uint8_t gmul3(uint8_t x) {
    return (uint8_t)(xtime8(x) ^ x);
}

static inline int sbox_diff_ok(uint8_t x, uint8_t dx, uint8_t dy) {
    return (uint8_t)(SBOX[x] ^ SBOX[x ^ dx]) == dy;
}

static void ddt_build(list_t *out, uint8_t dx, uint8_t dy) {
    out->n = 0;
    for (int x = 0; x < 256; x++) {
        if (sbox_diff_ok((uint8_t)x, dx, dy)) {
            out->v[out->n++] = (uint8_t)x;
        }
    }
}

static void init_tables(void) {
    for (int i = 0; i < 256; i++) INV_SBOX[SBOX[i]] = (uint8_t)i;
    for (int i = 0; i < 256; i++) INV_GMUL3[gmul3((uint8_t)i)] = (uint8_t)i;
    for (int i = 0; i < 16; i++) ddt_build(&X0C[i], DX0[i], DY0[i]);
    ddt_build(&X1_2, 0xf9, 0xae);
    ddt_build(&X1_7, 0x86, 0xdd);
    ddt_build(&X1_8, 0x8d, 0x3e);
    ddt_build(&X1_13, 0xe3, 0x05);
    ddt_build(&X1_15, 0xbd, 0x31);
    ddt_build(&K2_15_SW, 0x48, 0x05);
    ddt_build(&X2_3, 0x48, 0x31);
    ddt_build(&X2_15, 0x48, 0x31);
}

static inline uint64_t rng_next(uint64_t *s) {
    uint64_t x = *s;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    *s = x;
    return x * UINT64_C(2685821657736338717);
}

static inline uint8_t choice(uint64_t *rng, const list_t *lst) {
    return lst->v[rng_next(rng) % (uint64_t)lst->n];
}

static void mix_columns(const uint8_t in[16], uint8_t out[16]) {
    for (int c = 0; c < 4; c++) {
        const uint8_t *p = in + 4 * c;
        uint8_t a0 = p[0], a1 = p[1], a2 = p[2], a3 = p[3];
        uint8_t t = a0 ^ a1 ^ a2 ^ a3;
        uint8_t u = a0;
        out[4*c + 0] = (uint8_t)(a0 ^ t ^ xtime8(a0 ^ a1));
        out[4*c + 1] = (uint8_t)(a1 ^ t ^ xtime8(a1 ^ a2));
        out[4*c + 2] = (uint8_t)(a2 ^ t ^ xtime8(a2 ^ a3));
        out[4*c + 3] = (uint8_t)(a3 ^ t ^ xtime8(a3 ^ u));
    }
}

static void shift_rows(const uint8_t in[16], uint8_t out[16]) {
    out[0]  = in[0];  out[4]  = in[4];  out[8]  = in[8];  out[12] = in[12];
    out[1]  = in[5];  out[5]  = in[9];  out[9]  = in[13]; out[13] = in[1];
    out[2]  = in[10]; out[6]  = in[14]; out[10] = in[2];  out[14] = in[6];
    out[3]  = in[15]; out[7]  = in[3];  out[11] = in[7];  out[15] = in[11];
}

static void expand_key_192(const uint8_t key[24], uint8_t rks[6][16]) {
    uint8_t w[24][4];
    static const uint8_t rcon[8] = {0,1,2,4,8,0x10,0x20,0x40};
    for (int i = 0; i < 6; i++) memcpy(w[i], key + 4*i, 4);
    for (int i = 6; i < 24; i++) {
        uint8_t t[4];
        memcpy(t, w[i-1], 4);
        if (i % 6 == 0) {
            uint8_t r = t[0];
            t[0] = SBOX[t[1]] ^ rcon[i/6];
            t[1] = SBOX[t[2]];
            t[2] = SBOX[t[3]];
            t[3] = SBOX[r];
        }
        for (int j = 0; j < 4; j++) w[i][j] = (uint8_t)(w[i-6][j] ^ t[j]);
    }
    for (int r = 0; r < 6; r++) {
        for (int i = 0; i < 4; i++) memcpy(rks[r] + 4*i, w[4*r + i], 4);
    }
}

static void aes192_5round(const uint8_t pt[16], const uint8_t key[24], uint8_t out[16]) {
    uint8_t rks[6][16], st[16], tmp[16], tmp2[16];
    expand_key_192(key, rks);
    for (int i = 0; i < 16; i++) st[i] = pt[i] ^ rks[0][i];
    for (int r = 1; r < 5; r++) {
        for (int i = 0; i < 16; i++) tmp[i] = SBOX[st[i]];
        shift_rows(tmp, tmp2);
        mix_columns(tmp2, tmp);
        for (int i = 0; i < 16; i++) st[i] = tmp[i] ^ rks[r][i];
    }
    for (int i = 0; i < 16; i++) tmp[i] = SBOX[st[i]];
    shift_rows(tmp, tmp2);
    for (int i = 0; i < 16; i++) out[i] = tmp2[i] ^ rks[5][i];
}

static int parse_hex(const char *hex, uint8_t *out, size_t outlen) {
    size_t n = strlen(hex);
    if (n != outlen * 2) return 0;
    for (size_t i = 0; i < outlen; i++) {
        unsigned int x;
        if (sscanf(hex + 2*i, "%2x", &x) != 1) return 0;
        out[i] = (uint8_t)x;
    }
    return 1;
}

static void print_hex_line(const char *name, const uint8_t *buf, size_t len) {
    printf("%s=", name);
    for (size_t i = 0; i < len; i++) printf("%02x", buf[i]);
    putchar('\n');
}

static int try_one(uint64_t *rng, const uint8_t pt[16], uint8_t key[24], uint8_t other[24], uint8_t digest[16]) {
    uint8_t x0[16], y0[16], z0[16], w0[16];

    for (int i = 0; i < 16; i++) x0[i] = choice(rng, &X0C[i]);
    for (int i = 0; i < 16; i++) y0[i] = SBOX[x0[i]];
    shift_rows(y0, z0);
    mix_columns(z0, w0);

    uint8_t x1[8] = {0};
    uint8_t x1_4_pre = choice(rng, &X1_15);
    uint8_t x1_5_pre = choice(rng, &X1_8);
    uint8_t x1_6_pre = choice(rng, &X1_13);
    x1[4] = (uint8_t)(w0[4] ^ INV_SBOX[x1_4_pre ^ w0[15] ^ pt[7] ^ x0[7] ^ pt[3] ^ x0[3]]);
    x1[5] = (uint8_t)(w0[5] ^ INV_SBOX[x1_5_pre ^ w0[8] ^ pt[0] ^ x0[0] ^ 0x01]);
    x1[6] = (uint8_t)(w0[6] ^ INV_SBOX[x1_6_pre ^ w0[13] ^ pt[5] ^ x0[5] ^ pt[1] ^ x0[1]]);
    x1[7] = choice(rng, &X1_7);

    uint8_t w5_0 = (uint8_t)(w0[4] ^ x1[4]);
    uint8_t w5_3 = (uint8_t)(w0[7] ^ x1[7]);
    uint8_t base_k2_15 = (uint8_t)(
        w5_3 ^ pt[15] ^ x0[15] ^ pt[11] ^ x0[11] ^
        pt[7] ^ x0[7] ^ pt[3] ^ x0[3] ^ SBOX[w5_0]
    );
    x1[3] = (uint8_t)(w0[3] ^ base_k2_15 ^ choice(rng, &K2_15_SW));

    uint8_t prefix[24], rks[6][16], x1_full[16], y1[16];
    for (int i = 0; i < 16; i++) prefix[i] = pt[i] ^ x0[i];
    for (int i = 0; i < 8; i++) prefix[16+i] = w0[i] ^ x1[i];
    expand_key_192(prefix, rks);
    for (int i = 0; i < 16; i++) {
        x1_full[i] = (uint8_t)(w0[i] ^ rks[1][i]);
        y1[i] = SBOX[x1_full[i]];
    }

    uint8_t base_x2_3 = (uint8_t)(y1[5] ^ y1[10] ^ gmul2(y1[15]) ^ rks[2][3]);
    uint8_t base_x2_15 = (uint8_t)(gmul3(y1[12]) ^ y1[6] ^ gmul2(y1[11]) ^ rks[2][15]);
    x1[0] = INV_SBOX[INV_GMUL3[choice(rng, &X2_3) ^ base_x2_3]];
    x1[1] = INV_SBOX[choice(rng, &X2_15) ^ base_x2_15];
    x1[2] = choice(rng, &X1_2);

    for (int i = 0; i < 16; i++) key[i] = pt[i] ^ x0[i];
    for (int i = 0; i < 8; i++) key[16+i] = w0[i] ^ x1[i];
    for (int i = 0; i < 24; i++) other[i] = key[i] ^ MASTER_DIFF[i];

    uint8_t d2[16];
    aes192_5round(pt, key, digest);
    aes192_5round(pt, other, d2);
    return memcmp(digest, d2, 16) == 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s PLAINTEXT_HEX [MAX_CANDIDATES] [SEED]\n", argv[0]);
        return 2;
    }

    uint8_t pt[16], key[24], other[24], digest[16];
    if (!parse_hex(argv[1], pt, 16)) {
        fprintf(stderr, "bad plaintext hex\n");
        return 2;
    }

    uint64_t max_candidates = argc >= 3 ? strtoull(argv[2], NULL, 0) : UINT64_C(200000000);
    uint64_t rng = argc >= 4 ? strtoull(argv[3], NULL, 0) : ((uint64_t)time(NULL) ^ UINT64_C(0xa35192));
    if (rng == 0) rng = UINT64_C(0x9e3779b97f4a7c15);

    init_tables();
    for (uint64_t tested = 1; tested <= max_candidates; tested++) {
        if (try_one(&rng, pt, key, other, digest)) {
            print_hex_line("key1", key, 24);
            print_hex_line("key2", other, 24);
            print_hex_line("digest", digest, 16);
            printf("candidates=%llu\n", (unsigned long long)tested);
            return 0;
        }
    }

    fprintf(stderr, "no collision found in %llu candidates\n", (unsigned long long)max_candidates);
    return 1;
}

