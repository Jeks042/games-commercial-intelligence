from __future__ import annotations

from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"


def load_titles() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for cohort, filename in [
        ("portfolio", "portfolio-titles.csv"),
        ("competitor", "competitor-titles.csv"),
    ]:
        path = DATA_DIR / filename
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                row = dict(row)
                row["cohort"] = cohort
                rows.append(row)
    ids = [row["app_id"] for row in rows]
    if (
        not rows
        or len(ids) != len(set(ids))
        or any(not app_id.isdigit() for app_id in ids)
    ):
        raise ValueError("Title universe must contain unique numeric Steam app IDs")
    if any(not row.get("title") or not row.get("peer_group") for row in rows):
        raise ValueError("Every scoped title requires a name and peer group")
    return rows
