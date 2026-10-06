"""Publish snapshot positioning from an explicitly pinned, verified model release."""

from __future__ import annotations
import argparse
from contextlib import closing
import csv
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import tempfile
from build_model import ROOT, TABLES, VIEWS, canonical, sha, check_model

OUTPUTS = [
    "v_portfolio_positioning",
    "v_reference_pair_context",
    "v_reference_metric_context",
    "v_direct_peer_benchmark",
    "v_lifecycle_coverage",
]
POLICY = {
    "minimum_direct_peers": 3,
    "minimum_reviews_for_positivity": 100,
    "maximum_pair_collection_seconds": 300,
    "require_same_source_utc_date": True,
    "require_same_review_contract": True,
    "percentile": "100 * (references_below_target + 0.5 * references_equal_target) / valid_reference_count",
    "classification": "No composite or overall performance score; unadjusted snapshot signals only.",
}


def verified_inputs(root, contract_path):
    root = Path(root).resolve()
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    if (
        contract.get("status") != "accepted"
        or contract.get("analysis_policy") != POLICY
    ):
        raise ValueError(
            "An accepted benchmark contract matching the SQL policy is required"
        )
    release = (root / contract["model_release_path"]).resolve()
    if not release.is_relative_to(root / "data" / "analytical" / "releases"):
        raise ValueError("Model input is outside the intended release directory")
    manifest_bytes = (release / "build-manifest.json").read_bytes()
    if sha(manifest_bytes) != contract["model_manifest_sha256"]:
        raise ValueError("Pinned model manifest hash differs")
    manifest = json.loads(manifest_bytes)
    if (
        sha(Path(__file__).with_name("build_model.py").read_bytes())
        != manifest["builder_sha256"]
    ):
        raise ValueError("Pinned model helper code differs")
    if manifest["status"] != "passed" or any(manifest["quality_checks"].values()):
        raise ValueError("Model release did not pass quality gates")
    if manifest["release_id"] != contract["model_release_id"]:
        raise ValueError("Pinned model release identity differs")
    dictionary = root / "docs" / "benchmark-metrics.csv"
    if sha(dictionary.read_bytes()) != contract["metric_dictionary_sha256"]:
        raise ValueError("Benchmark metric dictionary hash differs")
    expected = {name + ".csv" for name in TABLES + VIEWS}
    if set(manifest["output_csv_sha256"]) != expected:
        raise ValueError("Model export inventory differs")
    for name, digest in manifest["output_csv_sha256"].items():
        if sha((release / name).read_bytes()) != digest:
            raise ValueError(f"Model input hash differs: {name}")
    for name, digest in manifest["sql_sha256"].items():
        if name not in {
            "01_schema.sql",
            "02_reporting_views.sql",
            "03_quality_checks.sql",
        }:
            raise ValueError("Unexpected model SQL file")
        if sha((root / "sql" / name).read_bytes()) != digest:
            raise ValueError(f"Pinned model SQL hash differs: {name}")
    if set(manifest["sql_sha256"]) != {
        "01_schema.sql",
        "02_reporting_views.sql",
        "03_quality_checks.sql",
    }:
        raise ValueError("Model SQL inventory differs")
    return contract, release, manifest


def load_model(connection, root, release, manifest):
    connection.executescript(
        (root / "sql" / "01_schema.sql").read_text(encoding="utf-8-sig")
    )
    for table in TABLES:
        info = connection.execute(f"PRAGMA table_info({table})").fetchall()
        columns = [row[1] for row in info]
        with (release / (table + ".csv")).open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            if next(reader) != columns:
                raise ValueError(f"Model header mismatch: {table}")
            count = 0
            for row in reader:
                if len(row) != len(info):
                    raise ValueError(f"Model row width mismatch: {table}")
                values = [
                    (
                        None
                        if value == ""
                        else int(value) if col[2] == "INTEGER" else value
                    )
                    for value, col in zip(row, info)
                ]
                connection.execute(
                    f"INSERT INTO {table} VALUES ({','.join('?' for _ in info)})",
                    values,
                )
                count += 1
        if count != manifest["row_counts"][table]:
            raise ValueError(f"Model row count mismatch: {table}")
    connection.executescript(
        (root / "sql" / "02_reporting_views.sql").read_text(encoding="utf-8-sig")
    )
    check_model(connection, root / "sql")


