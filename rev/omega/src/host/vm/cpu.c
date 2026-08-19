/* cpu.c - the PRISM interpreter core (MIPS I underneath). */
#include "prismvm.h"
#include "prism.h"

#define OP(i) PRISM_OP(i)
#define RS(i) PRISM_RS(i)
#define RT(i) PRISM_RT(i)
#define RD(i) PRISM_RD(i)
#define SA(i) PRISM_SA(i)
#define FUNCT(i) PRISM_FN(i)
#define IMM(i) PRISM_IMM(i)
#define SIMM(i) PRISM_SIMM(i)
#define TARGET(i) PRISM_TARGET(i)

#define R(n) (c->reg[(n)])
#define SET(n, v)                                                              \
    do {                                                                       \
        uint32_t _v = (uint32_t)(v);                                           \
        if ((n) != 0)                                                          \
            c->reg[(n)] = _v;                                                  \
    } while (0)

void cpu_init(CPU *c) {
    for (int i = 0; i < 32; i++)
        c->reg[i] = 0;
    c->pc = c->next_pc = 0;
    c->hi = c->lo = 0;
    c->brk_cur = c->brk_min = 0;
    c->mmap_top = 0x60000000u; /* anonymous mmap region grows upward */
    c->halted = 0;
    c->exit_code = 0;
    mmu_init(&c->mmu);
}

static void take_branch(CPU *c, uint32_t cur_pc, int32_t simm, int taken) {
    if (taken)
        c->next_pc = cur_pc + 4 + ((uint32_t)simm << 2);
}

static void illegal_instruction(CPU *c) {
    c->halted = 1;
    c->exit_code = 128 + 4; /* SIGILL */
}

/* lwl/lwr: merge an unaligned word into rt, byte by byte (little-endian).
 * M[k] is the memory byte at (aligned + k); b[k] is register byte k
 * (b[0] = least significant). */
static void op_lwl_lwr(CPU *c, uint32_t inst, int left) {
    uint32_t addr = R(RS(inst)) + (uint32_t)SIMM(inst);
    uint32_t aligned = addr & ~3u;
    int o = (int)(addr & 3);
    uint8_t M[4];
    for (int k = 0; k < 4; k++)
        M[k] = mmu_r8(&c->mmu, aligned + (uint32_t)k);

    uint32_t v = R(RT(inst));
    uint8_t b[4] = {(uint8_t)v, (uint8_t)(v >> 8), (uint8_t)(v >> 16),
                    (uint8_t)(v >> 24)};

    if (left)
        for (int j = 0; j <= o; j++)
            b[3 - o + j] = M[j];
    else
        for (int j = 0; j <= 3 - o; j++)
            b[j] = M[o + j];

    SET(RT(inst), (uint32_t)b[0] | ((uint32_t)b[1] << 8) |
                      ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24));
}

/* swl/swr: store the matching subset of rt's bytes into the straddled word. */
static void op_swl_swr(CPU *c, uint32_t inst, int left) {
    uint32_t addr = R(RS(inst)) + (uint32_t)SIMM(inst);
    uint32_t aligned = addr & ~3u;
    int o = (int)(addr & 3);
    uint32_t v = R(RT(inst));
    uint8_t b[4] = {(uint8_t)v, (uint8_t)(v >> 8), (uint8_t)(v >> 16),
                    (uint8_t)(v >> 24)};

    if (left)
        for (int j = 0; j <= o; j++)
            mmu_w8(c, aligned + (uint32_t)j, b[3 - o + j]);
    else
        for (int j = 0; j <= 3 - o; j++)
            mmu_w8(c, aligned + (uint32_t)(o + j), b[j]);
}

