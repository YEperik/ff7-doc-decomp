#ifndef GAME_LOCK_H
#define GAME_LOCK_H
#include "game_types.h"
/* FIFO lock: ring of waiting thread ids. u32 slot[32] | u16 r (+0x80) | u16 w (+0x82) | s32 init (+0x84) */
typedef struct { u32 slot[32]; u16 r; u16 w; s32 init; } LockQ;
void lock_acquire(LockQ *q);   /* 0x0042d428 */
void lock_release(LockQ *q);   /* 0x0042d590 */
#endif
