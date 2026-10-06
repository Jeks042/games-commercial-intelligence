"""Build a quality-gated SQL release from explicitly accepted source runs."""

from __future__ import annotations
import argparse
import csv
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import tempfile
from acquisition import read_csv
from common import ROOT
from collect_snapshot import FIELDS as STEAM_FIELDS
from collect_market_benchmark import FIELDS as BENCHMARK_FIELDS

TABLES = [
    "dim_peer_group",
    "dim_title",
    "dim_date",
    "dim_run",
    "bridge_title_reference",
    "fact_steam_observation",
    "fact_external_benchmark",
    "dim_metric",
]
VIEWS = [
    "v_steam_metrics",
    "v_latest_steam_metrics",
    "v_price_reference",
    "v_weekly_comparable_pulse",
    "v_momentum_readiness",
]


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timedelta(0):
        raise ValueError(f"Expected an explicit UTC timestamp: {value}")
    return parsed.isoformat(timespec="microseconds")


def integer(row, field, nullable=False):
    value = row.get(field, "")
    if nullable and value == "":
        return None
    if not isinstance(value, str) or not value.isdigit():
        raise ValueError(f"{field} is missing or is not a nonnegative integer")
    return int(value)


def boolean(value, nullable=False):
    if nullable and value == "":
        return None
    if value not in ("True", "False"):
        raise ValueError(f"Invalid boolean: {value}")
    return int(value == "True")


