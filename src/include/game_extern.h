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
extern s32  FUN_0036f798(s32 a, s32 b);     /* 0x0036f798 */
extern s32  FUN_002f3278(s32 a, s32 b);     /* 0x002f3278 */
extern s32  FUN_0030b6b0(s32 a, s32 b, s32 c);        /* 0x0030b6b0 */

/* Address of the assertion message in .rodata (text intentionally not copied). */
#define ASSERT_MSG_0 ((const char *)0x004a9e68)
#endif
