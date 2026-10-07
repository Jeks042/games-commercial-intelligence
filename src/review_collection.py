"""Collect dated review cohorts; preserve private text and publish coded features."""

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import time
import unicodedata

import requests

from acquisition import new_run_id, utc_now
from benchmark_portfolio import verified_inputs
from build_model import ROOT, canonical, sha

THEMES = {
    "performance": [
        "crash",
        "crashes",
        "crashing",
        "stutter",
        "stuttering",
        "fps",
        "framerate",
        "optimization",
        "optimisation",
        "lag",
        "laggy",
    ],
    "value": ["price", "expensive", "worth", "refund", "sale", "discount"],
    "content": ["story", "content", "campaign", "missions", "characters", "world"],
    "controls": ["controls", "controller", "keyboard", "mouse", "steering", "wheel"],
    "difficulty": [
        "difficulty",
        "difficult",
        "hard",
        "easy",
        "boss",
        "bosses",
        "challenging",
    ],
    "updates": ["patch", "patches", "update", "updates", "fixed", "bug", "bugs"],
}


def integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"Invalid {name}")
    return value


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Invalid UTC timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("UTC timestamp required")
    return parsed


def inputs(root=ROOT):
    root = Path(root).resolve()
    benchmark, release, _ = verified_inputs(
        root, root / "data/benchmarking-contract.json"
    )
    contract = json.loads(
        (root / "data/player-reviews/source-contract.json").read_bytes()
    )
    expected_query = {
        "filter": 1,
        "languages": ["english"],
        "review_type": 0,
        "purchase_type": 1,
        "filter_offtopic_activity": True,
        "display_language": "english",
    }
    if (
        contract["version"] != 1
        or contract["endpoint"]
        != "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
        or contract["query"] != expected_query
        or contract["scope"] != "pinned_model_portfolio_only"
    ):
        raise ValueError("Review source contract differs")
    for field, expected in [
        ("window_days", 30),
        ("maximum_pages_per_window", 5),
        ("page_size", 100),
        ("minimum_comparison_reviews_per_window", 30),
        ("minimum_words_for_theme_screening", 5),
    ]:
        if type(contract[field]) is not int or contract[field] != expected:
            raise ValueError("Review coverage policy differs")
    timestamp(contract["as_of_utc"])
    with (release / "dim_title.csv").open(newline="", encoding="utf-8") as handle:
        scope = [r for r in csv.DictReader(handle) if r["cohort"] == "portfolio"]
    if len(scope) != 12 or len({r["app_id"] for r in scope}) != 12:
        raise ValueError("Pinned review scope differs")
    return contract, scope, benchmark["model_manifest_sha256"]


def windows(contract):
    cutoff = int(timestamp(contract["as_of_utc"]).timestamp())
    span = contract["window_days"] * 86400
    return {
        "recent": (cutoff - span + 1, cutoff),
        "prior": (cutoff - 2 * span + 1, cutoff - span),
    }


def query(contract, app, cursor="*", bounds=None, summary=False):
    params = {
        **contract["query"],
        "appid": int(app),
        "num_per_page": 1 if summary else contract["page_size"],
        "cursor": cursor,
    }
    if bounds:
        params.update(date_range_start=bounds[0], date_range_end=bounds[1])
    return params


def fetch(endpoint, params):
    for attempt in range(3):
        time.sleep(1.1)
        try:
            response = requests.get(
                endpoint,
                params={"input_json": json.dumps(params)},
                headers={"User-Agent": "games-commercial-intelligence/3.0"},
                timeout=(10, 30),
            )
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
            response.raise_for_status()
            return response.content
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise RuntimeError("Review source connection failed") from None
        except requests.HTTPError:
            raise RuntimeError("Review source HTTP failure") from None
    raise RuntimeError("Review source retry budget exhausted")


