"""Separate, privacy-projected context diagnostics; original source is immutable."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata

from build_model import ROOT, canonical, sha
from review_analysis import admitted, encode
from review_collection import THEMES, clean, verify_private

BASE = "data/review-refinement"
LANGUAGES = {
    "short_text_not_assessed",
    "no_letters_language_unverified",
    "non_latin_letters_present_language_unverified",
    "latin_letters_only_language_unverified",
}


def method(root):
    raw = (root / BASE / "method-v1.json").read_bytes()
    policy = json.loads(raw)
    if policy["version"] != 1 or policy["minimum_words"] != 5:
        raise ValueError("Unsupported refinement policy")
    ids = set()
    for rule in policy["exclusions"]:
        if (
            set(rule) != {"id", "theme", "term", "pattern"}
            or rule["id"] in ids
            or rule["term"] not in THEMES[rule["theme"]]
        ):
            raise ValueError("Invalid context rule")
        re.compile(rule["pattern"])
        ids.add(rule["id"])
    if (
        policy["fresh_audit"]["strata"]
        != [
            "app_id",
            "window",
            "voted_up",
            "original_any_match",
            "retained_any_match",
            "any_context_exclusion",
            "language_risk",
        ]
        or policy["fresh_audit"]["exclude_all_development_review_keys"] is not True
    ):
        raise ValueError("Audit protocol differs")
    development = root / policy["development_selection_path"]
    if (
        development.resolve()
        != (root / "data/player-reviews/audit/selection-20261007.json").resolve()
    ):
        raise ValueError("Development selection path differs")
    return policy, raw, development.read_bytes()


def classify(text, policy):
    text = clean(text)
    letters = [c for c in text if c.isalpha()]
    if len(text.split()) < policy["minimum_words"]:
        language = "short_text_not_assessed"
    elif not letters:
        language = "no_letters_language_unverified"
    elif any("LATIN" not in unicodedata.name(c, "") for c in letters):
        language = "non_latin_letters_present_language_unverified"
    else:
        language = "latin_letters_only_language_unverified"
    retained, excluded = {}, {}
    for theme, terms in THEMES.items():
        retained[theme], excluded[theme] = [], []
        for term in terms:
            occurrences = list(
                re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text)
            )
            rules = [
                r
                for r in policy["exclusions"]
                if (r["theme"], r["term"]) == (theme, term)
            ]
            masks = [
                (m.start(), m.end(), r["id"])
                for r in rules
                for m in re.finditer(r["pattern"], text)
            ]
            survivors = False
            hits = set()
            for occurrence in occurrences:
                reasons = {
                    rid
                    for start, end, rid in masks
                    if start <= occurrence.start() and occurrence.end() <= end
                }
                if reasons:
                    hits.update(reasons)
                else:
                    survivors = True
            if survivors:
                retained[theme].append(term)
            excluded[theme].extend(sorted(hits))
        excluded[theme] = sorted(set(excluded[theme]))
    return language, retained, excluded


def project(original, text, policy):
    if sha(text.encode()) != original["text_sha256"]:
        raise ValueError("Text fingerprint differs")
    language, retained, excluded = classify(text, policy)
    return {
        "review_key": original["review_key"],
        "text_sha256": original["text_sha256"],
        "language_risk": language,
        "retained_theme_terms": retained,
        "excluded_context_rules": excluded,
    }


def select_audit(features, coded, policy, development):
    excluded = {r["review_key"] for r in json.loads(development)}
    by_key = {r["review_key"]: r for r in features}
    chosen = {}
    for row in coded:
        source = by_key[row["review_key"]]
        if (
            source["review_key"] in excluded
            or source["clean_word_count"] < policy["minimum_words"]
        ):
            continue
        key = (
            source["app_id"],
            source["window"],
            source["voted_up"],
            any(source["theme_matches"].values()),
            any(row["retained_theme_terms"].values()),
            any(row["excluded_context_rules"].values()),
            row["language_risk"],
        )
        rank = sha((policy["fresh_audit"]["salt"] + ":" + row["review_key"]).encode())
        if key not in chosen or rank < chosen[key][0]:
            chosen[key] = (rank, row)
    return [
        {
            "audit_index": i,
            "app_id": key[0],
            "window": key[1],
            "voted_up": key[2],
            "original_any_match": key[3],
            "retained_any_match": key[4],
            "any_context_exclusion": key[5],
            **row,
        }
        for i, (key, (_, row)) in enumerate(sorted(chosen.items()))
    ]


def derive(root=ROOT):
    """Requires the verified private archive; never runs on hosted CI."""
    root = Path(root).resolve()
    _, manifest, features = admitted(root)
    policy, raw_policy, development = method(root)
    run = root / "data/player-reviews/runs" / manifest["run_id"]
    verify_private(run, root)
    texts = {}
    for item in manifest["private_raw_inventory"]:
        match = re.fullmatch(r"(\d+)-(prior|recent)-\d+\.json", item["file"])
        if not match:
            continue
        response = json.loads(
            (root / "data/raw/player-reviews" / run.name / item["file"]).read_bytes()
        )["response"]
        for review in response.get("reviews", []):
            key = sha((match[1] + ":" + review["recommendationid"]).encode())
            if key in texts:
                raise ValueError("Duplicate private identity")
            texts[key] = review["review"]
    if set(texts) != {r["review_key"] for r in features}:
        raise ValueError("Private text inventory differs")
    coded = [project(r, texts[r["review_key"]], policy) for r in features]
    coded_raw = canonical(coded) + b"\n"
    fingerprint = {
        "source_manifest_sha256": sha((run / "manifest.json").read_bytes()),
        "original_features_sha256": manifest["features_sha256"],
        "method_sha256": sha(raw_policy),
        "development_selection_sha256": sha(development),
        "producer_sha256": sha(Path(__file__).read_bytes()),
        "normalizer_sha256": manifest["collector_sha256"],
        "unicode_database_version": unicodedata.unidata_version,
        "coded_features_sha256": sha(coded_raw),
    }
    receipt = {
        **fingerprint,
        "candidate_id": sha(canonical(fingerprint))[:16],
        "status": "candidate_context_diagnostics_pending_fresh_audit_and_independent_review",
        "source_run_id": run.name,
        "record_count": len(coded),
        "private_raw_files_verified": len(manifest["private_raw_inventory"]),
        "private_raw_to_derived_projection": "replayed",
        "language_certification": "unavailable",
        "concern_prevalence": "unavailable",
    }
    candidate = root / BASE / "candidates" / receipt["candidate_id"]
    publish(
        candidate,
        {"coded-features.json": coded_raw, "manifest.json": canonical(receipt) + b"\n"},
    )
    audit = select_audit(features, coded, policy, development)
    private_audit = [{**r, "text": texts[r["review_key"]]} for r in audit]
    private_path = (
        root
        / "data/raw"
        / ("review-refinement-audit-" + receipt["candidate_id"] + ".json")
    )
    private_raw = canonical(private_audit) + b"\n"
    if private_path.exists() and private_path.read_bytes() != private_raw:
        raise ValueError("Existing private audit differs")
    private_path.write_bytes(private_raw)
    print(
        json.dumps(
            {
                "candidate_id": candidate.name,
                "records": len(coded),
                "fresh_audit_count": len(audit),
            }
        )
    )
    return candidate


def validate(coded, features, policy):
    if not isinstance(coded, list) or len(coded) != len(features):
        raise ValueError("Derived inventory differs")
    by_key = {r["review_key"]: r for r in features}
    seen = set()
    rules = {r["id"]: r for r in policy["exclusions"]}
    for row in coded:
        if not isinstance(row, dict) or set(row) != {
            "review_key",
            "text_sha256",
            "language_risk",
            "retained_theme_terms",
            "excluded_context_rules",
        }:
            raise ValueError("Derived privacy schema differs")
        key = row["review_key"]
        if key in seen or key not in by_key:
            raise ValueError("Derived review inventory differs")
        seen.add(key)
        original = by_key[key]
        if (
            row["text_sha256"] != original["text_sha256"]
            or row["language_risk"] not in LANGUAGES
        ):
            raise ValueError("Derived provenance or language flag differs")
        if (original["clean_word_count"] < policy["minimum_words"]) != (
            row["language_risk"] == "short_text_not_assessed"
        ):
            raise ValueError("Derived short-text flag differs")
        for field in ["retained_theme_terms", "excluded_context_rules"]:
            if not isinstance(row[field], dict) or set(row[field]) != set(THEMES):
                raise ValueError("Derived theme inventory differs")
        for theme in THEMES:
            retained, excluded = (
                row["retained_theme_terms"][theme],
                row["excluded_context_rules"][theme],
            )
            original_terms = original["theme_matches"][theme]
            if (
                not isinstance(retained, list)
                or retained != [t for t in original_terms if t in retained]
                or not isinstance(excluded, list)
                or excluded != sorted(set(excluded))
                or any(
                    r not in rules
                    or rules[r]["theme"] != theme
                    or rules[r]["term"] not in original_terms
                    for r in excluded
                )
            ):
                raise ValueError("Derived terms or exclusion rules differ")
            removed = set(original_terms) - set(retained)
            if not removed <= {rules[r]["term"] for r in excluded}:
                raise ValueError("Unexplained term removal")


def publish(path, output):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if {p.name for p in path.iterdir()} != set(output) or any(
            (path / n).read_bytes() != b for n, b in output.items()
        ):
            raise ValueError("Existing immutable refinement differs")
    else:
        stage = Path(tempfile.mkdtemp(prefix=".building-refinement-", dir=path.parent))
        for name, raw in output.items():
            (stage / name).write_bytes(raw)
        os.replace(stage, path)


def build(candidate_id, root=ROOT):
    """Public rebuild of a candidate diagnostic package; no admission pointer."""
    root = Path(root).resolve()
    if not re.fullmatch(r"[0-9a-f]{16}", candidate_id):
        raise ValueError("Invalid candidate path")
    _, source, features = admitted(root)
    policy, raw_policy, development = method(root)
    candidate = root / BASE / "candidates" / candidate_id
    receipt = json.loads((candidate / "manifest.json").read_bytes())
    raw = (candidate / "coded-features.json").read_bytes()
    bindings = {
        "source_manifest_sha256": sha(canonical(source) + b"\n"),
        "original_features_sha256": source["features_sha256"],
        "method_sha256": sha(raw_policy),
        "development_selection_sha256": sha(development),
        "producer_sha256": sha(Path(__file__).read_bytes()),
        "normalizer_sha256": source["collector_sha256"],
        "unicode_database_version": unicodedata.unidata_version,
        "coded_features_sha256": sha(raw),
    }
    if (
        any(receipt.get(k) != v for k, v in bindings.items())
        or receipt["candidate_id"] != candidate_id
        or sha(canonical(bindings))[:16] != candidate_id
        or receipt["record_count"] != len(features)
        or receipt["source_run_id"] != source["run_id"]
        or receipt["private_raw_files_verified"] != len(source["private_raw_inventory"])
        or receipt["status"]
        != "candidate_context_diagnostics_pending_fresh_audit_and_independent_review"
    ):
        raise ValueError("Derived candidate binding differs")
    coded = json.loads(raw)
    validate(coded, features, policy)
    audit = select_audit(features, coded, policy, development)
    by_key = {r["review_key"]: r for r in coded}
    summary = []
    for title in source["scope"]:
        for window in ["prior", "recent"]:
            rows = [
                r
                for r in features
                if (r["app_id"], r["window"]) == (title["app_id"], window)
            ]
            counts = Counter(by_key[r["review_key"]]["language_risk"] for r in rows)
            summary.append(
                {
                    "app_id": title["app_id"],
                    "title": title["title"],
                    "creation_cohort": window,
                    "returned_review_count_unchanged": len(rows),
                    **{k + "_count": counts[k] for k in sorted(LANGUAGES)},
                    "records_with_context_exclusion": sum(
                        any(by_key[r["review_key"]]["excluded_context_rules"].values())
                        for r in rows
                    ),
                    "confirmed_concern_prevalence_percent": None,
                    "language_certification": "unavailable",
                    "theme_change_percent": None,
                    "interpretation": "candidate_diagnostics_only_pending_fresh_audit",
                }
            )
    output = {
        "cohort_diagnostics.csv": encode(summary),
        "fresh-audit-selection.json": canonical(audit) + b"\n",
    }
    output["build-manifest.json"] = (
        canonical(
            {
                "candidate_id": candidate_id,
                "candidate_manifest_sha256": sha(
                    (candidate / "manifest.json").read_bytes()
                ),
                "output_sha256": {n: sha(b) for n, b in output.items()},
                "row_counts": {
                    "cohort_diagnostics": len(summary),
                    "fresh_audit_selection": len(audit),
                },
                "status": receipt["status"],
            }
        )
        + b"\n"
    )
    release = root / BASE / "diagnostics" / candidate_id
    publish(release, output)
    print(json.dumps({"diagnostic_id": candidate_id, "fresh_audit_count": len(audit)}))
    return release


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--derive-private", action="store_true")
    parser.add_argument("--candidate")
    args = parser.parse_args()
    if args.derive_private:
        if args.candidate:
            parser.error("Choose private derivation or public candidate rebuild")
        derive()
    elif args.candidate:
        build(args.candidate)
    else:
        parser.error("Explicit --derive-private or --candidate required")
