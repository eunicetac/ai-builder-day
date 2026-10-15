import copy
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import app
import judge
import storage


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "results.json"
        environment = patch.dict(os.environ, {"RESULTS_PATH": str(self.path),
            "CONFIDENCE_LOW_THRESHOLD": "0.50", "CONFIDENCE_HIGH_THRESHOLD": "0.80"})
        environment.start()
        self.addCleanup(environment.stop)
        self.client = app.app.test_client()
        self.original = {"file": "deck.pdf", "team": "Alpha", "judged_at": "2026-10-12T00:00:00Z",
            "raw_total": 12, "weighted_score": 24, "assessed_text": "Page 1: evidence <example>",
            "criteria": {k: {"score": 3, "raw": 2.0, "confidence": confidence,
                "distribution": [0, 0, 1, 0, 0]} for k, confidence in zip(judge.CRITERIA_ORDER, [.4, .6, .9, None])}}
        storage.store_result(copy.deepcopy(self.original))

    def current(self):
        response = self.client.get("/api/results/detail?file=deck.pdf")
        self.assertEqual(response.status_code, 200)
        return response.json["result"]

    def body(self, **changes):
        result = self.current()
        body = {"file": "deck.pdf", "judged_at": result["judged_at"], "revision": result["review_revision"],
                "reviewer": "Judge A", "criterion": "problem_and_user", "action": "confirm"}
        body.update(changes)
        return body

    def test_override_retains_ai_and_recalculates_score(self):
        response = self.client.post("/api/results/review", json=self.body(action="override", score=5,
            rationale="Clear problem and consequences", evidence_refs="PDF page 1"))
        self.assertEqual(response.status_code, 200)
        result = response.json
        criterion = result["criteria"]["problem_and_user"]
        self.assertEqual(criterion["score"], 3)
        self.assertEqual(criterion["raw"], 2.0)
        self.assertEqual(criterion["distribution"], [0, 0, 1, 0, 0])
        self.assertEqual(criterion["effective_score"], 5)
        self.assertEqual(criterion["human_review"]["reviewer"], "Judge A")
        self.assertEqual(result["weighted_score"], 24)
        self.assertEqual(result["effective_weighted_score"], 28)
        self.assertEqual(len(result["review_history"]), 1)

    def test_validation_does_not_write_invalid_reviews(self):
        before = self.path.read_bytes()
        for changes in [{"reviewer": ""}, {"action": "override", "score": 6},
                        {"action": "override", "score": True}, {"action": "override", "score": 4.5},
                        {"action": "override", "score": 4, "rationale": "reason"},
                        {"criterion": "unknown"}]:
            response = self.client.post("/api/results/review", json=self.body(**changes))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.path.read_bytes(), before)

    def test_finalize_requires_low_and_unavailable_reviews(self):
        self.assertEqual(self.client.post("/api/results/finalize", json=self.body()).status_code, 400)
        for key in ("problem_and_user", "test_and_learn"):
            self.assertEqual(self.client.post("/api/results/review", json=self.body(criterion=key)).status_code, 200)
        response = self.client.post("/api/results/finalize", json=self.body())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["submission_status"], "finalized")
        self.assertIn("problem_understanding", response.json["pending_review"])
        response = self.client.post("/api/results/review", json=self.body(action="reset"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("finalization", response.json)
        self.assertIn("problem_and_user", response.json["required_review"])

    def test_conflicts_and_concurrent_edits(self):
        body = self.body()
        def post(_):
            with app.app.test_client() as client:
                return client.post("/api/results/review", json=body).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(post, range(2)))
        self.assertEqual(sorted(codes), [200, 409])
        self.assertEqual(len(self.current()["review_history"]), 1)

    def test_rejudging_archives_reviews_and_rejects_old_version(self):
        self.client.post("/api/results/review", json=self.body(action="override", score=5,
            rationale="Excellent", evidence_refs="Page 1"))
        stale_body = self.body()
        new = copy.deepcopy(self.original)
        new["judged_at"] = "2026-10-12T01:00:00Z"
        storage.store_result(new)
        result = self.current()
        self.assertNotIn("human_review", result["criteria"]["problem_and_user"])
        self.assertEqual(result["effective_weighted_score"], 24)
        self.assertEqual(result["review_history"][-1]["action"], "rejudged")
        previous = result["review_history"][-1]["previous_result"]
        self.assertEqual(previous["criteria"]["problem_and_user"]["human_review"]["score"], 5)
        self.assertEqual(self.client.post("/api/results/review", json=stale_body).status_code, 409)

    def test_detail_contains_evidence_and_rubric_but_list_omits_large_fields(self):
        detail = self.client.get("/api/results/detail?file=deck.pdf").json
        self.assertEqual(detail["result"]["assessed_text"], self.original["assessed_text"])
        self.assertEqual(len(detail["anchors"]["outcomes"]), 5)
        result = self.client.get("/api/results").json[0]
        self.assertNotIn("assessed_text", result)
        self.assertNotIn("review_history", result)
        self.assertEqual(self.client.get("/api/results/detail?file=missing.pdf").status_code, 404)

    def test_delete_removes_selected_result_and_preserves_other_submissions(self):
        other = copy.deepcopy(self.original)
        other["file"] = "other.pdf"
        storage.store_result(other)
        self.client.post("/api/results/review", json=self.body())
        response = self.client.post("/api/results/delete", json=self.body())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"deleted": "deck.pdf"})
        self.assertEqual(storage.load_results(), [other])
        self.assertEqual(self.client.get("/api/results/detail?file=deck.pdf").status_code, 404)

    def test_delete_last_result_returns_empty_list_and_allows_rejudging(self):
        response = self.client.post("/api/results/delete", json=self.body())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/results").json, [])
        self.assertEqual(json.loads(self.path.read_text()), [])
        storage.store_result(copy.deepcopy(self.original))
        self.assertEqual(len(self.client.get("/api/results").json), 1)

    def test_stale_delete_cannot_remove_updated_or_rejudged_result(self):
        stale = self.body()
        self.client.post("/api/results/review", json=self.body())
        self.assertEqual(self.client.post("/api/results/delete", json=stale).status_code, 409)
        stale = self.body()
        new = copy.deepcopy(self.original)
        new["judged_at"] = "2026-10-15T00:00:00Z"
        storage.store_result(new)
        self.assertEqual(self.client.post("/api/results/delete", json=stale).status_code, 409)
        self.assertEqual(len(storage.load_results()), 1)

    def test_delete_validation_and_failed_storage_write(self):
        self.assertEqual(self.client.post("/api/results/delete", json={}).status_code, 400)
        self.assertEqual(self.client.post("/api/results/delete", json=self.body(file="missing.pdf")).status_code, 404)
        before = self.path.read_bytes()
        body = self.body()
        with patch.object(storage.os, "replace", side_effect=OSError("write failed")):
            response = self.client.post("/api/results/delete", json=body)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
