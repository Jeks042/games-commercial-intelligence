from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import csv
import time

from common import DATA_DIR, load_titles
from fetch_market_benchmark import fetch_market_benchmark

OUTPUT_DIR = DATA_DIR / "benchmarks"
OUTPUT = OUTPUT_DIR / "steamspy-market-benchmark.csv"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []

    for index, title in enumerate(load_titles(), start=1):
        app_id = title["app_id"]
        print(f"Benchmark {index}: {app_id} - {title['title']}")

        row = {
            "benchmark_timestamp_utc": timestamp,
            "cohort": title["cohort"],
            "app_id": app_id,
            "title": title["title"],
            "peer_group": title.get("peer_group", ""),
            "lifecycle_role": title.get("lifecycle_role", ""),
        }

        try:
            row.update(fetch_market_benchmark(app_id))
        except Exception as exc:
            row["steamspy_error"] = str(exc)
            print(f"[WARN] SteamSpy failed for {app_id}: {exc}")

        rows.append(row)
        time.sleep(1.1)

    fieldnames = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} benchmark rows to {OUTPUT}")


if __name__ == "__main__":
    main()
