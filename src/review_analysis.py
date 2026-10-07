"""Build bounded player-feedback context from explicitly admitted coded features."""

import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import platform
import re
import tempfile

from build_model import ROOT, canonical, sha
from review_collection import THEMES, inputs, integer, windows


def audit_selection(features, minimum_words=5):
    chosen = {}
    for row in features:
        if row["clean_word_count"] < minimum_words:
            continue
        key = (
            row["app_id"],
            row["window"],
            row["voted_up"],
            any(row["theme_matches"].values()),
        )
        if key not in chosen or row["review_key"] < chosen[key]["review_key"]:
            chosen[key] = row
    return [
        {
            "app_id": key[0],
            "window": key[1],
            "voted_up": key[2],
            "has_theme_match": key[3],
            "review_key": row["review_key"],
            "theme_matches": row["theme_matches"],
            "text_sha256": row["text_sha256"],
        }
        for key, row in sorted(chosen.items())
    ]


def validate_features(features, manifest, contract):
    scope = {r["app_id"] for r in manifest["scope"]}
    bounds = windows(contract)
    expected = {
        "app_id",
        "window",
        "review_key",
        "created_date_utc",
        "updated_date_utc",
        "updated_after_creation_window_end",
        "text_sha256",
        "clean_word_count",
        "voted_up",
        "steam_purchase",
        "received_for_free",
        "written_during_early_access",
        "refunded",
        "theme_matches",
    }
    flags = [
        "updated_after_creation_window_end",
        "voted_up",
        "steam_purchase",
        "received_for_free",
        "written_during_early_access",
        "refunded",
    ]
    seen = set()
    if not isinstance(features, list):
        raise ValueError("Feature list required")
    for row in features:
        if (
            not isinstance(row, dict)
            or set(row) != expected
            or type(row["app_id"]) is not int
            or row["app_id"] not in scope
            or row["window"] not in bounds
        ):
            raise ValueError("Review feature schema or scope differs")
        integer(row["clean_word_count"], "word count")
        if any(type(row[k]) is not bool for k in flags):
            raise ValueError("Invalid feature flags")
        if any(
            not isinstance(row[k], str) or not re.fullmatch(r"[0-9a-f]{64}", row[k])
            for k in ["review_key", "text_sha256"]
        ):
            raise ValueError("Invalid feature hashes")
        if row["review_key"] in seen:
            raise ValueError("Duplicate coded review")
        seen.add(row["review_key"])
        created = datetime.strptime(row["created_date_utc"], "%Y-%m-%d").date()
        updated = datetime.strptime(row["updated_date_utc"], "%Y-%m-%d").date()
        low, high = bounds[row["window"]]
        if (
            not datetime.fromtimestamp(low, timezone.utc).date()
            <= created
            <= datetime.fromtimestamp(high, timezone.utc).date()
            or updated < created
        ):
            raise ValueError("Feature date outside declared cohort")
        if not isinstance(row["theme_matches"], dict) or set(
            row["theme_matches"]
        ) != set(THEMES):
            raise ValueError("Theme inventory differs")
        for theme, matches in row["theme_matches"].items():
            if (
                not isinstance(matches, list)
                or len(matches) != len(set(matches))
                or matches != [term for term in THEMES[theme] if term in matches]
            ):
                raise ValueError("Theme rule matches differ")
    expected_pairs = {(app, window) for app in scope for window in bounds}
    coverage = manifest["window_coverage"]
    if (
        len(coverage) != len(expected_pairs)
        or {(r["app_id"], r["window"]) for r in coverage} != expected_pairs
    ):
        raise ValueError("Review coverage inventory differs")
    for entry in coverage:
        selected = [
            r
            for r in features
            if (r["app_id"], r["window"]) == (entry["app_id"], entry["window"])
        ]
        integer(entry["returned_review_count"], "coverage count")
        integer(entry["initial_total_matching"], "matching count")
        if (
            len(selected) != entry["returned_review_count"]
            or (entry["start_timestamp"], entry["end_timestamp"])
            != bounds[entry["window"]]
        ):
            raise ValueError("Review feature coverage count or boundaries differ")
        state = entry["coverage_status"]
        observations = entry["total_matching_observations"]
        if (
            state
            not in [
                "complete_returned_creation_cohort",
                "inconsistent_source_counts",
                "capped_latest_creation_sample",
            ]
            or len(observations) != entry["pages"]
            or not 1 <= entry["pages"] <= contract["maximum_pages_per_window"]
        ):
            raise ValueError("Review pagination coverage differs")
        for count in observations:
            integer(count, "page matching count")
        complete = (
            entry["empty_terminal_page"]
            and len(set(observations)) == 1
            and len(selected) == entry["initial_total_matching"]
        )
        expected_state = (
            "complete_returned_creation_cohort"
            if complete
            else (
                "inconsistent_source_counts"
                if len(set(observations)) > 1 or entry["empty_terminal_page"]
                else "capped_latest_creation_sample"
            )
        )
        if (
            state != expected_state
            or observations[0] != entry["initial_total_matching"]
        ):
            raise ValueError("Review completeness classification differs")
        if (
            state == "capped_latest_creation_sample"
            and entry["pages"] != contract["maximum_pages_per_window"]
        ):
            raise ValueError("Review cap not reached")
    lifetime = manifest["lifetime_summaries"]
    if (
        len(lifetime) != len(scope)
        or {r["app_id"] for r in lifetime} != scope
        or len(features) != manifest["feature_count"]
    ):
        raise ValueError("Review summary or feature inventory differs")
    for entry in lifetime:
        summary = entry["summary"]
        positive, negative, total = [
            integer(summary[k], k)
            for k in ["total_positive", "total_negative", "total_reviews"]
        ]
        if positive + negative != total:
            raise ValueError("Lifetime summary counts differ")


