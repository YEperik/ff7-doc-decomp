<p align="center"><img src="assets/banner.png" alt="FF7-DoC Decompilation"></p>

<p align="center"><img src="assets/badge-decompiled.svg" alt="decompiled"></p>

<p align="center"><a href="README.md">English</a> · <a href="docs/PROGRESS.md">Progres</a> · <a href="docs/ANALYSIS.md">Analisis</a> · <a href="LEGAL.md">Legal</a></p>

---

Toolkit decompile dan peta simbol untuk **FF7 DoC** (PS2, SLPM-66629, Jepang).

## Mulai cepat

Butuh Python 3.9+, tanpa dependensi.

```sh
cp /path/ke/SLPM_666.29 game/      # salinan milik Anda sendiri
make verify                        # cek SHA-256
make test                          # uji C vs kode asli
python -m ps2an info game/SLPM_666.29
python -m ps2an functions game/SLPM_666.29 -o functions.csv
```

## Isi

- `ps2an/` toolkit analisis (info, functions, strings, xrefs, sdk, disasm, stubs)
- `symbols/` alamat dan nama fungsi saja
- `src/libc/` dan `src/game/` C untuk 12 fungsi libc dan 19 fungsi game, diuji terhadap kode asli
- `docs/ANALYSIS.md` hasil analisis ELF

## Progres

Persentase decompile dihitung otomatis dari metadata publik: [docs/PROGRESS.md](docs/PROGRESS.md). Fungsi dihitung selesai hanya jika C-nya lolos uji diferensial terhadap kode asli. Perbarui dengan `make progress`.

## Kontribusi

- Pilih fungsi dari `symbols/hubs.csv`, tulis C-nya di `src/game/`, pastikan `make test` lulus, lalu jalankan `make progress`.
- PR hanya berisi C dan tes.

Lihat [LEGAL.md](LEGAL.md). Tooling berlisensi MIT.
