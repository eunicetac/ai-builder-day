"""Shared result storage on the Railway volume or the local filesystem."""

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def results_path() -> Path:
    configured = os.environ.get("RESULTS_PATH")
    mount = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    if mount:
        volume_path = Path(mount).resolve()
        path = Path(configured).resolve() if configured else volume_path / "results.json"
        if not path.is_relative_to(volume_path):
            raise RuntimeError("RESULTS_PATH must be inside the attached Railway volume")
        return path
    if os.environ.get("RAILWAY_ENVIRONMENT_ID"):
        raise RuntimeError("No Railway volume is attached. Apply the volume changes and redeploy.")
    return Path(configured or "results.json")


def load_results() -> list:
    path = results_path()
    if not path.exists():
        return []
    with path.open() as stream:
        return json.load(stream)


def store_result(result: dict) -> list:
    def update(results):
        previous = next((r for r in results if r.get("file") == result["file"]), None)
        if previous and (previous.get("review_history") or previous.get("finalization")):
            result["review_history"] = list(previous.get("review_history", [])) + [{
                "action": "rejudged", "at": datetime.now(timezone.utc).isoformat(),
                "previous_result": {k: v for k, v in previous.items() if k != "review_history"},
            }]
        return [r for r in results if r.get("file") != result["file"]] + [result]
    return mutate_results(update)


def update_result(filename: str, update) -> dict:
    changed = []
    def apply(results):
        for index, result in enumerate(results):
            if result.get("file") == filename:
                changed.append(update(result))
                results[index] = changed[0]
                return results
        raise KeyError("Submission not found")
    mutate_results(apply)
    return changed[0]


def mutate_results(update) -> list:
    """Lock the entire read/update/write cycle and atomically replace the file."""
    path = results_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(path.name + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            results = load_results()
            results = update(results)
            temporary_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", dir=path.parent, prefix=".results-", suffix=".json", delete=False
                ) as stream:
                    temporary_path = Path(stream.name)
                    json.dump(results, stream, indent=2)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary_path, path)
            finally:
                if temporary_path is not None and temporary_path.exists():
                    temporary_path.unlink()
            return results
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
