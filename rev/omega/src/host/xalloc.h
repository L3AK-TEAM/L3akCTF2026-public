/* xalloc.h -- Fail-fast memory allocation wrappers. */
#ifndef XALLOC_H
#define XALLOC_H 1

#include "compiler.h"
#include <stddef.h>

void xfree(void *ptr);

void *xmalloc(size_t size) ATTR_MALLOC ATTR_DEALLOC(xfree, 1) ATTR_ALLOC_SIZE(1)
    ATTR_ASSUME_ALIGNED(__alignof__(max_align_t))
        ATTR_RETURNS_NONNULL ATTR_NODISCARD;

void *xcalloc(size_t nmemb, size_t size) ATTR_MALLOC ATTR_DEALLOC(xfree, 1)
    ATTR_ALLOC_SIZE(1, 2) ATTR_ASSUME_ALIGNED(__alignof__(max_align_t))
        ATTR_RETURNS_NONNULL ATTR_NODISCARD;

void *xrealloc(void *ptr, size_t size) ATTR_DEALLOC(xfree, 1) ATTR_ALLOC_SIZE(2)
    ATTR_ASSUME_ALIGNED(__alignof__(max_align_t))
        ATTR_RETURNS_NONNULL ATTR_NODISCARD;

#endif /* XALLOC_H */
