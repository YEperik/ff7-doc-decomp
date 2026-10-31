/* Lock around the allocator and its two thin wrappers. */
#include "game_extern.h"
#include "game_lock.h"

#define LOCK_004DFD00 GPTR(LockQ, 0x004dfd00)

void lock_acquire_004dfd00(void) { lock_acquire(LOCK_004DFD00); }   /* 0x00251e30 */
void lock_release_004dfd00(void) { lock_release(LOCK_004DFD00); }   /* 0x00251e50 */

/* 0x002521f0 */
void FUN_002521f0(void *p) {
    lock_acquire_004dfd00();
    FUN_00251150(p);
    lock_release_004dfd00();
}

/* 0x00252160 and 0x002521a8 are byte-identical copies */
u32 FUN_00252160(u32 size) {
    u32 v;
    lock_acquire_004dfd00();
    v = FUN_002510b8(size, 0, RETURN_ADDRESS());
    lock_release_004dfd00();
    return v;
}

u32 FUN_002521a8(u32 size) {
    u32 v;
    lock_acquire_004dfd00();
    v = FUN_002510b8(size, 0, RETURN_ADDRESS());
    lock_release_004dfd00();
    return v;
}
