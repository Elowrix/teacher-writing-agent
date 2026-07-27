from __future__ import annotations

import unittest

from epe_report_tool.analytics import (
    decision_threshold,
    normalize_result,
    normalize_scholarship,
    score_band,
    threshold_group,
    wilson_interval,
)


class AnalyticsRuleTests(unittest.TestCase):
    def test_result_normalization(self) -> None:
        self.assertEqual(normalize_result("PASS"), "PASS")
        self.assertEqual(normalize_result("Fail"), "FAIL")
        self.assertEqual(normalize_result("ABSENT"), "ABSENT")

    def test_threshold_group(self) -> None:
        self.assertEqual(threshold_group("English Language Teaching"), "ELL–ELT")
        self.assertEqual(threshold_group("Computer Engineering"), "Other undergraduate")
        self.assertEqual(decision_threshold("ELL–ELT"), 74.50)
        self.assertEqual(decision_threshold("Other undergraduate"), 64.50)

    def test_bands(self) -> None:
        self.assertEqual(score_band(-4.99, "FAIL"), "FAIL 0–5")
        self.assertEqual(score_band(-5.01, "FAIL"), "FAIL 5–10")
        self.assertEqual(score_band(0.00, "PASS"), "PASS 0–5")
        self.assertEqual(score_band(5.00, "PASS"), "PASS 5–10")

    def test_scholarship(self) -> None:
        self.assertEqual(normalize_scholarship("%50"), 50.0)
        self.assertEqual(normalize_scholarship(0.25), 25.0)
        self.assertEqual(normalize_scholarship("BURSSUZ"), 0.0)

    def test_wilson(self) -> None:
        lower, upper = wilson_interval(50, 100)
        self.assertIsNotNone(lower)
        self.assertIsNotNone(upper)
        self.assertLess(lower, 0.5)
        self.assertGreater(upper, 0.5)


if __name__ == "__main__":
    unittest.main()
