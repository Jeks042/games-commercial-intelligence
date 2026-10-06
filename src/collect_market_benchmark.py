from acquisition import atomic_csv, new_run_id, save_run, utc_now
from common import DATA_DIR, load_titles
from collect_snapshot import safe_fetch
from fetch_market_benchmark import FIELDS as METRICS, fetch_market_benchmark

OUTPUT = DATA_DIR / "benchmarks" / "steamspy-market-benchmark.csv"
FIELDS = (
    [
        "benchmark_timestamp_utc",
        "cohort",
        "app_id",
        "title",
        "peer_group",
        "lifecycle_role",
    ]
    + METRICS
    + [
        "run_id",
        "schema_version",
        "steamspy_status",
        "steamspy_retrieved_at_utc",
        "steamspy_error",
    ]
)


def main():
    timestamp, run_id, titles = utc_now(), new_run_id("steamspy"), load_titles()
    rows = []
    for title in titles:
        print(f"Benchmark {title['app_id']} - {title['title']}", flush=True)
        row = {
            field: title.get(field, "")
            for field in ["cohort", "app_id", "title", "peer_group", "lifecycle_role"]
        }
        row.update(benchmark_timestamp_utc=timestamp, run_id=run_id, schema_version=2)
        row.update(safe_fetch("steamspy", fetch_market_benchmark, title["app_id"]))
        rows.append(row)
    passed = save_run(DATA_DIR, run_id, FIELDS, rows, ["steamspy"], timestamp, titles)
    if not passed:
        raise SystemExit(
            "SteamSpy coverage incomplete. Evidence saved; previous benchmark unchanged."
        )
    atomic_csv(OUTPUT, FIELDS, rows)
    print(
        f"Published {len(rows)} validated benchmark responses; estimate fitness requires separate review",
        flush=True,
    )


if __name__ == "__main__":
    main()
