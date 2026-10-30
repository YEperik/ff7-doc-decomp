ELF ?= game/SLPM_666.29
PY  ?= python3

.PHONY: progress milestone test verify info symbols stubs split ghidra-check release clean
progress: ; $(PY) -m ps2an progress
milestone: ; $(PY) -m ps2an progress --record "$(LABEL)"   # usage: make milestone LABEL="..."
test:    ; $(PY) tests/diff_test.py $(ELF) && $(PY) tests/game_test.py $(ELF)
verify:  ; $(PY) -m ps2an verify $(ELF)
info:    ; $(PY) -m ps2an info $(ELF)
symbols: ; $(PY) -m ps2an symbols $(ELF)
stubs:   ; $(PY) -m ps2an stubs $(ELF)
split:   ; $(PY) -m ps2an split $(ELF) -o build/asm      # local only, git-ignored
ghidra-check: ; $(PY) -m ps2an ghidra $(ELF) ghidra/SLPM_666_29.gzf
release: ; $(PY) scripts/make_release.py
clean:   ; rm -rf build dist
