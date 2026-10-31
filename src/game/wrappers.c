/* Small non-leaf wrappers from the most-called list. Names are provisional. */
#include "game_extern.h"

typedef struct { u64 lo, hi; } Quad;

/* 0x002424a0 */
s32 get_gvar_0046b4fc(void) { return GV(s32, 0x0046b4fc); }
/* 0x00326540 */
s32 FUN_00326540(void) { return get_gvar_0046b4fc() != 0; }

/* 0x0054a920: out = o->f8 ? (value computed by FUN_0054a7e8) : o->quad90 */
typedef struct { u8 pad0[8]; s32 f8; u8 pad0c[0x84]; Quad q90; } Obj54;
void FUN_0054a920(Obj54 *o, Quad *out) {
    u8 tmp[0x40] __attribute__((aligned(16)));
    if (o->f8 != 0) {
        FUN_0054a7e8(o, tmp);
        *out = *(Quad *)(tmp + 0x30);
    } else {
        *out = o->q90;
    }
}

/* 0x005a3a48 */
typedef struct { u8 pad[0x14]; s32 f14; } Obj5a;
/* the second argument is passed by callers but never read */
s32 FUN_005a3a48(u32 x, s32 unused) { return FUN_0036f798(PTR(Obj5a, GV(u32, 0x0046f2e0))->f14, x); }

/* 0x005a39e8 */
typedef struct { u8 pad[0x7c]; u32 f7c; } Obj5b;
void FUN_005a39e8(Obj5b *o, s32 flags) {
    o->f7c = 0x005a6e80;
    if (flags & 1) FUN_005a3a48(P32(o), 0x80);
}

/* 0x002a8060 */
typedef struct { u8 pad[0x1c]; s32 f1c; } Obj2a;
void FUN_002a8060(s32 x) {
    if (x) FUN_002f3278(PTR(Obj2a, GV(u32, 0x004ec258))->f1c, x);
}

/* 0x002e14f8 */
s32 FUN_002e14f8(s32 a0, s32 a1, s32 a2, s32 a3) { return FUN_0030b6b0(a1, a2, a3 != 1); }
