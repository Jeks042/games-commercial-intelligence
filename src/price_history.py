"""Collect immutable ITAD Steam GBP change logs; derive explicitly bounded episodes."""

from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import io
import os
from pathlib import Path
import time
from uuid import UUID
from datetime import timedelta
import tempfile
import platform
import shutil
import requests
from acquisition import atomic_csv, new_run_id, utc_now
from build_model import canonical, sha
from common import ROOT
from benchmark_portfolio import verified_inputs

EVENT_FIELDS = [
    "app_id",
    "itad_game_id",
    "run_id",
    "source_timestamp",
    "event_at_utc",
    "shop_id",
    "shop_name",
    "country",
    "price_status",
    "price_amount_source",
    "regular_amount_source",
    "price_minor",
    "regular_minor",
    "currency",
    "cut_percent_source",
    "discount_depth_percent",
    "retrieved_at_utc",
    "raw_response_sha256",
    "product_basis",
]


def instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Source timestamp must have an explicit offset")
    return parsed.astimezone(timezone.utc)


def api_key(root=ROOT):
    key = os.getenv("ITAD_API_KEY", "").strip()
    path = Path(root) / ".env"
    if not key and path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip().startswith("ITAD_API_KEY="):
                key = line.strip().split("=", 1)[1].strip().strip("\"'")
    if not key:
        raise ValueError(
            "ITAD_API_KEY is not configured in the environment or ignored local .env"
        )
    return key


def load_contract(root=ROOT):
    root = Path(root).resolve()
    contract = json.loads(
        (root / "data/price-history/source-contract.json").read_bytes()
    )
    required = {
        "history_endpoint": "https://api.isthereanydeal.com/games/history/v2",
        "country": "GB",
        "currency": "GBP",
        "shop_id": 61,
        "shop_name": "Steam",
        "api_documentation_version": "2.11.0",
    }
    if any(contract.get(k) != v for k, v in required.items()):
        raise ValueError("Unsupported source contract")
    start, end = instant(contract["window_start_utc"]), instant(contract["as_of_utc"])
    if start >= end:
        raise ValueError("Historical window must have increasing boundaries")
    discovery = (root / contract["discovery_path"]).resolve()
    if not discovery.is_relative_to(root / "data/price-history"):
        raise ValueError("Discovery leaves the source evidence directory")
    content = (discovery / "manifest.json").read_bytes()
    if sha(content) != contract["discovery_manifest_sha256"]:
        raise ValueError("Discovery manifest hash differs")
    manifest = json.loads(content)
    if set(manifest["raw_sha256"]) != {
        "shops.json",
        "app-lookup.json",
        "reverse-lookup.json",
    }:
        raise ValueError("Discovery inventory differs")
    for name, digest in manifest["raw_sha256"].items():
        if sha((discovery / name).read_bytes()) != digest:
            raise ValueError("Discovery source hash differs")
    shops = json.loads((discovery / "shops.json").read_bytes())
    if [s for s in shops if s.get("title") == "Steam"] != [
        {"id": 61, "title": "Steam"}
    ]:
        raise ValueError("Steam shop identity differs")
    forward = json.loads((discovery / "app-lookup.json").read_bytes())
    reverse = json.loads((discovery / "reverse-lookup.json").read_bytes())
    scope = manifest["scope"]
    _, model_release, _ = verified_inputs(
        root, root / "data/benchmarking-contract.json"
    )
    if contract["model_manifest_sha256"] != sha(
        (model_release / "build-manifest.json").read_bytes()
    ):
        raise ValueError("Price contract's accepted model differs")
    with (model_release / "dim_title.csv").open(encoding="utf-8", newline="") as handle:
        model_titles = {
            int(t["app_id"]): (t["title"], t["cohort"]) for t in csv.DictReader(handle)
        }
    if {t["app_id"]: (t["title"], t["cohort"]) for t in scope} != model_titles:
        raise ValueError("Discovery scope differs from the accepted title model")
    with (model_release / "dim_run.csv").open(encoding="utf-8", newline="") as handle:
        steam_ends = [
            instant(r["finished_at_utc"])
            for r in csv.DictReader(handle)
            if r["source_layer"] == "steam"
        ]
    if not steam_ends or end != max(steam_ends):
        raise ValueError(
            "Price cutoff differs from the accepted Steam observation period"
        )
    if len({t["app_id"] for t in scope}) != len(scope) or not scope:
        raise ValueError("Duplicate or empty discovery scope")
    for t in scope:
        shop_app = "app/" + str(t["app_id"])
        gid = forward.get(shop_app)
        if gid:
            UUID(gid)
        products = reverse.get(gid, [])
        apps = [p for p in products if p.startswith("app/")]
        status = (
            "eligible_app_linked_game_context"
            if gid and apps == [shop_app]
            else "requires_identity_review"
        )
        if (
            t["itad_game_id"] != gid
            or t["reverse_shop_ids"] != products
            or t["identity_status"] != status
        ):
            raise ValueError("Discovery mapping or declared exclusion differs")
    return contract, scope


