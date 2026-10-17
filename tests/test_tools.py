import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure repository root is on sys.path for test runners like pytest
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.analyze_elf import main as analyze_elf_main
from tools.hash_file import main as hash_file_main
from tools.summarize_ghidra_export import main as summarize_ghidra_main


def create_dummy_elf(
    path: Path,
    entry: int = 0x00100000,
    text_words: list[int] = None,
    include_invalid: bool = False,
):
    """Creates a small valid ELF32 little-endian MIPS executable for testing."""
    if text_words is None:
        text_words = [0x00000000] * 16  # 16 NOPs

    phoff = 52
    phentsize = 32
    phnum = 1
    shoff = phoff + phentsize * phnum
    shentsize = 40
    shnum = 3
    shstrndx = 2

    shstrtab = b"\x00.text\x00.shstrtab\x00"
    shstrtab_off = shoff + shentsize * shnum
    text_off = shstrtab_off + len(shstrtab)
    text_bytes = struct.pack(f"<{len(text_words)}I", *text_words)
    text_size = len(text_bytes)

    if include_invalid:
        path.write_bytes(b"\x7fELF\x01\x01\x010000000000")
        return

    ehdr = struct.pack(
        "<16sHHIIIIIHHHHHH",
        b"\x7fELF\x01\x01\x01" + b"\x00" * 9,
        2,  # ET_EXEC
        8,  # MIPS
        1,  # EV_CURRENT
        entry,
        phoff,
        shoff,
        0x20924001,  # e_flags
        52,
        phentsize,
        phnum,
        shentsize,
        shnum,
        shstrndx,
    )

    phdr = struct.pack(
        "<IIIIIIII",
        1,  # PT_LOAD
        text_off,
        entry,  # vaddr
        entry,  # paddr
        text_size,
        text_size,
        5,  # PF_R | PF_X
        0x1000,
    )

    sh0 = b"\x00" * 40
    sh1 = struct.pack(
        "<IIIIIIIIII",
        1,  # offset into shstrtab for ".text"
        1,  # SHT_PROGBITS
        6,  # SHF_ALLOC | SHF_EXECINSTR
        entry,
        text_off,
        text_size,
        0,
        0,
        16,
        0,
    )
    sh2 = struct.pack(
        "<IIIIIIIIII",
        7,  # offset into shstrtab for ".shstrtab"
        3,  # SHT_STRTAB
        0,
        0,
        shstrtab_off,
        len(shstrtab),
        0,
        0,
        1,
        0,
    )

    with path.open("wb") as f:
        f.write(ehdr)
        f.write(phdr)
        f.write(sh0 + sh1 + sh2)
        f.write(shstrtab)
        f.write(text_bytes)