def page(raw, first, size):
    payload = json.loads(raw)
    response = payload.get("response")
    if not isinstance(response, dict):
        raise ValueError("Missing review page")
    summary = response.get("query_summary")
    if (
        "reviews" not in response
        and isinstance(summary, dict)
        and type(summary.get("num_reviews")) is int
        and summary["num_reviews"] == 0
    ):
        response["reviews"] = []
    if not isinstance(response.get("reviews"), list):
        raise ValueError("Missing review page")
    records = response["reviews"]
    if (
        not isinstance(summary, dict)
        or integer(summary.get("num_reviews"), "page count") != len(records)
        or len(records) > size
    ):
        raise ValueError("Review page count differs")
    total = integer(response.get("total_matching"), "matching count")
    if first:
        positive = integer(summary.get("total_positive"), "positive count")
        negative = integer(summary.get("total_negative"), "negative count")
        if positive + negative != integer(
            summary.get("total_reviews"), "summary count"
        ):
            raise ValueError("Review summary does not reconcile")
    cursor = response.get("cursor")
    if not isinstance(cursor, str):
        raise ValueError("Missing pagination cursor")
    return response, total, cursor


def clean(text):
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\[/?[a-z][^\]]*\]", " ", text, flags=re.I)
    text = re.sub(r"https?://\S+", " ", text, flags=re.I)
    return " ".join(text.casefold().split())


def feature(review, app, window, bounds, retrieved):
    review_id = review.get("recommendationid")
    if not isinstance(review_id, str) or not review_id.isdigit():
        raise ValueError("Invalid review identity")
    if review.get("language") != "english" or not isinstance(review.get("review"), str):
        raise ValueError("Review language or text differs")
    created = integer(review.get("timestamp_created"), "creation timestamp")
    updated = integer(review.get("timestamp_updated"), "update timestamp")
    if not bounds[0] <= created <= bounds[1] or not created <= updated <= int(
        timestamp(retrieved).timestamp()
    ):
        raise ValueError("Review timestamp outside declared coverage")
    flags = [
        "voted_up",
        "steam_purchase",
        "received_for_free",
        "written_during_early_access",
        "refunded",
    ]
    if any(type(review.get(k)) is not bool for k in flags):
        raise ValueError("Review flags must be booleans")
    text = clean(review["review"])
    return {
        "app_id": int(app),
        "window": window,
        "review_key": sha(f"{app}:{review_id}".encode()),
        "created_date_utc": datetime.fromtimestamp(created, timezone.utc)
        .date()
        .isoformat(),
        "updated_date_utc": datetime.fromtimestamp(updated, timezone.utc)
        .date()
        .isoformat(),
        "updated_after_creation_window_end": updated > bounds[1],
        "text_sha256": sha(review["review"].encode()),
        "clean_word_count": len(text.split()),
        **{k: review[k] for k in flags},
        "theme_matches": {
            theme: [
                term
                for term in terms
                if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text)
            ]
            for theme, terms in THEMES.items()
        },
    }


def project_window(pages, app, window, bounds, contract):
    """Replay pagination and classify the exact returned private bytes."""
    rows, seen, cursors, counts = [], set(), {"*"}, []
    expected_cursor, finished = "*", False
    first_total, summary = None, None
    last_created = bounds[1]
    for index, item in enumerate(pages):
        if finished or item["query"] != query(contract, app, expected_cursor, bounds):
            raise ValueError("Review page chain differs")
        response, total, next_cursor = page(
            item["raw"], index == 0, contract["page_size"]
        )
        if index == 0:
            first_total, summary = total, response["query_summary"]
        counts.append(total)
        for review in response["reviews"]:
            row = feature(review, app, window, bounds, item["retrieved_at_utc"])
            if row["review_key"] in seen:
                raise ValueError("Duplicate review across pages")
            if review["timestamp_created"] > last_created:
                raise ValueError("Review creation order differs")
            last_created = review["timestamp_created"]
            seen.add(row["review_key"])
            rows.append(row)
        finished = not response["reviews"]
        if not finished and next_cursor in cursors:
            raise ValueError("Review cursor did not advance")
        expected_cursor = next_cursor
        cursors.add(next_cursor)
    if not pages or len(pages) > contract["maximum_pages_per_window"]:
        raise ValueError("Invalid review page budget")
    if not finished and len(pages) < contract["maximum_pages_per_window"]:
        raise ValueError("Review pagination stopped before the declared budget")
    complete = finished and len(set(counts)) == 1 and len(rows) == first_total
    state = (
        "complete_returned_creation_cohort"
        if complete
        else (
            "inconsistent_source_counts"
            if len(set(counts)) > 1 or finished
            else "capped_latest_creation_sample"
        )
    )
    return rows, {
        "app_id": int(app),
        "window": window,
        "start_timestamp": bounds[0],
        "end_timestamp": bounds[1],
        "returned_review_count": len(rows),
        "initial_total_matching": first_total,
        "total_matching_observations": counts,
        "pages": len(pages),
        "empty_terminal_page": finished,
        "coverage_status": state,
        "first_page_summary": summary,
    }


