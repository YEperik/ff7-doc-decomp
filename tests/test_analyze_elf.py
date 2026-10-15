import csv
import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.analyze_elf import cstr, main, parse_elf


def create_mock_elf(text_words=None, jalr_words=None):
    """Creates a minimal valid ELF32 LE bytearray for testing."""
    if text_words is None:
        text_words = []

    # ehdr: ELF32, LE, ET_EXEC(2), MIPS(8), entry 0x00100000, phoff=52, shoff=84
    ehdr = struct.pack(
        "<16sHHIIIIIHHHHHH",
        b"\x7fELF\x01\x01\x01\x00" + b"\x00" * 8,
        2,
        8,
        1,
        0x00100000,
        52,
        84,
        0x20924001,
        52,
        32,
        1,
        40,
        3,
        1,
    )
    # Program header: PT_LOAD(1), offset 0, vaddr 0x00100000, paddr 0x00100000, filesz 2000, memsz 2000, PF_X(1)|PF_R(4)=5, align 16
    phdr = struct.pack("<IIIIIIII", 1, 0, 0x00100000, 0x00100000, 2000, 2000, 5, 16)
    # Section header 0: NULL
    sh0 = b"\x00" * 40
    # Section header 1: .shstrtab (type 3)
    names = b"\x00.shstrtab\x00.text\x00"
    sh1 = struct.pack("<IIIIIIIIII", 1, 3, 0, 0, 300, len(names), 0, 0, 1, 0)
    # Section header 2: .text (type 1 SHT_PROGBITS, flags 4 SHF_EXECINSTR, addr 0x00100000, offset 500)
    sec_size = len(text_words) * 4
    sh2 = struct.pack(
        "<IIIIIIIIII", 11, 1, 4, 0x00100000, 500, sec_size, 0, 0, 16, 0
    )

    buf = bytearray(1000 + sec_size)
    buf[0:52] = ehdr
    buf[52:84] = phdr
    buf[84:124] = sh0
    buf[124:164] = sh1
    buf[164:204] = sh2
    buf[300 : 300 + len(names)] = names

    for i, word in enumerate(text_words):
        buf[500 + i * 4 : 500 + (i + 1) * 4] = struct.pack("<I", word)

    return buf


class TestAnalyzeElf(unittest.TestCase):

    def test_cstr(self):
        buf = b"hello\x00world\x00"
        self.assertEqual(cstr(buf, 0), "hello")
        self.assertEqual(cstr(buf, 6), "world")
        self.assertEqual(cstr(buf, 100), "")

    def test_parse_elf_invalid(self):
        with self.assertRaises(ValueError):
            parse_elf(b"not an elf file")

        with self.assertRaises(ValueError):
            parse_elf(b"\x7fELF\x02\x01" + b"\x00" * 50)  # ELF64 not supported

    def test_parse_elf_valid(self):
        data = create_mock_elf([0x00000000])
        info = parse_elf(data)
        self.assertEqual(info["elf_type"], 2)
        self.assertEqual(info["machine"], 8)
        self.assertEqual(info["entry"], 0x00100000)
        self.assertEqual(len(info["sections"]), 3)
        self.assertEqual(info["sections"][2]["name"], ".text")

    def test_main_scanning(self):
        # 0x0C040004 => JAL to 0x00100010 (opcode 3)
        # 0x00000000 => NOP
        text_words = [0x0C040004, 0x00000000, 0x0C040005]
        data = create_mock_elf(text_words)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            elf_file = tmp_path / "test.elf"
            elf_file.write_bytes(data)

            out_dir = tmp_path / "reports"

            import sys
            old_argv = sys.argv
            try:
                sys.argv = ["analyze_elf.py", str(elf_file), "--out", str(out_dir)]
                exit_code = main()
                self.assertEqual(exit_code, 0)

                # Check json report
                report_path = out_dir / "elf_report.json"
                self.assertTrue(report_path.is_file())
                report = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(report["jal_and_optional_jalr_candidates_written"], 2)

                # Check candidate CSV
                csv_path = out_dir / "jal_candidates_001.csv"
                self.assertTrue(csv_path.is_file())
                with csv_path.open("r", encoding="utf-8") as f:
                    reader = list(csv.reader(f))
                    self.assertEqual(len(reader), 3)  # header + 2 rows
                    self.assertEqual(reader[1][0], ".text")
                    self.assertEqual(reader[1][1], "0x00100000")
                    self.assertEqual(reader[1][3], "JAL")
                    self.assertEqual(reader[1][4], "0x0C040004")
                    self.assertEqual(reader[1][5], "0x00100010")
            finally:
                sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
