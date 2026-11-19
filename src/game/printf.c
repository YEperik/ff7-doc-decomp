/* Formatted output wrappers. The original compiler saves the argument registers in an area on the stack
 * (the vararg frame); the registers are explicit parameters here so that the layout can be reproduced. */
#include "game_extern.h"

/* register save area built by the two wrappers (0x58 bytes) */
typedef struct { u32 nint, nfloat; f32 f[8]; u32 i[6]; u32 pad[2]; u32 sp, ra, z0, z1; } VaFrame;

/* 0x00248f4c: (dst, fmt, ...) -> formatted write limited to 10000 characters */
s32 FUN_00248f4c(char *dst, const char *fmt, u32 a2, u32 a3, u32 t0, u32 t1, u32 t2, u32 t3,
                 f32 f12, f32 f13, f32 f14, f32 f15, f32 f16, f32 f17, f32 f18, f32 f19) {
    VaFrame fr;
    fr.nint = 6; fr.nfloat = 8;
    fr.f[0] = f12; fr.f[1] = f13; fr.f[2] = f14; fr.f[3] = f15; fr.f[4] = f16; fr.f[5] = f17; fr.f[6] = f18; fr.f[7] = f19;
    fr.i[0] = a2; fr.i[1] = a3; fr.i[2] = t0; fr.i[3] = t1; fr.i[4] = t2; fr.i[5] = t3;
    fr.sp = 0; fr.ra = 0; fr.z0 = 0; fr.z1 = 0;
    return FUN_003728e8(dst, 10000, fmt, &fr);
}

/* 0x00248ed8: (dst, size, fmt, ...) */
s32 FUN_00248ed8(char *dst, s32 size, const char *fmt, u32 a3, u32 t0, u32 t1, u32 t2, u32 t3,
                 f32 f12, f32 f13, f32 f14, f32 f15, f32 f16, f32 f17, f32 f18, f32 f19) {
    VaFrame fr;
    fr.nint = 5; fr.nfloat = 8;
    fr.f[0] = f12; fr.f[1] = f13; fr.f[2] = f14; fr.f[3] = f15; fr.f[4] = f16; fr.f[5] = f17; fr.f[6] = f18; fr.f[7] = f19;
    fr.i[0] = a3; fr.i[1] = t0; fr.i[2] = t1; fr.i[3] = t2; fr.i[4] = t3;
    fr.sp = 0; fr.ra = 0; fr.z0 = 0; fr.z1 = 0;
    return FUN_003728e8(dst, size, fmt, &fr);
}

/* 0x002a80b0: builds the last two path components, a separator, the line number, a separator and the message,
 * prints the text at level 3 and, if the global flag is set, hands it to the assertion helper and stops. */
typedef struct { f32 f[4]; u64 i[5]; } VaArea;
void FUN_002a80b0(const char *file, s32 line, const char *fmt, u64 a3, u64 t0, u64 t1, u64 t2, u64 t3,
                  f32 f12, f32 f13, f32 f14, f32 f15, f32 f16, f32 f17, f32 f18, f32 f19) {
    char buf[0x200];
    char out[0x200];
    VaArea va;
    s32 n = 0, slashes = 0;
    const char *q;
    va.f[0] = f12; va.f[1] = f14; va.f[2] = f16; va.f[3] = f18;
    va.i[0] = a3; va.i[1] = t0; va.i[2] = t1; va.i[3] = t2; va.i[4] = t3;
    buf[0] = 0;
    n = FUN_004484ec(file);
    q = file + n - 1;
    if (!(q < file)) {                                   /* find the start of the last two path components */
        if (file[n - 1] == '/') slashes = 1;
        for (;;) {
            q--;
            if (q < file) break;
            if (*q == '/') { slashes++; if (slashes == 2) break; }
        }
    }
    FUN_00447fac(buf, q + 1);
    FUN_00447fac(buf, GPTR(const char, 0x0049d258));
    FUN_00248f4c(buf + FUN_004484ec(buf), GPTR(const char, 0x0049d260), line, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
    FUN_00447fac(buf, GPTR(const char, 0x0049d268));
    FUN_004489d0(out, fmt, &va.i[0]);
    FUN_00447fac(buf, out);
    FUN_002e2f90(3, buf);
    if (GV(s8, 0x0046d63c)) { FUN_00248fd0(buf); BREAK(); }
}
