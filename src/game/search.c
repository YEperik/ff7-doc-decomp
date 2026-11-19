/* String copy, linear and binary searches, and small thunks from the most-called list. Names are provisional. */
#include "game_extern.h"

/* 0x00422f18: bounded copy that stops at the terminator; writes the terminator and returns a pointer to it */
char *FUN_00422f18(char *dst, const char *src, s32 n) {
    s32 i = 0;
    if (*src != 0 && n > 0) {
        do { dst[i] = src[i]; i++; } while (src[i] != 0 && i < n);
    }
    dst[i] = 0;
    return dst + i;
}

/* 0x0037a640: find the entry (stride 0x200, key at +0x18 of the entry at +0x1800) holding key; 0 if key is 0 or absent */
u32 FUN_0037a640(u8 *base, s32 key) {
    s32 i;
    if (key == 0) return 0;
    for (i = 0; i < 0x40; i++)
        if (*(s32 *)(base + 0x1818 + i * 0x200) == key) return P32(base + 0x1800 + i * 0x200);
    return 0;
}

/* 0x00454110 */
s32 FUN_00454110(u8 *o) {
    u8 *p = PTR(u8, *(u32 *)o);
    if (!p) return 0;
    if (*(u32 *)(o + 4) != *(u32 *)(p + 24)) return 0;
    return (*(u32 *)(p + 16) & 1) != 0;
}

/* 0x0055bd40: is the byte a continuation byte (0x80..0xbf)? */
s32 FUN_0055bd40(u8 *o) { u8 c = o[260]; return c >= 0x80 && c < 0xc0; }

/* binary searches over records with a u32 key at +24; return the index or -1 */
s32 FUN_00bd7f38(s32 unused, u8 *arr, s32 lo, s32 hi, u32 key) {       /* 0x00bd7f38, record size 0x40 */
    while (lo <= hi) {
        s32 mid = (lo + hi) >> 1;
        u32 v = *(u32 *)(arr + mid * 0x40 + 24);
        if (v == key) return mid;
        if (key < v) hi = mid - 1; else lo = mid + 1;
    }
    return -1;
}
s32 FUN_00bd81a8(s32 unused, u8 *arr, s32 lo, s32 hi, u32 key) {       /* 0x00bd81a8, record size 0x50 */
    while (lo <= hi) {
        s32 mid = (lo + hi) >> 1;
        u32 v = *(u32 *)(arr + mid * 0x50 + 24);
        if (v == key) return mid;
        if (key < v) hi = mid - 1; else lo = mid + 1;
    }
    return -1;
}

/* thunks to FUN_0040a288 */
s32 FUN_002490bc(void)       { return FUN_0040a288(0x64); }                    /* 0x002490bc */
s32 FUN_002490c8(s32 a)      { return FUN_0040a288((s32)((u32)a << 6)); }      /* 0x002490c8 */
s32 FUN_002490d0(u32 a)      { return FUN_0040a288((s32)a); }                  /* 0x002490d0: argument zero-extended */
