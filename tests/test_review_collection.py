import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import review_collection as reviews
import test_price_history


def record(
    identity="1", created=1791385100, text="No crashes; the story is worth the price."
):
    return {
        "recommendationid": identity,
        "language": "english",
        "review": text,
        "timestamp_created": created,
        "timestamp_updated": created,
        "voted_up": True,
        "steam_purchase": True,
        "received_for_free": False,
        "written_during_early_access": False,
        "refunded": False,
        "author": {"steamid": "PRIVATE-AUTHOR"},
    }


def payload(records, matching=1, cursor="next"):
    return json.dumps(
        {
            "response": {
                "reviews": records,
                "cursor": cursor,
                "total_matching": matching,
                "query_summary": {
                    "num_reviews": len(records),
                    "total_positive": matching,
                    "total_negative": 0,
                    "total_reviews": matching,
                },
            }
        }
    ).encode()


class ReviewSourceTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(
            (reviews.ROOT / "data/player-reviews/source-contract.json").read_bytes()
        )
        self.bounds = reviews.windows(self.contract)["recent"]
        self.at = "2026-10-07T15:01:00+00:00"

    def pages(self, first=None, second=None):
        return [
            {
                "query": reviews.query(self.contract, 1, "*", self.bounds),
                "raw": first or payload([record()]),
                "retrieved_at_utc": self.at,
            },
            {
                "query": reviews.query(self.contract, 1, "next", self.bounds),
                "raw": second or payload([], cursor="end"),
                "retrieved_at_utc": self.at,
            },
        ]

    def project(self, pages):
        return reviews.project_window(pages, 1, "recent", self.bounds, self.contract)

    def test_adjacent_windows_do_not_overlap_and_are_exactly_thirty_days(self):
        w = reviews.windows(self.contract)
        self.assertEqual(w["prior"][1] + 1, w["recent"][0])
        self.assertEqual(w["recent"][1] - w["recent"][0] + 1, 30 * 86400)

    def test_valid_complete_cohort_replays_without_author_or_text(self):
        rows, coverage = self.project(self.pages())
        self.assertEqual(
            coverage["coverage_status"], "complete_returned_creation_cohort"
        )
        self.assertEqual(rows[0]["theme_matches"]["performance"], ["crashes"])
        self.assertNotIn("PRIVATE-AUTHOR", json.dumps(rows))
        self.assertNotIn("No crashes", json.dumps(rows))

    def test_screening_is_case_normalised_and_uses_word_boundaries(self):
        r = reviews.feature(
            record(text="[b]FPS[/b] controller crashworthy difficulty"),
            1,
            "recent",
            self.bounds,
            self.at,
        )
        self.assertEqual(r["theme_matches"]["performance"], ["fps"])
        self.assertEqual(r["theme_matches"]["controls"], ["controller"])

    def test_negation_is_not_inferred_as_complaint_or_aspect_sentiment(self):
        r = reviews.feature(
            record(text="No crashes whatsoever and good optimization."),
            1,
            "recent",
            self.bounds,
            self.at,
        )
        self.assertTrue(r["voted_up"])
        self.assertEqual(
            set(r["theme_matches"]["performance"]), {"crashes", "optimization"}
        )
        self.assertNotIn("sentiment", r)

    def test_creation_outside_declared_window_fails(self):
        with self.assertRaisesRegex(ValueError, "timestamp outside"):
            reviews.feature(
                record(created=self.bounds[0] - 1), 1, "recent", self.bounds, self.at
            )

    def test_non_english_review_fails(self):
        r = record()
        r["language"] = "french"
        with self.assertRaisesRegex(ValueError, "language"):
            reviews.feature(r, 1, "recent", self.bounds, self.at)

    def test_future_updated_text_fails(self):
        r = record()
        r["timestamp_updated"] = 1791389999
        with self.assertRaisesRegex(ValueError, "timestamp outside"):
            reviews.feature(r, 1, "recent", self.bounds, self.at)

    def test_boolean_cannot_replace_integer(self):
        r = record()
        r["timestamp_created"] = True
        with self.assertRaisesRegex(ValueError, "creation timestamp"):
            reviews.feature(r, 1, "recent", self.bounds, self.at)

    def test_false_boolean_type_fails(self):
        r = record()
        r["voted_up"] = 1
        with self.assertRaisesRegex(ValueError, "booleans"):
            reviews.feature(r, 1, "recent", self.bounds, self.at)

    def test_duplicate_review_across_pages_fails(self):
        with self.assertRaisesRegex(ValueError, "Duplicate review"):
            self.project(self.pages(second=payload([record()], cursor="end")))

    def test_repeated_cursor_fails(self):
        with self.assertRaisesRegex(ValueError, "cursor did not advance"):
            self.project(self.pages(first=payload([record()], cursor="*")))

    def test_wrong_query_or_cursor_chain_fails(self):
        pages = self.pages()
        pages[1]["query"]["cursor"] = "wrong"
        with self.assertRaisesRegex(ValueError, "chain differs"):
            self.project(pages)

    def test_changed_matching_count_is_unavailable_not_complete(self):
        _, c = self.project(self.pages(second=payload([], matching=2, cursor="end")))
        self.assertEqual(c["coverage_status"], "inconsistent_source_counts")

    def test_empty_cohort_is_complete_source_coverage_with_zero_records(self):
        pages = self.pages(first=payload([], matching=0))[:1]
        rows, c = self.project(pages)
        self.assertEqual(rows, [])
        self.assertEqual(c["coverage_status"], "complete_returned_creation_cohort")

    def test_explicit_zero_terminal_page_can_omit_review_array(self):
        raw = json.loads(payload([], matching=1, cursor="end"))
        del raw["response"]["reviews"]
        _, coverage = self.project(self.pages(second=json.dumps(raw).encode()))
        self.assertEqual(
            coverage["coverage_status"], "complete_returned_creation_cohort"
        )

    def test_missing_review_array_with_positive_count_fails(self):
        raw = json.loads(payload([record()]))
        del raw["response"]["reviews"]
        with self.assertRaisesRegex(ValueError, "Missing review page"):
            self.project(self.pages(first=json.dumps(raw).encode()))

    def test_public_features_use_dates_and_keep_edited_state_explicit(self):
        r = record()
        r["timestamp_updated"] = 1791385260
        result = reviews.feature(r, 1, "recent", self.bounds, self.at)
        self.assertEqual(result["created_date_utc"], "2026-10-07")
        self.assertTrue(result["updated_after_creation_window_end"])
        self.assertNotIn("timestamp_created", result)
        self.assertNotIn("recommendationid", result)

    def test_budget_without_terminal_empty_page_is_capped(self):
        pages = []
        for i in range(5):
            cursor = "*" if i == 0 else str(i)
            pages.append(
                {
                    "query": reviews.query(self.contract, 1, cursor, self.bounds),
                    "raw": payload(
                        [record(str(i + 1), created=1791385100 - i)],
                        matching=5,
                        cursor=str(i + 1),
                    ),
                    "retrieved_at_utc": self.at,
                }
            )
        _, c = self.project(pages)
        self.assertEqual(c["coverage_status"], "capped_latest_creation_sample")

    def test_partial_page_chain_does_not_claim_budget_cap(self):
        with self.assertRaisesRegex(ValueError, "stopped before"):
            self.project(self.pages()[:1])


class ReviewReplayTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_price_history.PriceAdmissionTests()
        self.fixture.setUp()
        self.root = self.fixture.root
        (self.root / "data/player-reviews").mkdir()
        shutil.copyfile(
            reviews.ROOT / "data/player-reviews/source-contract.json",
            self.root / "data/player-reviews/source-contract.json",
        )
        shutil.copyfile(
            reviews.ROOT / "data/player-reviews/accepted-runs.json",
            self.root / "data/player-reviews/accepted-runs.json",
        )
        (self.root / "data/player-reviews/accepted-runs.json").write_text(
            '{"accepted_runs":[]}\n'
        )

        def fetch(endpoint, params):
            if params["num_per_page"] == 1:
                return payload([record()], matching=1)
            if params["cursor"] == "*":
                return payload(
                    [
                        record(
                            identity=str(params["date_range_end"]),
                            created=params["date_range_end"] - 1,
                        )
                    ],
                    matching=1,
                )
            return payload([], matching=1, cursor="end")

        with patch(
            "review_collection.fetch", side_effect=fetch
        ), contextlib.redirect_stdout(io.StringIO()):
            self.run = reviews.collect(self.root)

    def tearDown(self):
        self.fixture.tearDown()
        self.fixture.doCleanups()

    def test_private_archive_replays_exact_public_features(self):
        manifest = reviews.verify_private(self.run, self.root)
        self.assertEqual(manifest["feature_count"], 24)

    def test_changed_private_bytes_fail_replay(self):
        raw = next(
            (self.root / "data/raw/player-reviews" / self.run.name).glob("*.json")
        )
        raw.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "hash"):
            reviews.verify_private(self.run, self.root)

    def test_changed_public_features_fail_replay(self):
        (self.run / "features.json").write_bytes(b"[]")
        with self.assertRaisesRegex(ValueError, "replay differs"):
            reviews.verify_private(self.run, self.root)


if __name__ == "__main__":
    unittest.main()
