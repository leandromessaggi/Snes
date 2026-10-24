import importlib.util
import unittest
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("elf_check", ROOT / "scripts" / "check_elf_16k.py")
elf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(elf)

class PipelineTests(unittest.TestCase):
    def test_invalid_elf_rejected(self):
        self.assertTrue(elf.validate_arm64_elf(b"anything"))


    def test_apk_missing_cpp_runtime_fails(self):
        with tempfile.NamedTemporaryFile(suffix=".apk") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as archive:
                archive.writestr("lib/arm64-v8a/libdesert_bridge.so", b"ELF mock")
                archive.writestr("lib/arm64-v8a/libsnes9x_libretro.so", b"ELF mock")
            errors = elf.check(Path(tmp.name))
            self.assertTrue(any("libc++_shared.so" in line and "missing" in line for line in errors))

    def test_empty_file_raises_message(self):
        self.assertIn("ELF64", elf.validate_arm64_elf(b"")[0])

if __name__ == "__main__":
    unittest.main()
