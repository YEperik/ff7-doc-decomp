/* Behavioural C equivalents of the game's libc cluster (0x447be8-0x448a00 and friends).
 * Verified by tests/diff_test.py against the original code running in the ps2an emulator.
 * Not byte-matching: ee-gcc is required for that. */
#include <stddef.h>

typedef unsigned char u8;

size_t strlen(const char *s)                        { const char *p = s; while (*p) p++; return p - s; }
void  *memchr(const void *s, int c, size_t n)       { const u8 *p = s; while (n--) { if (*p == (u8)c) return (void *)p; p++; } return NULL; }
void  *memcpy(void *d, const void *s, size_t n)     { u8 *a = d; const u8 *b = s; while (n--) *a++ = *b++; return d; }
void  *memmove(void *d, const void *s, size_t n)    {
    u8 *a = d; const u8 *b = s;
    if (a <= b || a >= b + n) { while (n--) *a++ = *b++; }
    else { a += n; b += n; while (n--) *--a = *--b; }
    return d;
}
void  *memset(void *d, int c, size_t n)             { u8 *a = d; while (n--) *a++ = (u8)c; return d; }
int    memcmp(const void *x, const void *y, size_t n) {
    const u8 *a = x, *b = y;
    for (; n; n--, a++, b++) if (*a != *b) return *a < *b ? -1 : 1;
    return 0;
}
char  *strchr(const char *s, int c)                 { for (;; s++) { if (*s == (char)c) return (char *)s; if (!*s) return NULL; } }
int    strcmp(const char *x, const char *y) {
    const u8 *a = (const u8 *)x, *b = (const u8 *)y;
    while (*a && *a == *b) { a++; b++; }
    return *a == *b ? 0 : (*a < *b ? -1 : 1);
}
int    strncmp(const char *x, const char *y, size_t n) {
    const u8 *a = (const u8 *)x, *b = (const u8 *)y;
    for (; n; n--, a++, b++) { if (*a != *b) return *a < *b ? -1 : 1; if (!*a) break; }
    return 0;
}
char  *strcpy(char *d, const char *s)               { char *r = d; while ((*d++ = *s++)) ; return r; }
char  *strncpy(char *d, const char *s, size_t n)    { size_t i = 0; for (; i < n && s[i]; i++) d[i] = s[i]; for (; i < n; i++) d[i] = 0; return d; }
void   bzero(void *d, size_t n)                     { u8 *a = d; while (n--) *a++ = 0; }
