"""Review bounded provider price context; do not estimate promotion response."""

import csv
import io
import json
import os
from pathlib import Path
import platform
import statistics
import tempfile

from price_history import ROOT, PRODUCT_BASIS, admitted_events, price_suitability
from benchmark_portfolio import verified_inputs
from build_model import canonical, sha

MIN_DIRECT_REFERENCES = 3


def evaluate(scope, events, observations, references, coverage=None):
    """Separate source values from price suitability and coverage-restricted comparisons."""
    titles = []
    for title in scope:
        app = title["app_id"]
        rows = sorted(
            (r for r in events if r["app_id"] == app), key=lambda r: r["event_at_utc"]
        )
        priced = [r for r in rows if r["price_status"] == "available"]
        latest = rows[-1] if rows else None
        steam = observations[app]
        source_status = (
            coverage[app]["history_status"]
            if coverage
            else ("returned_events" if rows else "no_returned_events")
        )
        snapshot_price = (
            int(steam["final_price_minor"]) if steam["final_price_minor"] else None
        )
        snapshot_regular = (
            int(steam["list_price_minor"]) if steam["list_price_minor"] else None
        )
        source_price = (
            latest["price_minor"]
            if latest and latest["price_status"] == "available"
            else None
        )
        source_regular = (
            latest["regular_minor"]
            if latest and latest["price_status"] == "available"
            else None
        )
        if title["identity_status"] != "eligible_app_linked_game_context":
            suitability = "excluded_current_mapping_unresolved"
        elif source_status.startswith("not_requested_") or source_status.startswith(
            "excluded_"
        ):
            suitability = "excluded_" + source_status
        elif not rows:
            suitability = "unavailable_no_in_window_records"
        else:
            suitability = price_suitability(latest, steam)
        suitable = suitability == "corroborated_latest_price_context_only"
        cuts = [
            float(r["cut_percent_source"]) for r in priced if r["regular_minor"] > 0
        ]
        titles.append(
            {
                "app_id": app,
                "title": title["title"],
                "cohort": title["cohort"],
                "itad_game_id": title["itad_game_id"],
                "evidence_basis": PRODUCT_BASIS,
                "suitability_status": suitability,
                "history_status": source_status,
                "returned_record_count": (
                    len(rows)
                    if title["identity_status"] == "eligible_app_linked_game_context"
                    and not source_status.startswith(("not_requested_", "excluded_"))
                    else None
                ),
                "source_latest_record_at_utc": (
                    latest["event_at_utc"] if latest else None
                ),
                "source_latest_price_minor": source_price,
                "source_latest_regular_minor": source_regular,
                "accepted_steam_price_minor": snapshot_price,
                "accepted_steam_regular_minor": snapshot_regular,
                "accepted_steam_retrieved_at_utc": steam[
                    "steam_store_retrieved_at_utc"
                ],
                "minimum_recorded_price_gbp": (
                    min(r["price_minor"] for r in priced) / 100
                    if suitable and priced
                    else None
                ),
                "maximum_recorded_price_gbp": (
                    max(r["price_minor"] for r in priced) / 100
                    if suitable and priced
                    else None
                ),
                "maximum_source_reported_cut_percent": (
                    max(cuts) if suitable and cuts else None
                ),
                "historical_sku_identity": "not_independently_verified",
                "window_coverage": "returned_records_only_left_state_unknown",
                "response_change_percent": None,
                "response_status": "unavailable_no_comparable_historical_response_series",
            }
        )
    lookup = {r["app_id"]: r for r in titles}
    pairs, benchmarks = [], []
    seen = set()
    for ref in references:
        target, reference = int(ref["portfolio_app_id"]), int(ref["reference_app_id"])
        if (target, reference) in seen:
            raise ValueError("Duplicate price-reference pair")
        seen.add((target, reference))
        if (
            lookup[target]["cohort"] != "portfolio"
            or lookup[reference]["cohort"] != "competitor"
        ):
            raise ValueError("Price-reference cohort differs")
        r = lookup[reference]
        pairs.append(
            {
                "portfolio_app_id": target,
                "portfolio_title": lookup[target]["title"],
                "reference_app_id": reference,
                "reference_title": r["title"],
                "peer_role": ref["peer_role"],
                "reference_suitability": r["suitability_status"],
                "reference_maximum_source_reported_cut_percent": r[
                    "maximum_source_reported_cut_percent"
                ],
                "reference_returned_record_count": r["returned_record_count"],
                "scope": "bounded_recorded_container_price_context_only",
            }
        )
    for target in (r for r in titles if r["cohort"] == "portfolio"):
        direct = [
            r
            for r in pairs
            if r["portfolio_app_id"] == target["app_id"]
            and r["peer_role"] == "direct_peer"
        ]
        values = [
            r["reference_maximum_source_reported_cut_percent"]
            for r in direct
            if r["reference_suitability"] == "corroborated_latest_price_context_only"
            and r["reference_maximum_source_reported_cut_percent"] is not None
        ]
        ready = (
            len(values) >= MIN_DIRECT_REFERENCES
            and target["maximum_source_reported_cut_percent"] is not None
        )
        median = statistics.median(values) if ready else None
        benchmarks.append(
            {
                "app_id": target["app_id"],
                "title": target["title"],
                "target_maximum_source_reported_cut_percent": target[
                    "maximum_source_reported_cut_percent"
                ],
                "target_minimum_recorded_price_gbp": target[
                    "minimum_recorded_price_gbp"
                ],
                "expected_direct_reference_count": len(direct),
                "usable_direct_reference_count": len(values),
                "minimum_direct_reference_count": MIN_DIRECT_REFERENCES,
                "direct_reference_median_maximum_recorded_cut_percent": median,
                "target_minus_reference_median_cut_pp": (
                    target["maximum_source_reported_cut_percent"] - median
                    if ready
                    else None
                ),
                "comparison_status": (
                    "available_coverage_restricted_recorded_cut_context"
                    if ready
                    else "unavailable_insufficient_usable_direct_context"
                ),
                "comparability_limit": "returned_states_are_not_complete_period_extrema_or_same_date_price_rankings; lifecycle_and_sku_unadjusted",
                "evidence_basis": PRODUCT_BASIS,
                "response_change_percent": None,
                "response_status": "unavailable_no_comparable_historical_response_series",
                "causal_uplift_status": "not_identified",
            }
        )
    return titles, pairs, benchmarks


