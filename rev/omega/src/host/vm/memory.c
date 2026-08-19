/* memory.c -- byte-addressable, lazily paged guest memory. */
#include "xalloc.h"
#include "prismvm.h"
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

void mmu_init(MMU *m) {
    m->pages = xcalloc(NUM_PAGES, sizeof(*m->pages));
}

void mmu_deinit(MMU *m) {
    if (!m->pages)
        return;

    for (size_t i = 0; i < NUM_PAGES; i++)
        free(m->pages[i]);

    free(m->pages);
    m->pages = NULL;
}

static uint8_t *page_for(MMU *m, uint32_t addr, bool alloc) {
    uint32_t vpn = addr >> PAGE_BITS;
    uint8_t *p = m->pages[vpn];
    if (!p && alloc) {
        p = xcalloc(1, PAGE_SIZE);
        m->pages[vpn] = p;
    }

    return p;
}

uint8_t mmu_r8(MMU *mmu, uint32_t a) {
    uint8_t *p = page_for(mmu, a, false);
    return p ? p[a & PAGE_MASK] : 0; /* unmapped reads as 0 (lenient) */
}

void mmu_w8(CPU *c, uint32_t a, uint8_t v) {
    uint8_t *p = page_for(&c->mmu, a, true);
    p[a & PAGE_MASK] = v;
}

uint16_t mmu_r16(MMU *mmu, uint32_t a) {
    uint8_t b0 = mmu_r8(mmu, a), b1 = mmu_r8(mmu, a + 1);
    return (uint16_t)((b1 << 8) | b0);
}

void mmu_w16(CPU *c, uint32_t a, uint16_t v) {
    mmu_w8(c, a, (uint8_t)v);
    mmu_w8(c, a + 1, (uint8_t)(v >> 8));
}

uint32_t mmu_r32(MMU *mmu, uint32_t a) {
    uint8_t b0 = mmu_r8(mmu, a), b1 = mmu_r8(mmu, a + 1);
    uint8_t b2 = mmu_r8(mmu, a + 2), b3 = mmu_r8(mmu, a + 3);
    return ((uint32_t)b3 << 24) | ((uint32_t)b2 << 16) | ((uint32_t)b1 << 8) |
           b0;
}

void mmu_w32(CPU *c, uint32_t a, uint32_t v) {
    mmu_w8(c, a, (uint8_t)v);
    mmu_w8(c, a + 1, (uint8_t)(v >> 8));
    mmu_w8(c, a + 2, (uint8_t)(v >> 16));
    mmu_w8(c, a + 3, (uint8_t)(v >> 24));
}

void mmu_write_block(CPU *c, uint32_t a, const void *src, size_t n) {
    const uint8_t *s = src;
    for (size_t i = 0; i < n; i++)
        mmu_w8(c, a + (uint32_t)i, s[i]);
}

void mmu_read_block(MMU *mmu, uint32_t a, void *dst, size_t n) {
    uint8_t *d = dst;
    for (size_t i = 0; i < n; i++)
        d[i] = mmu_r8(mmu, a + (uint32_t)i);
}

void mmu_zero(CPU *c, uint32_t a, size_t n) {
    for (size_t i = 0; i < n; i++)
        mmu_w8(c, a + (uint32_t)i, 0);
}
