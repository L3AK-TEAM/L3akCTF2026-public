/* loader.c -- load a PRX (PRISM Executable) image into the guest memory. */
#include "prismvm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PRX_VERSION 1
#define PRX_HDR_SIZE 0x30u /* 48-byte header; phdr table starts here    */
#define PRX_PH_SIZE 0x10u  /* 16 bytes per program header               */
#define PRX_SPILLOVER 0xFFFFFFFFu /* p_filesz sentinel: map p_offset .. EOF */
#define PRX_FLAG_HAS_GP 0x01u /* e_flags bit 0: e_gp is valid               */

#define STACK_TOP 0x7ffff000u /* top of the VM-owned stack ($sp)            */

static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

/* Map an in-memory PRX image into the guest. */
int load_prx_mem(CPU *c, const uint8_t *buf, size_t sz) {
    if (sz < (size_t)PRX_HDR_SIZE) {
        fprintf(stderr, "image too small to be a PRX image\n");
        return -1;
    }

    if (buf[0] != 'P' || buf[1] != 'R' || buf[2] != 'X' || buf[3] != 0) {
        fprintf(stderr, "bad PRX magic\n");
        return -1;
    }
    if (buf[4] != PRX_VERSION) {
        fprintf(stderr, "unsupported PRX version %u\n", buf[4]);
        return -1;
    }

    uint8_t e_phnum = buf[5];
    uint8_t e_flags = buf[6];
    uint32_t e_entry = rd32(buf + 0x08);
    uint32_t e_gp = rd32(buf + 0x0c);
    /* buf[0x10 .. 0x30) is e_mac; authentication is the verifier's job. */

    if (e_phnum == 0) {
        // fprintf(stderr, "PRX has no program headers\n");
        return -1;
    }
    if (PRX_HDR_SIZE + (uint64_t)e_phnum * PRX_PH_SIZE > (uint64_t)sz) {
        // fprintf(stderr, "program-header table exceeds file\n");
        return -1;
    }

    uint32_t max_end = 0;
    for (unsigned i = 0; i < e_phnum; i++) {
        const uint8_t *ph = buf + PRX_HDR_SIZE + i * PRX_PH_SIZE;
        uint32_t p_offset = rd32(ph + 0x00);
        uint32_t p_vaddr = rd32(ph + 0x04);
        uint32_t p_filesz = rd32(ph + 0x08);
        uint32_t p_memsz = rd32(ph + 0x0c);

        if ((uint64_t)p_offset > (uint64_t)sz) {
            // fprintf(stderr, "segment %u: offset past EOF\n", i);
            return -1;
        }

        /* Spillover: maps p_offset .. EOF. */
        uint32_t eff_filesz =
            (p_filesz == PRX_SPILLOVER) ? (uint32_t)sz - p_offset : p_filesz;
        if ((uint64_t)p_offset + eff_filesz > (uint64_t)sz) {
            // fprintf(stderr, "segment %u: extends past EOF\n", i);
            return -1;
        }

        /* Copy eff_filesz file bytes, then zero-fill the VA span tail (bss). */
        mmu_write_block(c, p_vaddr, buf + p_offset, eff_filesz);
        uint32_t va_span = eff_filesz > p_memsz ? eff_filesz : p_memsz;
        if (va_span > eff_filesz)
            mmu_zero(c, p_vaddr + eff_filesz, va_span - eff_filesz);

        if (p_vaddr + va_span > max_end)
            max_end = p_vaddr + va_span;
    }

    c->pc = e_entry;
    c->next_pc = e_entry + 4;
    if (e_flags & PRX_FLAG_HAS_GP)
        c->reg[28] = e_gp;
    c->brk_min = c->brk_cur = (max_end + PAGE_MASK) & ~PAGE_MASK;
    return 0;
}

/* Read a PRX from disk and map it (thin wrapper over load_prx_mem). */
int load_prx(CPU *c, const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        perror("open");
        return -1;
    }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz < (long)PRX_HDR_SIZE) {
        fprintf(stderr, "file too small to be a PRX image\n");
        fclose(f);
        return -1;
    }
    uint8_t *buf = malloc((size_t)sz);
    if (!buf || fread(buf, 1, (size_t)sz, f) != (size_t)sz) {
        fprintf(stderr, "read failed\n");
        fclose(f);
        free(buf);
        return -1;
    }
    fclose(f);

    int rc = load_prx_mem(c, buf, (size_t)sz);
    free(buf);
    return rc;
}

void setup_stack(CPU *c) {
    c->reg[29] = STACK_TOP; /* 16-byte aligned, grows down */
}
