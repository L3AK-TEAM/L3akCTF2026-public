#ifndef WHATWHO_H
#define WHATWHO_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define WW_MAGIC "\x89WWHO\r\n\x1a"
#define WW_VERSION 3u
#define WW_HEADER_SIZE 64u
#define WW_CARD_SIZE 12u

#define WW_DATA_BASE 0x2000u
#define WW_INPUT_BASE 0x0800u
#define WW_MEMORY_SIZE 0x6000u
#define WW_INPUT_CAP 192u
#define WW_STACK_CAP 192u
#define WW_REGISTER_COUNT 8u
#define WW_STEP_LIMIT 2000000u

#define WW_DOMAIN_CODE UINT64_C(0x434152445F564549)
#define WW_DOMAIN_DATA UINT64_C(0x4C45444745525F56)

enum ww_face {
    FACE_WHAT = 0,
    FACE_WHO = 1,
};

enum ww_query_format {
    QUERY_RAW = 0,
    QUERY_HEX32 = 1,
    QUERY_HEX64 = 2,
    QUERY_HEX128 = 3,
    QUERY_DEC64 = 4,
};

/*
 * WHAT glyphs operate on eight shared 64-bit registers.  Their deliberately
 * sparse values are part of the challenge's on-disk instruction alphabet.
 */
enum ww_what_glyph {
    W_MOVI    = 0xA7,
    W_MOV     = 0x39,
    W_LDBX    = 0xD2,
    W_ADD     = 0x4B,
    W_ADDI    = 0xF0,
    W_XOR     = 0x16,
    W_XORI    = 0x8D,
    W_MUL     = 0xC3,
    W_MULI    = 0x52,
    W_ANDI    = 0xE8,
    W_SHLI    = 0x25,
    W_SHRI    = 0xB4,
    W_ROLI    = 0x69,
    W_RORI    = 0x9A,
    W_ROL32I  = 0x71,
    W_ROR32I  = 0x06,
    W_CMP     = 0xDD,
    W_CMPI    = 0x43,
    W_JEQ     = 0xBC,
    W_JNE     = 0x2E,
    W_JMP     = 0x95,
    W_QUERY   = 0x5F,
    W_NONCE   = 0xCA,
    W_TRAIL   = 0x31,
    W_MARK    = 0x7B,
    W_REVEAL  = 0xE1,
    W_FLIP    = 0x0C,
    W_HALT    = 0xF7,
};

/*
 * WHO glyphs are a postfix machine.  The active face is execution state, not
 * metadata attached to a card: only FLIP changes how the next glyph is read.
 */
enum ww_who_glyph {
    H_PUSHI   = 0x44,
    H_PUSHR   = 0x9D,
    H_POPR    = 0x23,
    H_DUP     = 0xF2,
    H_SWAP    = 0x68,
    H_DROP    = 0xB1,
    H_LDB     = 0x0F,
    H_LD16    = 0xC8,
    H_LD64LE  = 0x75,
    H_LD64BE  = 0xA3,
    H_ADD     = 0x37,
    H_SUB     = 0xDE,
    H_XOR     = 0x82,
    H_MUL     = 0x19,
    H_AND     = 0xEF,
    H_OR      = 0x56,
    H_SHL     = 0xC1,
    H_SHR     = 0x2A,
    H_ROL     = 0x97,
    H_ROR     = 0x4C,
    H_ROL8    = 0xD5,
    H_MOD     = 0x6B,
    H_EQ      = 0x14,
    H_JZ      = 0xAB,
    H_JNZ     = 0x7E,
    H_JMP     = 0x30,
    H_FLIP    = 0xFA,
    H_HALT    = 0x5C,
};

typedef struct __attribute__((packed)) {
    uint8_t magic[8];
    uint16_t version;
    uint16_t header_size;
    uint32_t card_count;
    uint32_t data_size;
    uint32_t entry_card;
    uint64_t salt;
    uint64_t code_seal;
    uint64_t data_seal;
    uint8_t cartridge_id[16];
} ww_header;

typedef struct __attribute__((packed)) {
    uint8_t glyph;
    uint8_t x;
    uint8_t y;
    uint8_t z;
    uint64_t arg;
} ww_card;

typedef struct {
    ww_card *cards;
    uint32_t card_count;
    uint32_t entry_card;
    uint8_t *data;
    uint32_t data_size;
} ww_cartridge;

typedef struct {
    const ww_cartridge *cart;
    uint64_t regs[WW_REGISTER_COUNT];
    uint64_t stack[WW_STACK_CAP];
    size_t sp;
    uint8_t memory[WW_MEMORY_SIZE];
    uint8_t last_input[WW_INPUT_CAP];
    size_t last_input_len;
    uint32_t ip;
    uint32_t steps;
    uint8_t face;
    uint8_t gate_mask;
    uint8_t next_gate;
    bool equal;
    bool halted;
    bool faulted;
    uint64_t nonce;
    uint64_t trail;
    const char *flag;
} ww_vm;

bool ww_load_cartridge(const char *path, ww_cartridge *out);
void ww_free_cartridge(ww_cartridge *cart);
bool ww_run(const ww_cartridge *cart, uint64_t nonce, const char *flag);

uint64_t ww_rotl64(uint64_t value, unsigned count);
uint64_t ww_rotr64(uint64_t value, unsigned count);
uint64_t ww_seal(const uint8_t *bytes, size_t length, uint64_t domain);
uint8_t ww_unveil_byte(uint8_t byte, uint64_t salt, size_t position,
                       uint64_t domain);
uint64_t ww_initial_trail(uint64_t nonce);

#endif
