#include "whatwho.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(ww_header) == WW_HEADER_SIZE, "vault.wwc header size");
_Static_assert(sizeof(ww_card) == WW_CARD_SIZE, "card size");

uint64_t ww_rotl64(uint64_t value, unsigned count) {
    count &= 63u;
    if (count == 0u) {
        return value;
    }
    return (value << count) | (value >> (64u - count));
}

uint64_t ww_rotr64(uint64_t value, unsigned count) {
    count &= 63u;
    if (count == 0u) {
        return value;
    }
    return (value >> count) | (value << (64u - count));
}

static uint8_t rotl8(uint8_t value, unsigned count) {
    count &= 7u;
    if (count == 0u) {
        return value;
    }
    return (uint8_t)((value << count) | (value >> (8u - count)));
}

static uint64_t stir(uint64_t value) {
    value ^= value >> 27;
    value *= UINT64_C(0x3C79AC492BA7B653);
    value ^= value >> 33;
    value *= UINT64_C(0x1C69B3F74AC4AE35);
    value ^= value >> 27;
    return value;
}

uint8_t ww_unveil_byte(uint8_t byte, uint64_t salt, size_t position,
                       uint64_t domain) {
    uint64_t lane = salt ^ domain;
    lane ^= (uint64_t)(position + 1u) * UINT64_C(0xA24BAED4963EE407);
    lane = stir(lane);

    unsigned shift = (unsigned)((position * 5u) & 56u);
    uint8_t key = (uint8_t)(lane >> shift);
    unsigned rotation = (unsigned)((salt + (position * 3u) + domain) & 7u);
    uint8_t bias =
        (uint8_t)((position * 29u) + (salt >> 16) + (domain >> 8));

    return (uint8_t)(rotl8((uint8_t)(byte ^ key), rotation) - bias);
}

uint64_t ww_seal(const uint8_t *bytes, size_t length, uint64_t domain) {
    uint64_t hash =
        domain ^ ((uint64_t)length * UINT64_C(0x9E6C63D0676A9A99));

    for (size_t i = 0; i < length; ++i) {
        hash ^= (uint64_t)bytes[i] +
                ((uint64_t)(i + 1u) * UINT64_C(0x6A09E667F3BCC909));
        hash = ww_rotl64(hash, 13);
        hash *= UINT64_C(0xD6E8FEB86659FD93);
        hash ^= hash >> 29;
    }

    hash ^= hash >> 32;
    hash *= UINT64_C(0xBEA225F9EB34556D);
    hash ^= hash >> 31;
    hash *= UINT64_C(0x94D049BB133111EB);
    hash ^= hash >> 30;
    return hash;
}

static bool read_exact(FILE *stream, void *destination, size_t length) {
    return fread(destination, 1, length, stream) == length;
}

static bool valid_header(const ww_header *header, size_t file_size) {
    if (memcmp(header->magic, WW_MAGIC, sizeof(header->magic)) != 0) {
        return false;
    }
    if (header->version != WW_VERSION ||
        header->header_size != WW_HEADER_SIZE) {
        return false;
    }
    if (header->card_count == 0u || header->card_count > 100000u ||
        header->data_size > (WW_MEMORY_SIZE - WW_DATA_BASE) ||
        header->entry_card >= header->card_count) {
        return false;
    }

    uint64_t expected = (uint64_t)WW_HEADER_SIZE +
                     ((uint64_t)header->card_count * WW_CARD_SIZE) +
                        header->data_size;
    return expected == file_size;
}

bool ww_load_cartridge(const char *path, ww_cartridge *out) {
    memset(out, 0, sizeof(*out));

    FILE *stream = fopen(path, "rb");
    if (stream == NULL) {
        fprintf(stderr, "vault.wwc unavailable: %s\n", strerror(errno));
        return false;
    }

    if (fseek(stream, 0, SEEK_END) != 0) {
        fclose(stream);
        return false;
    }
    long file_length = ftell(stream);
    if (file_length < 0 || fseek(stream, 0, SEEK_SET) != 0) {
        fclose(stream);
        return false;
    }

    ww_header header;
    if (!read_exact(stream, &header, sizeof(header)) ||
        !valid_header(&header, (size_t)file_length)) {
        fprintf(stderr, "vault.wwc header rejected\n");
        fclose(stream);
        return false;
    }

    size_t code_length = (size_t)header.card_count * WW_CARD_SIZE;
    uint8_t *code_bytes = malloc(code_length);
    uint8_t *data_bytes = malloc(header.data_size == 0u ? 1u : header.data_size);
    if (code_bytes == NULL || data_bytes == NULL) {
        free(code_bytes);
        free(data_bytes);
        fclose(stream);
        return false;
    }

    if (!read_exact(stream, code_bytes, code_length) ||
        !read_exact(stream, data_bytes, header.data_size)) {
        fprintf(stderr, "truncated vault.wwc\n");
        free(code_bytes);
        free(data_bytes);
        fclose(stream);
        return false;
    }
    fclose(stream);

    for (size_t i = 0; i < code_length; ++i) {
        code_bytes[i] =
            ww_unveil_byte(code_bytes[i], header.salt, i, WW_DOMAIN_CODE);
    }
    for (size_t i = 0; i < header.data_size; ++i) {
        data_bytes[i] =
            ww_unveil_byte(data_bytes[i], header.salt, i, WW_DOMAIN_DATA);
    }

    if (ww_seal(code_bytes, code_length, WW_DOMAIN_CODE) != header.code_seal ||
        ww_seal(data_bytes, header.data_size, WW_DOMAIN_DATA) !=
            header.data_seal) {
        fprintf(stderr, "vault.wwc seal mismatch\n");
        memset(code_bytes, 0, code_length);
        memset(data_bytes, 0, header.data_size);
        free(code_bytes);
        free(data_bytes);
        return false;
    }

    out->cards = (ww_card *)code_bytes;
    out->card_count = header.card_count;
    out->entry_card = header.entry_card;
    out->data = data_bytes;
    out->data_size = header.data_size;
    return true;
}

void ww_free_cartridge(ww_cartridge *cart) {
    if (cart == NULL) {
        return;
    }
    if (cart->cards != NULL) {
        memset(cart->cards, 0, (size_t)cart->card_count * WW_CARD_SIZE);
        free(cart->cards);
    }
    if (cart->data != NULL) {
        memset(cart->data, 0, cart->data_size);
        free(cart->data);
    }
    memset(cart, 0, sizeof(*cart));
}