def build(root=ROOT, output_dir=None, contract_path=None):
    root = Path(root).resolve()
    output_dir = Path(output_dir or root / "data" / "positioning").resolve()
    contract_path = Path(contract_path or root / "data" / "benchmarking-contract.json")
    if sqlite3.sqlite_version_info < (3, 37, 0):
        raise ValueError("SQLite 3.37 or later is required")
    contract, model_release, model_manifest = verified_inputs(root, contract_path)
    sql_dir = root / "sql" / "benchmarking"
    sql_hashes = {
        name: sha((sql_dir / name).read_bytes())
        for name in ("01_positioning.sql", "02_quality_checks.sql")
    }
    fingerprint = {
        "analysis_version": 1,
        "contract": contract,
        "sql_sha256": sql_hashes,
        "builder_sha256": sha(Path(__file__).read_bytes()),
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
    }
    release_id = sha(canonical(fingerprint))[:16]
    releases = output_dir / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".building-", dir=releases))
    try:
        database = stage / "portfolio-positioning.sqlite"
        with closing(sqlite3.connect(database)) as connection:
            load_model(connection, root, model_release, model_manifest)
            connection.executescript(
                (sql_dir / "01_positioning.sql").read_text(encoding="utf-8-sig")
            )
            checks = dict(
                connection.execute(
                    (sql_dir / "02_quality_checks.sql").read_text(encoding="utf-8-sig")
                ).fetchall()
            )
            if any(checks.values()):
                raise ValueError(f"Positioning quality gate failed: {checks}")
            connection.commit()
            counts, hashes = {}, {}
            for name in OUTPUTS:
                columns = connection.execute(
                    f"SELECT * FROM {name} LIMIT 0"
                ).description
                cursor = connection.execute(
                    f"SELECT * FROM {name} ORDER BY "
                    + ",".join(str(i + 1) for i in range(len(columns)))
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
            "status": "passed",
            **fingerprint,
            "model_release_id": model_manifest["release_id"],
            "model_manifest_sha256": contract["model_manifest_sha256"],
            "row_counts": counts,
            "quality_checks": checks,
            "output_csv_sha256": hashes,
            "database_sha256": sha(database.read_bytes()),
            "csv_null_policy": "Empty fields are NULL; genuine zero remains 0.",
            "interpretation": "Configured reference-set context only; no lifecycle-adjusted or overall performance classification.",
        }
        (stage / "build-manifest.json").write_bytes(canonical(manifest) + b"\n")
        target = releases / release_id
        if (
            stage.resolve().parent != releases.resolve()
            or target.resolve().parent != releases.resolve()
        ):
            raise RuntimeError("Publication leaves the intended releases directory")
        if target.exists():
            for name, digest in hashes.items():
                if sha((target / name).read_bytes()) != digest:
                    raise ValueError("Existing positioning release differs")
            if (target / "build-manifest.json").read_bytes() != (
                stage / "build-manifest.json"
            ).read_bytes():
                raise ValueError("Existing positioning manifest differs")
            if not (target / database.name).exists():
                os.replace(database, target / database.name)
            elif (
                sha((target / database.name).read_bytes())
                != manifest["database_sha256"]
            ):
                raise ValueError("Existing positioning database differs")
        else:
            os.replace(stage, target)
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
        os.replace(temporary, output_dir / "current.json")
        print(
            json.dumps(
                {"release_id": release_id, "status": "passed", "row_counts": counts}
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
                raise RuntimeError("Unsafe positioning staging cleanup")
            shutil.rmtree(stage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    arguments = parser.parse_args()
    build(output_dir=arguments.output_dir)
