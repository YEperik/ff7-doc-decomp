/* FIFO lock built from a ring of waiting thread ids.
 * Layout: u32 slot[32] | u16 r (+0x80) | u16 w (+0x82) | s32 init (+0x84). */
#include "game_extern.h"
#include "game_lock.h"

/* 0x0042d428: queue the current thread; sleep unless it is first in line */
void lock_acquire(LockQ *q) {
    u32 tid = GetThreadId();
    u16 w;
    int was_empty;
    if (q->init == 0) { FUN_00248fd0(ASSERT_MSG_0); BREAK(); }
    DIntr();
    for (;;) {
        w = q->w;
        if (((w + 1) & 0x1f) != q->r) break;       /* not full */
        EIntr();
        FUN_0042d398(1);
        DIntr();
    }
    q->slot[w] = tid;
    was_empty = (q->w == q->r);
    q->w = (q->w + 1) & 0x1f;
    EIntr();
    if (!was_empty) SleepThread();
}

/* 0x0042d590: drop the head of the queue and wake the next waiter */
void lock_release(LockQ *q) {
    s32 next = -1;
    u16 r, w;
    if (q->init == 0) { FUN_00248fd0(ASSERT_MSG_0); BREAK(); }
    DIntr();
    r = q->r; w = q->w;
    if (r != w) {
        r = (r + 1) & 0x1f;
        q->r = r;
        if (r != w) next = q->slot[r];
    }
    EIntr();
    if (next >= 0) WakeupThread(next);
}
