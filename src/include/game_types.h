#ifndef GAME_TYPES_H
#define GAME_TYPES_H
#include <stdint.h>
typedef int8_t s8;   typedef uint8_t u8;   typedef int16_t s16; typedef uint16_t u16;
typedef int32_t s32; typedef uint32_t u32; typedef int64_t s64;  typedef uint64_t u64;

/* The game is 32-bit: pointers stored in game structs are u32. */
#define PTR(T, x) ((T *)(uintptr_t)(x))
#define P32(p)    ((u32)(uintptr_t)(p))

/* Absolute data address. Placeholder until .data/.bss are split into real symbols. */
#ifndef GV_BASE
#define GV_BASE 0UL            /* tests/game_test.py maps globals at a host offset */
#endif
#define GV(T, addr) (*(volatile T *)((uintptr_t)(addr) + GV_BASE))
#endif
