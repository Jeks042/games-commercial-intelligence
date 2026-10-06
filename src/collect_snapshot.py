from concurrent.futures import ThreadPoolExecutor
import requests
from acquisition import append_history, new_run_id, save_run, utc_now
from common import DATA_DIR, SNAPSHOT_DIR, load_titles
import fetch_steam_store as store
import fetch_steam_reviews as reviews
import fetch_current_players as players

OUTPUT = SNAPSHOT_DIR / "commercial-snapshot-history.csv"
SOURCES = {
    "steam_store": store.fetch_store_details,
    "steam_reviews": reviews.fetch_review_summary,
    "current_players": players.fetch_current_players,
}
FIELDS = (
    [
        "snapshot_timestamp_utc",
        "cohort",
        "app_id",
        "title",
        "peer_group",
        "comparable_to",
        "lifecycle_role",
        "source_url",
    ]
    + store.FIELDS
    + reviews.FIELDS
    + players.FIELDS
    + ["market_benchmark_error", "run_id", "schema_version"]
)
for source in SOURCES:
    FIELDS += [source + "_status", source + "_retrieved_at_utc", source + "_error"]


def safe_fetch(label, fn, app_id):
    try:
        result = fn(app_id)
        return {
            **result,
            label + "_status": "ok",
            label + "_retrieved_at_utc": utc_now(),
        }
    except Exception as exc:
        status = (
            "invalid_payload"
            if isinstance(exc, ValueError)
            else (
                "http_error" if isinstance(exc, requests.HTTPError) else "source_failed"
            )
        )
        print(
            f"[WARN] {label} failed for {app_id}: {type(exc).__name__}: {exc}",
            flush=True,
        )
        return {
            label + "_status": status,
            label + "_retrieved_at_utc": utc_now(),
            label + "_error": f"{type(exc).__name__}: {exc}",
        }


def collect_title(title, timestamp, run_id):
    print(f"Collecting {title['app_id']} - {title['title']}", flush=True)
    row = {
        field: title.get(field, "")
        for field in [
            "cohort",
            "app_id",
            "title",
            "peer_group",
            "comparable_to",
            "lifecycle_role",
            "source_url",
        ]
    }
    row.update(snapshot_timestamp_utc=timestamp, run_id=run_id, schema_version=2)
    for source, fetch in SOURCES.items():
        row.update(safe_fetch(source, fetch, title["app_id"]))
    return row


def main():
    timestamp, run_id, titles = utc_now(), new_run_id("steam"), load_titles()
    with ThreadPoolExecutor(max_workers=2) as executor:
        rows = list(
            executor.map(lambda title: collect_title(title, timestamp, run_id), titles)
        )
    rows.sort(key=lambda row: (row["cohort"], row["peer_group"], row["title"]))
    passed = save_run(DATA_DIR, run_id, FIELDS, rows, SOURCES, timestamp, titles)
    if not passed:
        raise SystemExit(
            "Required Steam source coverage incomplete. Evidence saved; history unchanged."
        )
    append_history(OUTPUT, FIELDS, rows)
    print(f"Published {len(rows)} validated Steam observations", flush=True)


if __name__ == "__main__":
    main()
