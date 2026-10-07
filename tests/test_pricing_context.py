import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pricing_context as context
import test_price_history


class PriceContextTests(unittest.TestCase):
    def setUp(self):
        self.scope = [
            {
                "app_id": a,
                "title": str(a),
                "cohort": "portfolio" if a == 101 else "competitor",
                "itad_game_id": str(a),
                "identity_status": "eligible_app_linked_game_context",
            }
            for a in (101, 201, 202, 203, 204)
        ]
        self.events, self.observations = [], {}
        for app, cut in ((101, 70), (201, 50), (202, 60), (203, 65), (204, 90)):
            price = 10000 - 100 * cut
            self.events.append(
                {
                    "app_id": app,
                    "event_at_utc": "2026-10-01T17:00:00+00:00",
                    "price_status": "available",
                    "price_minor": price,
                    "regular_minor": 10000,
                    "cut_percent_source": str(cut),
                }
            )
            self.observations[app] = {
                "final_price_minor": str(price),
                "list_price_minor": "10000",
                "is_free": "0",
                "currency": "GBP",
                "steam_store_retrieved_at_utc": "2026-10-06T19:00:00+00:00",
            }
        self.references = [
            {
                "portfolio_app_id": "101",
                "reference_app_id": str(a),
                "peer_role": "adjacent_reference" if a == 204 else "direct_peer",
            }
            for a in (201, 202, 203, 204)
        ]

    def evaluate(self, coverage=None):
        return context.evaluate(
            self.scope, self.events, self.observations, self.references, coverage
        )

    def test_three_usable_direct_contexts_yield_declared_recorded_cut_comparison(self):
        _, _, result = self.evaluate()
        self.assertEqual(
            result[0]["direct_reference_median_maximum_recorded_cut_percent"], 60
        )
        self.assertEqual(result[0]["target_minus_reference_median_cut_pp"], 10)
        self.assertIsNone(result[0]["response_change_percent"])

    def test_adjacent_reference_never_fills_sparse_direct_group(self):
        self.references[2]["peer_role"] = "adjacent_reference"
        _, _, result = self.evaluate()
        self.assertEqual(result[0]["usable_direct_reference_count"], 2)
        self.assertIsNone(
            result[0]["direct_reference_median_maximum_recorded_cut_percent"]
        )

    def test_empty_returned_log_is_unavailable_not_zero_discount(self):
        self.events = [r for r in self.events if r["app_id"] != 203]
        titles, _, result = self.evaluate()
        empty = next(r for r in titles if r["app_id"] == 203)
        self.assertEqual(empty["returned_record_count"], 0)
        self.assertIsNone(empty["maximum_source_reported_cut_percent"])
        self.assertIsNone(result[0]["target_minus_reference_median_cut_pp"])

    def test_zero_zero_source_for_paid_game_is_quarantined_not_free_offer(self):
        event = next(r for r in self.events if r["app_id"] == 203)
        event.update(price_minor=0, regular_minor=0, cut_percent_source="0")
        titles, _, result = self.evaluate()
        flagged = next(r for r in titles if r["app_id"] == 203)
        self.assertEqual(
            flagged["suitability_status"], "requires_review_zero_zero_price_context"
        )
        self.assertEqual(flagged["source_latest_price_minor"], 0)
        self.assertIsNone(flagged["minimum_recorded_price_gbp"])
        self.assertEqual(result[0]["usable_direct_reference_count"], 2)

    def test_real_source_zero_with_positive_regular_and_matching_snapshot_is_retained(
        self,
    ):
        event = next(r for r in self.events if r["app_id"] == 203)
        event.update(price_minor=0, cut_percent_source="100")
        self.observations[203]["final_price_minor"] = "0"
        titles, _, _ = self.evaluate()
        valid = next(r for r in titles if r["app_id"] == 203)
        self.assertEqual(valid["minimum_recorded_price_gbp"], 0)
        self.assertEqual(valid["maximum_source_reported_cut_percent"], 100)

    def test_source_snapshot_disagreement_blocks_target_comparison(self):
        self.observations[101]["final_price_minor"] = "10000"
        _, _, result = self.evaluate()
        self.assertIsNone(result[0]["target_maximum_source_reported_cut_percent"])
        self.assertIsNone(result[0]["target_minus_reference_median_cut_pp"])

    def test_removed_latest_record_does_not_carry_forward_earlier_price(self):
        r = deepcopy(self.events[0])
        r.update(
            event_at_utc="2026-10-02T00:00:00+00:00",
            price_status="removed_or_unavailable",
            price_minor=None,
            regular_minor=None,
        )
        self.events.append(r)
        titles, _, result = self.evaluate()
        self.assertEqual(
            titles[0]["suitability_status"], "unavailable_latest_source_price_removed"
        )
        self.assertIsNone(result[0]["target_minimum_recorded_price_gbp"])

    def test_assignment_exclusion_retains_not_requested_status_and_null_count(self):
        self.events = [r for r in self.events if r["app_id"] != 203]
        coverage = {
            t["app_id"]: {"history_status": "returned_events"} for t in self.scope
        }
        coverage[203]["history_status"] = "not_requested_assignment_review"
        titles, _, _ = self.evaluate(coverage)
        excluded = next(t for t in titles if t["app_id"] == 203)
        self.assertIsNone(excluded["returned_record_count"])
        self.assertEqual(excluded["history_status"], "not_requested_assignment_review")

    def test_duplicate_reference_cannot_inflate_usable_count(self):
        self.references.append(deepcopy(self.references[0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.evaluate()


class ContextPublicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_price_history.PriceAdmissionTests()
        self.fixture.setUp()
        self.root = self.fixture.root

    def tearDown(self):
        self.fixture.tearDown()
        self.fixture.doCleanups()

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return context.build(self.root)

    def test_unreviewed_history_cannot_publish_context(self):
        with self.assertRaisesRegex(ValueError, "reviewed history run"):
            self.build()
        self.assertFalse((self.root / "data/pricing-review/current.json").exists())

    def test_accepted_context_rerun_is_identical_and_covers_scope(self):
        self.fixture.accept()
        release = self.build()
        before = {p.name: p.read_bytes() for p in release.iterdir()}
        self.assertEqual(release, self.build())
        self.assertEqual(before, {p.name: p.read_bytes() for p in release.iterdir()})
        counts = json.loads((release / "build-manifest.json").read_bytes())[
            "row_counts"
        ]
        self.assertEqual(
            counts,
            {
                "title_price_context": 32,
                "reference_discount_context": 38,
                "portfolio_discount_context": 12,
            },
        )

    def test_changed_context_release_fails_without_overwriting_pointer(self):
        self.fixture.accept()
        release = self.build()
        pointer = self.root / "data/pricing-review/current.json"
        before = pointer.read_bytes()
        (release / "title_price_context.csv").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "release differs"):
            self.build()
        self.assertEqual(pointer.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
