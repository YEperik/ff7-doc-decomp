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
#define GV_BASE 0UL            /* tests map globals at a host offset */
#endif
#define GV(T, addr) (*(volatile T *)((uintptr_t)(addr) + GV_BASE))
#define GPTR(T, addr) ((T *)((uintptr_t)(addr) + GV_BASE))   /* pointer to a global object */

/* `break` after a failed assertion. Tests replace it with a recording hook. */
#ifdef HOST_TEST
extern void game_break(void);
#define BREAK() game_break()
#elif defined(CC_PARSE)
extern void __cc_break(void);
#define BREAK() __cc_break()
#else
#define BREAK() __asm__ volatile("break")
#endif

/* Return address of the current function (used as an allocation tag). */
#ifdef HOST_TEST
extern u32 game_ra(void);
#define RETURN_ADDRESS() game_ra()
#elif defined(CC_PARSE)
extern u32 __cc_ra(void);
#define RETURN_ADDRESS() __cc_ra()
#else
#define RETURN_ADDRESS() ((u32)__builtin_return_address(0))
#endif
#endif