def admitted(root=ROOT):
    root = Path(root).resolve()
    contract, scope, model_sha = inputs(root)
    registry = json.loads(
        (root / "data/player-reviews/accepted-runs.json").read_bytes()
    )
    entries = registry.get("accepted_runs")
    if (
        not isinstance(entries, list)
        or len(entries) != 1
        or entries[0].get("status") != "accepted"
    ):
        raise ValueError("One explicitly reviewed coded-review run is required")
    entry = entries[0]
    run = (root / "data/player-reviews/runs" / entry["run_id"]).resolve()
    if run.parent != root / "data/player-reviews/runs":
        raise ValueError("Review run path differs")
    raw_manifest = (run / "manifest.json").read_bytes()
    manifest = json.loads(raw_manifest)
    if (
        sha(raw_manifest) != entry["manifest_sha256"]
        or manifest["run_id"] != run.name
        or manifest["status"] != "passed_unreviewed"
        or manifest["contract_sha256"] != sha(canonical(contract))
        or manifest["model_manifest_sha256"] != model_sha
        or manifest["collector_sha256"]
        != sha(Path(__file__).with_name("review_collection.py").read_bytes())
    ):
        raise ValueError("Admitted review source binding differs")
    if manifest["scope"] != [
        {"app_id": int(r["app_id"]), "title": r["title"]} for r in scope
    ]:
        raise ValueError("Admitted review scope differs")
    raw_features = (run / "features.json").read_bytes()
    if sha(raw_features) != manifest["features_sha256"]:
        raise ValueError("Review features hash differs")
    features = json.loads(raw_features)
    validate_features(features, manifest, contract)
    proof = (root / entry["private_replay_verification_path"]).resolve()
    if (
        not proof.is_relative_to(root / "data/player-reviews/verification")
        or sha(proof.read_bytes()) != entry["private_replay_verification_sha256"]
    ):
        raise ValueError("Private replay verification binding differs")
    evidence = json.loads(proof.read_bytes())
    if (
        evidence["run_id"] != run.name
        or evidence["manifest_sha256"] != sha(raw_manifest)
        or evidence["features_sha256"] != sha(raw_features)
        or evidence["raw_to_features_replay"] != "byte_identical"
        or evidence["private_raw_files_verified"]
        != len(manifest["private_raw_inventory"])
    ):
        raise ValueError("Private replay evidence differs")
    return contract, manifest, features


