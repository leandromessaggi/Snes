import unittest
from scripts.scan_control_xrefs import normalize, lorom_address, scan, report

class XrefTests(unittest.TestCase):
    def test_strip_header(self):
        image = bytes(0x10000)
        self.assertEqual(normalize(b"X"*512 + image), image)
        self.assertEqual(report(image)["references_found"], 0)
    def test_scan_and_bank_boundary(self):
        data = bytearray(0x18000)
        data[0x8010:0x8013] = bytes((0xAD,0xE6,0x20))
        data[0x8020:0x8023] = bytes((0x8D,0xE8,0x20))
        data[0x7FFE:0x8001] = bytes((0xAD,0xE8,0x20))
        refs = scan(bytes(data))
        self.assertEqual(len(refs), 2)
        self.assertEqual([r["access"] for r in refs], ["read","write"])
        self.assertEqual(refs[0]["lorom_candidate"], "$01:8010")
        self.assertEqual(lorom_address(0xFFFF), "$01:FFFF")
    def test_invalid(self):
        with self.assertRaises(ValueError):
            normalize(b"bad")
        with self.assertRaises(ValueError):
            lorom_address(-1)

if __name__ == "__main__":
    unittest.main()