class TestAnalyzeElf(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_analyze_elf_jal_candidates(self):
        elf_path = self.dir_path / "test.elf"
        out_dir = self.dir_path / "reports"
        # 0x0C040000 is JAL 0x00100000 (target inside executable load segment)
        # 0x0C000000 is JAL 0x00000000 (target outside load segment)
        words = [
            0x00000000,  # NOP
            0x0C040000,  # JAL 0x00100000
            0x00000000,  # NOP
            0x0C000000,  # JAL 0x00000000
        ]
        create_dummy_elf(elf_path, text_words=words)

        with patch("sys.argv", ["analyze_elf.py", str(elf_path), "--out", str(out_dir)]):
            ret = analyze_elf_main()
            self.assertEqual(ret, 0)

        report_file = out_dir / "elf_report.json"
        self.assertTrue(report_file.exists())
        data = json.loads(report_file.read_text(encoding="utf-8"))
        self.assertEqual(data["jal_and_optional_jalr_candidates_written"], 2)
        self.assertEqual(data["jal_targets_outside_executable_load_segments"], 1)

        csv_file = out_dir / "jal_candidates_001.csv"
        self.assertTrue(csv_file.exists())
        csv_content = csv_file.read_text(encoding="utf-8")
        self.assertIn("JAL", csv_content)
        self.assertIn("0x00100000", csv_content)

    def test_analyze_elf_include_jalr(self):
        elf_path = self.dir_path / "test.elf"
        out_dir = self.dir_path / "reports"
        # 0x03E0F809 is JALR $ra, $ra (opcode=0, rs=31, rd=31, sa=0, funct=9)
        words = [0x00000000, 0x03E0F809]
        create_dummy_elf(elf_path, text_words=words)

        with patch("sys.argv", ["analyze_elf.py", str(elf_path), "--out", str(out_dir), "--include-jalr"]):
            ret = analyze_elf_main()
            self.assertEqual(ret, 0)

        report_file = out_dir / "elf_report.json"
        data = json.loads(report_file.read_text(encoding="utf-8"))
        self.assertEqual(data["jal_and_optional_jalr_candidates_written"], 1)

        csv_file = out_dir / "jal_candidates_001.csv"
        self.assertIn("JALR", csv_file.read_text(encoding="utf-8"))

    def test_analyze_elf_chunk_splitting(self):
        elf_path = self.dir_path / "test.elf"
        out_dir = self.dir_path / "reports"
        words = [0x0C040000] * 5  # 5 JAL instructions
        create_dummy_elf(elf_path, text_words=words)

        with patch("sys.argv", ["analyze_elf.py", str(elf_path), "--out", str(out_dir), "--chunk-rows", "2"]):
            ret = analyze_elf_main()
            self.assertEqual(ret, 0)

        self.assertTrue((out_dir / "jal_candidates_001.csv").exists())
        self.assertTrue((out_dir / "jal_candidates_002.csv").exists())
        self.assertTrue((out_dir / "jal_candidates_003.csv").exists())

    def test_analyze_elf_max_candidates(self):
        elf_path = self.dir_path / "test.elf"
        out_dir = self.dir_path / "reports"
        words = [0x0C040000] * 10
        create_dummy_elf(elf_path, text_words=words)

        with patch("sys.argv", ["analyze_elf.py", str(elf_path), "--out", str(out_dir), "--max-candidates", "3"]):
            ret = analyze_elf_main()
            self.assertEqual(ret, 0)

        report_file = out_dir / "elf_report.json"
        data = json.loads(report_file.read_text(encoding="utf-8"))
        self.assertEqual(data["jal_and_optional_jalr_candidates_written"], 3)


class TestHashFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_hash_file(self):
        file_path = self.dir_path / "sample.bin"
        file_path.write_bytes(b"hello world\n")

        with patch("sys.argv", ["hash_file.py", str(file_path)]), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            hash_file_main()
            output = mock_stdout.getvalue()
            self.assertIn("SHA256:", output)


class TestSummarizeGhidraExport(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_summarize_ghidra_export(self):
        csv_path = self.dir_path / "jal_triage_001.csv"
        csv_content = (
            '"address","mnemonic","function","source_block","flow_targets","target_executable"\n'
            '"0x00100000","JAL","main",".text","0x00100020","true"\n'
            '"0x00100004","JAL","<no function>",".text","<no resolved flow target>","false"\n'
        )
        csv_path.write_text(csv_content, encoding="utf-8")

        summary_json = self.dir_path / "summary.json"
        review_csv = self.dir_path / "review.csv"

        with patch(
            "sys.argv",
            [
                "summarize_ghidra_export.py",
                str(csv_path),
                "--out",
                str(summary_json),
                "--review-out",
                str(review_csv),
            ],
        ):
            ret = summarize_ghidra_main()
            self.assertEqual(ret, 0)

        self.assertTrue(summary_json.exists())
        self.assertTrue(review_csv.exists())
        summary_data = json.loads(summary_json.read_text(encoding="utf-8"))
        self.assertEqual(summary_data["rows_processed"], 2)


if __name__ == "__main__":
    unittest.main()
