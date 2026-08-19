/* syscall.h -- 32-bit MIPS (O32) syscall wrappers
 *
 * O32 syscall ABI:
 *   number -> $v0 ($2)
 *   args   -> $a0..$a3 ($4..$7)
 *   args 5,6 -> caller stack at 16($sp), 20($sp)
 *   `syscall`
 *   return -> $v0 ($2)
 *   error  -> $a3 ($7) set to 0/1; on error $v0 holds the POSITIVE errno
 */

#ifndef MIPS_SYSCALL_H
#define MIPS_SYSCALL_H 1

#if !defined(__mips__) || defined(__mips64) || _MIPS_SIM != _ABIO32
#error "mips/syscall.h is for 32-bit MIPS, O32 ABI only"
#endif

#define SYS_exit 4001
#define SYS_read 4003
#define SYS_write 4004
#define SYS_open 4005
#define SYS_close 4006
#define SYS_lseek 4019

/* Caller-saved scratch regs the kernel may trash.
 * - $2/$7 (return/error), $4-$6 (args): operands
 * - callee-saved ($s0-$s8): preserved
 * - hi/lo: mult/div regs
 * - memory: barrier across the trap
 * - $8-$10: added per arity
 */
#define _SYSCALL_CLOBBERLIST                                                   \
    "$1", "$3", "$11", "$12", "$13", "$14", "$15", "$24", "$25", "hi", "lo",   \
        "memory"

static inline long _syscall0(long nr) {
    register long r2 __asm__("$2");
    register long r7 __asm__("$7");
    __asm__ __volatile__("addu $2,$0,%[nr] ; syscall"
                         : "=&r"(r2), "=r"(r7)
                         : [nr] "ir"(nr)
                         : _SYSCALL_CLOBBERLIST, "$8", "$9", "$10");
    return r7 ? -r2 : r2;
}

static inline long _syscall1(long nr, long arg1) {
    register long r2 __asm__("$2");
    register long r4 __asm__("$4") = arg1;
    register long r7 __asm__("$7");
    __asm__ __volatile__("addu $2,$0,%[nr] ; syscall"
                         : "=&r"(r2), "=r"(r7)
                         : [nr] "ir"(nr), "r"(r4)
                         : _SYSCALL_CLOBBERLIST, "$8", "$9", "$10");
    return r7 ? -r2 : r2;
}

static inline long _syscall2(long nr, long arg1, long arg2) {
    register long r2 __asm__("$2");
    register long r4 __asm__("$4") = arg1;
    register long r5 __asm__("$5") = arg2;
    register long r7 __asm__("$7");
    __asm__ __volatile__("addu $2,$0,%[nr] ; syscall"
                         : "=&r"(r2), "=r"(r7)
                         : [nr] "ir"(nr), "r"(r4), "r"(r5)
                         : _SYSCALL_CLOBBERLIST, "$8", "$9", "$10");
    return r7 ? -r2 : r2;
}

static inline long _syscall3(long nr, long arg1, long arg2, long arg3) {
    register long r2 __asm__("$2");
    register long r4 __asm__("$4") = arg1;
    register long r5 __asm__("$5") = arg2;
    register long r6 __asm__("$6") = arg3;
    register long r7 __asm__("$7");
    __asm__ __volatile__("addu $2,$0,%[nr] ; syscall"
                         : "=&r"(r2), "=r"(r7)
                         : [nr] "ir"(nr), "r"(r4), "r"(r5), "r"(r6)
                         : _SYSCALL_CLOBBERLIST, "$8", "$9", "$10");
    return r7 ? -r2 : r2;
}

static inline long _syscall4(long nr, long arg1, long arg2, long arg3,
                             long arg4) {
    register long r2 __asm__("$2");
    register long r4 __asm__("$4") = arg1;
    register long r5 __asm__("$5") = arg2;
    register long r6 __asm__("$6") = arg3;
    register long r7 __asm__("$7") = arg4; /* $a3: arg-in AND flag-out */
    __asm__ __volatile__("addu $2,$0,%[nr] ; syscall"
                         : "=&r"(r2), "+r"(r7)
                         : [nr] "ir"(nr), "r"(r4), "r"(r5), "r"(r6)
                         : _SYSCALL_CLOBBERLIST, "$8", "$9", "$10");
    return r7 ? -r2 : r2;
}

static inline long _syscall5(long nr, long arg1, long arg2, long arg3,
                             long arg4, long arg5) {
    register long r2 __asm__("$2");
    register long r4 __asm__("$4") = arg1;
    register long r5 __asm__("$5") = arg2;
    register long r6 __asm__("$6") = arg3;
    register long r7 __asm__("$7") = arg4;

    /* Pin arg5 to $8 (caller-saved). An operand would force allocation to a
     * callee-saved register (available caller-saved are clobbered). */
    register long r8 __asm__("$8") = arg5;

    __asm__ __volatile__("subu $sp,$sp,32 ; sw $8,16($sp) ;"
                         "addu $2,$0,%[nr] ; syscall ;"
                         "addiu $sp,$sp,32"
                         : "=&r"(r2), "+r"(r7), "+r"(r8)
                         : [nr] "ir"(nr), "r"(r4), "r"(r5), "r"(r6)
                         : _SYSCALL_CLOBBERLIST, "$9", "$10");
    return r7 ? -r2 : r2;
}

static inline long _syscall6(long nr, long arg1, long arg2, long arg3,
                             long arg4, long arg5, long arg6) {
    register long r2 __asm__("$2");
    register long r4 __asm__("$4") = arg1;
    register long r5 __asm__("$5") = arg2;
    register long r6 __asm__("$6") = arg3;
    register long r7 __asm__("$7") = arg4;
    register long r8 __asm__("$8") = arg5;
    register long r9 __asm__("$9") = arg6;

    __asm__ __volatile__("subu $sp,$sp,32 ; sw $8,16($sp) ; sw $9,20($sp) ;"
                         "addu  $2,$0,%[nr] ; syscall ;"
                         "addiu $sp,$sp,32"
                         : "=&r"(r2), "+r"(r7), "+r"(r8), "+r"(r9)
                         : [nr] "ir"(nr), "r"(r4), "r"(r5), "r"(r6)
                         : _SYSCALL_CLOBBERLIST, "$10");
    return r7 ? -r2 : r2;
}

#define _SYSCALL_RESOLVE(_n, _1, _2, _3, _4, _5, _6, NAME, ...) NAME
#define _SYSCALL_NARG(...)                                                     \
    _SYSCALL_RESOLVE(__VA_ARGS__, _syscall6, _syscall5, _syscall4, _syscall3,  \
                     _syscall2, _syscall1, _syscall0)

#define _syscall(...) (_SYSCALL_NARG(__VA_ARGS__)(__VA_ARGS__))

#endif