int cpu_step(CPU *c) {
    if (c->halted)
        return 1;

    uint32_t cur_pc = c->pc;
    uint32_t inst = mmu_r32(&c->mmu, cur_pc);

    /* advance the PC pair before executing, so branches can override next_pc */
    c->pc = c->next_pc;
    c->next_pc = c->pc + 4;

    uint32_t op = OP(inst);
    switch (op) {
    case PRISM_OP_SPECIAL: { /* SPECIAL (R-type): secondary dispatch on funct */
        switch (FUNCT(inst)) {
        case PRISM_FN_SLL:
            SET(RD(inst), R(RT(inst)) << SA(inst));
            break; /* sll  */
        case PRISM_FN_SRL:
            SET(RD(inst), R(RT(inst)) >> SA(inst));
            break; /* srl  */
        case PRISM_FN_SRA:
            SET(RD(inst), (int32_t)R(RT(inst)) >> SA(inst));
            break; /* sra  */
        case PRISM_FN_SLLV:
            SET(RD(inst), R(RT(inst)) << (R(RS(inst)) & 31));
            break; /* sllv */
        case PRISM_FN_SRLV:
            SET(RD(inst), R(RT(inst)) >> (R(RS(inst)) & 31));
            break; /* srlv */
        case PRISM_FN_SRAV:
            SET(RD(inst), (int32_t)R(RT(inst)) >> (R(RS(inst)) & 31));
            break; /* srav */
        case PRISM_FN_JR:
            c->next_pc = R(RS(inst));
            break; /* jr   */
        case PRISM_FN_JALR: {
            uint32_t t = R(RS(inst)); /* jalr */
            SET(RD(inst) ? RD(inst) : 31, cur_pc + 8);
            c->next_pc = t;
        } break;
        case PRISM_FN_SYSCALL:
            do_syscall(c);
            break; /* syscall */
        case PRISM_FN_BREAK: /* break: halt, no diagnostic */
            c->halted = 1;
            c->exit_code = 128 + 5;
            break;
        case PRISM_FN_MFHI:
            SET(RD(inst), c->hi);
            break; /* mfhi */
        case PRISM_FN_MTHI:
            c->hi = R(RS(inst));
            break; /* mthi */
        case PRISM_FN_MFLO:
            SET(RD(inst), c->lo);
            break; /* mflo */
        case PRISM_FN_MTLO:
            c->lo = R(RS(inst));
            break; /* mtlo */
        case PRISM_FN_MULT: {
            int64_t r =
                (int64_t)(int32_t)R(RS(inst)) * (int32_t)R(RT(inst)); /* mult */
            c->lo = (uint32_t)r;
            c->hi = (uint32_t)((uint64_t)r >> 32);
        } break;
        case PRISM_FN_MULTU: {
            uint64_t r = (uint64_t)R(RS(inst)) * R(RT(inst)); /* multu */
            c->lo = (uint32_t)r;
            c->hi = (uint32_t)(r >> 32);
        } break;
        case PRISM_FN_DIV: {
            int32_t a = (int32_t)R(RS(inst)),
                    b = (int32_t)R(RT(inst)); /* div  */
            if (b) {
                c->lo = (uint32_t)(a / b);
                c->hi = (uint32_t)(a % b);
            }
        } break;
        case PRISM_FN_DIVU: {
            uint32_t a = R(RS(inst)), b = R(RT(inst)); /* divu */
            if (b) {
                c->lo = a / b;
                c->hi = a % b;
            }
        } break;
        case PRISM_FN_ADD: {
            int32_t a = (int32_t)R(RS(inst)),
                    b = (int32_t)R(RT(inst)); /* add  */
            int32_t s = (int32_t)((uint32_t)a + (uint32_t)b);
            SET(RD(inst), (uint32_t)s);
        } break;
        case PRISM_FN_ADDU:
            SET(RD(inst), R(RS(inst)) + R(RT(inst)));
            break; /* addu */
        case PRISM_FN_SUB: {
            int32_t a = (int32_t)R(RS(inst)),
                    b = (int32_t)R(RT(inst)); /* sub  */
            int32_t s = (int32_t)((uint32_t)a - (uint32_t)b);
            SET(RD(inst), (uint32_t)s);
        } break;
        case PRISM_FN_SUBU:
            SET(RD(inst), R(RS(inst)) - R(RT(inst)));
            break; /* subu */
        case PRISM_FN_AND:
            SET(RD(inst), R(RS(inst)) & R(RT(inst)));
            break; /* and  */
        case PRISM_FN_OR:
            SET(RD(inst), R(RS(inst)) | R(RT(inst)));
            break; /* or   */
        case PRISM_FN_XOR:
            SET(RD(inst), R(RS(inst)) ^ R(RT(inst)));
            break; /* xor  */
        case PRISM_FN_NOR:
            SET(RD(inst), ~(R(RS(inst)) | R(RT(inst))));
            break; /* nor  */
        case PRISM_FN_SLT:
            SET(RD(inst), (int32_t)R(RS(inst)) < (int32_t)R(RT(inst)));
            break; /* slt  */
        case PRISM_FN_SLTU:
            SET(RD(inst), R(RS(inst)) < R(RT(inst)));
            break; /* sltu */
        default:
            illegal_instruction(c);
        }
    } break;

    case PRISM_OP_REGIMM: { /* REGIMM: bltz/bgez/bltzal/bgezal */
        uint32_t rt = RT(inst);
        int32_t s = (int32_t)R(RS(inst));
        int link = (rt & 0x10) != 0; /* bit 4 -> save return address */
        int ge = (rt & 0x01) != 0;   /* bit 0 -> bgez, else bltz     */
        int taken = ge ? (s >= 0) : (s < 0);
        if (link)
            SET(31, cur_pc + 8);
        take_branch(c, cur_pc, SIMM(inst), taken);
    } break;

    case PRISM_OP_J:
        c->next_pc = ((cur_pc + 4) & 0xf0000000u) | (TARGET(inst) << 2);
        break; /* j   */
    case PRISM_OP_JAL:
        SET(31, cur_pc + 8); /* jal */
        c->next_pc = ((cur_pc + 4) & 0xf0000000u) | (TARGET(inst) << 2);
        break;

    case PRISM_OP_BEQ:
        take_branch(c, cur_pc, SIMM(inst), R(RS(inst)) == R(RT(inst)));
        break; /* beq  */
    case PRISM_OP_BNE:
        take_branch(c, cur_pc, SIMM(inst), R(RS(inst)) != R(RT(inst)));
        break; /* bne  */
    case PRISM_OP_BLEZ:
        take_branch(c, cur_pc, SIMM(inst), (int32_t)R(RS(inst)) <= 0);
        break; /* blez */
    case PRISM_OP_BGTZ:
        take_branch(c, cur_pc, SIMM(inst), (int32_t)R(RS(inst)) > 0);
        break; /* bgtz */

    case PRISM_OP_ADDI: {
        int32_t a = (int32_t)R(RS(inst)),
                s = (int32_t)((uint32_t)a + (uint32_t)SIMM(inst));
        SET(RT(inst), (uint32_t)s);
    } break; /* addi  */
    case PRISM_OP_ADDIU:
        SET(RT(inst), R(RS(inst)) + (uint32_t)SIMM(inst));
        break; /* addiu */
    case PRISM_OP_SLTI:
        SET(RT(inst), (int32_t)R(RS(inst)) < SIMM(inst));
        break; /* slti  */
    case PRISM_OP_SLTIU:
        SET(RT(inst), R(RS(inst)) < (uint32_t)SIMM(inst));
        break; /* sltiu */
    case PRISM_OP_ANDI:
        SET(RT(inst), R(RS(inst)) & IMM(inst));
        break; /* andi  */
    case PRISM_OP_ORI:
        SET(RT(inst), R(RS(inst)) | IMM(inst));
        break; /* ori   */
    case PRISM_OP_XORI:
        SET(RT(inst), R(RS(inst)) ^ IMM(inst));
        break; /* xori  */
    case PRISM_OP_LUI:
        SET(RT(inst), IMM(inst) << 16);
        break; /* lui   */

    case PRISM_OP_LB:
        SET(RT(inst),
            (int32_t)(int8_t)mmu_r8(&c->mmu, R(RS(inst)) + SIMM(inst)));
        break; /* lb  */
    case PRISM_OP_LH:
        SET(RT(inst),
            (int32_t)(int16_t)mmu_r16(&c->mmu, R(RS(inst)) + SIMM(inst)));
        break; /* lh  */
    case PRISM_OP_LWL:
        op_lwl_lwr(c, inst, 1);
        break; /* lwl */
    case PRISM_OP_LW:
        SET(RT(inst), mmu_r32(&c->mmu, R(RS(inst)) + SIMM(inst)));
        break; /* lw  */
    case PRISM_OP_LBU:
        SET(RT(inst), (uint32_t)mmu_r8(&c->mmu, R(RS(inst)) + SIMM(inst)));
        break; /* lbu */
    case PRISM_OP_LHU:
        SET(RT(inst), (uint32_t)mmu_r16(&c->mmu, R(RS(inst)) + SIMM(inst)));
        break; /* lhu */
    case PRISM_OP_LWR:
        op_lwl_lwr(c, inst, 0);
        break; /* lwr */

    case PRISM_OP_SB:
        mmu_w8(c, R(RS(inst)) + SIMM(inst), (uint8_t)R(RT(inst)));
        break; /* sb  */
    case PRISM_OP_SH:
        mmu_w16(c, R(RS(inst)) + SIMM(inst), (uint16_t)R(RT(inst)));
        break; /* sh  */
    case PRISM_OP_SWL:
        op_swl_swr(c, inst, 1);
        break; /* swl */
    case PRISM_OP_SW:
        mmu_w32(c, R(RS(inst)) + SIMM(inst), R(RT(inst)));
        break; /* sw  */
    case PRISM_OP_SWR:
        op_swl_swr(c, inst, 0);
        break; /* swr */

    default:
        /* anything not decoded above (including unmodeled coprocessor ops) is
         * a fatal illegal instruction */
        illegal_instruction(c);
    }

    c->reg[0] = 0; /* $zero stays 0 even if something wrote it */
    return c->halted;
}

void cpu_run(CPU *c) {
    while (!c->halted)
        cpu_step(c);
}
