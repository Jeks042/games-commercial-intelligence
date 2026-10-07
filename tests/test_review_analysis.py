import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import review_analysis as analysis
import review_collection as collection
import test_review_collection


class ReviewAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(
            (collection.ROOT / "data/player-reviews/source-contract.json").read_bytes()
        )
        self.features = []
        coverage = []
        for window, bounds in collection.windows(self.contract).items():
            for i in range(30):
                r = test_review_collection.record(
                    str(i + 1),
                    bounds[1] - i,
                    text="The story is great but no crashes occurred.",
                )
                r["voted_up"] = i < (20 if window == "recent" else 10)
                self.features.append(
                    collection.feature(
                        r, 1, window, bounds, "2026-10-07T16:00:00+00:00"
                    )
                )
            coverage.append(
                {
                    "app_id": 1,
                    "window": window,
                    "start_timestamp": bounds[0],
                    "end_timestamp": bounds[1],
                    "returned_review_count": 30,
                    "initial_total_matching": 30,
                    "total_matching_observations": [30, 30],
                    "pages": 2,
                    "empty_terminal_page": True,
                    "coverage_status": "complete_returned_creation_cohort",
                }
            )
        # Distinct review identities across creation cohorts.
        for row in self.features:
            row["review_key"] = collection.sha(
                (row["window"] + row["review_key"]).encode()
            )
        self.manifest = {
            "scope": [{"app_id": 1, "title": "Game"}],
            "feature_count": 60,
            "window_coverage": coverage,
            "lifetime_summaries": [
                {
                    "app_id": 1,
                    "retrieved_at_utc": "2026-10-07T16:00:00+00:00",
                    "summary": {
                        "total_reviews": 100,
                        "total_positive": 70,
                        "total_negative": 30,
                    },
                }
            ],
        }

    def analyse(self):
        return analysis.analyse(self.contract, self.manifest, self.features)

    def test_complete_adequate_cohorts_allow_descriptive_recommendation_gap(self):
        _, _, result = self.analyse()
        self.assertAlmostEqual(
            result[0]["recent_minus_prior_recommendation_pp"], 33.3334, places=4
        )
        self.assertEqual(result[0]["causal_effect_status"], "not_identified")

    def test_capped_cohort_never_yields_population_change(self):
        self.manifest["window_coverage"][0][
            "coverage_status"
        ] = "capped_latest_creation_sample"
        _, _, result = self.analyse()
        self.assertIsNone(result[0]["recent_minus_prior_recommendation_pp"])

    def test_low_n_never_yields_period_comparison(self):
        self.features.pop()
        _, _, result = self.analyse()
        self.assertIsNone(result[0]["recent_minus_prior_recommendation_pp"])

    def test_empty_cohort_rate_is_unavailable_not_zero(self):
        self.features = [r for r in self.features if r["window"] != "recent"]
        cohorts, _, result = self.analyse()
        self.assertIsNone(cohorts[1]["observed_recommendation_percent"])
        self.assertIsNone(result[0]["recent_minus_prior_recommendation_pp"])

    def test_short_texts_are_counted_in_recommendations_not_theme_denominator(self):
        self.features[0]["clean_word_count"] = 1
        cohorts, themes, _ = self.analyse()
        recent = next(r for r in cohorts if r["creation_cohort"] == "recent")
        self.assertEqual(recent["returned_review_count"], 30)
        self.assertEqual(recent["screenable_text_count"], 29)
        for r in themes:
            if r["creation_cohort"] == "recent":
                self.assertEqual(r["screenable_text_count"], 29)

    def test_keyword_counts_do_not_claim_confirmed_concern_or_aspect_sentiment(self):
        _, themes, result = self.analyse()
        for r in themes:
            self.assertIsNone(r["confirmed_concern_prevalence_percent"])
            self.assertIsNone(r["theme_change_percent"])
        self.assertIsNone(result[0]["lifetime_theme_change_percent"])

    def test_every_output_preserves_unverified_source_language_semantics(self):
        cohorts, themes, titles = self.analyse()
        for row in cohorts + themes + titles:
            self.assertEqual(
                row["language_suitability_status"],
                "Steam_label_not_independently_verified_text_language",
            )
        self.assertIn("steam_labelled_english_lifetime_total_at_retrieval", titles[0])
        self.assertNotIn("english_lifetime_total_at_retrieval", titles[0])
        self.assertIn("Steam_labelled_English", titles[0]["comparability_limit"])

    def test_audit_selects_matched_and_unmatched_strata_deterministically(self):
        self.features[0]["theme_matches"] = {t: [] for t in collection.THEMES}
        selected = analysis.audit_selection(self.features)
        self.assertTrue(any(not r["has_theme_match"] for r in selected))
        self.assertEqual(
            selected, analysis.audit_selection(list(reversed(self.features)))
        )
        self.assertEqual(
            len(
                {
                    (r["app_id"], r["window"], r["voted_up"], r["has_theme_match"])
                    for r in selected
                }
            ),
            len(selected),
        )

    def test_sensitive_extra_feature_field_is_rejected(self):
        self.features[0]["author"] = {"steamid": "private"}
        with self.assertRaisesRegex(ValueError, "schema"):
            analysis.validate_features(self.features, self.manifest, self.contract)

    def test_duplicate_review_key_is_rejected(self):
        self.features[1]["review_key"] = self.features[0]["review_key"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analysis.validate_features(self.features, self.manifest, self.contract)

    def test_complete_label_cannot_hide_changed_source_counts(self):
        self.manifest["window_coverage"][0]["total_matching_observations"] = [30, 31]
        with self.assertRaisesRegex(ValueError, "completeness"):
            analysis.validate_features(self.features, self.manifest, self.contract)


class ReviewPublicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_review_collection.ReviewReplayTests()
        self.fixture.setUp()
        self.root = self.fixture.root
        self.run = self.fixture.run

    def tearDown(self):
        self.fixture.tearDown()

    def accept(self):
        manifest = collection.verify_private(self.run, self.root)
        path = self.root / "data/player-reviews/verification/fixture.json"
        path.parent.mkdir()
        proof = {
            "run_id": self.run.name,
            "manifest_sha256": collection.sha(
                (self.run / "manifest.json").read_bytes()
            ),
            "features_sha256": manifest["features_sha256"],
            "raw_to_features_replay": "byte_identical",
            "private_raw_files_verified": len(manifest["private_raw_inventory"]),
        }
        path.write_bytes(collection.canonical(proof) + b"\n")
        entry = {
            "run_id": self.run.name,
            "status": "accepted",
            "manifest_sha256": proof["manifest_sha256"],
            "private_replay_verification_path": path.relative_to(self.root).as_posix(),
            "private_replay_verification_sha256": collection.sha(path.read_bytes()),
        }
        (self.root / "data/player-reviews/accepted-runs.json").write_bytes(
            collection.canonical({"accepted_runs": [entry]}) + b"\n"
        )

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return analysis.build(self.root)

    def test_unreviewed_coded_source_cannot_publish(self):
        with self.assertRaisesRegex(ValueError, "reviewed coded-review"):
            self.build()
        self.assertFalse((self.root / "data/review-analysis/current.json").exists())

    def test_admitted_build_and_repeat_are_identical(self):
        self.accept()
        release = self.build()
        before = {p.name: p.read_bytes() for p in release.iterdir()}
        self.assertEqual(release, self.build())
        self.assertEqual(before, {p.name: p.read_bytes() for p in release.iterdir()})

    def test_changed_features_fail_without_publication(self):
        self.accept()
        (self.run / "features.json").write_bytes(b"[]")
        with self.assertRaisesRegex(ValueError, "features hash"):
            self.build()

    def test_changed_private_replay_evidence_fails(self):
        self.accept()
        (self.root / "data/player-reviews/verification/fixture.json").write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "verification binding"):
            self.build()

    def test_tampered_release_fails_and_pointer_stays_unchanged(self):
        self.accept()
        release = self.build()
        pointer = self.root / "data/review-analysis/current.json"
        before = pointer.read_bytes()
        (release / "title_review_context.csv").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "release differs"):
            self.build()
        self.assertEqual(before, pointer.read_bytes())


if __name__ == "__main__":
    unittest.main()