def request_history(contract, gid, key):
    """Three attempts, header-only credential, bounded delays and sanitised errors."""
    params = {
        "id": gid,
        "country": "GB",
        "shops": "61",
        "since": contract["window_start_utc"],
    }
    for attempt in range(3):
        time.sleep(1.1 if attempt == 0 else 2**attempt)
        try:
            response = requests.get(
                contract["history_endpoint"],
                params=params,
                headers={
                    "ITAD-API-Key": key,
                    "User-Agent": "games-commercial-intelligence/4.0",
                },
                timeout=(10, 30),
            )
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise RuntimeError(
                    "History source connection failed after three attempts"
                ) from None
            continue
        if response.status_code == 429 or response.status_code >= 500:
            if attempt < 2:
                retry = response.headers.get("Retry-After", "")
                if retry.isdigit():
                    time.sleep(min(30, int(retry)))
                continue
        if response.status_code != 200:
            raise RuntimeError(f"History source returned HTTP {response.status_code}")
        return response.content
    raise RuntimeError("History request retry budget exhausted")


def price_value(obj):
    if not isinstance(obj, dict) or obj.get("currency") != "GBP":
        raise ValueError("History currency must be explicitly GBP")
    minor = obj.get("amountInt")
    if (
        type(minor) is not int
        or minor < 0
        or type(obj.get("amount")) not in (int, float)
    ):
        raise ValueError("Invalid source price representation")
    try:
        amount = Decimal(str(obj["amount"]))
    except (KeyError, InvalidOperation):
        raise ValueError("Missing or invalid source price amount") from None
    if not amount.is_finite() or amount < 0 or amount * 100 != minor:
        raise ValueError("Source decimal and GBP minor-unit price disagree")
    return minor, str(obj["amount"])


