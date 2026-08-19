#include "syscall.h"

void _exit(int code) {
    _syscall(SYS_exit, code);
}

void _start() {
    _syscall(SYS_write, 1, (long)(void *)"Hello, World!\n", 14);

    _exit(0);
}