def encode(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def build(root=ROOT, output_dir=None):
    root = Path(root).resolve()
    contract, scope, manifest, events = admitted_events(root)
    _, model, _ = verified_inputs(root, root / "data/benchmarking-contract.json")
    with (model / "fact_steam_observation.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        observation_rows = list(csv.DictReader(handle))
    observations = {int(r["app_id"]): r for r in observation_rows}
    if len(observations) != len(observation_rows) or set(observations) != {
        t["app_id"] for t in scope
    }:
        raise ValueError("One accepted Steam observation per scoped title is required")
    with (model / "bridge_title_reference.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        references = list(csv.DictReader(handle))
    titles, pairs, benchmarks = evaluate(
        scope,
        events,
        observations,
        references,
        {r["app_id"]: r for r in manifest["title_coverage"]},
    )
    outputs = {
        name: encode(rows)
        for name, rows in (
            ("title_price_context.csv", titles),
            ("reference_discount_context.csv", pairs),
            ("portfolio_discount_context.csv", benchmarks),
        )
    }
    fingerprint = {
        "source_manifest_sha256": sha(canonical(manifest) + b"\n"),
        "accepted_model_manifest_sha256": contract["model_manifest_sha256"],
        "builder_sha256": sha(Path(__file__).read_bytes()),
        "python_version": platform.python_version(),
        "minimum_direct_references": MIN_DIRECT_REFERENCES,
        "since_utc": contract["window_start_utc"],
        "as_of_utc": contract["as_of_utc"],
    }
    release_id = sha(canonical(fingerprint))[:16]
    receipt = {
        "release_id": release_id,
        "status": "passed_bounded_price_context_only",
        **fingerprint,
        "output_csv_sha256": {n: sha(b) for n, b in outputs.items()},
        "row_counts": {
            "title_price_context": len(titles),
            "reference_discount_context": len(pairs),
            "portfolio_discount_context": len(benchmarks),
        },
        "suitability_counts": {
            s: sum(r["suitability_status"] == s for r in titles)
            for s in sorted({r["suitability_status"] for r in titles})
        },
        "interpretation": "Provider-container returned price states, latest-price corroboration only; no campaign, annual frequency, same-date historical rank, exactSKU or response-uplift conclusion.",
    }
    outputs["build-manifest.json"] = canonical(receipt) + b"\n"
    output = Path(output_dir or root / "data/pricing-review").resolve()
    release = output / "releases" / release_id
    release.parent.mkdir(parents=True, exist_ok=True)
    if release.exists():
        if any((release / name).read_bytes() != body for name, body in outputs.items()):
            raise ValueError(
                "Existing price-context release differs; pointer unchanged"
            )
    else:
        # Failures preserve their isolated staging directory; no partial release is published.
        stage = Path(
            tempfile.mkdtemp(prefix=".building-context-", dir=release.parent)
        ).resolve()
        if (
            stage.parent != release.parent.resolve()
            or release.resolve().parent != release.parent.resolve()
        ):
            raise ValueError(
                "Price-context publication leaves intended release directory"
            )
        for name, body in outputs.items():
            (stage / name).write_bytes(body)
        os.replace(stage, release)
    fd, temporary = tempfile.mkstemp(dir=output, suffix=".tmp")
    with os.fdopen(fd, "wb") as handle:
        handle.write(
            canonical(
                {
                    "release_id": release_id,
                    "path": f"releases/{release_id}",
                    "status": receipt["status"],
                }
            )
            + b"\n"
        )
    os.replace(temporary, output / "current.json")
    print(
        json.dumps(
            {
                "release_id": release_id,
                "status": receipt["status"],
                "row_counts": receipt["row_counts"],
            }
        ),
        flush=True,
    )
    return release


if __name__ == "__main__":
    build()
