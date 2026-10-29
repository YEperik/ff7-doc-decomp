/* Trivial accessors for global variables (addresses in the .data/.bss range). */
#include "game_types.h"

s32  get_gvar_004efda0(void)      { return GV(s32, 0x004efda0); }   /* 0x003a8db8 */
s32  get_gvar_0046de04(void)      { return GV(s32, 0x0046de04); }   /* 0x002e14e8 */
s32  get_gvar_004b8d9c(void)      { return GV(s32, 0x004b8d9c); }   /* 0x00241a00 */
void set_gvar_004b8d9c(s32 v)     { GV(s32, 0x004b8d9c) = v; }      /* 0x002419f0 */
s32  get_gvar_004b8d3c(void)      { return GV(s32, 0x004b8d3c); }   /* 0x00241a10 */
void set_gvar_0046b3d4(s32 v)     { GV(s32, 0x0046b3d4) = v; }      /* 0x002413e0 */

/* 0x002419d8: bit n of a flag word (arithmetic shift, low 5 bits of n) */
s32 get_flag_004b8cc8(s32 n)      { return (GV(s32, 0x004b8cc8) >> (n & 31)) & 1; }
/* 0x002413c0: mask test */
s32 has_flag_004b8b80(s32 n)      { return (GV(u32, 0x004b8b80) & (1u << (n & 31))) != 0; }
