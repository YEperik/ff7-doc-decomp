/* 8-byte cell stack. The stack pointer lives at ctx+0xF014 and grows downward. */
#include "game_types.h"

typedef struct { s16 type; s16 pad; s32 value; } Cell;
typedef struct { u8 pad[0xF014]; u32 sp; } CellCtx;

/* 0x003aa140 */
s32 cstack_pop(CellCtx *c) {
    Cell *p = PTR(Cell, c->sp);
    s32 v = p->value;
    c->sp = P32(p + 1);
    return v;
}

/* 0x003aa0c0 */
void cstack_push_int(CellCtx *c, s32 v) {
    c->sp -= sizeof(Cell);
    PTR(Cell, c->sp)->type = 1;
    PTR(Cell, c->sp)->value = v;
}

/* 0x003aa108: discard the top cell, optionally copying it to out first */
void cstack_drop(CellCtx *c, void *out) {
    if (out) *(u64 *)out = *PTR(u64, c->sp);
    c->sp += sizeof(Cell);
}
