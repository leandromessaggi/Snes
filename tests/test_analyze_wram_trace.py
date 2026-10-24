import unittest
from scripts.analyze_wram_trace import summarize


class WramTraceReportTests(unittest.TestCase):
    def test_v2_ranks_offset_outside_preview(self):
        report = summarize({
            "schema": "desert-wram-diff-v2",
            "frames": [{"changed_total": 49, "changes": [[i, 0, 1] for i in range(32)]}],
            "rankings": [{"button": 6, "frames_on": 10, "frames_off": 10,
                          "top": [[200, 10, 0, 100], [15, 10, 10, 0]]}],
        }, 6)
        self.assertEqual(report["not_in_preview"], 17)
        self.assertEqual(report["candidates"][0]["ram_offset_hex"], "0x000C8")
        self.assertEqual(report["candidates"][0]["rate_difference"], 1.0)

    def test_legacy_warns(self):
        result = summarize({"schema": "desert-wram-diff-v1", "frames": []})
        self.assertIn("Legacy", result["warning"])

    def test_empty_comparison_warns(self):
        result = summarize({"schema": "desert-wram-diff-v2", "frames": [],
                            "rankings": [{"button": 6, "frames_on": 0,
                                          "frames_off": 0, "top": []}]})
        self.assertIn("two frames", result["warning"])

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            summarize({"schema": "unknown", "frames": []})


if __name__ == "__main__":
    unittest.main()
