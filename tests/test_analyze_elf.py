import os
import struct
import tempfile
import unittest
from pathlib import Path
from tools.analyze_elf import parse_elf, sha256_stream


class TestAnalyzeElf(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.elf_path = Path(self.temp_dir.name) / "test.elf"

        # Create a mock valid ELF32 file
        header = bytearray(52)
        header[0:4] = b'\x7fELF'
        header[4] = 1 # 32-bit
        header[5] = 1 # little endian
        # etype=2 (EXEC), machine=8 (MIPS), version=1, entry=0x100000, phoff=52, shoff=84, flags=0x20924001, ehsize=52, phentsize=32, phnum=1, shentsize=40, shnum=2, shstrndx=1
        struct.pack_into('<HHIIIIIHHHHHH', header, 16, 2, 8, 1, 0x100000, 52, 84, 0x20924001, 52, 32, 1, 40, 2, 1)

        # Program header (PT_LOAD=1, p_off=0x1000, vaddr=0x100000, paddr=0x100000, filesz=0x100, memsz=0x100, p_flags=PF_X (1), align=0x1000)
        ph = struct.pack('<IIIIIIII', 1, 0x1000, 0x100000, 0x100000, 0x100, 0x100, 1, 0x1000)

        # Section headers
        # Section 0: NULL
        sh0 = struct.pack('<IIIIIIIIII', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        # Section 1: .shstrtab (type SHT_STRTAB=3)
        sh1 = struct.pack('<IIIIIIIIII', 1, 3, 0, 0, 0x200, 0x20, 0, 0, 1, 0)

        shstrtab = b'\x00.shstrtab\x00.text\x00'

        data = bytearray(0x1100)
        data[0:52] = header
        data[52:84] = ph
        data[84:124] = sh0
        data[124:164] = sh1
        data[0x200:0x200+len(shstrtab)] = shstrtab

        # Add JAL opcode instruction in executable area (JAL 0x100000 -> 0x0C040000)
        jal_word = struct.pack('<I', 0x0C040000)
        data[0x1000:0x1004] = jal_word

        with open(self.elf_path, 'wb') as f:
            f.write(data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_elf(self):
        with open(self.elf_path, 'rb') as f:
            data = f.read()
            info = parse_elf(data)
            self.assertEqual(info['elf_type'], 2)
            self.assertEqual(info['machine'], 8)
            self.assertEqual(info['entry'], 0x100000)
            self.assertEqual(len(info['program_headers']), 1)

    def test_sha256_stream(self):
        digest = sha256_stream(self.elf_path)
        self.assertEqual(len(digest), 64)


if __name__ == '__main__':
    unittest.main()