def normalise(raw, title, contract, run_id, retrieved):
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError(
            "History must be an array; wrapped or partial-page responses are unsupported"
        )
    start, end, retrieval = (
        instant(contract["window_start_utc"]),
        instant(contract["as_of_utc"]),
        instant(retrieved),
    )
    seen, rows = {}, []
    excluded = {"before_or_at_start": 0, "after_as_of": 0, "identical_duplicates": 0}
    for event in payload:
        if not isinstance(event, dict) or not {"timestamp", "shop", "deal"}.issubset(
            event
        ):
            raise ValueError("History event shape differs")
        at = instant(event["timestamp"])
        if at > retrieval:
            raise ValueError("History contains a future source timestamp")
        if event["shop"] != {"id": 61, "name": "Steam"}:
            raise ValueError("History contains a non-Steam shop")
        deal = event["deal"]
        row = {
            "app_id": title["app_id"],
            "itad_game_id": title["itad_game_id"],
            "run_id": run_id,
            "source_timestamp": event["timestamp"],
            "event_at_utc": at.isoformat(timespec="microseconds"),
            "shop_id": 61,
            "shop_name": "Steam",
            "country": "GB",
            "retrieved_at_utc": retrieved,
            "raw_response_sha256": sha(raw),
            "product_basis": "app_linked_game_shop_context_sku_unresolved",
        }
        if deal is None:
            row.update(
                price_status="removed_or_unavailable",
                price_amount_source=None,
                regular_amount_source=None,
                price_minor=None,
                regular_minor=None,
                currency=None,
                cut_percent_source=None,
                discount_depth_percent=None,
            )
        else:
            if not isinstance(deal, dict) or not {"price", "regular", "cut"}.issubset(
                deal
            ):
                raise ValueError("History deal shape differs")
            final, final_source = price_value(deal["price"])
            regular, regular_source = price_value(deal["regular"])
            if type(deal["cut"]) not in (int, float):
                raise ValueError("Invalid source cut")
            try:
                cut = Decimal(str(deal["cut"]))
            except InvalidOperation:
                raise ValueError("Invalid source cut") from None
            depth = Decimal(100) * (regular - final) / regular if regular else None
            if (
                final > regular
                or not cut.is_finite()
                or not 0 <= cut <= 100
                or (depth is not None and abs(depth - cut) > 1)
                or (regular == 0 and cut != 0)
            ):
                raise ValueError("History price/cut arithmetic differs")
            row.update(
                price_status="available",
                price_amount_source=final_source,
                regular_amount_source=regular_source,
                price_minor=final,
                regular_minor=regular,
                currency="GBP",
                cut_percent_source=str(deal["cut"]),
                discount_depth_percent=(
                    round(float(depth), 4) if depth is not None else None
                ),
            )
        # Validate even excluded source events; preserve all raw bytes independently.
        if at <= start:
            excluded["before_or_at_start"] += 1
            continue
        if at > end:
            excluded["after_as_of"] += 1
            continue
        signature = tuple(
            row.get(k)
            for k in (
                "price_status",
                "price_minor",
                "regular_minor",
                "cut_percent_source",
            )
        )
        if at in seen:
            if seen[at] != signature:
                raise ValueError("Conflicting history states at one UTC timestamp")
            excluded["identical_duplicates"] += 1
            continue
        seen[at] = signature
        rows.append(row)
    rows.sort(key=lambda row: row["event_at_utc"])
    return rows, excluded


