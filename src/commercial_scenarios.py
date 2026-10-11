"""Build conditional price/volume arithmetic from an admitted dated Steam model."""

import csv
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import io
import itertools
import json
import os
from pathlib import Path
import tempfile

from benchmark_portfolio import verified_inputs
from build_model import ROOT, canonical, sha


def number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean scenario input")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Invalid scenario number") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Scenario numbers must be finite and nonnegative")
    return result


def display(value):
    return None if value is None else str(value.quantize(Decimal("0.000001")))


def calculate(price_minor, price_factor, paid_unit_factor, engagement_factor):
    p, u, e = map(number, (price_factor, paid_unit_factor, engagement_factor))
    if p > 1:
        raise ValueError("This contract supports unchanged/lower hypothetical prices")
    anchor = None if price_minor is None else number(price_minor)
    if anchor is not None and anchor != anchor.to_integral_value():
        raise ValueError("Anchor price must be integer pence")
    hypothetical = (
        None
        if anchor is None
        else (anchor * p).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    valid_anchor = anchor is not None and anchor > 0
    factor = hypothetical / anchor if valid_anchor else None
    index = 100 * factor * u if valid_anchor else None
    neutral = anchor / hypothetical if valid_anchor and hypothetical > 0 else None
    return {
        "assumed_price_factor": str(p),
        "assumed_paid_unit_factor": str(u),
        "assumed_engagement_factor": str(e),
        "hypothetical_price_minor": None if hypothetical is None else int(hypothetical),
        "rounded_price_factor": display(factor),
        "conditional_gross_receipts_index": display(index),
        "hypothetical_engagement_index": display(100 * e),
        "gross_receipts_neutral_paid_unit_factor": display(neutral),
        "required_paid_unit_change_percent": display(
            None if neutral is None else 100 * (neutral - 1)
        ),
        "arithmetic_status": (
            "unavailable_nonpositive_or_missing_anchor"
            if not valid_anchor
            else (
                "undefined_neutral_threshold_zero_hypothetical_price"
                if hypothetical == 0
                else "available_conditional_arithmetic_only"
            )
        ),
        "receipts_condition": (
            "unavailable"
            if index is None
            else (
                "below_reference"
                if index < 100
                else "above_reference" if index > 100 else "equal_reference"
            )
        ),
        "budget_decision": "not_supported_requires_paid_unit_response_and_contribution_economics",
        "evidence_class": "derived_from_observed_anchor_and_explicit_assumptions",
        "forecast_status": "not_a_forecast",
    }


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def validate_contract(contract):
    required = {
        "predicted_paid_units",
        "predicted_revenue",
        "forecast_mae",
        "forecast_wape",
        "prediction_interval_lower",
        "prediction_interval_upper",
        "elasticity",
        "roi",
    }
    if set(contract["unsupported_measures"]) != required or len(
        contract["unsupported_measures"]
    ) != len(required):
        raise ValueError("Unsupported-measure inventory differs")
    for field, values in contract["sensitivity"].items():
        numbers = [number(v) for v in values]
        if not numbers or len(numbers) != len(set(numbers)):
            raise ValueError("Sensitivity dimensions must be nonempty and unique")
        if field == "price_factors" and any(v > 1 for v in numbers):
            raise ValueError("Unsupported sensitivity price factor")
    if set(contract["sensitivity"]) != {
        "price_factors",
        "paid_unit_factors",
        "engagement_factors",
    }:
        raise ValueError("Sensitivity dimension inventory differs")
    for s in contract["scenarios"]:
        calculate(
            1000, s["price_factor"], s["paid_unit_factor"], s["engagement_factor"]
        )
    hold = next(
        (s for s in contract["scenarios"] if s["name"] == "hold_reference"), None
    )
    if hold is None or any(
        number(hold[k]) != 1
        for k in ("price_factor", "paid_unit_factor", "engagement_factor")
    ):
        raise ValueError("Hold reference must preserve normalized baseline")


def evaluate(observations, readiness, counts, contract):
    validate_contract(contract)
    anchors, scenarios, sensitivity, thresholds, forecast = [], [], [], [], []
    names = [s["name"] for s in contract["scenarios"]]
    if len(names) != len(set(names)) or set(names) != {
        "hold_reference",
        "base",
        "upside",
        "downside",
    }:
        raise ValueError("Require unique hold/base/upside/downside cases")
    portfolio = sorted(
        (r for r in observations if r["cohort"] == "portfolio"),
        key=lambda r: int(r["app_id"]),
    )
    if not portfolio or len({r["app_id"] for r in portfolio}) != len(portfolio):
        raise ValueError("Portfolio scope is empty or duplicated")
    for r in portfolio:
        app = r["app_id"]
        m = readiness[app]
        usable = (
            r["currency"] == "GBP"
            and r["price_status"] == "available"
            and r["steam_store_status"] == "ok"
            and r["coming_soon"] == "0"
        )
        raw_price = (
            None if r["final_price_minor"] == "" else int(r["final_price_minor"])
        )
        if raw_price is not None and raw_price < 0:
            raise ValueError("Negative observed price")
        anchor = raw_price if usable else None
        identity = {
            "app_id": int(app),
            "title": r["title"],
            "anchor_run_id": r["run_id"],
            "anchor_retrieved_at_utc": r["steam_store_retrieved_at_utc"],
        }
        anchors.append(
            {
                **identity,
                "observed_final_price_minor": raw_price,
                "observed_currency": r["currency"],
                "observed_price_status": r["price_status"],
                "eligible_anchor_price_minor": anchor,
                "anchor_status": (
                    "available_dated_GBP_anchor"
                    if usable
                    else "unavailable_unsuitable_anchor"
                ),
                "observed_point_current_players": (
                    None if r["current_players"] == "" else int(r["current_players"])
                ),
                "player_retrieved_at_utc": r["current_players_retrieved_at_utc"],
                "observed_evidence_class": "observed",
                "anchor_is_live_quote": False,
                "paid_unit_baseline": None,
                "paid_unit_baseline_status": "unobserved",
                "engagement_to_paid_units": "not_established",
            }
        )
        for s in contract["scenarios"]:
            scenarios.append(
                {
                    **identity,
                    "scenario": s["name"],
                    **calculate(
                        anchor,
                        s["price_factor"],
                        s["paid_unit_factor"],
                        s["engagement_factor"],
                    ),
                }
            )
        grid = contract["sensitivity"]
        for p, u, e in itertools.product(
            grid["price_factors"], grid["paid_unit_factors"], grid["engagement_factors"]
        ):
            sensitivity.append({**identity, **calculate(anchor, p, u, e)})
        for p in grid["price_factors"]:
            thresholds.append({**identity, **calculate(anchor, p, "1", "1")})
        forecast.append(
            {
                **identity,
                "accepted_observation_count": counts.get(app, 0),
                "qualifying_comparable_weeks": int(m["comparable_week_count"]),
                "momentum_minimum_weeks": int(m["minimum_comparable_weeks"]),
                "player_momentum_status": m["player_momentum_status"],
                "review_velocity_status": m["review_velocity_status"],
                "forecast_status": "unavailable_no_admitted_target_series_and_untouched_holdout",
                "validation_status": "not_run_no_eligible_forecast",
                "forecast_horizon": None,
                **{name: None for name in contract["unsupported_measures"]},
                "uncertainty_status": "scenario_stress_range_not_predictive_interval",
            }
        )
    return {
        name: csv_bytes(rows)
        for name, rows in (
            ("observed_anchors.csv", anchors),
            ("commercial_scenarios.csv", scenarios),
            ("scenario_sensitivity.csv", sensitivity),
            ("receipts_neutral_thresholds.csv", thresholds),
            ("forecast_readiness.csv", forecast),
        )
    }


def build(root=ROOT, output_dir=None):
    root = Path(root).resolve()
    _, model, manifest = verified_inputs(root, root / "data/benchmarking-contract.json")
    contract_path = root / "data/scenario-contract.json"
    contract = json.loads(contract_path.read_bytes())
    if (
        contract["version"] != 1
        or contract["status"] != "specified_pending_independent_review"
    ):
        raise ValueError("Unsupported scenario contract")

    def read(name):
        with (model / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    observations = read("v_latest_steam_metrics.csv")
    readiness_rows = read("v_momentum_readiness.csv")
    readiness = {r["app_id"]: r for r in readiness_rows}
    if len(readiness) != len(readiness_rows) or set(readiness) != {
        r["app_id"] for r in observations
    }:
        raise ValueError("Readiness identity coverage differs")
    counts = {}
    for r in read("fact_steam_observation.csv"):
        counts[r["app_id"]] = counts.get(r["app_id"], 0) + 1
    outputs = evaluate(observations, readiness, counts, contract)
    fingerprint = {
        "accepted_model_manifest_sha256": sha(
            (model / "build-manifest.json").read_bytes()
        ),
        "scenario_contract_sha256": sha(contract_path.read_bytes()),
        "builder_sha256": sha(Path(__file__).read_bytes()),
    }
    release_id = sha(canonical(fingerprint))[:16]
    receipt = {
        "release_id": release_id,
        "status": "built_conditional_scenarios_pending_review",
        **fingerprint,
        "accepted_model_release_id": manifest["release_id"],
        "output_csv_sha256": {name: sha(body) for name, body in outputs.items()},
        "row_counts": {
            name: len(body.decode().splitlines()) - 1 for name, body in outputs.items()
        },
        "csv_null_policy": "Empty fields are unavailable, never imputed as zero",
        "forecast_validation": "not_run; no eligible predictive target series or holdout",
        "interpretation": "Conditional arithmetic only; no estimated sales, net revenue, causal response, elasticity, ROI or predictive interval",
    }
    outputs["build-manifest.json"] = canonical(receipt) + b"\n"
    output = Path(output_dir or root / "data/scenarios").resolve()
    release = output / "releases" / release_id
    release.parent.mkdir(parents=True, exist_ok=True)
    if release.exists():
        if {p.name: p.read_bytes() for p in release.iterdir()} != outputs:
            raise ValueError("Existing scenario release differs; pointer unchanged")
    else:
        stage = Path(
            tempfile.mkdtemp(prefix=".building-scenarios-", dir=release.parent)
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
                "row_counts": receipt["row_counts"],
                "status": receipt["status"],
            }
        ),
        flush=True,
    )
    return release


if __name__ == "__main__":
    build()
