## 2025-10-15 - Python mmap Buffer Exports with memoryview and struct.iter_unpack

**Learning:** Slicing a `memoryview` over an `mmap.mmap` object (e.g. for fast word iteration using `struct.iter_unpack`) creates an exported buffer pointer. Exiting the `with mmap.mmap(...)` context manager while buffer references exist causes Python to raise `BufferError: cannot close exported pointers exist`.
**Action:** Always wrap `memoryview` section operations in `try ... finally` blocks and call `mv.release()` to explicitly unbind exported pointers before the `mmap` context closes.
