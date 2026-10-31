/* Per-object lock at +0x3d4, taken unless the caller is the owning thread. */
#include "game_extern.h"
#include "game_lock.h"

typedef struct { u8 pad[0x3d4]; LockQ lock; } LockedObj;

/* 0x00241de8: is the current thread the one stored in the global? */
s32 FUN_00241de8(void) { return GetThreadId() == GV(s32, 0x004b8cf8); }

/* 0x00376198 */
void FUN_00376198(LockedObj *o, s32 force) {
    if (force != 0) { lock_acquire(&o->lock); return; }
    if (FUN_00241de8() == 0) lock_acquire(&o->lock);
}

/* 0x003761e8 */
void FUN_003761e8(LockedObj *o, s32 force) {
    RotateThreadReadyQueue(3);
    if (force != 0) { lock_release(&o->lock); return; }
    if (FUN_00241de8() == 0) lock_release(&o->lock);
}
