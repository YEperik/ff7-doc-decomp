#ifndef GAME_EXTERN_H
#define GAME_EXTERN_H
#include "game_types.h"

/* Callees used by reconstructed functions. Bodies live in the original code. */
extern void DIntr(void);                   /* 0x0044cb68  disable interrupts (COP0 Status, `di`) */
extern void EIntr(void);                   /* 0x0044cbb0  enable interrupts (`ei`) */
extern s32  GetThreadId(void);             /* 0x00451fd0  syscall 0x2f */
extern void SleepThread(void);             /* 0x00452000  syscall 0x32 */
extern s32  WakeupThread(s32 tid);         /* 0x00452010  syscall 0x33 */
extern void FUN_0042d398(s32 arg);         /* 0x0042d398  wait helper */
extern void FUN_00248fd0(const char *msg); /* 0x00248fd0  assertion/print helper (varargs) */

extern s32  RotateThreadReadyQueue(s32 prio);   /* 0x00451f90  syscall 0x2b */
extern void FUN_00251150(void *p);          /* 0x00251150 */
extern u32  FUN_002510b8(u32 size, u32 a, u32 tag);   /* 0x002510b8 */
extern void FUN_0054a7e8(void *obj, void *out);       /* 0x0054a7e8  fills a 0x40-byte buffer */
extern void FUN_0036f798(s32 a, s32 b);     /* 0x0036f798 */
extern s32  FUN_002f3278(s32 a, s32 b);     /* 0x002f3278 */
extern s32  FUN_0030b6b0(s32 a, s32 b, s32 c);        /* 0x0030b6b0 */
extern s32  FUN_0040a288(s32 a);            /* 0x0040a288 */

extern s32  FUN_005a9a60(u32 a);                              /* 0x005a9a60 */
extern s32  FUN_00344648(u32 o, u64 e, s32 a2, s32 a3, s32 a4);   /* 0x00344648 */
extern void FUN_00371ab0(u32 a, void *p, s32 n);              /* 0x00371ab0 */
extern void FUN_002501b0(void);                               /* 0x002501b0 */
extern void FUN_00250048(s32 x);                              /* 0x00250048 */
extern s32  FUN_0036b650(s32 a, s32 b);                       /* 0x0036b650 */
extern s32  FUN_00251ed0(void);                               /* 0x00251ed0 */
extern s32  FUN_00251ef0(u32 a, s32 b, u32 tag);              /* 0x00251ef0 */
extern s32  FUN_002f30a8(s32 a, s32 b, s32 c);                /* 0x002f30a8 */
extern s32  FUN_004484ec(const char *s);                      /* 0x004484ec  strlen */
extern void *FUN_00448800(void *dst, const char *src, s32 n); /* 0x00448800  strncpy */
extern void *FUN_00447c7c(void *dst, const void *src, u32 n); /* 0x00447c7c  memcpy */
extern s32  get_gvar_0046de04(void);                          /* 0x002e14e8 */

extern u32  FUN_0040b700(void);                               /* 0x0040b700  random number source */
extern f32  FUN_0045b730(f32 a);                              /* 0x0045b730 */
extern f32  FUN_0045b628(f32 a);                              /* 0x0045b628 */
extern void FUN_00261420(void *m);                            /* 0x00261420  matrix initialiser */
extern s32  FUN_00445218(s32 a, s32 b, f32 lo, f32 hi);       /* 0x00445218 */
extern s32  FUN_0040b278(s32 a);                              /* 0x0040b278 */
extern s32  FUN_00414c80(s32 a, s32 b);                       /* 0x00414c80 */
extern s32  FUN_003728e8(char *dst, s32 size, const char *fmt, void *frame);   /* 0x003728e8  formatted write */
extern s32  FUN_004489d0(char *out, const char *fmt, void *va);               /* 0x004489d0 */
extern void FUN_002e2f90(s32 level, const char *text);                        /* 0x002e2f90  print */
extern char *FUN_00447fac(char *dst, const char *src);                        /* 0x00447fac  strcat */

/* Address of the assertion message in .rodata (text intentionally not copied). */
#define ASSERT_MSG_0 GPTR(const char, 0x004a9e68)
#endif
