ELF ?= game/SLPM_666.29
PY  ?= python3

.PHONY: progress milestone match test verify info symbols stubs split clean
progress: ; $(PY) -m ps2an progress
milestone: ; $(PY) -m ps2an progress --record "$(LABEL)"   # usage: make milestone LABEL="..."
match:   ; $(PY) -m ps2an match $(ELF) --write
test:    ; $(PY) tests/diff_test.py $(ELF) && $(PY) tests/game_test.py $(ELF) && $(PY) tests/asm_test.py $(ELF) && $(PY) tests/match_test.py $(ELF)
verify:  ; $(PY) -m ps2an verify $(ELF)
info:    ; $(PY) -m ps2an info $(ELF)
symbols: ; $(PY) -m ps2an symbols $(ELF)
stubs:   ; $(PY) -m ps2an stubs $(ELF)
split:   ; $(PY) -m ps2an split $(ELF) -o build/asm      # local only, git-ignored
clean:   ; rm -rf build dist
