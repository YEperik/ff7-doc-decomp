/* Accessors, flag setters and small table lookups from the most-called list. Names are provisional. */
#include "game_extern.h"
#include "game_lock.h"

/* global variables */
s32  get_gvar_0047dadc(void) { return GV(s32, 0x0047dadc); }    /* 0x003ef028 */
s32  get_gvar_0046b4dc(void) { return GV(s32, 0x0046b4dc); }    /* 0x00242450 */
s32  get_gvar_0046e780(void) { return GV(s32, 0x0046e780); }    /* 0x0033ab08 */
s32  get_gvar_0046de0c(void) { return GV(s32, 0x0046de0c); }    /* 0x0030b650 */
void FUN_003e1f80(void)      { GV(u8, 0x004f5ac8) = -1; }     /* 0x003e1f80 */
void FUN_003e1f10(s32 a, s32 b, s32 c) {                        /* 0x003e1f10 */
    GV(u8, 0x004f5ac8) = a; GV(u16, 0x004f5acc) = b; GV(u16, 0x004f5ace) = c;
}
void FUN_004250f8(void)      { GV(s32, 0x00487480) = 0; }       /* 0x004250f8 */
void FUN_00425108(void)      { GV(s32, 0x00487480) = 1; }       /* 0x00425108 */
void FUN_004250f0(void)      { FUN_0042d398(1); }               /* 0x004250f0 */

/* flag words: set or clear one bit */
void set_flag_004b8b80(s32 bit, s32 on) {                       /* 0x00241378 */
    if (on) GV(u32, 0x004b8b80) |= 1u << (bit & 31); else GV(u32, 0x004b8b80) &= ~(1u << (bit & 31));
}
void set_flag_004b8cc8(s32 bit, s32 on) {                       /* 0x00241990 */
    if (on) GV(u32, 0x004b8cc8) |= 1u << (bit & 31); else GV(u32, 0x004b8cc8) &= ~(1u << (bit & 31));
}
void FUN_003e17f8(s32 on) {                                     /* 0x003e17f8 */
    if (on) GV(u32, 0x004f3244) |= 0x1000; else GV(u32, 0x004f3244) &= 0xffffefffu;
}
s32 FUN_003262d8(s32 n) { return (GV(u32, 0x0046e498) & (1u << (n & 31))) != 0; }   /* 0x003262d8 */

/* locks */
void lock_acquire_005035a8(void) { lock_acquire(GPTR(LockQ, 0x005035a8)); }   /* 0x00425098 */
void lock_release_005035a8(void) { lock_release(GPTR(LockQ, 0x005035a8)); }   /* 0x004250a8 */
typedef struct { LockQ q; s32 f88; } LockQX;
void FUN_0042d628(LockQX *q) { q->f88 = -1; q->q.init = 1; q->q.w = 0; q->q.r = 0; }   /* 0x0042d628 */
void FUN_0042d648(LockQ *q)  { q->init = 0; }                                          /* 0x0042d648 */

/* objects */
typedef struct { u8 pad[0x564]; u32 flags; } FlagObj;
void FUN_00341790(FlagObj *o, s32 on) { if (on) o->flags |= 0x400000; else o->flags &= 0xffbfffffu; }   /* 0x00341790 */
s32  FUN_00342348(FlagObj *o) { return (o->flags & 0x800) != 0; }                                        /* 0x00342348 */
typedef struct { u8 pad[0x10]; u16 f10; } HObj;
void FUN_003d49c8(HObj *o, s32 on) { if (on) o->f10 |= 0x100; else o->f10 &= 0xfeff; }                   /* 0x003d49c8 */
void FUN_00249860(s32 *p) { *p = -1; }                                                                   /* 0x00249860 */

typedef struct { u32 f0, f4, f8, f12; u8 pad[0x60]; u32 f112, f116, f120, f124; } InitObj;
InitObj *FUN_005a39b8(InitObj *o) {                                                                      /* 0x005a39b8 */
    o->f0 = 0; o->f124 = 0x005a6e80; o->f4 = 0; o->f8 = 0; o->f12 = 0; o->f120 = 0; o->f116 = 0; o->f112 = 0; return o;
}
u32 FUN_003ee808(void) {                                                                                 /* 0x003ee808 */
    u8 *p = PTR(u8, GV(u32, 0x0047dac0));
    return P32(p) + 0x10 + *(s32 *)p * 0xe0;
}
u32 FUN_005a7918(u8 *o, u32 i) { return i < 4 ? *(u32 *)(o + 1000 + i * 4) : 0; }                       /* 0x005a7918 */

/* tables behind global pointers */
u32 FUN_00318cd8(void) {                                                                                 /* 0x00318cd8 */
    u8 *p = PTR(u8, GV(u32, 0x0046e400)); u32 n;
    if (!p) return 0;
    n = *(u32 *)p;
    return n < 0x100 ? *(u32 *)(p + 12 + n * 4) : 0;
}
u32 FUN_00318c38(s32 a) {                                                                                /* 0x00318c38 */
    u8 *p = PTR(u8, GV(u32, 0x0046e400)); s32 i = (s16)a;
    if (!p) return 0;
    return (u16)i < 0x100 ? *(u32 *)(p + 12 + i * 4) : 0;
}
typedef struct { u8 pad[0x34]; u32 f34; } G68;
typedef struct { u8 pad[0x20]; s32 count; u8 pad24[1]; } G68b;
s32 FUN_00310c80(void) { u8 *p = PTR(u8, GV(u32, 0x0046df68)); return p ? *(s32 *)(p + 100) : -1; }   /* 0x00310c80 */
s32 FUN_00310ca0(void) { u8 *p = PTR(u8, GV(u32, 0x0046df68)); return p ? *(s32 *)(p + 96) : -1; }    /* 0x00310ca0 */
u32 FUN_00310b40(s32 i) {                                                                                /* 0x00310b40 */
    u8 *p = PTR(u8, GV(u32, 0x0046df68)), *t;
    if (!p) return 0;
    t = PTR(u8, *(u32 *)(p + 52));
    if (!t) return 0;
    return i < *(s32 *)(t + 32) ? P32(t) + i * 16 + 0x24 : 0;
}

/* free list: head at +24, next pointer in the first word of each node */
void FUN_0036f798(s32 a, s32 b) {                                                                        /* 0x0036f798 */
    u32 *o = PTR(u32, a), *n = PTR(u32, b);
    if (n) { *n = o[6]; o[6] = P32(n); }
}
u32 FUN_0036f770(u32 *o) {                                                                               /* 0x0036f770 */
    u32 n = o[6];
    if (n) o[6] = *PTR(u32, n);
    return n;
}

/* 0x0033ab18: reset an object and publish it in a global */
typedef struct { u32 f0, f4; } InitObj2;
InitObj2 *FUN_0033ab18(InitObj2 *o) {
    o->f0 = 0; o->f4 = 0x004a1160;
    GV(u32, 0x0046e790) = P32(o);
    return o;
}
s32 FUN_0036f7b8(u32 *o) { return o[6] != 0; }   /* 0x0036f7b8 */
u32 FUN_0036f7c8(u32 *o) { return o[6]; }        /* 0x0036f7c8 */
