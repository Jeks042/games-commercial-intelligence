"""Validated acquisition, immutable run evidence and atomic publication."""

import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4
import requests

_lock = threading.Lock()
_last_request = {}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def new_run_id(prefix):
    return (
        prefix
        + "-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        + "-"
        + uuid4().hex[:8]
    )


def get_json(url, params):
    """Three attempts maximum; space each host's requests by 1.1 seconds."""
    host = urlparse(url).netloc
    for attempt in range(3):
        with _lock:
            delay = 1.1 - (time.monotonic() - _last_request.get(host, 0))
            if delay > 0:
                time.sleep(delay)
            _last_request[host] = time.monotonic()
        try:
            response = requests.get(
                url,
                params=params,
                timeout=(10, 30),
                headers={"User-Agent": "games-commercial-intelligence/2.0"},
            )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 2:
                    wait = response.headers.get("Retry-After", "")
                    time.sleep(
                        min(30, float(wait)) if wait.isdigit() else 2 ** (attempt + 1)
                    )
                    continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")
            return payload
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("Request retry budget exhausted")


def nonnegative_int(value, name, allow_string=False):
    if allow_string and isinstance(value, str) and value.isdigit():
        value = int(value)
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if not fields or len(fields) != len(set(fields)):
            raise ValueError(f"Invalid CSV header: {path}")
        rows = list(reader)
        if any(
            None in row or any(value is None for value in row.values()) for row in rows
        ):
            raise ValueError(f"CSV row width differs from header: {path}")
        return fields, rows


def atomic_csv(path, fields, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        read_csv(temporary)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_history(path, fields, rows):
    """Rewrite header and rows together. Failed validation leaves history untouched."""
    previous = []
    if Path(path).exists():
        existing_fields, previous = read_csv(path)
        if set(existing_fields) - set(fields):
            raise ValueError(
                "History contains unknown columns; explicit migration required"
            )
        for row in previous:
            if not row.get("run_id"):
                row["run_id"] = "legacy-" + row["snapshot_timestamp_utc"]
                row["schema_version"] = "legacy-1"
    keys = [(r["run_id"], r["app_id"]) for r in previous + rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate run_id/app_id; history was not changed")
    atomic_csv(path, fields, previous + rows)


def save_run(root, run_id, fields, rows, sources, started, titles):
    run_dir = Path(root) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    output = run_dir / "observations.csv"
    atomic_csv(output, fields, rows)
    coverage = {
        source: sum(row.get(source + "_status") == "ok" for row in rows)
        for source in sources
    }
    expected_ids = {title["app_id"] for title in titles}
    passed = (
        len(rows) == len(titles) == len(expected_ids)
        and {row["app_id"] for row in rows} == expected_ids
        and all(n == len(titles) for n in coverage.values())
    )
    try:
        repo = Path(__file__).resolve().parents[1]
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=repo,
                text=True,
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = "unknown", True
    manifest = {
        "run_id": run_id,
        "schema_version": 2,
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "status": "passed" if passed else "failed",
        "expected_titles": len(titles),
        "collected_titles": len(rows),
        "coverage": coverage,
        "failures": [
            {
                "app_id": row["app_id"],
                "source": source,
                "error": row.get(source + "_error"),
            }
            for row in rows
            for source in sources
            if row.get(source + "_status") != "ok"
        ],
        "title_universe_sha256": hashlib.sha256(
            json.dumps(titles, sort_keys=True).encode()
        ).hexdigest(),
        "observations_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "collector_revision": revision,
        "working_tree_modified": dirty,
        "collector_source_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((Path(__file__).parent).glob("*.py"))
        },
        "python_version": platform.python_version(),
        "requests_version": requests.__version__,
        "time_contract": "Retrieval timestamps, not source event/update timestamps",
    }
    manifest["source_contracts"] = {
        "steam_store": {
            "endpoint": "https://store.steampowered.com/api/appdetails",
            "country": "gb",
            "currency": "GBP",
            "language": "english",
        },
        "steam_reviews": {
            "endpoint": "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/",
            "query_version": "steam-service-v1-all-languages-all-purchases-offtopic-filtered",
            "languages": ["all"],
            "purchase_type": 1,
            "review_type": 0,
            "filter_offtopic_activity": True,
        },
        "current_players": {
            "endpoint": "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/",
            "measure": "point-in-time concurrency",
        },
        "steamspy": {
            "endpoint": "https://steamspy.com/api.php",
            "request": "appdetails",
            "evidence_class": "third-party benchmark",
            "owner_estimate_status": "requires_review",
        },
    }
    manifest["source_contracts"] = {
        source: manifest["source_contracts"][source] for source in sources
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"run_id": run_id, "status": manifest["status"], "coverage": coverage}
        ),
        flush=True,
    )
    return passed
