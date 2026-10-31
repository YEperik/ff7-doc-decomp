/* Test shim: callees that are not reconstructed are forwarded to a Python callback by name.
 * The callback records the call and returns a deterministic mock value. */
#include "game_extern.h"
typedef long long (*cb_t)(const char *, unsigned long long, unsigned long long, unsigned long long, unsigned long long);
static cb_t cb;
void shim_set_cb(cb_t f) { cb = f; }
#define A(x) ((unsigned long long)(long long)(x))
#define P(x) ((unsigned long long)(uintptr_t)(x))

void DIntr(void)                 { cb("DIntr", 0, 0, 0, 0); }
void EIntr(void)                 { cb("EIntr", 0, 0, 0, 0); }
s32  GetThreadId(void)           { return (s32)cb("GetThreadId", 0, 0, 0, 0); }
void SleepThread(void)           { cb("SleepThread", 0, 0, 0, 0); }
s32  WakeupThread(s32 t)         { return (s32)cb("WakeupThread", A(t), 0, 0, 0); }
void FUN_0042d398(s32 a)         { cb("FUN_0042d398", A(a), 0, 0, 0); }
void FUN_00248fd0(const char *m) { cb("FUN_00248fd0", P(m), 0, 0, 0); }
s32  RotateThreadReadyQueue(s32 p) { return (s32)cb("RotateThreadReadyQueue", A(p), 0, 0, 0); }
void FUN_00251150(void *p)       { cb("FUN_00251150", P(p), 0, 0, 0); }
u32  FUN_002510b8(u32 s, u32 a, u32 t) { return (u32)cb("FUN_002510b8", A(s), A(a), A(t), 0); }
void FUN_0054a7e8(void *o, void *out)  { cb("FUN_0054a7e8", P(o), P(out), 0, 0); }
s32  FUN_0036f798(s32 a, s32 b)  { return (s32)cb("FUN_0036f798", A(a), A(b), 0, 0); }
s32  FUN_002f3278(s32 a, s32 b)  { return (s32)cb("FUN_002f3278", A(a), A(b), 0, 0); }
s32  FUN_0030b6b0(s32 a, s32 b, s32 c) { return (s32)cb("FUN_0030b6b0", A(a), A(b), A(c), 0); }
u32  game_ra(void)               { return 0xDEAD0000u; }
void game_break(void)            { cb("break", 0, 0, 0, 0); }
