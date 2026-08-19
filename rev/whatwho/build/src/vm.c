#include "whatwho.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t rotl32(uint32_t value, unsigned count) {
    count &= 31u;
    if (count == 0u) {
        return value;
    }
    return (value << count) | (value >> (32u - count));
}

static uint32_t rotr32(uint32_t value, unsigned count) {
    count &= 31u;
    if (count == 0u) {
        return value;
    }
    return (value >> count) | (value << (32u - count));
}

static uint64_t avalanche(uint64_t value) {
    value ^= value >> 28;
    value *= UINT64_C(0xA3B195354A39B70D);
    value ^= value >> 33;
    value *= UINT64_C(0xF1357AEA2E62A9C5);
    value ^= value >> 29;
    return value;
}

uint64_t ww_initial_trail(uint64_t nonce) {
    return avalanche(nonce ^ UINT64_C(0x57484F5F57415443));
}

static uint64_t transcript_hash(const uint8_t *input, size_t length) {
    uint64_t hash =
        UINT64_C(0x243F6A8885A308D3) ^ ((uint64_t)length << 48);
    for (size_t i = 0; i < length; ++i) {
        hash ^= (uint64_t)input[i] +
                ((uint64_t)(i + 1u) * UINT64_C(0x9B1D2D6B42F0A7B5));
        hash = ww_rotl64(hash, 11);
        hash *= UINT64_C(0xD1342543DE82EF95);
        hash += UINT64_C(0xC6BC279692B5CC83);
    }
    return avalanche(hash);
}

static bool valid_register(uint8_t index) {
    return index < WW_REGISTER_COUNT;
}

static bool read_memory(const ww_vm *vm, uint64_t address, void *out,
                        size_t length) {
    if (address > WW_MEMORY_SIZE ||
        length > WW_MEMORY_SIZE - (size_t)address) {
        return false;
    }
    memcpy(out, vm->memory + (size_t)address, length);
    return true;
}

static bool read_u8(const ww_vm *vm, uint64_t address, uint64_t *out) {
    uint8_t value;
    if (!read_memory(vm, address, &value, sizeof(value))) {
        return false;
    }
    *out = value;
    return true;
}

static bool read_u16le(const ww_vm *vm, uint64_t address, uint64_t *out) {
    uint8_t bytes[2];
    if (!read_memory(vm, address, bytes, sizeof(bytes))) {
        return false;
    }
    *out = (uint64_t)bytes[0] | ((uint64_t)bytes[1] << 8);
    return true;
}

static bool read_u64le(const ww_vm *vm, uint64_t address, uint64_t *out) {
    uint8_t bytes[8];
    if (!read_memory(vm, address, bytes, sizeof(bytes))) {
        return false;
    }
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) {
        value |= (uint64_t)bytes[i] << (i * 8u);
    }
    *out = value;
    return true;
}

static bool read_u64be(const ww_vm *vm, uint64_t address, uint64_t *out) {
    uint8_t bytes[8];
    if (!read_memory(vm, address, bytes, sizeof(bytes))) {
        return false;
    }
    uint64_t value = 0;
    for (unsigned i = 0; i < 8; ++i) {
        value = (value << 8) | bytes[i];
    }
    *out = value;
    return true;
}

static bool push(ww_vm *vm, uint64_t value) {
    if (vm->sp == WW_STACK_CAP) {
        return false;
    }
    vm->stack[vm->sp++] = value;
    return true;
}

static bool pop(ww_vm *vm, uint64_t *out) {
    if (vm->sp == 0u) {
        return false;
    }
    *out = vm->stack[--vm->sp];
    return true;
}

static bool jump_to(ww_vm *vm, uint64_t target) {
    if (target >= vm->cart->card_count) {
        return false;
    }
    vm->ip = (uint32_t)target;
    return true;
}

static bool print_prompt(const ww_vm *vm, uint64_t address) {
    if (address >= WW_MEMORY_SIZE) {
        return false;
    }
    for (size_t i = (size_t)address; i < WW_MEMORY_SIZE; ++i) {
        uint8_t byte = vm->memory[i];
        if (byte == 0u) {
            fflush(stdout);
            return true;
        }
        if (fputc(byte, stdout) == EOF) {
            return false;
        }
    }
    return false;
}

