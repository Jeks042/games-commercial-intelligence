import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import acquisition as acq
import collect_snapshot as live
import collect_market_benchmark as benchmark
import fetch_current_players as players
import fetch_market_benchmark as spy
import fetch_steam_reviews as reviews
import fetch_steam_store as store


class PayloadTests(unittest.TestCase):
    def review(self, summary):
        with patch.object(
            reviews, "get_json", return_value={"response": {"query_summary": summary}}
        ):
            return reviews.fetch_review_summary("1")

    def test_failed_reviews_are_not_zero(self):
        for payload in ({"success": 0}, {}, {"response": {}}):
            with self.subTest(payload=payload), patch.object(
                reviews, "get_json", return_value=payload
            ):
                with self.assertRaises(ValueError):
                    reviews.fetch_review_summary("1")

    def test_reviews_reconcile_and_reject_missing_or_negative_counts(self):
        for summary in (
            {"total_reviews": 4, "total_positive": 4, "total_negative": 1},
            {"total_reviews": 4, "total_positive": 4},
            {"total_reviews": -1, "total_positive": 0, "total_negative": -1},
        ):
            with self.subTest(summary=summary), self.assertRaises(ValueError):
                self.review(summary)

    def test_valid_zero_review_count_has_null_ratio(self):
        result = self.review(
            {
                "total_reviews": 0,
                "total_positive": 0,
                "total_negative": 0,
                "review_score": 0,
                "review_score_desc": "No user reviews",
            }
        )
        self.assertEqual(result["total_reviews"], 0)
        self.assertIsNone(result["review_positive_percent"])

    def test_review_query_keeps_all_purchases_and_languages(self):
        summary = {
            "total_reviews": 10,
            "total_positive": 8,
            "total_negative": 2,
            "review_score": 8,
            "review_score_desc": "Very Positive",
        }
        with patch.object(
            reviews, "get_json", return_value={"response": {"query_summary": summary}}
        ) as request:
            self.assertEqual(
                reviews.fetch_review_summary("1")["review_positive_percent"], 80
            )
            params = json.loads(request.call_args.args[1]["input_json"])
            self.assertEqual(params["purchase_type"], 1)
            self.assertEqual(params["languages"], ["all"])
            self.assertEqual(params["review_type"], 0)

    def test_player_failures_and_missing_counts_rejected(self):
        for response in (
            {"result": 0, "player_count": 0},
            {"result": 1},
            {"result": 1, "player_count": -1},
        ):
            with self.subTest(response=response), patch.object(
                players, "get_json", return_value={"response": response}
            ):
                with self.assertRaises(ValueError):
                    players.fetch_current_players("1")

    def test_valid_zero_players_preserved(self):
        with patch.object(
            players,
            "get_json",
            return_value={"response": {"result": 1, "player_count": 0}},
        ):
            self.assertEqual(players.fetch_current_players("1")["current_players"], 0)

    def test_failed_store_and_wrong_identity_rejected(self):
        for payload in (
            {"1": {"success": False}},
            {
                "1": {
                    "success": True,
                    "data": {
                        "steam_appid": 2,
                        "name": "Game",
                        "type": "game",
                        "is_free": False,
                    },
                }
            },
        ):
            with self.subTest(payload=payload), patch.object(
                store, "get_json", return_value=payload
            ):
                with self.assertRaises(ValueError):
                    store.fetch_store_details("1")

    def test_missing_paid_price_is_unavailable_not_zero(self):
        payload = {
            "1": {
                "success": True,
                "data": {
                    "steam_appid": 1,
                    "name": "Game",
                    "type": "game",
                    "is_free": False,
                },
            }
        }
        with patch.object(store, "get_json", return_value=payload):
            result = store.fetch_store_details("1")
            self.assertEqual(result["price_status"], "unavailable")
            self.assertIsNone(result["final_price_minor"])

    def test_wrong_currency_or_invalid_price_rejected(self):
        for price in (
            {"currency": "USD", "initial": 100, "final": 100, "discount_percent": 0},
            {"currency": "GBP", "initial": 100, "final": 200, "discount_percent": 0},
        ):
            payload = {
                "1": {
                    "success": True,
                    "data": {
                        "steam_appid": 1,
                        "name": "Game",
                        "type": "game",
                        "is_free": False,
                        "price_overview": price,
                    },
                }
            }
            with self.subTest(price=price), patch.object(
                store, "get_json", return_value=payload
            ):
                with self.assertRaises(ValueError):
                    store.fetch_store_details("1")

    def test_steamspy_identity_and_owner_band_required(self):
        for row in (
            {"appid": 2, "name": "Wrong"},
            {"appid": 1, "name": "Game", "owners": "unknown"},
        ):
            with self.subTest(row=row), patch.object(spy, "get_json", return_value=row):
                with self.assertRaises(ValueError):
                    spy.fetch_market_benchmark("1")

    def test_steamspy_zero_playtime_is_unavailable(self):
        row = {
            "appid": 1,
            "name": "Game",
            "owners": "0 .. 20,000",
            "ccu": 0,
            "positive": 0,
            "negative": 0,
            "average_forever": 0,
            "average_2weeks": 0,
            "median_forever": 0,
            "median_2weeks": 0,
        }
        with patch.object(spy, "get_json", return_value=row):
            result = spy.fetch_market_benchmark("1")
            self.assertIsNone(result["average_playtime_forever_minutes"])
            self.assertEqual(result["playtime_status"], "unavailable")
            self.assertEqual(result["owner_estimate_status"], "requires_review")


