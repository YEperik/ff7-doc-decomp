<p align="center"><img src="assets/banner.png" alt="FF7-DoC Decompilation"></p>

<p align="center"><a href="README.md">English</a> · <a href="docs/ANALYSIS.md">Analisis</a> · <a href="LEGAL.md">Legal</a></p>

---

Toolkit decompile dan peta simbol untuk **FF7 DoC** (PS2, SLPM-66629, Jepang).

## Mulai cepat

Butuh Python 3.9+, tanpa dependensi.

```sh
cp /path/ke/SLPM_666.29 game/      # file milik Anda sendiri, tidak pernah di-commit
make verify                        # cek SHA-256
python -m ps2an info game/SLPM_666.29
python -m ps2an functions game/SLPM_666.29 -o functions.csv
```

## Isi

- `ps2an/` toolkit analisis (info, functions, strings, xrefs, sdk, disasm, stubs)
- `symbols/` alamat dan nama fungsi saja
- `docs/ANALYSIS.md` hasil analisis ELF

## Aturan penting

- Repo ini **tidak berisi** kode, aset, atau disassembly game.
- Asm dibuat **lokal** (`make split`) dan sudah di-ignore git.
- PR hanya boleh berisi kode C, bukan asm atau biner.

Lihat [LEGAL.md](LEGAL.md). Tooling berlisensi MIT.