def analyse(contract, manifest, features):
    cohorts, themes, contrasts = [], [], []
    covers = {(r["app_id"], r["window"]): r for r in manifest["window_coverage"]}
    lifetime = {r["app_id"]: r for r in manifest["lifetime_summaries"]}
    cohort_by_pair = {}
    for title in manifest["scope"]:
        app = title["app_id"]
        for window in ["prior", "recent"]:
            selected = [
                r for r in features if r["app_id"] == app and r["window"] == window
            ]
            n = len(selected)
            positive = sum(r["voted_up"] for r in selected)
            cover = covers[(app, window)]
            screenable = [
                r
                for r in selected
                if r["clean_word_count"]
                >= contract["minimum_words_for_theme_screening"]
            ]
            row = {
                "app_id": app,
                "title": title["title"],
                "creation_cohort": window,
                "creation_start_utc": datetime.fromtimestamp(
                    cover["start_timestamp"], timezone.utc
                ).isoformat(),
                "creation_end_utc": datetime.fromtimestamp(
                    cover["end_timestamp"], timezone.utc
                ).isoformat(),
                "returned_review_count": n,
                "initial_source_matching_count": cover["initial_total_matching"],
                "coverage_status": cover["coverage_status"],
                "positive_recommendations": positive,
                "negative_recommendations": n - positive,
                "observed_recommendation_percent": (
                    round(100 * positive / n, 4) if n else None
                ),
                "screenable_text_count": len(screenable),
                "short_text_count": n - len(screenable),
                "edited_after_creation_window_count": sum(
                    r["updated_after_creation_window_end"] for r in selected
                ),
                "steam_purchase_count": sum(r["steam_purchase"] for r in selected),
                "received_for_free_count": sum(
                    r["received_for_free"] for r in selected
                ),
                "early_access_count": sum(
                    r["written_during_early_access"] for r in selected
                ),
                "refunded_flag_count": sum(r["refunded"] for r in selected),
                "interpretation": "retrieved_creation_cohort_state_not_historical_recommendation_or_text_snapshot",
            }
            cohorts.append(row)
            cohort_by_pair[(app, window)] = row
            for theme in THEMES:
                matched = [r for r in screenable if r["theme_matches"][theme]]
                themes.append(
                    {
                        "app_id": app,
                        "title": title["title"],
                        "creation_cohort": window,
                        "theme": theme,
                        "screenable_text_count": len(screenable),
                        "keyword_matched_review_count": len(matched),
                        "keyword_match_percent": (
                            round(100 * len(matched) / len(screenable), 4)
                            if screenable
                            else None
                        ),
                        "matched_positive_recommendations": sum(
                            r["voted_up"] for r in matched
                        ),
                        "matched_negative_recommendations": sum(
                            not r["voted_up"] for r in matched
                        ),
                        "coverage_status": cover["coverage_status"],
                        "classification_status": "provisional_keyword_screening_not_aspect_sentiment",
                        "confirmed_concern_prevalence_percent": None,
                        "theme_change_percent": None,
                    }
                )
        prior, recent = [cohort_by_pair[(app, w)] for w in ["prior", "recent"]]
        ready = all(
            r["coverage_status"] == "complete_returned_creation_cohort"
            and r["returned_review_count"]
            >= contract["minimum_comparison_reviews_per_window"]
            for r in [prior, recent]
        )
        summary = lifetime[app]["summary"]
        contrasts.append(
            {
                "app_id": app,
                "title": title["title"],
                "prior_review_count": prior["returned_review_count"],
                "recent_review_count": recent["returned_review_count"],
                "prior_coverage_status": prior["coverage_status"],
                "recent_coverage_status": recent["coverage_status"],
                "recent_minus_prior_recommendation_pp": (
                    round(
                        recent["observed_recommendation_percent"]
                        - prior["observed_recommendation_percent"],
                        4,
                    )
                    if ready
                    else None
                ),
                "comparison_status": (
                    "available_descriptive_creation_cohort_difference"
                    if ready
                    else "unavailable_incomplete_or_below_30_reviews_per_cohort"
                ),
                "english_lifetime_total_at_retrieval": summary["total_reviews"],
                "english_lifetime_positive_percent_at_retrieval": (
                    round(100 * summary["total_positive"] / summary["total_reviews"], 4)
                    if summary["total_reviews"]
                    else None
                ),
                "lifetime_summary_retrieved_at_utc": lifetime[app]["retrieved_at_utc"],
                "lifetime_theme_change_percent": None,
                "commercial_response_status": "unavailable_no_linked_sales_conversion_or_campaign_evidence",
                "causal_effect_status": "not_identified",
                "comparability_limit": "self_selected_English_creation_cohorts_current_mutable_text_and_votes_composition_unadjusted",
            }
        )
    return cohorts, themes, contrasts


