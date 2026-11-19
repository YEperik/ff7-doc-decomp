/* Test shim: callees that are not reconstructed are forwarded to a Python callback by name.
 * The callback records the call and returns a deterministic mock value.
 * Already verified libc routines are provided by the host libc. */
#include <string.h>
#include "game_extern.h"
typedef long long (*cb_t)(const char *, unsigned long long, unsigned long long, unsigned long long, unsigned long long, unsigned long long, unsigned long long, unsigned long long);
static cb_t cb;
#define cbx(n, a, b, c, d, e) cb(n, a, b, c, d, e, 0, 0)
static unsigned FB(float f) { unsigned u; memcpy(&u, &f, 4); return u; }
static float BF(long long r) { unsigned u = (unsigned)r; float f; memcpy(&f, &u, 4); return f; }
void shim_set_cb(cb_t f) { cb = f; }
#define A(x) ((unsigned long long)(long long)(x))
#define P(x) ((unsigned long long)(uintptr_t)(x))

void DIntr(void)                 { cbx("DIntr", 0, 0, 0, 0, 0); }
void EIntr(void)                 { cbx("EIntr", 0, 0, 0, 0, 0); }
s32  GetThreadId(void)           { return (s32)cbx("GetThreadId", 0, 0, 0, 0, 0); }
void SleepThread(void)           { cbx("SleepThread", 0, 0, 0, 0, 0); }
s32  WakeupThread(s32 t)         { return (s32)cbx("WakeupThread", A(t), 0, 0, 0, 0); }
void FUN_0042d398(s32 a)         { cbx("FUN_0042d398", A(a), 0, 0, 0, 0); }
void FUN_00248fd0(const char *m) { cbx("FUN_00248fd0", P(m), 0, 0, 0, 0); }
s32  RotateThreadReadyQueue(s32 p) { return (s32)cbx("RotateThreadReadyQueue", A(p), 0, 0, 0, 0); }
void FUN_00251150(void *p)       { cbx("FUN_00251150", P(p), 0, 0, 0, 0); }
u32  FUN_002510b8(u32 s, u32 a, u32 t) { return (u32)cbx("FUN_002510b8", A(s), A(a), A(t), 0, 0); }
void FUN_0054a7e8(void *o, void *out)  { cbx("FUN_0054a7e8", P(o), P(out), 0, 0, 0); }
s32  FUN_002f3278(s32 a, s32 b)  { return (s32)cbx("FUN_002f3278", A(a), A(b), 0, 0, 0); }
s32  FUN_0030b6b0(s32 a, s32 b, s32 c) { return (s32)cbx("FUN_0030b6b0", A(a), A(b), A(c), 0, 0); }
s32  FUN_0040a288(s32 a)         { return (s32)cbx("FUN_0040a288", A(a), 0, 0, 0, 0); }
s32  FUN_005a9a60(u32 a)         { return (s32)cbx("FUN_005a9a60", A(a), 0, 0, 0, 0); }
s32  FUN_00344648(u32 o, u64 e, s32 a2, s32 a3, s32 a4) { return (s32)cbx("FUN_00344648", A(o), (unsigned long long)e, A(a2), A(a3), A(a4)); }
void FUN_00371ab0(u32 a, void *p, s32 n) { cbx("FUN_00371ab0", A(a), P(p), A(n), 0, 0); }
void FUN_002501b0(void)          { cbx("FUN_002501b0", 0, 0, 0, 0, 0); }
void FUN_00250048(s32 x)         { cbx("FUN_00250048", A(x), 0, 0, 0, 0); }
s32  FUN_0036b650(s32 a, s32 b)  { return (s32)cbx("FUN_0036b650", A(a), A(b), 0, 0, 0); }
s32  FUN_00251ed0(void)          { return (s32)cbx("FUN_00251ed0", 0, 0, 0, 0, 0); }
s32  FUN_00251ef0(u32 a, s32 b, u32 t) { return (s32)cbx("FUN_00251ef0", A(a), A(b), A(t), 0, 0); }
s32  FUN_002f30a8(s32 a, s32 b, s32 c) { return (s32)cbx("FUN_002f30a8", A(a), A(b), A(c), 0, 0); }
u32  FUN_0040b700(void)         { return (u32)cbx("FUN_0040b700", 0, 0, 0, 0, 0); }
f32  FUN_0045b730(f32 a)         { return BF(cb("FUN_0045b730", 0, 0, 0, 0, 0, FB(a), 0)); }
f32  FUN_0045b628(f32 a)         { return BF(cb("FUN_0045b628", 0, 0, 0, 0, 0, FB(a), 0)); }
void FUN_00261420(void *m)       { cbx("FUN_00261420", P(m), 0, 0, 0, 0); }
s32  FUN_00445218(s32 a, s32 b, f32 lo, f32 hi) { return (s32)cb("FUN_00445218", A(a), A(b), 0, 0, 0, FB(lo), FB(hi)); }
s32  FUN_0040b278(s32 a)         { return (s32)cbx("FUN_0040b278", A(a), 0, 0, 0, 0); }
s32  FUN_00414c80(s32 a, s32 b)  { return (s32)cbx("FUN_00414c80", A(a), A(b), 0, 0, 0); }
s32  FUN_003728e8(char *d, s32 n, const char *f, void *fr) { return (s32)cbx("FUN_003728e8", P(d), A(n), P(f), P(fr), 0); }
s32  FUN_004489d0(char *o, const char *f, void *va)       { return (s32)cbx("FUN_004489d0", P(o), P(f), P(va), 0, 0); }
void FUN_002e2f90(s32 l, const char *t)                   { cbx("FUN_002e2f90", A(l), P(t), 0, 0, 0); }
char *FUN_00447fac(char *d, const char *s)                { return strcat(d, s); }
u32  game_ra(void)               { return 0xDEAD0000u; }
void game_break(void)            { cbx("break", 0, 0, 0, 0, 0); }

/* verified libc routines (see tests/diff_test.py) */
s32   FUN_004484ec(const char *s)                       { return (s32)strlen(s); }
void *FUN_00448800(void *d, const char *s, s32 n)       { return strncpy(d, s, n); }
void *FUN_00447c7c(void *d, const void *s, u32 n)       { return memcpy(d, s, n); }
