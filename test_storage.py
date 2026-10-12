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


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "data" / "results.json"
        env = patch.dict(os.environ, {"RESULTS_PATH": str(self.path)})
        env.start()
        self.addCleanup(env.stop)

    def test_missing_file_and_persistence_through_both_apps(self):
        self.assertEqual(storage.load_results(), [])
        result = {"file": "deck.pdf", "team": "Alpha", "criteria": {}}
        storage.store_result(result)
        self.assertEqual(judge.load_results(), [result])
        response = app.app.test_client().get("/api/results").json
        self.assertEqual(response[0]["file"], result["file"])
        self.assertEqual(response[0]["team"], result["team"])
        self.assertEqual(json.loads(self.path.read_text()), [result])

    def test_same_filename_is_replaced(self):
        storage.store_result({"file": "one.pdf", "score": 1})
        storage.store_result({"file": "two.pptx", "score": 2})
        storage.store_result({"file": "one.pdf", "score": 5})
        results = storage.load_results()
        self.assertEqual(len(results), 2)
        self.assertEqual(next(r["score"] for r in results if r["file"] == "one.pdf"), 5)

    def test_judge_text_route_writes_to_configured_volume_path(self):
        criteria = {key: {"score": 3, "confidence": 0.9} for key in judge.CRITERIA_ORDER}
        with patch.object(app, "score_deck", return_value=criteria):
            response = app.app.test_client().post("/api/judge-text", data={
                "text": "Evidence", "team": "Alpha", "filename": "alpha.pdf"})
        self.assertEqual(response.status_code, 200)
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved[0]["team"], "Alpha")
        self.assertEqual(saved[0]["weighted_score"], 24)

    def test_invalid_existing_json_is_not_overwritten(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("broken JSON")
        with self.assertRaises(json.JSONDecodeError):
            storage.store_result({"file": "new.pdf"})
        self.assertEqual(self.path.read_text(), "broken JSON")

    def test_simultaneous_updates_do_not_lose_results(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(storage.store_result, [{"file": f"deck-{i}.pdf"} for i in range(40)]))
        self.assertEqual(len(storage.load_results()), 40)
        self.assertEqual(list(self.path.parent.glob(".results-*.json")), [])

    def test_failed_write_keeps_existing_results(self):
        storage.store_result({"file": "original.pdf"})
        before = self.path.read_bytes()
        with patch.object(storage.os, "replace", side_effect=OSError("write failed")):
            with self.assertRaises(OSError):
                storage.store_result({"file": "new.pdf"})
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob(".results-*.json")), [])

    def test_local_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(storage.results_path(), Path("results.json"))

    def test_railway_mount_used_without_docker_configuration(self):
        with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT_ID": "production",
                "RAILWAY_VOLUME_MOUNT_PATH": self.directory.name}, clear=True):
            self.assertEqual(storage.results_path(), Path(self.directory.name).resolve() / "results.json")
            storage.store_result({"file": "persistent.pdf"})
            self.assertEqual(storage.load_results(), [{"file": "persistent.pdf"}])

    def test_railway_refuses_missing_volume_or_path_outside_volume(self):
        with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT_ID": "production"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "No Railway volume"):
                storage.store_result({"file": "deck.pdf"})
        with patch.dict(os.environ, {"RAILWAY_VOLUME_MOUNT_PATH": "/data",
                "RESULTS_PATH": "/app/results.json"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "inside the attached Railway volume"):
                storage.results_path()


if __name__ == "__main__":
    unittest.main()
