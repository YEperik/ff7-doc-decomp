/* Floating point helpers from the most-called list. Names are provisional. */
#include "game_extern.h"

/* 0x0040b7c0: a random float in [0, 1): random mantissa bits under the exponent of 1.0, minus 1.0 */
f32 FUN_0040b7c0(void) {
    u32 v = FUN_0040b700();
    u32 b = 0x3f800000u | ((v << 9) >> 9);
    return *(f32 *)&b - 1.0f;
}

/* 0x002599d0: rotation about one axis: two trigonometric values placed in an initialised matrix */
void FUN_002599d0(f32 *m, f32 angle) {
    f32 a = FUN_0045b730(angle);
    f32 b = FUN_0045b628(angle);
    FUN_00261420(m);
    m[10] = b; m[8] = a; m[0] = b; m[2] = -a;
}

/* 0x00284fc8 */
s32 FUN_00284fc8(s32 x) { return FUN_00445218(x, x, 0.0f, 255.0f); }

/* 0x0023c1f0: advance a scaled counter by the elapsed time */
void FUN_0023c1f0(void) {
    s32 now = FUN_00414c80(FUN_0040b278(GV(s32, 0x004bced0)), 0x24000);
    s32 prev = GV(s32, 0x0046b290);
    u32 acc, sum;
    GV(s32, 0x0046b290) = now;
    GV(s32, 0x004b1d08) = now - prev;
    sum = (acc = GV(u32, 0x0046b294)) + (u32)(s32)((f32)(now - prev) * GV(f32, 0x0046b28c));
    GV(u32, 0x0046b294) = acc < sum ? sum : acc;
}