def steam_date(value):
    if not value:
        return None
    match = re.fullmatch(r"(\d{1,2}) ([A-Za-z]{3}), (\d{4})", value)
    if not match:
        return None
    months = dict(
        zip("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), range(1, 13))
    )
    return date(int(match[3]), months[match[2]], int(match[1])).isoformat()


def insert(connection, table, row):
    keys = list(row)
    connection.execute(
        f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
        [row[key] for key in keys],
    )


def load_inputs(data_dir):
    titles = []
    for cohort, filename in (
        ("portfolio", "portfolio-titles.csv"),
        ("competitor", "competitor-titles.csv"),
    ):
        _, rows = read_csv(data_dir / filename)
        titles.extend([{**row, "cohort": cohort} for row in rows])
    ids = [row["app_id"] for row in titles]
    if (
        not titles
        or len(ids) != len(set(ids))
        or any(not value.isdigit() for value in ids)
    ):
        raise ValueError("Title scope must contain unique numeric app IDs")
    if any(not r["title"] or not r["peer_group"] for r in titles):
        raise ValueError("Title scope has missing names or groups")
    _, references = read_csv(data_dir / "title-references.csv")
    _, metrics = read_csv(ROOT / "docs" / "metric-dictionary.csv")
    register = json.loads(
        (data_dir / "accepted-runs.json").read_text(encoding="utf-8-sig")
    )
    if register.get("register_version") != 1 or not register.get("accepted_runs"):
        raise ValueError("An explicit accepted-run register is required")
    approved_ids = [entry["run_id"] for entry in register["accepted_runs"]]
    if len(approved_ids) != len(set(approved_ids)):
        raise ValueError("Duplicate run in accepted register")
    runs = []
    for entry in register["accepted_runs"]:
        run_id = entry["run_id"]
        if entry.get("admission_status") != "accepted" or not re.fullmatch(
            r"(steam|steamspy)-[A-Za-z0-9-]+", run_id
        ):
            raise ValueError("Invalid accepted-run entry")
        layer = entry["source_layer"]
        if layer not in ("steam", "steamspy"):
            raise ValueError("Unknown source layer")
        folder = data_dir / "runs" / run_id
        manifest = json.loads(
            (folder / "manifest.json").read_text(encoding="utf-8-sig")
        )
        if sha(canonical(manifest)) != entry["manifest_canonical_sha256"]:
            raise ValueError("Manifest differs from the reviewed acceptance record")
        if (
            manifest["run_id"] != run_id
            or manifest["schema_version"] != 2
            or manifest["status"] != "passed"
            or manifest["failures"]
        ):
            raise ValueError("Only passed schema-v2 runs can be admitted")
        required = (
            ["steam_store", "steam_reviews", "current_players"]
            if layer == "steam"
            else ["steamspy"]
        )
        if set(manifest["coverage"]) != set(required) or any(
            manifest["coverage"][s] != len(titles) for s in required
        ):
            raise ValueError("Accepted run has incomplete source coverage")
        if manifest["expected_titles"] != len(titles) or manifest[
            "collected_titles"
        ] != len(titles):
            raise ValueError("Accepted run scope differs from current title universe")
        # Acquisition uses json.dumps(..., sort_keys=True) with the default whitespace.
        universe_digest = sha(json.dumps(titles, sort_keys=True).encode())
        if manifest["title_universe_sha256"] != universe_digest:
            raise ValueError(
                "Title scope changed; an explicit scope/admission revision is required"
            )
        output = folder / "observations.csv"
        digest = sha(output.read_bytes())
        if (
            digest != manifest["observations_sha256"]
            or digest != entry["observations_sha256"]
        ):
            raise ValueError("Observation hash does not match accepted evidence")
        fields, rows = read_csv(output)
        expected_fields = STEAM_FIELDS if layer == "steam" else BENCHMARK_FIELDS
        if fields != expected_fields:
            raise ValueError(
                "Observation schema differs from declared acquisition schema"
            )
        if len(rows) != len(titles) or {row["app_id"] for row in rows} != set(ids):
            raise ValueError("Observation scope or uniqueness is invalid")
        start, finish = utc(manifest["started_at_utc"]), utc(
            manifest["finished_at_utc"]
        )
        if start > finish:
            raise ValueError("Invalid run time interval")
        scope = {r["app_id"]: r for r in titles}
        for row in rows:
            if row["run_id"] != run_id or row["schema_version"] != "2":
                raise ValueError("Row version/run does not match its manifest")
            if (
                row["cohort"] != scope[row["app_id"]]["cohort"]
                or row["peer_group"] != scope[row["app_id"]]["peer_group"]
            ):
                raise ValueError("Row classification differs from title scope")
            stamp = (
                "snapshot_timestamp_utc"
                if layer == "steam"
                else "benchmark_timestamp_utc"
            )
            if utc(row[stamp]) != start:
                raise ValueError("Observation timestamp differs from run start")
            for source in required:
                if row[source + "_status"] != "ok" or row[source + "_error"]:
                    raise ValueError("A failed source cannot enter an accepted fact")
                retrieval = utc(row[source + "_retrieved_at_utc"])
                if not start <= retrieval <= finish:
                    raise ValueError(
                        "Retrieval timestamp outside the accepted run interval"
                    )
            if layer == "steam":
                if row["store_country_code"] != "gb":
                    raise ValueError(
                        "Observation country differs from the approved Store contract"
                    )
                if (
                    manifest["source_contracts"]["steam_store"]["currency"] != "GBP"
                    or manifest["source_contracts"]["steam_store"]["country"] != "gb"
                ):
                    raise ValueError("Unapproved price region/currency")
                if (
                    row["review_query_version"]
                    != manifest["source_contracts"]["steam_reviews"]["query_version"]
                ):
                    raise ValueError("Review query version differs from manifest")
                if integer(row, "current_players_result") != 1:
                    raise ValueError("Invalid current-player result")
        runs.append((entry, manifest, rows))
    if {entry["source_layer"] for entry in register["accepted_runs"]} != {
        "steam",
        "steamspy",
    }:
        raise ValueError("Both observed and benchmark source layers are required")
    excluded = []
    for path in sorted((data_dir / "runs").glob("*/manifest.json")):
        if path.parent.name not in approved_ids:
            excluded.append(
                {"run_id": path.parent.name, "reason": "not_in_accepted_register"}
            )
    return titles, references, metrics, register, runs, excluded


def populate(connection, titles, references, metrics, runs):
    for group in sorted({r["peer_group"] for r in titles}):
        insert(connection, "dim_peer_group", {"peer_group": group})
    for row in sorted(titles, key=lambda r: int(r["app_id"])):
        release = row.get("release_date") or None
        if release:
            date.fromisoformat(release)
        insert(
            connection,
            "dim_title",
            {
                "app_id": int(row["app_id"]),
                "title": row["title"],
                "cohort": row["cohort"],
                "peer_group": row["peer_group"],
                "curated_publisher": row.get("publisher") or None,
                "curated_developer": row.get("developer") or None,
                "curated_release_date": release,
                "curated_lifecycle_role": row.get("lifecycle_role") or None,
                "source_url": row["source_url"],
            },
        )
    timestamps = [
        utc(m[key]) for _, m, _ in runs for key in ("started_at_utc", "finished_at_utc")
    ]
    first = date(min(datetime.fromisoformat(t).year for t in timestamps), 1, 1)
    last = date(max(datetime.fromisoformat(t).year for t in timestamps), 12, 31)
    day = first
    while day <= last:
        iso = day.isocalendar()
        insert(
            connection,
            "dim_date",
            {
                "date_key": day.isoformat(),
                "calendar_year": day.year,
                "calendar_month": day.month,
                "calendar_day": day.day,
                "iso_year": iso.year,
                "iso_week": iso.week,
                "iso_weekday": iso.weekday,
                "week_start_date": (day - timedelta(days=day.weekday())).isoformat(),
            },
        )
        day += timedelta(days=1)
    for row in references:
        insert(
            connection,
            "bridge_title_reference",
            {
                "portfolio_app_id": integer(row, "portfolio_app_id"),
                "reference_app_id": integer(row, "reference_app_id"),
                "peer_role": row["peer_role"],
                "rationale": row["rationale"],
            },
        )
    for metric in metrics:
        insert(connection, "dim_metric", metric)
    for entry, manifest, rows in sorted(runs, key=lambda item: item[0]["run_id"]):
        layer = entry["source_layer"]
        contracts = manifest["source_contracts"]
        insert(
            connection,
            "dim_run",
            {
                "run_id": manifest["run_id"],
                "source_layer": layer,
                "schema_version": 2,
                "admission_status": "accepted",
                "accepted_at_utc": utc(entry["accepted_at_utc"]),
                "acceptance_evidence": entry["acceptance_evidence"],
                "started_at_utc": utc(manifest["started_at_utc"]),
                "finished_at_utc": utc(manifest["finished_at_utc"]),
                "expected_titles": manifest["expected_titles"],
                "manifest_path": f"runs/{manifest['run_id']}/manifest.json",
                "manifest_canonical_sha256": entry["manifest_canonical_sha256"],
                "observations_sha256": manifest["observations_sha256"],
                "collector_revision": manifest["collector_revision"],
                "source_contracts_json": canonical(contracts).decode(),
                "collector_source_hashes_json": canonical(
                    manifest["collector_source_sha256"]
                ).decode(),
                "review_contract_sha256": (
                    sha(canonical(contracts["steam_reviews"]))
                    if layer == "steam"
                    else None
                ),
            },
        )
        for row in sorted(rows, key=lambda r: int(r["app_id"])):
            if layer == "steam":
                timestamp = utc(row["snapshot_timestamp_utc"])
                fact = {
                    "app_id": int(row["app_id"]),
                    "run_id": row["run_id"],
                    "observation_timestamp_utc": timestamp,
                    "date_key": timestamp[:10],
                    "store_name": row["store_name"],
                    "developer_live": row["developer_live"] or None,
                    "publisher_live": row["publisher_live"] or None,
                    "steam_release_date": steam_date(row["release_date_live"]),
                    "steam_release_date_text": row["release_date_live"] or None,
                    "early_access_genre_flag": (
                        int("Early Access" in row["genres_live"].split("; "))
                        if row["genres_live"]
                        else None
                    ),
                    "is_free": boolean(row["is_free"]),
                    "coming_soon": boolean(row["coming_soon"], True),
                    "currency": row["currency"] or None,
                    "price_status": row["price_status"],
                    "list_price_minor": integer(row, "list_price_minor", True),
                    "final_price_minor": integer(row, "final_price_minor", True),
                    "discount_percent_reported": integer(row, "discount_percent", True),
                    "review_query_version": row["review_query_version"],
                    "review_score_desc": row["review_score_desc"],
                    "evidence_class": "observed",
                }
                for field in (
                    "total_positive_reviews",
                    "total_negative_reviews",
                    "total_reviews",
                    "review_score_code",
                    "current_players",
                ):
                    fact[field] = integer(row, field)
                for source in ("steam_store", "steam_reviews", "current_players"):
                    fact[source + "_status"] = row[source + "_status"]
                    fact[source + "_retrieved_at_utc"] = utc(
                        row[source + "_retrieved_at_utc"]
                    )
                insert(connection, "fact_steam_observation", fact)
            else:
                bounds = re.fullmatch(
                    r"([\d,]+)\s*\.\.\s*([\d,]+)", row["estimated_owners"]
                )
                if not bounds:
                    raise ValueError("Malformed SteamSpy owner band")
                timestamp = utc(row["benchmark_timestamp_utc"])
                fact = {
                    "app_id": int(row["app_id"]),
                    "run_id": row["run_id"],
                    "benchmark_source": "steamspy",
                    "benchmark_timestamp_utc": timestamp,
                    "date_key": timestamp[:10],
                    "retrieved_at_utc": utc(row["steamspy_retrieved_at_utc"]),
                    "source_status": row["steamspy_status"],
                    "owner_band_raw": row["estimated_owners"],
                    "estimated_owners_lower": int(bounds[1].replace(",", "")),
                    "estimated_owners_upper": int(bounds[2].replace(",", "")),
                    "owner_estimate_status": row["owner_estimate_status"],
                    "playtime_status": row["playtime_status"],
                    "ownership_evidence_class": "estimated",
                    "reported_context_evidence_class": "observed",
                    "reported_context_status": "period_unresolved",
                    "steamspy_peak_ccu_previous_day_reported": integer(
                        row, "steamspy_ccu", True
                    ),
                }
                for field in (
                    "steamspy_positive",
                    "steamspy_negative",
                    "average_playtime_forever_minutes",
                    "average_playtime_2weeks_minutes",
                    "median_playtime_forever_minutes",
                    "median_playtime_2weeks_minutes",
                ):
                    fact[field] = integer(row, field, True)
                insert(connection, "fact_external_benchmark", fact)


def check_model(connection, sql_dir):
    if (
        connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
        or connection.execute("PRAGMA foreign_key_check").fetchall()
    ):
        raise ValueError("SQL database integrity/relationships failed")
    checks = dict(
        connection.execute(
            (sql_dir / "03_quality_checks.sql").read_text(encoding="utf-8-sig")
        ).fetchall()
    )
    if any(checks.values()):
        raise ValueError(f"Analytical quality gate failed: {checks}")
    return checks


def build_model(data_dir=None, output_dir=None, sql_dir=None):
    data_dir = Path(data_dir or ROOT / "data")
    output_dir = Path(output_dir or data_dir / "analytical")
    sql_dir = Path(sql_dir or ROOT / "sql")
    if sqlite3.sqlite_version_info < (3, 37, 0):
        raise ValueError("SQLite 3.37 or later is required for STRICT tables")
    titles, references, metrics, register, runs, excluded = load_inputs(data_dir)
    fingerprint = {
        "model_version": 1,
        "title_universe": titles,
        "references": references,
        "metrics": metrics,
        "accepted_register": register,
        "sql_sha256": {
            p.name: sha(p.read_bytes()) for p in sorted(sql_dir.glob("*.sql"))
        },
        "builder_sha256": sha(Path(__file__).read_bytes()),
        "sqlite_version": sqlite3.sqlite_version,
        "python_version": platform.python_version(),
    }
    release_id = sha(canonical(fingerprint))[:16]
    releases = output_dir / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".building-", dir=releases))
    try:
        database = stage / "commercial-model.sqlite"
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(
                (sql_dir / "01_schema.sql").read_text(encoding="utf-8-sig")
            )
            populate(connection, titles, references, metrics, runs)
            connection.executescript(
                (sql_dir / "02_reporting_views.sql").read_text(encoding="utf-8-sig")
            )
            checks = check_model(connection, sql_dir)
            connection.commit()
            counts, hashes = {}, {}
            for name in TABLES + VIEWS:
                cursor = connection.execute(
                    f"SELECT * FROM {name} ORDER BY "
                    + ",".join(
                        str(i + 1)
                        for i in range(
                            len(
                                connection.execute(
                                    f"SELECT * FROM {name} LIMIT 0"
                                ).description
                            )
                        )
                    )
                )
                rows = cursor.fetchall()
                target = stage / (name + ".csv")
                with target.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle, lineterminator="\n")
                    writer.writerow([col[0] for col in cursor.description])
                    writer.writerows(rows)
                counts[name], hashes[target.name] = len(rows), sha(target.read_bytes())
        manifest = {
            "release_id": release_id,
            "model_version": 1,
            "status": "passed",
            "sqlite_version": sqlite3.sqlite_version,
            "python_version": platform.python_version(),
            "input_fingerprint_sha256": sha(canonical(fingerprint)),
            "builder_sha256": fingerprint["builder_sha256"],
            "sql_sha256": fingerprint["sql_sha256"],
            "accepted_run_ids": [e["run_id"] for e in register["accepted_runs"]],
            "admission_policy": "Explicit accepted register, passed schema-v2 manifest, matching hashes and full scope; all unregistered and legacy evidence excluded.",
            "row_counts": counts,
            "quality_checks": checks,
            "output_csv_sha256": hashes,
            "database_sha256": sha(database.read_bytes()),
            "csv_null_policy": "Empty field is NULL. Valid numeric zero is written as 0.",
            "price_policy": "Observed GBP minor units retained; reporting GBP = minor units / 100.",
            "trend_policy": "Four consecutive comparable Monday UTC slots; same review contract; no same-day trends.",
        }
        (stage / "build-manifest.json").write_bytes(canonical(manifest) + b"\n")
        target = releases / release_id
        if (
            stage.resolve().parent != releases.resolve()
            or target.resolve().parent != releases.resolve()
        ):
            raise RuntimeError(
                "Publication paths leave the intended releases directory"
            )
        if target.exists():
            for name, digest in hashes.items():
                if sha((target / name).read_bytes()) != digest:
                    raise ValueError(
                        "Existing release differs from deterministic output; publication stopped"
                    )
            if (target / "build-manifest.json").read_bytes() != (
                stage / "build-manifest.json"
            ).read_bytes():
                raise ValueError(
                    "Existing release manifest differs; publication stopped"
                )
            if not (target / database.name).exists():
                os.replace(database, target / database.name)
            elif (
                sha((target / database.name).read_bytes())
                != manifest["database_sha256"]
            ):
                raise ValueError("Existing database hash differs; publication stopped")
        else:
            os.replace(stage, target)
        pointer = output_dir / "current.json"
        fd, temporary = tempfile.mkstemp(dir=output_dir, suffix=".tmp")
        with os.fdopen(fd, "wb") as handle:
            handle.write(
                canonical(
                    {
                        "release_id": release_id,
                        "path": f"releases/{release_id}",
                        "status": "passed",
                    }
                )
                + b"\n"
            )
        os.replace(temporary, pointer)
        print(
            json.dumps(
                {
                    "release_id": release_id,
                    "status": "passed",
                    "row_counts": counts,
                    "ignored_run_ids": [entry["run_id"] for entry in excluded],
                }
            ),
            flush=True,
        )
        return target
    finally:
        if stage.exists():
            if (
                stage.resolve().parent != releases.resolve()
                or not stage.name.startswith(".building-")
            ):
                raise RuntimeError(
                    "Refusing cleanup outside the model staging directory"
                )
            shutil.rmtree(stage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    arguments = parser.parse_args()
    build_model(arguments.data_dir, arguments.output_dir)