def collect(root=ROOT):
    root = Path(root).resolve()
    contract, scope, model_sha = inputs(root)
    started = utc_now()
    if timestamp(contract["as_of_utc"]) > timestamp(started):
        raise ValueError("Review cutoff is in the future")
    run_id = new_run_id("steam-reviews")
    private = root / "data/raw/player-reviews" / run_id
    public = root / "data/player-reviews/runs" / run_id
    private.mkdir(parents=True, exist_ok=False)
    public.mkdir(parents=True, exist_ok=False)
    manifest = {
        "run_id": run_id,
        "status": "collecting",
        "started_at_utc": started,
        "contract_sha256": sha(canonical(contract)),
        "collector_sha256": sha(Path(__file__).read_bytes()),
        "model_manifest_sha256": model_sha,
        "scope": [{"app_id": int(r["app_id"]), "title": r["title"]} for r in scope],
        "private_raw_inventory": [],
        "window_coverage": [],
        "lifetime_summaries": [],
        "raw_storage": "ignored_private_archive_not_in_public_git",
    }
    all_features = []
    try:
        for title in scope:
            app = title["app_id"]
            params = query(contract, app, summary=True)
            raw = fetch(contract["endpoint"], params)
            at = utc_now()
            name = f"{app}-lifetime.json"
            (private / name).write_bytes(raw)
            manifest["private_raw_inventory"].append(
                {
                    "file": name,
                    "query": params,
                    "retrieved_at_utc": at,
                    "sha256": sha(raw),
                }
            )
            response, total, _ = page(raw, True, 1)
            manifest["lifetime_summaries"].append(
                {
                    "app_id": int(app),
                    "retrieved_at_utc": at,
                    "total_matching": total,
                    "summary": response["query_summary"],
                }
            )
            for window, bounds in windows(contract).items():
                cursor, pages, seen = "*", [], {"*"}
                for index in range(contract["maximum_pages_per_window"]):
                    params = query(contract, app, cursor, bounds)
                    raw = fetch(contract["endpoint"], params)
                    at = utc_now()
                    name = f"{app}-{window}-{index + 1}.json"
                    (private / name).write_bytes(raw)
                    manifest["private_raw_inventory"].append(
                        {
                            "file": name,
                            "query": params,
                            "retrieved_at_utc": at,
                            "sha256": sha(raw),
                        }
                    )
                    pages.append({"raw": raw, "query": params, "retrieved_at_utc": at})
                    response, _, next_cursor = page(
                        raw, index == 0, contract["page_size"]
                    )
                    if not response["reviews"]:
                        break
                    if next_cursor in seen:
                        raise ValueError("Review cursor did not advance")
                    seen.add(next_cursor)
                    cursor = next_cursor
                rows, coverage = project_window(pages, app, window, bounds, contract)
                all_features.extend(rows)
                manifest["window_coverage"].append(coverage)
            print(f"Collected review cohorts: {title['title']}", flush=True)
        features = (
            canonical(
                sorted(
                    all_features,
                    key=lambda r: (r["app_id"], r["window"], r["review_key"]),
                )
            )
            + b"\n"
        )
        (public / "features.json").write_bytes(features)
        manifest.update(
            status="passed_unreviewed",
            features_sha256=sha(features),
            feature_count=len(all_features),
            finished_at_utc=utc_now(),
        )
    except Exception as error:
        manifest.update(
            status="failed",
            failure_type=type(error).__name__,
            finished_at_utc=utc_now(),
        )
        raise
    finally:
        (public / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    print(
        json.dumps(
            {
                "run_id": run_id,
                "status": manifest["status"],
                "feature_count": len(all_features),
            }
        ),
        flush=True,
    )
    return public


def verify_private(run, root=ROOT):
    """Verify and replay the locally retained raw archive before source admission."""
    root, run = Path(root).resolve(), Path(run).resolve()
    if run.parent != root / "data/player-reviews/runs":
        raise ValueError("Review run outside intended source directory")
    manifest = json.loads((run / "manifest.json").read_bytes())
    contract, scope, model_sha = inputs(root)
    if (
        manifest["status"] != "passed_unreviewed"
        or manifest["run_id"] != run.name
        or manifest["contract_sha256"] != sha(canonical(contract))
        or manifest["collector_sha256"] != sha(Path(__file__).read_bytes())
        or manifest["model_manifest_sha256"] != model_sha
    ):
        raise ValueError("Review source manifest binding differs")
    expected_scope = [{"app_id": int(r["app_id"]), "title": r["title"]} for r in scope]
    if manifest["scope"] != expected_scope:
        raise ValueError("Review run scope differs")
    private = root / "data/raw/player-reviews" / run.name
    items = manifest["private_raw_inventory"]
    names = [r["file"] for r in items]
    if len(names) != len(set(names)) or set(names) != {
        p.name for p in private.iterdir()
    }:
        raise ValueError("Private source inventory differs")
    by_name = {}
    for item in items:
        path = (private / item["file"]).resolve()
        if path.parent != private.resolve() or sha(path.read_bytes()) != item["sha256"]:
            raise ValueError("Private review hash or path differs")
        if (
            not timestamp(manifest["started_at_utc"])
            <= timestamp(item["retrieved_at_utc"])
            <= timestamp(manifest["finished_at_utc"])
        ):
            raise ValueError("Review retrieval time outside run")
        by_name[item["file"]] = {**item, "raw": path.read_bytes()}
    features, covers, lifetimes, consumed = [], [], [], set()
    for title in scope:
        app = title["app_id"]
        item = by_name[f"{app}-lifetime.json"]
        consumed.add(item["file"])
        if item["query"] != query(contract, app, summary=True):
            raise ValueError("Lifetime query differs")
        response, total, _ = page(item["raw"], True, 1)
        lifetimes.append(
            {
                "app_id": int(app),
                "retrieved_at_utc": item["retrieved_at_utc"],
                "total_matching": total,
                "summary": response["query_summary"],
            }
        )
        for window, bounds in windows(contract).items():
            pages = [
                by_name[f"{app}-{window}-{i}.json"]
                for i in range(1, contract["maximum_pages_per_window"] + 1)
                if f"{app}-{window}-{i}.json" in by_name
            ]
            rows, coverage = project_window(pages, app, window, bounds, contract)
            consumed.update(p["file"] for p in pages)
            features.extend(rows)
            covers.append(coverage)
    encoded = (
        canonical(
            sorted(features, key=lambda r: (r["app_id"], r["window"], r["review_key"]))
        )
        + b"\n"
    )
    if consumed != set(names):
        raise ValueError("Unexpected private source file")
    if (
        encoded != (run / "features.json").read_bytes()
        or sha(encoded) != manifest["features_sha256"]
        or len(features) != manifest["feature_count"]
        or covers != manifest["window_coverage"]
        or lifetimes != manifest["lifetime_summaries"]
    ):
        raise ValueError("Review source replay differs")
    return manifest


if __name__ == "__main__":
    collect()
