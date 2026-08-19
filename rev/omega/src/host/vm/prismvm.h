/* prismvm.h - lightweight userspace PRISM (MIPS I) interpreter */
#ifndef PRISMVM_H
#define PRISMVM_H

#include <stddef.h>
#include <stdint.h>

/* 32-bit address space, lazily allocated in 4 KiB pages. */
#define PAGE_BITS 12
#define PAGE_SIZE (1u << PAGE_BITS)
#define PAGE_MASK (PAGE_SIZE - 1u)
#define NUM_PAGES (1u << (32 - PAGE_BITS)) /* 2^20 page-table entries */

typedef struct {
    uint8_t **pages; /* pages[vpn] -> 4 KiB block, or NULL if unmapped */
} MMU;

typedef struct CPU {
    uint32_t reg[32]; /* general registers; reg[0] is hardwired to 0     */
    uint32_t pc;      /* address of the instruction being fetched        */
    uint32_t next_pc; /* address of the following instruction (delay slot)*/
    uint32_t hi, lo;  /* mult/div result registers                       */
    MMU mmu;
    uint32_t brk_cur;  /* current program break                           */
    uint32_t brk_min;  /* lowest legal break (end of bss)                 */
    uint32_t mmap_top; /* bump pointer for anonymous mmap                 */
    int halted;
    int exit_code;
} CPU;

/* ---- memory.c ---- */
void mmu_init(MMU *m);
void mmu_deinit(MMU *m);
uint8_t mmu_r8(MMU *mmu, uint32_t a);
uint16_t mmu_r16(MMU *mmu, uint32_t a);
uint32_t mmu_r32(MMU *mmu, uint32_t a);
void mmu_w8(CPU *c, uint32_t a, uint8_t v);
void mmu_w16(CPU *c, uint32_t a, uint16_t v);
void mmu_w32(CPU *c, uint32_t a, uint32_t v);
void mmu_write_block(CPU *c, uint32_t a, const void *src, size_t n);
void mmu_read_block(MMU *mmu, uint32_t a, void *dst, size_t n);
void mmu_zero(CPU *c, uint32_t a, size_t n);

/* ---- cpu.c ---- */
void cpu_init(CPU *c);
int cpu_step(CPU *c); /* returns nonzero once the machine has halted */
void cpu_run(CPU *c);

/* ---- loader.c ---- */
int load_prx(CPU *c, const char *path);
int load_prx_mem(CPU *c, const uint8_t *buf, size_t sz);
void setup_stack(CPU *c);

/* ---- syscalls.c ---- */
void do_syscall(CPU *c);

#endif /* PRISMVM_H */
