# Windows 10 setup

## Python

Install Python 3 from https://www.python.org/downloads/windows/ and enable **Add Python to PATH**. Verify in Command Prompt:

```bat
py --version
```

No third-party Python packages are required for the included scripts.

## Generate reports

From the project folder:

```bat
py tools\analyze_elf.py "D:\research\SLPM_666.29" --out reports
```

Or drag an ELF file onto `analyze-elf.bat`.

## Ghidra

1. Install Ghidra using its official instructions.
2. Install a compatible release of Ghidra Emotion Engine: Reloaded from its GitHub Releases page.
3. In Ghidra, create a project and import your ELF.
4. Check the selected language is the PS2 Emotion Engine/R5900 language provided by the extension.
5. Run analysis, inspect any errors, then use `Window > Script Manager` to run `ghidra_scripts/ExportJalCandidates.py` (add this folder to script search paths if needed).

Do not run scripts or executables from unknown re-upload sites. Keep your original ELF backed up and do not overwrite it with experiments.
