"""Shared result storage on the Railway volume or the local filesystem."""

import fcntl
import json
import os
import tempfile
from pathlib import Path


def results_path() -> Path:
    return Path(os.environ.get("RESULTS_PATH", "results.json"))


def load_results() -> list:
    path = results_path()
    if not path.exists():
        return []
    with path.open() as stream:
        return json.load(stream)


def store_result(result: dict) -> list:
    """Lock the entire read/update/write cycle and atomically replace the file."""
    path = results_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(path.name + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            results = load_results()
            results = [entry for entry in results if entry.get("file") != result["file"]]
            results.append(result)
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
