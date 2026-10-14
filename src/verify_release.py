"""Rebuild the accepted public package without changing its sources or pointers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import tempfile

from common import ROOT
from build_model import build_model
from benchmark_portfolio import build as position
from price_history import build_analysis as prices
from pricing_context import build as price_context
from review_analysis import build as reviews
from review_refinement import build as refinement
from commercial_scenarios import build as scenarios
from build_executive_report import build as executive


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(folder):
    return {
        p.relative_to(folder).as_posix(): digest(p)
        for p in folder.rglob("*")
        if p.is_file()
    }


def verify(root=ROOT):
    root = Path(root)
    prior = json.loads(
        (root / "docs/verification/review-refinement-37842049911.json").read_bytes()
    )
    scenario_receipt = json.loads(
        (root / "docs/verification/scenarios-38150259475.json").read_bytes()
    )
    executive_receipt = json.loads(
        (root / "docs/verification/executive-38475056427.json").read_bytes()
    )
    expected = {}
    for group, evidence in prior["prior_accepted_outputs"].items():
        for name, value in evidence["output_sha256"].items():
            expected[f"data/{group}/releases/{evidence['local_release_id']}/{name}"] = (
                value
            )
    for key in (
        "admitted_source_files_verified_unchanged",
        "refinement_files_match_committed_local",
    ):
        expected.update({"data/" + k: v for k, v in prior[key].items()})
    expected.update(
        {"data/" + k: v for k, v in scenario_receipt["scenario_files_verified"].items()}
    )
    expected.update(executive_receipt["dashboard_file_sha256"])
    for name, value in expected.items():
        if digest(root / name) != value:
            raise ValueError(f"Accepted evidence differs: {name}")

    results = {}
    # Copy only public inputs; never read or copy raw archives, secrets or native caches.
    with tempfile.TemporaryDirectory(prefix="games-public-rebuild-") as directory:
        work = Path(directory)
        for name in ("src", "sql", "docs", "data"):
            shutil.copytree(
                root / name,
                work / name,
                ignore=shutil.ignore_patterns("raw", "__pycache__", "*.sqlite"),
            )
        jobs = {
            "analytical": lambda: build_model(
                data_dir=work / "data",
                output_dir=work / "rebuilt/analytical",
                sql_dir=work / "sql",
            ),
            "positioning": lambda: position(
                root=work, output_dir=work / "rebuilt/positioning"
            ),
            "pricing-analysis": lambda: prices(
                root=work, output_dir=work / "rebuilt/pricing-analysis"
            ),
            "pricing-review": lambda: price_context(
                root=work, output_dir=work / "rebuilt/pricing-review"
            ),
            "review-analysis": lambda: reviews(root=work),
            "review-refinement": lambda: refinement("94c88909fe4c88a1", root=work),
            "scenarios": lambda: scenarios(
                root=work, output_dir=work / "rebuilt/scenarios"
            ),
            "executive": lambda: executive(
                root=work, output_dir=work / "rebuilt/dashboard"
            ),
        }
        for group, build in jobs.items():
            output = build()
            before = files(output)
            second = build()
            if output != second or before != files(second):
                raise ValueError(f"Non-identical repeated build: {group}")
            if group in prior["prior_accepted_outputs"]:
                hashes = prior["prior_accepted_outputs"][group]["output_sha256"]
            elif group == "review-refinement":
                prefix = "review-refinement/diagnostics/94c88909fe4c88a1/"
                hashes = {
                    k.removeprefix(prefix): v
                    for k, v in prior["refinement_files_match_committed_local"].items()
                    if k.startswith(prefix)
                }
            elif group == "scenarios":
                prefix = "scenarios/releases/1a2624a982917ec1/"
                hashes = {
                    k.removeprefix(prefix): v
                    for k, v in scenario_receipt["scenario_files_verified"].items()
                    if k.startswith(prefix)
                }
            else:
                hashes = {
                    k.removeprefix("dashboard/"): v
                    for k, v in executive_receipt["dashboard_file_sha256"].items()
                }
            for name, value in hashes.items():
                if before.get(name) != value:
                    raise ValueError(f"Rebuilt evidence differs: {group}/{name}")
            results[group] = {
                "files_matched_to_accepted_evidence": len(hashes),
                "repeated_build_identical": True,
                "output_sha256": {name: before[name] for name in hashes},
            }

    for name, value in expected.items():
        if digest(root / name) != value:
            raise ValueError(f"Accepted evidence changed during verification: {name}")
    return {
        "status": "passed_public_reproduction",
        "python_version": platform.python_version(),
        "accepted_files_verified_unchanged": len(expected),
        "private_archive_used": False,
        "api_key_used": False,
        "fresh_acquisition_performed": False,
        "interpretation": "Rebuilds frozen public coded evidence; no live refresh, private text replay or new source admission.",
        "builds": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--receipt", type=Path, help="Save verification outside accepted release trees"
    )
    args = parser.parse_args()
    result = verify()
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        with args.receipt.open("xb") as handle:
            handle.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps({k: v for k, v in result.items() if k != "builds"}))