static bool lower_hex(uint8_t byte) {
    return (byte >= '0' && byte <= '9') ||
           (byte >= 'a' && byte <= 'f');
}

static uint8_t nibble(uint8_t byte) {
    if (byte <= '9') {
        return (uint8_t)(byte - '0');
    }
    return (uint8_t)(byte - 'a' + 10);
}

static bool read_answer_line(ww_vm *vm, uint8_t max_length) {
    char line[WW_INPUT_CAP + 2u];
    if (fgets(line, sizeof(line), stdin) == NULL) {
        return false;
    }

    size_t length = strlen(line);
    bool had_newline = length > 0u && line[length - 1u] == '\n';
    if (had_newline) {
        line[--length] = '\0';
    } else if (length == WW_INPUT_CAP + 1u) {
        int byte;
        do {
            byte = fgetc(stdin);
        } while (byte != '\n' && byte != EOF);
        return false;
    }
    if (length > WW_INPUT_CAP ||
        (max_length != 0u && length > max_length)) {
        return false;
    }

    memcpy(vm->last_input, line, length);
    vm->last_input_len = length;
    return true;
}

static bool query(ww_vm *vm, const ww_card *card) {
    if (!valid_register(card->x) || !print_prompt(vm, card->arg)) {
        return false;
    }
    if (!read_answer_line(vm, card->z)) {
        return false;
    }

    memset(vm->memory + WW_INPUT_BASE, 0, WW_INPUT_CAP);

    switch (card->y) {
    case QUERY_RAW:
        memcpy(vm->memory + WW_INPUT_BASE, vm->last_input,
               vm->last_input_len);
        vm->regs[card->x] = vm->last_input_len;
        return true;

    case QUERY_HEX32:
    case QUERY_HEX64: {
        size_t wanted = card->y == QUERY_HEX32 ? 8u : 16u;
        if (vm->last_input_len != wanted) {
            return false;
        }
        uint64_t value = 0;
        for (size_t i = 0; i < wanted; ++i) {
            uint8_t byte = vm->last_input[i];
            if (!lower_hex(byte)) {
                return false;
            }
            value = (value << 4) | nibble(byte);
        }
        vm->regs[card->x] = value;
        return true;
    }

    case QUERY_HEX128:
        if (vm->last_input_len != 32u) {
            return false;
        }
        for (size_t i = 0; i < 16u; ++i) {
            uint8_t high = vm->last_input[i * 2u];
            uint8_t low = vm->last_input[i * 2u + 1u];
            if (!lower_hex(high) || !lower_hex(low)) {
                return false;
            }
            vm->memory[WW_INPUT_BASE + i] =
                (uint8_t)((nibble(high) << 4) | nibble(low));
        }
        vm->regs[card->x] = 16u;
        return true;

    case QUERY_DEC64: {
        if (vm->last_input_len == 0u) {
            return false;
        }
        if (vm->last_input_len > 1u && vm->last_input[0] == '0') {
            return false;
        }
        uint64_t value = 0;
        for (size_t i = 0; i < vm->last_input_len; ++i) {
            uint8_t byte = vm->last_input[i];
            if (byte < '0' || byte > '9') {
                return false;
            }
            uint64_t digit = (uint64_t)(byte - '0');
            if (value > (UINT64_MAX - digit) / 10u) {
                return false;
            }
            value = value * 10u + digit;
        }
        vm->regs[card->x] = value;
        return true;
    }

    default:
        return false;
    }
}

