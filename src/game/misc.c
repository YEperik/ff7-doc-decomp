/* Small leaf functions from the most-called list (symbols/hubs.csv). Names are provisional. */
#include "game_types.h"

/* 0x00444eb8: copy one aligned quadword */
typedef struct { u64 lo, hi; } Quad;
void copy16(Quad *dst, const Quad *src) { *dst = *src; }

typedef struct { u8 pad[0x17c]; u32 f17c; } ObjA;
u32 FUN_0055a570(ObjA *o) { return o->f17c; }

typedef struct { u8 pad[0x20]; u32 f20; } ObjB;
s32 FUN_00316d38(ObjB *o) { return o->f20 == 0; }

/* 0x002535e0 */
s32 FUN_002535e0(s32 x) { return x < 0 ? x : x >> 16; }

/* 0x003cb2f8: first node in the owner's list whose id byte matches; owner itself if none (or id == 0xff) */
typedef struct { u8 pad0[3]; u8 id; u8 pad4[0x2c]; u32 next; } Node;
typedef struct { u8 pad[0x24]; u32 head; } NodeOwner;
void *FUN_003cb2f8(NodeOwner *o, u32 id) {
    u32 p;
    id &= 0xff;
    if (id == 0xff) return o;
    for (p = o->head; p != 0; p = PTR(Node, p)->next)
        if (PTR(Node, p)->id == id) return PTR(Node, p);
    return o;
}

/* 0x002533b0: table[idx & 0xffff] -> entry; value if bit 0 of entry->flags is set */
typedef struct { u8 pad[0x24]; u32 table; } Table;
typedef struct { u32 flags; u32 value; } Entry;
u32 FUN_002533b0(Table *t, u32 idx) {
    u32 e = PTR(u32, t->table)[idx & 0xffff];
    if (e == 0) return 0;
    if (PTR(Entry, e)->flags & 1) return PTR(Entry, e)->value;
    return 0;
}

/* 0x002533f0: 1 if any element's f4 is below the previous element's f8 */
typedef struct { u8 pad[4]; u32 f4; u32 f8; } Span;
typedef struct { u8 pad0[0xc]; s32 count; u8 pad10[8]; u32 arr; } SpanList;
s32 FUN_002533f0(SpanList *s) {
    s32 i; u32 prev = 0; u32 *a;
    if (s->count <= 0) return 0;
    a = PTR(u32, s->arr);
    for (i = 0; i < s->count; i++) {
        u32 cur = a[i];
        if (prev != 0 && PTR(Span, cur)->f4 < PTR(Span, prev)->f8) return 1;
        prev = cur;
    }
    return 0;
}

/* 0x00340bf8: flag bit 1 and a byte at +0x591 */
typedef struct { u8 pad0[0x564]; u32 flags; u8 pad568[0x29]; u8 b591; u8 pad592[0x12e]; u8 b6c0; } Obj340;
void FUN_00340bf8(Obj340 *o, s32 on, s32 v) {
    if (on == 0) { o->flags |= 2; return; }
    if (v >= 0) { o->b591 = v; o->flags &= ~2u; return; }
    if (o->b6c0 == 0) { o->flags |= 2; return; }
    o->b591 = o->b6c0;
    o->flags &= ~2u;
}
