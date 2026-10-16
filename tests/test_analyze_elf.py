import os
import struct
import tempfile
import unittest
from pathlib import Path
from tools.analyze_elf import parse_elf, main

class TestAnalyzeElf(unittest.TestCase):
    def test_parse_elf_and_scan(self):
        header = b'\x7fELF\x01\x01\x01' + b'\x00' * 9
        shstrtab = b'\x00.text\x00.shstrtab\x00'
        sh0 = struct.pack('<IIIIIIIIII', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        secsize = 16
        # .text section: executable, vaddr = 0x100000, offset = 0x1000
        sh1 = struct.pack('<IIIIIIIIII', 1, 1, 4, 0x100000, 0x1000, secsize, 0, 0, 4, 0)
        sh2 = struct.pack('<IIIIIIIIII', 7, 3, 0, 0, 0x1000 + secsize, len(shstrtab), 0, 0, 1, 0)
        shoff = 52 + 32
        ehdr = struct.pack('<16sHHIIIIIHHHHHH', header, 2, 8, 1, 0x100000, 52, shoff, 0x20924001, 52, 32, 1, 40, 3, 2)
        phdr = struct.pack('<IIIIIIII', 1, 0x1000, 0x100000, 0x100000, secsize, secsize, 5, 0x1000)

        with tempfile.TemporaryDirectory() as tmpdir:
            elf_path = Path(tmpdir) / "test.elf"
            out_dir = Path(tmpdir) / "reports"
            with open(elf_path, "wb") as f:
                f.write(ehdr)
                f.write(phdr)
                f.seek(shoff)
                f.write(sh0 + sh1 + sh2)
                f.seek(0x1000)
                # JAL instruction to 0x100004
                jal_target = 0x100004
                jal_word = (3 << 26) | ((jal_target & 0x0FFFFFFF) >> 2)
                nop_word = 0
                f.write(struct.pack('<IIII', jal_word, nop_word, jal_word, nop_word))
                f.seek(0x1000 + secsize)
                f.write(shstrtab)

            # Test parse_elf directly
            with open(elf_path, "rb") as f:
                data = f.read()
            info = parse_elf(data)
            self.assertEqual(info['entry'], 0x100000)
            self.assertEqual(len(info['sections']), 3)

            # Test main scanner
            sys_argv_backup = list(os.sys.argv)
            os.sys.argv = ["analyze_elf.py", str(elf_path), "--out", str(out_dir)]
            try:
                ret = main()
                self.assertEqual(ret, 0)
            finally:
                os.sys.argv = sys_argv_backup

            # Check exported report
            report_file = out_dir / "elf_report.json"
            self.assertTrue(report_file.exists())
            candidates_file = out_dir / "jal_candidates_001.csv"
            self.assertTrue(candidates_file.exists())
            with open(candidates_file, "r") as f:
                lines = f.readlines()
                # Header + 2 candidates
                self.assertEqual(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