def encode(rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def build(root=ROOT):
    root = Path(root).resolve()
    contract, manifest, features = admitted(root)
    cohorts, themes, contrasts = analyse(contract, manifest, features)
    selection = audit_selection(features, contract["minimum_words_for_theme_screening"])
    output = {
        "cohort_review_context.csv": encode(cohorts),
        "theme_screening_context.csv": encode(themes),
        "title_review_context.csv": encode(contrasts),
        "audit_selection.json": canonical(selection) + b"\n",
    }
    fingerprint = {
        "source_manifest_sha256": sha(canonical(manifest) + b"\n"),
        "contract_sha256": sha(canonical(contract)),
        "builder_sha256": sha(Path(__file__).read_bytes()),
        "python_version": platform.python_version(),
    }
    release_id = sha(canonical(fingerprint))[:16]
    receipt = {
        **fingerprint,
        "release_id": release_id,
        "status": "passed_bounded_coded_review_context_only",
        "source_run_id": manifest["run_id"],
        "output_sha256": {name: sha(raw) for name, raw in output.items()},
        "row_counts": {
            "cohort_review_context": len(cohorts),
            "theme_screening_context": len(themes),
            "title_review_context": len(contrasts),
            "audit_selection": len(selection),
        },
        "reproduction": "Public coded-feature analytical rebuild; private immutable raw archive required for source-to-feature replay.",
        "theme_interpretation": "Provisional keyword matches; confirmed aspect sentiment and population concern prevalence unavailable.",
    }
    output["build-manifest.json"] = canonical(receipt) + b"\n"
    releases = root / "data/review-analysis/releases"
    release = releases / release_id
    releases.mkdir(parents=True, exist_ok=True)
    if release.exists():
        if {p.name for p in release.iterdir()} != set(output) or any(
            (release / name).read_bytes() != raw for name, raw in output.items()
        ):
            raise ValueError("Existing review release differs; pointer unchanged")
    else:
        stage = Path(tempfile.mkdtemp(prefix=".building-reviews-", dir=releases))
        for name, raw in output.items():
            (stage / name).write_bytes(raw)
        os.replace(stage, release)
    fd, temporary = tempfile.mkstemp(dir=releases.parent, suffix=".tmp")
    with os.fdopen(fd, "wb") as handle:
        handle.write(
            canonical(
                {
                    "release_id": release_id,
                    "path": "releases/" + release_id,
                    "status": receipt["status"],
                }
            )
            + b"\n"
        )
    os.replace(temporary, releases.parent / "current.json")
    print(
        json.dumps({"release_id": release_id, "row_counts": receipt["row_counts"]}),
        flush=True,
    )
    return release


if __name__ == "__main__":
    build()
