/* Small non-leaf wrappers (second batch). Names are provisional. */
#include "game_extern.h"
#include "game_lock.h"

typedef struct { u8 pad[0x1c]; s32 f1c; } Obj2a2;

/* 0x00346118 */
s32 FUN_00346118(u8 *o) { u32 p = *(u32 *)(o + 1992); if (!p) return 1; return FUN_005a9a60(p) ^ 1; }

/* 0x00345700: element of a table of 64-bit values, passed on with the caller's last argument */
s32 FUN_00345700(u8 *o, s32 idx, s32 a2, s32 a3) {
    u64 e = *(u64 *)(PTR(u8, *(u32 *)(o + 2044)) + idx * 8);
    return FUN_00344648(P32(o), e, a2, 0, a3);
}

/* 0x00371cf0: write the same buffer twice, the first time through a local copy of its length */
void FUN_00371cf0(u32 a0, u32 a1, s32 a2) {
    s32 tmp = a2;
    FUN_00371ab0(a0, &tmp, 4);
    FUN_00371ab0(a0, PTR(void, a1), a2);
}

/* 0x002500d8 */
void FUN_002500d8(s32 x) { FUN_002501b0(); FUN_00250048(x); }

/* 0x003260a8 */
s32 FUN_003260a8(s32 x) { return FUN_0036b650(GV(s32, 0x0046e494), x); }

/* 0x003db060 */
s32 FUN_003db060(void) { return FUN_00251ed0(); }

/* 0x003db010: passes the caller's return address as a tag */
s32 FUN_003db010(u32 a) { return FUN_00251ef0(a, 0, RETURN_ADDRESS()); }

/* 0x002585d0: the first 8 bytes of a string packed into a 64-bit value (zero padded) */
u64 FUN_002585d0(const char *s) {
    u64 buf = 0;
    s32 n = FUN_004484ec(s);
    FUN_00448800(&buf, s, n < 9 ? n : 8);
    return buf;
}

/* 0x00371b40: read up to n bytes from an in-memory stream (position +24, end +28) */
void FUN_00371b40(u8 *o, void *dst, u32 n) {
    u32 pos, end, take;
    if (*(u32 *)(o + 4) != 0) return;
    if (*(u32 *)(o + 12) != 0) return;
    pos = *(u32 *)(o + 24); end = *(u32 *)(o + 28);
    take = end < pos + n ? end - pos : n;
    if (*(u32 *)(o + 8) == 0 && dst != 0) FUN_00447c7c(dst, PTR(void, pos), take);
    *(u32 *)(o + 24) += take;
}

/* 0x002a8010 */
s32 FUN_002a8010(s32 x) {
    s32 b = x ? x : 1;
    return FUN_002f30a8(PTR(Obj2a2, GV(u32, 0x004ec258))->f1c, b, 1);
}

/* 0x00286670 */
u32 *FUN_00286670(u32 *o) {
    s32 v = get_gvar_0046de04();
    o[0] = v; o[1] = v + 0x30;
    return o;
}

/* 0x00bd0008 (overlay): take the lock at +0x44; if the state is 2 set the top bit of +28, otherwise release and fail */
s32 FUN_00bd0008(u8 *o) {
    lock_acquire((LockQ *)(o + 0x44));
    if (*(s32 *)(o + 12) == 2) { *(u32 *)(o + 28) |= 0x80000000u; return 0; }
    lock_release((LockQ *)(o + 0x44));
    return 0xffff448a;
}

/* 0x00258618: stub */
s32 FUN_00258618(void) { return 0; }
