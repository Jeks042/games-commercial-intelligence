import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import review_refinement as refinement
import review_collection as collection
import review_analysis as analysis
import test_review_analysis


class ContextDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.policy, _, self.development = refinement.method(collection.ROOT)

    def classify(self, text):
        return refinement.classify(text, self.policy)

    def test_fps_genre_exclusion_retains_separate_frame_rate_mention(self):
        _, kept, excluded = self.classify(
            "This FPS game runs at 30 fps with stuttering."
        )
        self.assertIn("fps", kept["performance"])
        self.assertIn("stuttering", kept["performance"])
        self.assertEqual(excluded["performance"], ["fps_genre"])

    def test_context_idiom_is_not_input_device(self):
        _, kept, excluded = self.classify(
            "This does not reinvent the wheel in its design."
        )
        self.assertEqual(kept["controls"], [])
        self.assertEqual(excluded["controls"], ["wheel_idiom"])

    def test_review_update_does_not_suppress_separate_game_update(self):
        _, kept, excluded = self.classify(
            "I will update my review after the next update."
        )
        self.assertEqual(kept["updates"], ["update"])
        self.assertEqual(excluded["updates"], ["review_edit"])

    def test_creator_mention_is_not_game_content(self):
        _, kept, excluded = self.classify(
            "A content creator recommended playing this game."
        )
        self.assertEqual(kept["content"], [])
        self.assertEqual(excluded["content"], ["content_creator"])

    def test_negation_and_praise_are_not_sentiment_labels(self):
        _, kept, _ = self.classify("No crashes occurred and the story was great.")
        self.assertEqual(kept["performance"], ["crashes"])
        self.assertEqual(kept["content"], ["story"])

    def test_latin_script_does_not_certify_english(self):
        language, _, _ = self.classify("Le jeu est vraiment très agréable à jouer.")
        self.assertEqual(language, "latin_letters_only_language_unverified")

    def test_non_latin_and_mixed_text_are_only_risk_flags(self):
        for text in [
            "This is a game with 名前 in the title.",
            "Эта игра очень хорошая и интересная.",
        ]:
            self.assertEqual(
                self.classify(text)[0], "non_latin_letters_present_language_unverified"
            )

    def test_short_text_remains_unassessed(self):
        self.assertEqual(self.classify("Great game!")[0], "short_text_not_assessed")

    def test_full_word_matching_avoids_accidental_substrings(self):
        _, kept, _ = self.classify("The wheelbarrow is worthlessly slow in practice.")
        self.assertEqual(kept["controls"], [])
        self.assertEqual(kept["value"], [])


class RefinementPipelineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_review_analysis.ReviewPublicationTests()
        self.fixture.setUp()
        self.fixture.accept()
        self.root = self.fixture.root
        target = self.root / refinement.BASE
        target.mkdir(parents=True)
        shutil.copyfile(
            collection.ROOT / refinement.BASE / "method-v1.json",
            target / "method-v1.json",
        )
        audit = self.root / "data/player-reviews/audit"
        audit.mkdir()
        (audit / "selection-20261007.json").write_bytes(b"[]\n")

    def tearDown(self):
        self.fixture.tearDown()

    def derive(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return refinement.derive(self.root)

    def build(self, candidate):
        with contextlib.redirect_stdout(io.StringIO()):
            return refinement.build(candidate.name, self.root)

    def test_private_derivation_public_rebuild_and_reruns_are_identical(self):
        candidate = self.derive()
        before = {p.name: p.read_bytes() for p in candidate.iterdir()}
        self.assertEqual(candidate, self.derive())
        self.assertEqual(before, {p.name: p.read_bytes() for p in candidate.iterdir()})
        release = self.build(candidate)
        outputs = {p.name: p.read_bytes() for p in release.iterdir()}
        self.assertEqual(release, self.build(candidate))
        self.assertEqual(outputs, {p.name: p.read_bytes() for p in release.iterdir()})
        self.assertFalse((self.root / refinement.BASE / "current.json").exists())

    def test_private_archive_changes_block_derivation(self):
        path = next(
            (self.root / "data/raw/player-reviews" / self.fixture.run.name).glob(
                "*.json"
            )
        )
        path.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "hash"):
            self.derive()

    def test_public_rebuild_does_not_require_private_text(self):
        candidate = self.derive()
        private = self.root / "data/raw/player-reviews" / self.fixture.run.name
        private.rename(private.with_name("unavailable-private-source"))
        self.build(candidate)

    def test_changed_method_blocks_candidate_rebuild(self):
        candidate = self.derive()
        path = self.root / refinement.BASE / "method-v1.json"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "binding"):
            self.build(candidate)

    def test_coded_feature_tampering_blocks_rebuild(self):
        candidate = self.derive()
        (candidate / "coded-features.json").write_bytes(b"[]")
        with self.assertRaisesRegex(ValueError, "binding"):
            self.build(candidate)

    def test_candidate_path_traversal_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "path"):
            refinement.build("../anything", self.root)

    def test_private_fields_and_unexplained_term_removal_are_rejected(self):
        candidate = self.derive()
        _, _, features = analysis.admitted(self.root)
        policy, _, _ = refinement.method(self.root)
        coded = json.loads((candidate / "coded-features.json").read_bytes())
        changed = deepcopy(coded)
        changed[0]["text"] = "private"
        with self.assertRaisesRegex(ValueError, "privacy schema"):
            refinement.validate(changed, features, policy)
        changed = deepcopy(coded)
        changed[0]["retained_theme_terms"]["content"] = []
        with self.assertRaisesRegex(ValueError, "Unexplained"):
            refinement.validate(changed, features, policy)

    def test_development_keys_are_mechanically_excluded_and_order_independent(self):
        candidate = self.derive()
        _, _, features = analysis.admitted(self.root)
        policy, _, _ = refinement.method(self.root)
        coded = json.loads((candidate / "coded-features.json").read_bytes())
        development = collection.canonical([{"review_key": features[0]["review_key"]}])
        selected = refinement.select_audit(features, coded, policy, development)
        self.assertNotIn(features[0]["review_key"], {r["review_key"] for r in selected})
        self.assertEqual(
            selected,
            refinement.select_audit(
                list(reversed(features)), list(reversed(coded)), policy, development
            ),
        )

    def test_exclusions_receive_a_separate_audit_stratum(self):
        candidate = self.derive()
        _, _, features = analysis.admitted(self.root)
        policy, _, _ = refinement.method(self.root)
        coded = json.loads((candidate / "coded-features.json").read_bytes())
        extra_feature = deepcopy(features[0])
        extra_feature["review_key"] = "a" * 64
        extra_feature["theme_matches"]["content"].append("content")
        features.append(extra_feature)
        extra = deepcopy(coded[0])
        extra["review_key"] = "a" * 64
        extra["excluded_context_rules"]["content"] = ["content_creator"]
        coded.append(extra)
        selected = refinement.select_audit(features, coded, policy, b"[]")
        self.assertIn("a" * 64, {r["review_key"] for r in selected})

    def test_tampered_immutable_output_is_not_overwritten(self):
        candidate = self.derive()
        release = self.build(candidate)
        (release / "cohort_diagnostics.csv").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.build(candidate)


class PublicAuditEvidenceTests(unittest.TestCase):
    def test_published_fresh_audit_is_complete_bound_and_excludes_development(self):
        base = collection.ROOT / refinement.BASE
        selection_path = (
            base / "diagnostics/94c88909fe4c88a1/fresh-audit-selection.json"
        )
        audit = json.loads((base / "audit/context-check-v1-20261008.json").read_bytes())
        selected = json.loads(selection_path.read_bytes())
        development = json.loads(
            (
                collection.ROOT / "data/player-reviews/audit/selection-20261007.json"
            ).read_bytes()
        )
        self.assertEqual(
            audit["selection_sha256"], collection.sha(selection_path.read_bytes())
        )
        self.assertEqual(
            audit["method_sha256"],
            collection.sha((base / "method-v1.json").read_bytes()),
        )
        self.assertEqual(audit["selected_count"], len(selected))
        self.assertEqual(len(audit["entries"]), len(selected))
        self.assertEqual(
            {r["review_key"] for r in selected}
            & {r["review_key"] for r in development},
            set(),
        )
        for selected_row, checked in zip(selected, audit["entries"], strict=True):
            for field in [
                "audit_index",
                "app_id",
                "window",
                "voted_up",
                "review_key",
                "text_sha256",
                "language_risk",
                "any_context_exclusion",
            ]:
                self.assertEqual(selected_row[field], checked[field])
            self.assertTrue(checked["context_note"])

    def test_published_audit_projection_contains_only_declared_fields(self):
        audit = json.loads(
            (
                collection.ROOT
                / refinement.BASE
                / "audit/context-check-v1-20261008.json"
            ).read_bytes()
        )
        expected = {
            "audit_index",
            "app_id",
            "window",
            "voted_up",
            "review_key",
            "text_sha256",
            "language_risk",
            "any_context_exclusion",
            "language_context_assessment",
            "context_note",
        }
        for row in audit["entries"]:
            self.assertEqual(set(row), expected)


if __name__ == "__main__":
    unittest.main()
