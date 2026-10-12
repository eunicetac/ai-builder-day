import unittest
from types import SimpleNamespace
from unittest.mock import patch

import judge


class ScoringTests(unittest.TestCase):
    def score(self, raw, probabilities):
        answer = SimpleNamespace(score=raw, probabilities=probabilities, confidence=0.8)
        response = SimpleNamespace(answers={key: answer for key in judge.CRITERIA_ORDER})
        with patch.dict(judge.os.environ, {"TYPESAFE_API_KEY": "test-key"}), \
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
        self.assertTrue(c["borderline"])
        self.assertEqual(c["distribution"], [0, 0, 0.6, 0.4, 0])


if __name__ == "__main__":
    unittest.main()
