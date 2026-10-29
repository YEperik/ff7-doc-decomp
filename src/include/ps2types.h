#ifndef PS2TYPES_H
#define PS2TYPES_H

typedef signed char        s8;   typedef unsigned char        u8;
typedef signed short       s16;  typedef unsigned short       u16;
typedef signed int         s32;  typedef unsigned int         u32;
typedef signed long        s64;  typedef unsigned long        u64;
typedef unsigned int       u128 __attribute__((mode(TI)));
typedef float              f32;

/* Pull an original function from the locally generated asm (never committed). */
#define INCLUDE_ASM(sec, name) __asm__(".include \"build/asm/" sec "/" #name ".s\"")

#endif