static bool execute_what(ww_vm *vm, const ww_card *card) {
    uint64_t address;

    switch (card->glyph) {
    case W_MOVI:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] = card->arg;
        return true;
    case W_MOV:
        if (!valid_register(card->x) || !valid_register(card->y)) return false;
        vm->regs[card->x] = vm->regs[card->y];
        return true;
    case W_LDBX:
        if (!valid_register(card->x) || !valid_register(card->y)) return false;
        address = card->arg + vm->regs[card->y];
        return read_u8(vm, address, &vm->regs[card->x]);
    case W_ADD:
        if (!valid_register(card->x) || !valid_register(card->y)) return false;
        vm->regs[card->x] += vm->regs[card->y];
        return true;
    case W_ADDI:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] += card->arg;
        return true;
    case W_XOR:
        if (!valid_register(card->x) || !valid_register(card->y)) return false;
        vm->regs[card->x] ^= vm->regs[card->y];
        return true;
    case W_XORI:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] ^= card->arg;
        return true;
    case W_MUL:
        if (!valid_register(card->x) || !valid_register(card->y)) return false;
        vm->regs[card->x] *= vm->regs[card->y];
        return true;
    case W_MULI:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] *= card->arg;
        return true;
    case W_ANDI:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] &= card->arg;
        return true;
    case W_SHLI:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] <<= (unsigned)(card->arg & 63u);
        return true;
    case W_SHRI:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] >>= (unsigned)(card->arg & 63u);
        return true;
    case W_ROLI:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] =
            ww_rotl64(vm->regs[card->x], (unsigned)card->arg);
        return true;
    case W_RORI:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] =
            ww_rotr64(vm->regs[card->x], (unsigned)card->arg);
        return true;
    case W_ROL32I:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] =
            rotl32((uint32_t)vm->regs[card->x], (unsigned)card->arg);
        return true;
    case W_ROR32I:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] =
            rotr32((uint32_t)vm->regs[card->x], (unsigned)card->arg);
        return true;
    case W_CMP:
        if (!valid_register(card->x) || !valid_register(card->y)) return false;
        vm->equal = vm->regs[card->x] == vm->regs[card->y];
        return true;
    case W_CMPI:
        if (!valid_register(card->x)) return false;
        vm->equal = vm->regs[card->x] == card->arg;
        return true;
    case W_JEQ:
        return !vm->equal || jump_to(vm, card->arg);
    case W_JNE:
        return vm->equal || jump_to(vm, card->arg);
    case W_JMP:
        return jump_to(vm, card->arg);
    case W_QUERY:
        return query(vm, card);
    case W_NONCE:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] = vm->nonce;
        return true;
    case W_TRAIL:
        if (!valid_register(card->x)) return false;
        vm->regs[card->x] = vm->trail;
        return true;
    case W_MARK: {
        uint8_t stage = (uint8_t)card->arg;
        if (stage == 0u || stage > 6u || stage != vm->next_gate) {
            return false;
        }
        vm->gate_mask |= (uint8_t)(1u << (stage - 1u));
        uint64_t line = transcript_hash(vm->last_input, vm->last_input_len);
        vm->trail ^= line +
                     ((uint64_t)stage * UINT64_C(0x8CB92BA72F3D8DD7));
        vm->trail = ww_rotl64(vm->trail, stage * 9u + 5u);
        vm->trail *= UINT64_C(0xDB4F0B9175AE2165);
        vm->trail ^= vm->trail >> 27;
        vm->next_gate++;
        printf("[answer %u accepted]\n", stage);
        fflush(stdout);
        return true;
    }
    case W_REVEAL:
        if (vm->gate_mask != 0x3fu || vm->next_gate != 7u ||
            vm->flag == NULL) {
            return false;
        }
        printf("\nBoth faces agree. Here is your flag: %s\n", vm->flag);
        fflush(stdout);
        return true;
    case W_FLIP:
        if (vm->sp != 0u) {
            return false;
        }
        vm->face = FACE_WHO;
        return true;
    case W_HALT:
        vm->halted = true;
        return true;
    default:
        return false;
    }
}

static bool binary_values(ww_vm *vm, uint64_t *left, uint64_t *right) {
    return pop(vm, right) && pop(vm, left);
}

