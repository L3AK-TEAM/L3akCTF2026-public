/* xalloc.c -- Fail-fast memory allocation wrappers. */

#include "xalloc.h"

#include "compiler.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>


static ATTR_NORETURN ATTR_COLD ATTR_FORMAT(printf, 1,
                                           2) void xalloc_die(const char *fmt,
                                                              ...) {
    char buf[128];
    va_list args;

    va_start(args, fmt);
    int n = vsnprintf(buf, sizeof buf, fmt, args);
    va_end(args);

    if (n > 0) {
        size_t len = (size_t)n < sizeof buf ? (size_t)n : sizeof buf - 1;
        ssize_t rv = write(STDERR_FILENO, buf, len);
        (void)rv;
    } else {
        static const char fb[] = "xalloc: fatal error\n";
        ssize_t rv = write(STDERR_FILENO, fb, sizeof fb - 1);
        (void)rv;
    }

    abort();
}

void *xmalloc(size_t size) {
    void *p;

    if (size == 0)
        size = 1;

    p = malloc(size);
    if (unlikely(p == NULL))
        xalloc_die("xalloc: out of memory in xmalloc (requested %zu bytes)\n",
                   size);

    return p;
}

void *xcalloc(size_t nmemb, size_t size) {
    void *p;
    size_t total;

    if (nmemb == 0 || size == 0) {
        nmemb = 1;
        size = 1;
    }

    if (unlikely(__builtin_mul_overflow(nmemb, size, &total)))
        xalloc_die("xalloc: fatal: xcalloc(%zu, %zu) overflows size_t\n", nmemb,
                   size);

    p = calloc(nmemb, size);
    if (unlikely(p == NULL))
        xalloc_die("xalloc: out of memory in xcalloc (requested %zu bytes)\n",
                   total);

    return p;
}

void *xrealloc(void *ptr, size_t size) {
    void *p;

    if (size == 0)
        size = 1;

    p = realloc(ptr, size);
    if (unlikely(p == NULL))
        xalloc_die("xalloc: out of memory in xrealloc (requested %zu bytes)\n",
                   size);

    return p;
}

void xfree(void *ptr) {
    free(ptr);
}
