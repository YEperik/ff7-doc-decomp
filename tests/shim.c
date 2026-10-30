/* Test shim: every callee the reconstructed code uses is forwarded to a Python callback,
 * which records the call and returns a deterministic mock value. */
typedef long long (*cb_t)(int, unsigned long long, unsigned long long, unsigned long long, unsigned long long);
static cb_t cb;
void shim_set_cb(cb_t f) { cb = f; }

void DIntr(void)                       { cb(1, 0, 0, 0, 0); }
void EIntr(void)                       { cb(2, 0, 0, 0, 0); }
int  GetThreadId(void)                 { return (int)cb(3, 0, 0, 0, 0); }
void SleepThread(void)                 { cb(4, 0, 0, 0, 0); }
int  WakeupThread(int tid)             { return (int)cb(5, (unsigned long long)(long long)tid, 0, 0, 0); }
void FUN_0042d398(int a)               { cb(6, (unsigned long long)(long long)a, 0, 0, 0); }
void FUN_00248fd0(const char *m)       { cb(7, (unsigned long long)(unsigned long)m, 0, 0, 0); }
void game_break(void)                  { cb(9, 0, 0, 0, 0); }
