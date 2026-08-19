/* prismvm.c - standalone command-line driver for the PRISM VM. */
#include "prismvm.h"
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <prx-file>\n", argv[0]);
        return 2;
    }

    CPU c;
    cpu_init(&c);

    if (load_prx(&c, argv[1]) != 0) {
        fprintf(stderr, "failed to load '%s'\n", argv[1]);
        return 1;
    }

    setup_stack(&c);

    cpu_run(&c);

    mmu_deinit(&c.mmu);
    return c.exit_code;
}
