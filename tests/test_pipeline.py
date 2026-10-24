import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("elf_check", ROOT / "scripts" / "check_elf_16k.py")
elf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(elf)

class PipelineTests(unittest.TestCase):
    def test_invalid_elf_rejected(self):
        self.assertTrue(elf.validate_arm64_elf(b"anything"))

    def test_empty_file_raises_message(self):
        self.assertIn("ELF64", elf.validate_arm64_elf(b"")[0])

if __name__ == "__main__":
    unittest.main()
