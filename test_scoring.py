import unittest
from types import SimpleNamespace
from unittest.mock import patch

import judge


class ScoringTests(unittest.TestCase):
    def score(self, raw, probabilities, confidence=0.8):
        answer = SimpleNamespace(score=raw, probabilities=probabilities, confidence=confidence)
        response = SimpleNamespace(answers={key: answer for key in judge.CRITERIA_ORDER})
        with patch.dict(judge.os.environ, {"TYPESAFE_API_KEY": "test-key", "CONFIDENCE_LOW_THRESHOLD": "0.50", "CONFIDENCE_HIGH_THRESHOLD": "0.80"}), \
                patch.object(judge, "TypeSafeClient") as client:
            client.return_value.__enter__.return_value.system_one.return_value = response
            return judge.score_deck("deck evidence")

    def test_all_api_levels_map_to_one_based_rubric_and_totals(self):
        for api_level in range(5):
            with self.subTest(api_level=api_level):
                criteria = self.score(api_level, {str(api_level): 1.0})
                for criterion in criteria.values():
                    self.assertEqual(criterion["score"], api_level + 1)
                    self.assertEqual(criterion["raw"], api_level)
                    self.assertEqual(len(criterion["distribution"]), 5)
                    self.assertEqual(criterion["distribution"][api_level], 1.0)
                    self.assertFalse(criterion["borderline"])
                result = judge.build_result("Team", "deck.pdf", criteria)
                self.assertEqual(result["raw_total"], 4 * (api_level + 1))
                self.assertEqual(result["weighted_score"], 8 * (api_level + 1))

    def test_fractional_score_conversion_keeps_distribution_and_confidence(self):
        probabilities = {"4": 0.05, "2": 0.20, "0": 0.0, "3": 0.75, "1": 0.0}
        c = self.score(2.85, probabilities)["outcomes"]
        self.assertEqual(c["score"], 4)
        self.assertEqual(c["distribution"], [0.0, 0.0, 0.20, 0.75, 0.05])
        self.assertEqual(c["confidence"], 0.8)

    def test_borderline_and_integer_probability_keys(self):
        c = self.score(2.4, {2: 0.6, 3: 0.4})["outcomes"]
        self.assertEqual(c["score"], 3)
        self.assertFalse(c["borderline"])
        self.assertEqual(c["distribution"], [0, 0, 0.6, 0.4, 0])

    def test_flag_uses_confidence_not_fractional_score(self):
        for confidence, expected in [(0.49, True), (0.50, True), (0.79, True), (0.80, False), (0.95, False), (None, False)]:
            for raw in (2.0, 2.4):
                with self.subTest(confidence=confidence, raw=raw):
                    c = self.score(raw, {2: 0.6, 3: 0.4}, confidence)["outcomes"]
                    self.assertEqual(c["borderline"], expected)

    def test_saved_flags_refresh_without_changing_scores(self):
        results = [{"raw_total": 8, "criteria": {
            "outcomes": {"score": 2, "raw": 1.4, "confidence": 0.9, "borderline": True},
            "test_and_learn": {"score": 2, "raw": 1.0, "confidence": 0.6, "borderline": False},
        }}]
        with patch.dict(judge.os.environ, {"CONFIDENCE_LOW_THRESHOLD": "0.50", "CONFIDENCE_HIGH_THRESHOLD": "0.80"}):
            judge.refresh_confidence_flags(results)
        self.assertFalse(results[0]["criteria"]["outcomes"]["borderline"])
        self.assertTrue(results[0]["criteria"]["test_and_learn"]["borderline"])
        self.assertEqual(results[0]["raw_total"], 8)
        self.assertEqual(results[0]["criteria"]["outcomes"]["score"], 2)
        with patch.dict(judge.os.environ, {"CONFIDENCE_LOW_THRESHOLD": "0.30", "CONFIDENCE_HIGH_THRESHOLD": "0.50"}):
            judge.refresh_confidence_flags(results)
        self.assertFalse(results[0]["criteria"]["test_and_learn"]["borderline"])

    def test_bands_and_threshold_boundaries(self):
        with patch.dict(judge.os.environ, {"CONFIDENCE_LOW_THRESHOLD": "0.50", "CONFIDENCE_HIGH_THRESHOLD": "0.80"}):
            for confidence, expected in [(0, "low"), (0.499, "low"), (0.50, "medium"),
                                         (0.799, "medium"), (0.80, "high"), (1, "high"),
                                         (None, "unavailable"), (float("nan"), "unavailable")]:
                self.assertEqual(judge.confidence_band(confidence), expected)

    def test_threshold_rejects_invalid_values(self):
        for low, high in [("-0.1", "0.8"), ("0.5", "1.1"), ("nan", "0.8"),
                          ("bad", "0.8"), ("0.8", "0.5"), ("0.5", "0.5")]:
            with patch.dict(judge.os.environ, {"CONFIDENCE_LOW_THRESHOLD": low, "CONFIDENCE_HIGH_THRESHOLD": high}):
                with self.assertRaises(ValueError):
                    judge.confidence_thresholds()


if __name__ == "__main__":
    unittest.main()
