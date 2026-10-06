from __future__ import annotations

from datetime import datetime, timezone
import csv

from common import SNAPSHOT_DIR, load_titles
from fetch_steam_store import fetch_store_details
from fetch_steam_reviews import fetch_review_summary
from fetch_current_players import fetch_current_players
from fetch_market_benchmark import fetch_market_benchmark

OUTPUT = SNAPSHOT_DIR / "commercial-snapshot-history.csv"


def safe_fetch(label, fn, app_id):
    try:
        return fn(app_id)
    except Exception as exc:
        print(f"[WARN] {label} failed for {app_id}: {exc}")
        return {f"{label}_error": str(exc)}


def main():
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rows = []
    for title in load_titles():
        app_id = title["app_id"]
        print(f"Collecting {app_id} - {title['title']}")

        row = {
            "snapshot_timestamp_utc": timestamp,
            "cohort": title["cohort"],
            "app_id": app_id,
            "title": title["title"],
            "peer_group": title.get("peer_group", ""),
            "comparable_to": title.get("comparable_to", ""),
            "lifecycle_role": title.get("lifecycle_role", ""),
            "source_url": title.get("source_url", ""),
        }

        row.update(safe_fetch("steam_store", fetch_store_details, app_id))
        row.update(safe_fetch("steam_reviews", fetch_review_summary, app_id))
        row.update(safe_fetch("current_players", fetch_current_players, app_id))
        row.update(safe_fetch("market_benchmark", fetch_market_benchmark, app_id))
        rows.append(row)

    fieldnames = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    existing_header = None
    if OUTPUT.exists():
        with OUTPUT.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            existing_header = next(reader, None)

    if existing_header:
        for key in existing_header:
            if key not in seen:
                fieldnames.append(key)
        fieldnames = existing_header + [x for x in fieldnames if x not in existing_header]

    write_header = not OUTPUT.exists() or OUTPUT.stat().st_size == 0
    with OUTPUT.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
