/* More accessors, flag setters and table lookups from the most-called list. Names are provisional. */
#include "game_extern.h"
#include "game_lock.h"

s32 get_gvar_0046b310(void) { return GV(s32, 0x0046b310); }     /* 0x0023ec60 */
s32 get_gvar_004f3234(void) { return GV(s32, 0x004f3234); }     /* 0x003dce58 */

/* one flag bit in a field of an object */
void FUN_003cb560(u8 *o, s32 on)  { if (on) o[2] |= 0x01; else o[2] &= 0xfe; }                          /* 0x003cb560 */
typedef struct { u8 pad[0x10]; u16 f10; } HObj3;
void FUN_003d49f8(HObj3 *o, s32 on) { if (on) o->f10 |= 0x1000; else o->f10 &= 0xefff; }               /* 0x003d49f8 */
void FUN_005a7538(u8 *o, s32 bit) { *(u32 *)(o + 1060) |= 1u << (bit & 31); }                          /* 0x005a7538 */
s32  FUN_00315778(u8 *o, s32 bit) { return (*(u32 *)(o + 12) & (1u << (bit & 31))) != 0; }             /* 0x00315778 */

/* byte and pointer getters */
u8   FUN_00563488(u8 *o) { return o[392]; }                                                           /* 0x00563488 */
s32  FUN_003177e8(u8 *o) { return o[39] & 0xf; }                                                       /* 0x003177e8 */
s32  FUN_00317670(u8 *o) {                                                                             /* 0x00317670 */
    u8 *p;
    if (!(*(u32 *)(o + 96) & 2)) return 0;
    p = PTR(u8, *(u32 *)(o + 156));
    if (!p) return 0;
    return (s8)p[174];
}
s32  FUN_00341a00(u8 *o) { u8 *p = PTR(u8, *(u32 *)(o + 2000)); return p ? *(s32 *)(p + 112) : 0; }     /* 0x00341a00 */
s32  FUN_003236e8(void)  { u8 *p = PTR(u8, GV(u32, 0x0046e490)); return p ? *(s32 *)(p + 60) : 0; }    /* 0x003236e8 */

/* tables */
u32 FUN_0053e240(u8 *o, u32 i) { u32 *t = PTR(u32, *(u32 *)(o + 4452)); return i < 0x400 ? t[i] : 0; }   /* 0x0053e240 */
u32 FUN_003b6610(s32 unused, u32 i) {                                                                  /* 0x003b6610 */
    u8 *e;
    if (i >= 8) return 0;
    e = GPTR(u8, 0x0050dd60u + i * 0x28);
    return *(u32 *)(e + 4) ? P32(e) : 0;
}
typedef struct { u32 w0; s16 h4; u8 pad6[10]; u32 p16; } Packed;
u32 FUN_0031a9d0(Packed *o) {                                                                          /* 0x0031a9d0 */
    s32 n = (s32)(o->w0 << 28) >> 28;
    if (n < 0) return 0;
    if (!(n < o->h4)) return 0;
    return o->p16 + n * 0xcc;
}
typedef struct { u8 pad[0x14]; u32 f14; u32 f18; } SObj;
u32 FUN_0033e158(SObj *o, s32 a) {                                                                     /* 0x0033e158 */
    s16 i = (s16)a;
    if (!(i < *(s16 *)(PTR(u8, o->f14) + 2))) return 0;
    if (i == -1) return 0;
    return o->f18 + ((u32)i << 5);
}
s32 FUN_00240f28(void) {                                                                               /* 0x00240f28 */
    s32 i;
    for (i = 0; i < 5; i++) if (GV(s32, 0x004b2790 + 4 * i) >= 0) return 1;
    return 0;
}
u32 FUN_002694e8(s32 key) {                                                                            /* 0x002694e8 */
    s32 i;
    for (i = 0; i < 3; i++) {
        u8 *e = GPTR(u8, 0x004e4e60u + i * 0x70);
        if (*(s32 *)(e + 92) != 0 && *(s32 *)(e + 84) == key) return P32(e);
    }
    return 0;
}
typedef struct { u8 pad[20]; s16 h20; u8 pad22[114]; s16 h136; u8 pad138[8]; s16 h146; } DObj;
void FUN_003d96d0(DObj *o, s32 a) {                                                                    /* 0x003d96d0 */
    s16 v = (s16)a;
    o->h146 = v;
    o->h136 = ((s32)o->h20 + v - 1) / v;
}

/* initialisers */
typedef struct { u32 f[16]; } Mat;
void FUN_002d84d0(Mat *m) {                                                                            /* 0x002d84d0: 4x4 identity */
    int i;
    for (i = 0; i < 16; i++) m->f[i] = 0;
    m->f[0] = 0x3f800000; m->f[5] = 0x3f800000; m->f[10] = 0x3f800000; m->f[15] = 0x3f800000;
}
typedef struct { u32 f0; } VObj;
VObj *FUN_003f1b68(VObj *o) { o->f0 = 0x004a7418; GV(u32, 0x0047dae0) = 0; return o; }               /* 0x003f1b68 */

/* object lock at +8 */
void FUN_0041f358(u8 *o) { lock_acquire((LockQ *)(o + 8)); }                                           /* 0x0041f358 */
void FUN_0041f360(u8 *o) { lock_release((LockQ *)(o + 8)); }                                           /* 0x0041f360 */