class PublicationTests(unittest.TestCase):
    def test_schema_extension_rewrites_header_and_preserves_legacy(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.csv"
            acq.atomic_csv(
                path,
                ["snapshot_timestamp_utc", "app_id"],
                [{"snapshot_timestamp_utc": "old", "app_id": "1"}],
            )
            fields = [
                "snapshot_timestamp_utc",
                "app_id",
                "run_id",
                "schema_version",
                "steam_reviews_error",
            ]
            acq.append_history(
                path,
                fields,
                [
                    {
                        "snapshot_timestamp_utc": "new",
                        "app_id": "1",
                        "run_id": "run2",
                        "schema_version": 2,
                        "steam_reviews_error": "failed",
                    }
                ],
            )
            header, rows = acq.read_csv(path)
            self.assertEqual(header, fields)
            self.assertEqual(rows[0]["schema_version"], "legacy-1")
            self.assertEqual(rows[1]["steam_reviews_error"], "failed")
            self.assertNotIn(None, rows[1])

    def test_duplicate_run_does_not_change_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.csv"
            fields = ["app_id", "run_id"]
            rows = [{"app_id": "1", "run_id": "run1"}]
            acq.atomic_csv(path, fields, rows)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                acq.append_history(path, fields, rows)
            self.assertEqual(path.read_bytes(), before)

    def test_malformed_legacy_csv_not_silently_repaired(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "history.csv"
            path.write_text("app_id,run_id\n1,a,extra\n", encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                acq.append_history(
                    path, ["app_id", "run_id"], [{"app_id": "2", "run_id": "new"}]
                )
            self.assertEqual(path.read_bytes(), before)

    def test_unknown_field_atomic_write_does_not_replace_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "out.csv"
            path.write_text("preserved", encoding="utf-8")
            with self.assertRaises(ValueError):
                acq.atomic_csv(path, ["app_id"], [{"app_id": "1", "unexpected": "x"}])
            self.assertEqual(path.read_text(), "preserved")

    def test_partial_live_run_saves_evidence_and_keeps_history(self):
        title = {
            "app_id": "1",
            "title": "Game",
            "peer_group": "group",
            "cohort": "portfolio",
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "history.csv"
            output.write_text("preserved", encoding="utf-8")
            with patch.object(live, "DATA_DIR", root), patch.object(
                live, "OUTPUT", output
            ), patch.object(live, "load_titles", return_value=[title]), patch.object(
                live,
                "SOURCES",
                {"steam_store": Mock(side_effect=ValueError("invalid payload"))},
            ):
                with self.assertRaises(SystemExit):
                    live.main()
            self.assertEqual(output.read_text(), "preserved")
            manifest = json.loads(
                next((root / "runs").glob("*/manifest.json")).read_text()
            )
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["coverage"], {"steam_store": 0})

    def test_failed_benchmark_does_not_overwrite_latest(self):
        title = {
            "app_id": "1",
            "title": "Game",
            "peer_group": "group",
            "cohort": "portfolio",
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "benchmark.csv"
            output.write_text("preserved", encoding="utf-8")
            with patch.object(benchmark, "DATA_DIR", root), patch.object(
                benchmark, "OUTPUT", output
            ), patch.object(
                benchmark, "load_titles", return_value=[title]
            ), patch.object(
                benchmark, "fetch_market_benchmark", side_effect=ValueError("wrong ID")
            ):
                with self.assertRaises(SystemExit):
                    benchmark.main()
            self.assertEqual(output.read_text(), "preserved")
            self.assertEqual(
                json.loads(next((root / "runs").glob("*/manifest.json")).read_text())[
                    "status"
                ],
                "failed",
            )


class RequestTests(unittest.TestCase):
    def setUp(self):
        acq._last_request.clear()

    def test_rate_limit_retries_and_succeeds(self):
        limited = Mock(status_code=429, headers={"Retry-After": "1"})
        good = Mock(status_code=200)
        good.json.return_value = {"ok": True}
        with patch.object(
            acq.requests, "get", side_effect=[limited, good]
        ) as request, patch.object(acq.time, "sleep"):
            self.assertEqual(acq.get_json("https://example.com/api", {}), {"ok": True})
            self.assertEqual(request.call_count, 2)

    def test_timeout_retry_budget_is_finite(self):
        with patch.object(
            acq.requests, "get", side_effect=acq.requests.Timeout()
        ) as request, patch.object(acq.time, "sleep"):
            with self.assertRaises(acq.requests.Timeout):
                acq.get_json("https://example.com/api", {})
            self.assertEqual(request.call_count, 3)

    def test_permanent_http_error_is_not_retried(self):
        response = Mock(status_code=404)
        response.raise_for_status.side_effect = acq.requests.HTTPError("404")
        with patch.object(acq.requests, "get", return_value=response) as request:
            with self.assertRaises(acq.requests.HTTPError):
                acq.get_json("https://example.com/api", {})
            self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