def collect(root=ROOT, key=None):
    root = Path(root).resolve()
    contract, scope = load_contract(root)
    key = key or api_key(
        root
    )  # Stop before creating a run or making a history request if absent.
    run_id, started = new_run_id("itad-history"), utc_now()
    folder = root / "data/price-history/runs" / run_id
    (folder / "responses").mkdir(parents=True, exist_ok=False)
    rows, coverage = [], []
    for title in scope:
        item = {
            "app_id": title["app_id"],
            "title": title["title"],
            "identity_status": title["identity_status"],
            "itad_game_id": title["itad_game_id"],
            "sku_status": title["sku_status"],
        }
        if title["identity_status"] != "eligible_app_linked_game_context":
            item.update(
                history_status="not_requested_mapping_unresolved",
                event_count=None,
                earliest_event_at_utc=None,
                latest_event_at_utc=None,
                retrieved_at_utc=None,
            )
            coverage.append(item)
            continue
        try:
            raw = request_history(contract, title["itad_game_id"], key)
            retrieved = utc_now()
            (folder / "responses" / f"{title['app_id']}.json").write_bytes(raw)
            events, exclusions = normalise(raw, title, contract, run_id, retrieved)
            rows.extend(events)
            item.update(
                history_status="returned_events" if events else "no_returned_events",
                event_count=len(events),
                earliest_event_at_utc=events[0]["event_at_utc"] if events else None,
                latest_event_at_utc=events[-1]["event_at_utc"] if events else None,
                retrieved_at_utc=retrieved,
                raw_response_sha256=sha(raw),
                exclusions=exclusions,
            )
        except Exception as exc:
            # Never persist server bodies, request headers, credentials or raw exception text.
            item.update(
                history_status=(
                    "invalid_payload"
                    if isinstance(exc, (ValueError, TypeError, KeyError))
                    else "source_failed"
                ),
                event_count=None,
                earliest_event_at_utc=None,
                latest_event_at_utc=None,
                retrieved_at_utc=utc_now(),
                error_category=type(exc).__name__,
            )
        coverage.append(item)
    atomic_csv(folder / "events.csv", EVENT_FIELDS, rows)
    requested = [
        r
        for r in coverage
        if r["identity_status"] == "eligible_app_linked_game_context"
    ]
    passed = bool(requested) and all(
        r["history_status"] in ("returned_events", "no_returned_events")
        for r in requested
    )
    manifest = {
        "run_id": run_id,
        "schema_version": 1,
        "status": "passed_with_declared_mapping_exclusions" if passed else "failed",
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "contract": contract,
        "source_contract_sha256": sha(canonical(contract)),
        "source_code_sha256": {
            name: sha((Path(__file__).parent / name).read_bytes())
            for name in (
                "price_history.py",
                "acquisition.py",
                "build_model.py",
                "benchmark_portfolio.py",
                "common.py",
            )
        },
        "scope_count": len(scope),
        "eligible_title_count": len(requested),
        "mapping_exclusion_count": len(scope) - len(requested),
        "event_count": len(rows),
        "events_sha256": sha((folder / "events.csv").read_bytes()),
        "raw_response_sha256": {
            p.name: sha(p.read_bytes())
            for p in sorted((folder / "responses").glob("*.json"))
        },
        "title_coverage": coverage,
        "coverage_status": "returned_change_log_only_not_verified_continuous_history",
        "boundary_status": "left_state_unknown; final_state_open_as_of_cutoff; source-removal_breaks_coverage",
    }
    (folder / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    print(
        json.dumps(
            {
                "run_id": run_id,
                "status": manifest["status"],
                "eligible_title_count": len(requested),
                "mapping_exclusion_count": len(scope) - len(requested),
                "event_count": len(rows),
            }
        ),
        flush=True,
    )
    return folder


def episodes(events, as_of):
    """Observed discount-state sequences; never infer a state before the first event."""
    end = instant(as_of)
    result, active, previous = [], None, None
    ordered = sorted(events, key=lambda r: r["event_at_utc"])
    for row in ordered:
        at = instant(row["event_at_utc"])
        if at > end:
            raise ValueError("Episode event exceeds analysis cutoff")
        discounted = (
            row["price_status"] == "available"
            and row["regular_minor"] > 0
            and row["price_minor"] < row["regular_minor"]
        )
        if active and not discounted:
            active.update(
                end_at_utc=at.isoformat(),
                end_status=(
                    "observed_full_price"
                    if row["price_status"] == "available"
                    else "source_unavailable_boundary"
                ),
                duration_days=round(
                    (at - instant(active["start_at_utc"])).total_seconds() / 86400, 6
                ),
            )
            result.append(active)
            active = None
        if discounted:
            signature = (row["price_minor"], row["regular_minor"])
            if active is None:
                start_status = (
                    "first_returned_event_left_censored"
                    if previous is None
                    else (
                        "source_unavailable_left_boundary"
                        if previous["price_status"] != "available"
                        else "observed_state_transition"
                    )
                )
                active = {
                    "app_id": row["app_id"],
                    "start_at_utc": at.isoformat(),
                    "minimum_price_minor": row["price_minor"],
                    "maximum_discount_percent": row["discount_depth_percent"],
                    "distinct_price_state_count": 1,
                    "_signature": signature,
                    "start_status": start_status,
                }
            else:
                active["distinct_price_state_count"] += int(
                    signature != active["_signature"]
                )
                active["_signature"] = signature
                active["minimum_price_minor"] = min(
                    active["minimum_price_minor"], row["price_minor"]
                )
                active["maximum_discount_percent"] = max(
                    active["maximum_discount_percent"], row["discount_depth_percent"]
                )
        previous = row
    if active:
        active.update(
            end_at_utc=None, end_status="open_at_analysis_cutoff", duration_days=None
        )
        result.append(active)
    for episode in result:
        episode.pop("_signature")
        if (
            episode["start_status"] != "observed_state_transition"
            or episode["end_status"] != "observed_full_price"
        ):
            episode["duration_days"] = None
        episode["interpretation"] = (
            "derived_recorded_discount_sequence_not_verified_campaign"
        )
    return result


def admitted_events(root=ROOT):
    root = Path(root).resolve()
    contract, scope = load_contract(root)
    register = json.loads((root / "data/price-history/accepted-runs.json").read_bytes())
    entries = register.get("accepted_runs", [])
    if len(entries) != 1 or entries[0].get("status") != "accepted":
        raise ValueError(
            "One explicitly reviewed history run is required; no analytical output published"
        )
    entry = entries[0]
    parent = root / "data/price-history/runs"
    folder = (parent / entry["run_id"]).resolve()
    if folder.parent != parent.resolve():
        raise ValueError("Accepted history path leaves the intended run directory")
    content = (folder / "manifest.json").read_bytes()
    if sha(content) != entry["manifest_sha256"]:
        raise ValueError("Accepted history manifest hash differs")
    manifest = json.loads(content)
    if (
        manifest["status"] != "passed_with_declared_mapping_exclusions"
        or manifest["schema_version"] != 1
        or manifest["run_id"] != entry["run_id"]
    ):
        raise ValueError("Accepted history run did not pass its source contract")
    if manifest["contract"] != contract or manifest["source_contract_sha256"] != sha(
        canonical(contract)
    ):
        raise ValueError("History source contract differs")
    names = {
        "price_history.py",
        "acquisition.py",
        "build_model.py",
        "benchmark_portfolio.py",
        "common.py",
    }
    if set(manifest["source_code_sha256"]) != names or any(
        sha((Path(__file__).parent / n).read_bytes()) != d
        for n, d in manifest["source_code_sha256"].items()
    ):
        raise ValueError("History processing code differs from collected contract")
    if sha((folder / "events.csv").read_bytes()) != manifest["events_sha256"]:
        raise ValueError("Normalised history events hash differs")
    coverage = {r["app_id"]: r for r in manifest["title_coverage"]}
    if len(coverage) != len(manifest["title_coverage"]) or set(coverage) != {
        t["app_id"] for t in scope
    }:
        raise ValueError("History title coverage differs")
    eligible = [
        t for t in scope if t["identity_status"] == "eligible_app_linked_game_context"
    ]
    files = {f"{t['app_id']}.json" for t in eligible}
    if (
        set(manifest["raw_response_sha256"]) != files
        or {p.name for p in (folder / "responses").iterdir()} != files
    ):
        raise ValueError("Raw history inventory differs")
    if (
        manifest["scope_count"] != len(scope)
        or manifest["eligible_title_count"] != len(eligible)
        or manifest["mapping_exclusion_count"] != len(scope) - len(eligible)
    ):
        raise ValueError("Declared history scope counts differ")
    rows = []
    for title in scope:
        item = coverage[title["app_id"]]
        if (
            item["identity_status"] != title["identity_status"]
            or item["itad_game_id"] != title["itad_game_id"]
            or item["sku_status"] != title["sku_status"]
        ):
            raise ValueError("History identity coverage differs")
        if title not in eligible:
            if (
                item["history_status"] != "not_requested_mapping_unresolved"
                or item["event_count"] is not None
            ):
                raise ValueError("Unresolved identity was admitted")
            continue
        raw = (folder / "responses" / f"{title['app_id']}.json").read_bytes()
        digest = sha(raw)
        if (
            digest != item["raw_response_sha256"]
            or digest != manifest["raw_response_sha256"][f"{title['app_id']}.json"]
        ):
            raise ValueError("Raw history hash differs")
        retrieved = instant(item["retrieved_at_utc"])
        if (
            not instant(manifest["started_at_utc"])
            <= retrieved
            <= instant(manifest["finished_at_utc"])
        ):
            raise ValueError("History retrieval time leaves its run interval")
        events, excluded = normalise(
            raw, title, contract, entry["run_id"], item["retrieved_at_utc"]
        )
        status = "returned_events" if events else "no_returned_events"
        if (
            item["history_status"] != status
            or item["event_count"] != len(events)
            or item["exclusions"] != excluded
            or item["earliest_event_at_utc"]
            != (events[0]["event_at_utc"] if events else None)
            or item["latest_event_at_utc"]
            != (events[-1]["event_at_utc"] if events else None)
        ):
            raise ValueError("History event coverage or interval differs")
        rows.extend(events)
    encoded = io.StringIO(newline="")
    writer = csv.DictWriter(encoded, fieldnames=EVENT_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    if (
        sha(encoded.getvalue().encode()) != manifest["events_sha256"]
        or len(rows) != manifest["event_count"]
    ):
        raise ValueError("Reprocessed raw history differs from admitted events")
    return contract, scope, manifest, rows


def build_analysis(root=ROOT, output_dir=None):
    """Publish price-only context and response coverage; unavailable responses stay NULL."""
    root = Path(root).resolve()
    contract, scope, manifest, events = admitted_events(root)
    _, model_release, _ = verified_inputs(
        root, root / "data/benchmarking-contract.json"
    )
    with (model_release / "fact_steam_observation.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        observations = list(csv.DictReader(handle))
    as_of = instant(contract["as_of_utc"])
    summaries, sequences = [], []
    for title in scope:
        rows = [r for r in events if r["app_id"] == title["app_id"]]
        prices = [r for r in rows if r["price_status"] == "available"]
        derived = episodes(rows, contract["as_of_utc"])
        coverage = next(
            r for r in manifest["title_coverage"] if r["app_id"] == title["app_id"]
        )
        summaries.append(
            {
                "app_id": title["app_id"],
                "title": title["title"],
                "cohort": title["cohort"],
                "itad_game_id": title["itad_game_id"],
                "identity_status": title["identity_status"],
                "history_status": coverage["history_status"],
                "scope_basis": "ITAD_game_Steam_shop_context",
                "sku_status": title["sku_status"],
                "country": "GB",
                "currency": "GBP" if prices else None,
                "shop_id": 61,
                "run_id": manifest["run_id"],
                "since_utc": contract["window_start_utc"],
                "as_of_utc": contract["as_of_utc"],
                "retrieved_at_utc": coverage["retrieved_at_utc"],
                "earliest_event_at_utc": coverage["earliest_event_at_utc"],
                "latest_event_at_utc": coverage["latest_event_at_utc"],
                "returned_event_count": coverage["event_count"],
                "available_price_state_count": (
                    len(prices) if coverage["event_count"] is not None else None
                ),
                "minimum_recorded_price_gbp": (
                    min(r["price_minor"] for r in prices) / 100 if prices else None
                ),
                "maximum_recorded_price_gbp": (
                    max(r["price_minor"] for r in prices) / 100 if prices else None
                ),
                "recorded_discount_sequence_count": len(derived) if prices else None,
                "coverage_status": "returned_log_only_left_state_unknown",
                "commercial_response_status": "unavailable_no_admitted_historical_response_series",
                "causal_uplift_status": "not_identified",
            }
        )
        for i, episode in enumerate(derived, 1):
            start = instant(episode["start_at_utc"])
            closed_end = (
                instant(episode["end_at_utc"]) if episode["end_at_utc"] else None
            )
            observed_end = closed_end or as_of
            source_rows = [
                r for r in observations if int(r["app_id"]) == title["app_id"]
            ]

            def dates(field, lower, upper):
                return len(
                    {
                        instant(r[field]).date()
                        for r in source_rows
                        if lower <= instant(r[field]) < upper
                        and instant(r[field]) <= as_of
                    }
                )

            episode.update(
                sequence_id=f"{title['app_id']}-{i}",
                title=title["title"],
                source_run_id=manifest["run_id"],
                product_basis="ITAD_game_Steam_shop_context_sku_unresolved",
                country="GB",
                currency="GBP",
                shop_id=61,
                pre_player_dates=dates(
                    "current_players_retrieved_at_utc",
                    start - timedelta(days=14),
                    start,
                ),
                during_player_dates=dates(
                    "current_players_retrieved_at_utc", start, observed_end
                ),
                post_player_dates=(
                    dates(
                        "current_players_retrieved_at_utc",
                        closed_end,
                        closed_end + timedelta(days=14),
                    )
                    if closed_end
                    else None
                ),
                pre_review_dates=dates(
                    "steam_reviews_retrieved_at_utc", start - timedelta(days=14), start
                ),
                during_review_dates=dates(
                    "steam_reviews_retrieved_at_utc", start, observed_end
                ),
                post_review_dates=(
                    dates(
                        "steam_reviews_retrieved_at_utc",
                        closed_end,
                        closed_end + timedelta(days=14),
                    )
                    if closed_end
                    else None
                ),
                player_response_change_percent=None,
                review_response_change_per_day=None,
                response_status="unavailable_snapshot_only_unresolved_sku",
                causal_uplift_status="not_identified",
            )
            sequences.append(episode)
    output_dir = Path(output_dir or root / "data/pricing-analysis")
    fingerprint = {
        "source_manifest_sha256": sha(canonical(manifest) + b"\n"),
        "model_manifest_sha256": contract["model_manifest_sha256"],
        "builder_sha256": sha(Path(__file__).read_bytes()),
        "python_version": platform.python_version(),
        "analysis_version": 1,
    }
    release_id = sha(canonical(fingerprint))[:16]
    release = output_dir / "releases" / release_id
    release.parent.mkdir(parents=True, exist_ok=True)
    # Prepare all deterministic bytes in memory, then write only the chosen release.
    outputs = {}
    fields_sequences = [
        "app_id",
        "start_at_utc",
        "minimum_price_minor",
        "maximum_discount_percent",
        "distinct_price_state_count",
        "start_status",
        "end_at_utc",
        "end_status",
        "duration_days",
        "interpretation",
        "sequence_id",
        "title",
        "source_run_id",
        "product_basis",
        "country",
        "currency",
        "shop_id",
        "pre_player_dates",
        "during_player_dates",
        "post_player_dates",
        "pre_review_dates",
        "during_review_dates",
        "post_review_dates",
        "player_response_change_percent",
        "review_response_change_per_day",
        "response_status",
        "causal_uplift_status",
    ]
    for name, rows, fields in (
        ("price_history_coverage.csv", summaries, list(summaries[0])),
        ("recorded_price_events.csv", events, EVENT_FIELDS),
        ("recorded_discount_sequences.csv", sequences, fields_sequences),
    ):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        outputs[name] = stream.getvalue().encode()
    receipt = {
        "release_id": release_id,
        "status": "passed_price_context_only",
        **fingerprint,
        "row_counts": {
            "price_history_coverage": len(summaries),
            "recorded_price_events": len(events),
            "recorded_discount_sequences": len(sequences),
        },
        "output_csv_sha256": {n: sha(b) for n, b in outputs.items()},
        "interpretation": "No response uplift or exact-SKU/campaign claim; raw source provenance and gaps retained.",
    }
    outputs["build-manifest.json"] = canonical(receipt) + b"\n"
    if release.exists():
        if any((release / n).read_bytes() != b for n, b in outputs.items()):
            raise ValueError(
                "Existing price-analysis release differs; pointer unchanged"
            )
    else:
        stage = Path(tempfile.mkdtemp(prefix=".building-price-", dir=release.parent))
        try:
            if (
                stage.resolve().parent != release.parent.resolve()
                or release.resolve().parent != release.parent.resolve()
            ):
                raise RuntimeError(
                    "Price publication leaves the intended releases directory"
                )
            for n, b in outputs.items():
                (stage / n).write_bytes(b)
            os.replace(stage, release)
        finally:
            if stage.exists():
                if (
                    stage.resolve().parent != release.parent.resolve()
                    or not stage.name.startswith(".building-price-")
                ):
                    raise RuntimeError("Unsafe price-analysis staging cleanup")
                shutil.rmtree(stage)
    output_dir.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=output_dir, suffix=".tmp")
    with os.fdopen(fd, "wb") as handle:
        handle.write(
            canonical(
                {
                    "release_id": release_id,
                    "path": f"releases/{release_id}",
                    "status": "passed_price_context_only",
                }
            )
            + b"\n"
        )
    os.replace(temporary, output_dir / "current.json")
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analyse",
        action="store_true",
        help="Build from the single explicitly accepted history run",
    )
    arguments = parser.parse_args()
    if arguments.analyse:
        build_analysis()
        raise SystemExit(0)
    folder = collect()
    manifest = json.loads((folder / "manifest.json").read_bytes())
    if manifest["status"] == "failed":
        raise SystemExit(
            "History coverage failed; diagnostics retained and no analytical release published"
        )
