/* syscalls.c - a minimal Linux/MIPS o32 syscall layer.
 *
 * o32 convention: syscall number in $v0 ($2), args in $arg1-$a3 ($4-$7).
 * On return $v0 holds the result (or errno on failure) and $a3 ($7) is the
 * error flag: 0 = success, 1 = error. Linux/MIPS numbers are based at 4000.
 *
 * errno values are passed through from the host; their numeric codes differ
 * slightly from MIPS Linux, but programs that only test success/failure work.
 */
#include "prismvm.h"
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define SYS_BASE 4000
#define ENOSYS_ 38

#define SYS_exit 4001
#define SYS_read 4003
#define SYS_write 4004
#define SYS_open 4005
#define SYS_close 4006
#define SYS_lseek 4019

/* MIPS open() flag bits differ from x86; translate the common ones. */
static int conv_open_flags(int mf) {
    int hf = mf & 3; /* O_RDONLY/WRONLY/RDWR share 0,1,2 */
    if (mf & 0x0008)
        hf |= O_APPEND;
    if (mf & 0x0080)
        hf |= O_NONBLOCK;
    if (mf & 0x0100)
        hf |= O_CREAT;
    if (mf & 0x0200)
        hf |= O_TRUNC;
    if (mf & 0x0400)
        hf |= O_EXCL;
    return hf;
}

static char *guest_str(CPU *c, uint32_t addr) {
    size_t cap = 256, len = 0;
    char *s = malloc(cap);
    for (;;) {
        char ch = (char)mmu_r8(&c->mmu, addr + (uint32_t)len);
        if (len + 1 >= cap) {
            cap *= 2;
            s = realloc(s, cap);
        }
        s[len++] = ch;
        if (!ch)
            break;
    }
    return s;
}

void do_syscall(CPU *c) {
    uint32_t nr = c->reg[2];
    uint32_t arg1 = c->reg[4], arg2 = c->reg[5], arg3 = c->reg[6];
    long ret = 0;
    int err = 0;

    switch (nr) {
    case SYS_exit:
        c->halted = 1;
        c->exit_code = (int)(arg1 & 0xff);
        return;

    case SYS_read: {
        if (arg3 == 0)
            break;

        char *buf = malloc(arg3);
        ssize_t r = read((int)arg1, buf, arg3);
        if (r < 0) {
            err = 1;
            ret = errno;
        } else {
            mmu_write_block(c, arg2, buf, (size_t)r);
            ret = r;
        }
        free(buf);
    } break;

    case SYS_write: {
        char *tmp = malloc(arg3 ? arg3 : 1);
        mmu_read_block(&c->mmu, arg2, tmp, arg3);
        ssize_t r = write((int)arg1, tmp, arg3);
        if (r < 0) {
            err = 1;
            ret = errno;
        } else
            ret = r;
        free(tmp);
    } break;

    case SYS_open: {
        char *p = guest_str(c, arg1);
        int r = open(p, conv_open_flags((int)arg2), (unsigned)arg3);
        if (r < 0) {
            err = 1;
            ret = errno;
        } else
            ret = r;
        free(p);
    } break;

    case SYS_close: {
        int r = close((int)arg1);
        if (r < 0) {
            err = 1;
            ret = errno;
        } else
            ret = r;
    } break;

    case SYS_lseek: {
        off_t r = lseek((int)arg1, (off_t)(int32_t)arg2, (int)arg3);
        if (r < 0) {
            err = 1;
            ret = errno;
        } else
            ret = (long)r;
    } break;

    default:
        /* unknown syscall: fail it silently with ENOSYS, no diagnostic */
        err = 1;
        ret = ENOSYS_;
    }

    c->reg[2] = (uint32_t)ret; /* $v0 */
    c->reg[7] = err ? 1 : 0;   /* $a3 = error flag */
}
