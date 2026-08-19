/* sha256.h - hand-rolled SHA-256 (FIPS 180-4). */
#ifndef SHA256_H
#define SHA256_H 1

#include <stddef.h>
#include <stdint.h>

/* ---- SHA-256 (FIPS 180-4) streaming context ---- */
typedef struct {
    uint32_t state[8];  /* chaining state: the IV at init, the digest at end */
    uint64_t bitlen;    /* total message bits absorbed so far                */
    uint8_t buffer[64]; /* unprocessed tail (< 64 bytes)                     */
    size_t buflen;      /* valid bytes currently in `buffer`                 */
} sha256_ctx;

void sha256_init(sha256_ctx *c);
void sha256_update(sha256_ctx *c, const void *data, size_t len);
void sha256_final(sha256_ctx *c, uint8_t out[32]);
void sha256(const void *data, size_t len, uint8_t out[32]);

#endif /* SHA256_H */