static bool execute_who(ww_vm *vm, const ww_card *card) {
    uint64_t left, right, value;

    switch (card->glyph) {
    case H_PUSHI:
        return push(vm, card->arg);
    case H_PUSHR:
        return valid_register(card->x) && push(vm, vm->regs[card->x]);
    case H_POPR:
        return valid_register(card->x) && pop(vm, &vm->regs[card->x]);
    case H_DUP:
        if (vm->sp == 0u) return false;
        return push(vm, vm->stack[vm->sp - 1u]);
    case H_SWAP:
        if (vm->sp < 2u) return false;
        value = vm->stack[vm->sp - 1u];
        vm->stack[vm->sp - 1u] = vm->stack[vm->sp - 2u];
        vm->stack[vm->sp - 2u] = value;
        return true;
    case H_DROP:
        return pop(vm, &value);
    case H_LDB:
        return pop(vm, &left) && read_u8(vm, left, &value) &&
               push(vm, value);
    case H_LD16:
        return pop(vm, &left) && read_u16le(vm, left, &value) &&
               push(vm, value);
    case H_LD64LE:
        return pop(vm, &left) && read_u64le(vm, left, &value) &&
               push(vm, value);
    case H_LD64BE:
        return pop(vm, &left) && read_u64be(vm, left, &value) &&
               push(vm, value);
    case H_ADD:
        return binary_values(vm, &left, &right) && push(vm, left + right);
    case H_SUB:
        return binary_values(vm, &left, &right) && push(vm, left - right);
    case H_XOR:
        return binary_values(vm, &left, &right) && push(vm, left ^ right);
    case H_MUL:
        return binary_values(vm, &left, &right) && push(vm, left * right);
    case H_AND:
        return binary_values(vm, &left, &right) && push(vm, left & right);
    case H_OR:
        return binary_values(vm, &left, &right) && push(vm, left | right);
    case H_SHL:
        return binary_values(vm, &left, &right) &&
               push(vm, left << (unsigned)(right & 63u));
    case H_SHR:
        return binary_values(vm, &left, &right) &&
               push(vm, left >> (unsigned)(right & 63u));
    case H_ROL:
        return binary_values(vm, &left, &right) &&
               push(vm, ww_rotl64(left, (unsigned)right));
    case H_ROR:
        return binary_values(vm, &left, &right) &&
               push(vm, ww_rotr64(left, (unsigned)right));
    case H_ROL8: {
        if (!binary_values(vm, &left, &right)) return false;
        unsigned count = (unsigned)(right & 7u);
        uint8_t byte = (uint8_t)left;
        if (count != 0u) {
            byte = (uint8_t)((byte << count) | (byte >> (8u - count)));
        }
        return push(vm, byte);
    }
    case H_MOD:
        if (!binary_values(vm, &left, &right) || right == 0u) return false;
        return push(vm, left % right);
    case H_EQ:
        return binary_values(vm, &left, &right) &&
               push(vm, left == right ? 1u : 0u);
    case H_JZ:
        if (!pop(vm, &value)) return false;
        return value != 0u || jump_to(vm, card->arg);
    case H_JNZ:
        if (!pop(vm, &value)) return false;
        return value == 0u || jump_to(vm, card->arg);
    case H_JMP:
        return jump_to(vm, card->arg);
    case H_FLIP:
        if (vm->sp != 0u) {
            return false;
        }
        vm->face = FACE_WHAT;
        return true;
    case H_HALT:
        vm->halted = true;
        return true;
    default:
        return false;
    }
}

bool ww_run(const ww_cartridge *cart, uint64_t nonce, const char *flag) {
    ww_vm vm;
    memset(&vm, 0, sizeof(vm));
    vm.cart = cart;
    vm.ip = cart->entry_card;
    vm.face = FACE_WHAT;
    vm.next_gate = 1u;
    vm.nonce = nonce;
    vm.trail = ww_initial_trail(nonce);
    vm.flag = flag;
    memcpy(vm.memory + WW_DATA_BASE, cart->data, cart->data_size);

    while (!vm.halted && !vm.faulted && vm.steps < WW_STEP_LIMIT) {
        if (vm.ip >= cart->card_count) {
            vm.faulted = true;
            break;
        }
        const ww_card card = cart->cards[vm.ip++];
        vm.steps++;

        bool ok = vm.face == FACE_WHAT ? execute_what(&vm, &card)
                                       : execute_who(&vm, &card);
        if (!ok) {
            vm.faulted = true;
        }
    }

    if (vm.steps >= WW_STEP_LIMIT) {
        vm.faulted = true;
    }

    if (vm.faulted) {
        puts("\nThat answer belongs to somebody else.");
    } else if (vm.gate_mask != 0x3fu) {
        puts("\nThe two faces disagree. Try again.");
    }
    fflush(stdout);

    bool success = !vm.faulted && vm.gate_mask == 0x3fu;
    memset(&vm, 0, sizeof(vm));
    return success;
}
