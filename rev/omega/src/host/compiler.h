#ifndef COMPILER_H
#define COMPILER_H 1

#ifndef likely
#define likely(x) __builtin_expect(!!(x), 1)
#endif

#ifndef unlikely
#define unlikely(x) __builtin_expect(!!(x), 0)
#endif

#if defined(__has_attribute)
#define HAS_ATTRIBUTE(x) __has_attribute(x)
#else
#define HAS_ATTRIBUTE(x) 0
#endif

#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 202311L
#define ATTR_NORETURN [[noreturn]]
#elif defined(__GNUC__)
#define ATTR_NORETURN __attribute__((noreturn))
#elif defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
#define ATTR_NORETURN _Noreturn
#else
#define ATTR_NORETURN
#endif

#if HAS_ATTRIBUTE(cold)
#define ATTR_COLD __attribute__((cold))
#else
#define ATTR_COLD
#endif

#if HAS_ATTRIBUTE(returns_nonnull)
#define ATTR_RETURNS_NONNULL __attribute__((returns_nonnull))
#else
#define ATTR_RETURNS_NONNULL
#endif

#if HAS_ATTRIBUTE(warn_unused_result)
#define ATTR_NODISCARD __attribute__((warn_unused_result))
#else
#define ATTR_NODISCARD
#endif

#if HAS_ATTRIBUTE(assume_aligned)
#define ATTR_ASSUME_ALIGNED(...) __attribute__((assume_aligned(__VA_ARGS__)))
#else
#define ATTR_ASSUME_ALIGNED(...)
#endif

#if HAS_ATTRIBUTE(alloc_size)
#define ATTR_ALLOC_SIZE(...) __attribute__((alloc_size(__VA_ARGS__)))
#else
#define ATTR_ALLOC_SIZE(...)
#endif

#if HAS_ATTRIBUTE(malloc)
#define ATTR_MALLOC __attribute__((malloc))
#else
#define ATTR_MALLOC
#endif

#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 11
#define ATTR_DEALLOC(...) __attribute__((malloc(__VA_ARGS__)))
#else
#define ATTR_DEALLOC(...)
#endif

#if HAS_ATTRIBUTE(format)
#  define ATTR_FORMAT(arch, fmt_idx, first) __attribute__((format(arch, fmt_idx, first)))
#else
#  define ATTR_FORMAT(arch, fmt_idx, first)
#endif

#endif