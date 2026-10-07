import contextlib
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import price_history as history


class PriceHistoryTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.scope = history.load_contract()
        # Unit fixtures deliberately use a broad independent window; production is contract-bound.
        self.contract = dict(
            self.contract, window_start_utc="2025-10-06T00:00:00+00:00"
        )
        self.title = next(t for t in self.scope if t["cohort"] == "portfolio")
        self.retrieved = "2026-10-06T22:00:00+00:00"

    def event(self, at="2026-01-01T12:00:00+00:00", price=500, regular=1000):
        return {
            "timestamp": at,
            "shop": {"id": 61, "name": "Steam"},
            "deal": {
                "price": {"amount": price / 100, "amountInt": price, "currency": "GBP"},
                "regular": {
                    "amount": regular / 100,
                    "amountInt": regular,
                    "currency": "GBP",
                },
                "cut": 100 * (regular - price) / regular if regular else 0,
            },
        }

    def normalise(self, events):
        return history.normalise(
            json.dumps(events).encode(),
            self.title,
            self.contract,
            "test-run",
            self.retrieved,
        )

    def test_discovery_reverse_proof_and_multi_app_exclusion(self):
        self.assertEqual(len(self.scope), 32)
        self.assertEqual(
            sum(
                t["identity_status"] == "eligible_app_linked_game_context"
                for t in self.scope
            ),
            31,
        )
        excluded = [
            t
            for t in self.scope
            if t["identity_status"] != "eligible_app_linked_game_context"
        ]
        self.assertEqual(excluded[0]["app_id"], 1144200)
        self.assertTrue(
            all(
                t["sku_status"] == "unresolved_history_has_no_package_identifier"
                for t in self.scope
            )
        )

    def test_raw_offset_and_original_fields_are_preserved(self):
        e = self.event("2026-01-01T13:00:00+01:00")
        rows, _ = self.normalise([e])
        self.assertEqual(rows[0]["source_timestamp"], e["timestamp"])
        self.assertEqual(rows[0]["event_at_utc"], "2026-01-01T12:00:00.000000+00:00")
        self.assertEqual(rows[0]["price_minor"], 500)
        self.assertEqual(rows[0]["currency"], "GBP")

    def test_non_gbp_or_non_steam_events_are_rejected(self):
        for change in ("currency", "shop"):
            e = self.event()
            if change == "currency":
                e["deal"]["price"]["currency"] = "USD"
            else:
                e["shop"] = {"id": 35, "name": "GOG"}
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.normalise([e])

    def test_minor_units_and_decimal_amount_must_agree(self):
        e = self.event()
        e["deal"]["price"]["amountInt"] = 501
        with self.assertRaisesRegex(ValueError, "disagree"):
            self.normalise([e])

    def test_invalid_price_cut_and_boolean_values_are_rejected(self):
        for field, value in (("cut", 110), ("cut", True), ("cut", 20)):
            e = self.event()
            e["deal"][field] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.normalise([e])
        e = self.event()
        e["deal"]["price"]["amountInt"] = True
        with self.assertRaises(ValueError):
            self.normalise([e])

    def test_future_and_naive_timestamps_are_rejected(self):
        for at in ("2026-10-07T12:00:00Z", "2026-01-01T12:00:00"):
            with self.subTest(at=at), self.assertRaises(ValueError):
                self.normalise([self.event(at)])

    def test_explicit_analysis_window_does_not_admit_later_changes(self):
        rows, excluded = self.normalise(
            [
                self.event("2025-01-01T00:00:00Z"),
                self.event(),
                self.event("2026-10-06T21:00:00Z"),
            ]
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(excluded["before_or_at_start"], 1)
        self.assertEqual(excluded["after_as_of"], 1)

    def test_removed_state_is_null_and_free_price_is_real_zero(self):
        removed = self.event()
        removed["deal"] = None
        rows, _ = self.normalise([removed, self.event("2026-01-02T00:00:00Z", 0, 1000)])
        self.assertEqual(rows[0]["price_status"], "removed_or_unavailable")
        self.assertIsNone(rows[0]["price_minor"])
        self.assertEqual(rows[1]["price_minor"], 0)
        self.assertEqual(rows[1]["discount_depth_percent"], 100)

    def test_empty_response_is_supported_without_fabricating_history(self):
        rows, _ = self.normalise([])
        self.assertEqual(rows, [])
        self.assertEqual(history.episodes(rows, self.contract["as_of_utc"]), [])

    def test_wrapped_pagination_or_missing_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            self.normalise({"data": [], "next": "page2"})
        e = self.event()
        del e["deal"]
        with self.assertRaises(ValueError):
            self.normalise([e])

    def test_duplicate_state_is_deduplicated_and_conflict_rejected(self):
        e = self.event()
        rows, excluded = self.normalise([e, deepcopy(e)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(excluded["identical_duplicates"], 1)
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.normalise([e, self.event(price=400)])

    def test_discount_deepening_is_one_sequence_with_two_states(self):
        rows, _ = self.normalise(
            [
                self.event(price=1000),
                self.event("2026-01-02T12:00:00Z", 500),
                self.event("2026-01-03T12:00:00Z", 400),
                self.event("2026-01-04T12:00:00Z", 1000),
            ]
        )
        episodes = history.episodes(rows, self.contract["as_of_utc"])
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["distinct_price_state_count"], 2)
        self.assertEqual(episodes[0]["maximum_discount_percent"], 60)
        self.assertEqual(episodes[0]["duration_days"], 2)

    def test_identical_repeated_states_do_not_add_discount_changes(self):
        rows, _ = self.normalise(
            [
                self.event(price=1000),
                self.event("2026-01-02T12:00:00Z", 500),
                self.event("2026-01-03T12:00:00Z", 500),
                self.event("2026-01-04T12:00:00Z", 1000),
            ]
        )
        self.assertEqual(
            history.episodes(rows, self.contract["as_of_utc"])[0][
                "distinct_price_state_count"
            ],
            1,
        )

    def test_full_price_return_splits_sequences(self):
        rows, _ = self.normalise(
            [
                self.event(price=1000),
                self.event("2026-01-02T12:00:00Z", 500),
                self.event("2026-01-03T12:00:00Z", 1000),
                self.event("2026-01-04T12:00:00Z", 500),
            ]
        )
        e = history.episodes(rows, self.contract["as_of_utc"])
        self.assertEqual(len(e), 2)
        self.assertEqual(e[1]["end_status"], "open_at_analysis_cutoff")
        self.assertIsNone(e[1]["duration_days"])

    def test_missing_price_breaks_sequence_and_unknown_return_start(self):
        removed = self.event("2026-01-03T12:00:00Z")
        removed["deal"] = None
        rows, _ = self.normalise(
            [
                self.event(price=1000),
                self.event("2026-01-02T12:00:00Z", 500),
                removed,
                self.event("2026-01-04T12:00:00Z", 500),
                self.event("2026-01-05T12:00:00Z", 1000),
            ]
        )
        e = history.episodes(rows, self.contract["as_of_utc"])
        self.assertEqual(e[0]["end_status"], "source_unavailable_boundary")
        self.assertEqual(e[1]["start_status"], "source_unavailable_left_boundary")
        self.assertTrue(all(r["duration_days"] is None for r in e))

    def test_first_discount_is_left_censored_not_full_campaign_duration(self):
        rows, _ = self.normalise(
            [self.event(), self.event("2026-01-03T12:00:00Z", 1000)]
        )
        e = history.episodes(rows, self.contract["as_of_utc"])[0]
        self.assertEqual(e["start_status"], "first_returned_event_left_censored")
        self.assertIsNone(e["duration_days"])

    @patch("price_history.time.sleep")
    @patch("price_history.requests.get")
    def test_header_credential_and_explicit_gb_steam_since(self, get, sleep):
        get.return_value = Mock(status_code=200, content=b"[]")
        history.request_history(
            self.contract, self.title["itad_game_id"], "test-secret"
        )
        kwargs = get.call_args.kwargs
        self.assertEqual(kwargs["headers"]["ITAD-API-Key"], "test-secret")
        self.assertNotIn("key", kwargs["params"])
        self.assertEqual(kwargs["params"]["country"], "GB")
        self.assertEqual(kwargs["params"]["shops"], "61")
        self.assertEqual(kwargs["params"]["since"], self.contract["window_start_utc"])

    @patch("price_history.time.sleep")
    @patch("price_history.requests.get")
    def test_retries_are_bounded_and_error_does_not_echo_key(self, get, sleep):
        get.return_value = Mock(status_code=503, headers={})
        with self.assertRaises(RuntimeError) as error:
            history.request_history(
                self.contract, self.title["itad_game_id"], "test-secret"
            )
        self.assertEqual(get.call_count, 3)
        self.assertNotIn("test-secret", str(error.exception))

    @patch("price_history.time.sleep")
    @patch("price_history.requests.get")
    def test_auth_failure_is_not_retried(self, get, sleep):
        get.return_value = Mock(status_code=401)
        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            history.request_history(
                self.contract, self.title["itad_game_id"], "test-secret"
            )
        self.assertEqual(get.call_count, 1)

    @patch("price_history.time.sleep")
    @patch("price_history.requests.get")
    def test_connection_error_is_sanitised(self, get, sleep):
        get.side_effect = requests.ConnectionError(
            "server accidentally echoed test-secret"
        )
        with self.assertRaises(RuntimeError) as error:
            history.request_history(
                self.contract, self.title["itad_game_id"], "test-secret"
            )
        self.assertEqual(get.call_count, 3)
        self.assertNotIn("test-secret", str(error.exception))

    def test_missing_key_stops_before_history_network_or_run_creation(self):
        with tempfile.TemporaryDirectory(
            prefix="gaming-price-credential-test-"
        ) as name:
            with patch.dict(os.environ, {}, clear=True), patch(
                "price_history.load_contract", return_value=(self.contract, self.scope)
            ), patch("price_history.request_history") as fetch:
                with self.assertRaisesRegex(ValueError, "ITAD_API_KEY"):
                    history.collect(Path(name))
                fetch.assert_not_called()
                self.assertFalse((Path(name) / "data/price-history/runs").exists())

    def test_partial_collection_is_failed_and_diagnostics_contain_no_key(self):
        with tempfile.TemporaryDirectory(
            prefix="gaming-price-collection-test-"
        ) as name:
            with patch("price_history.request_assignments", return_value=b"[]"), patch(
                "price_history.load_contract",
                return_value=(self.contract, [self.scope[0], self.scope[1]]),
            ), patch(
                "price_history.request_history",
                side_effect=[b"[]", RuntimeError("test-secret")],
            ), contextlib.redirect_stdout(
                io.StringIO()
            ):
                folder = history.collect(Path(name), key="test-secret")
            manifest = json.loads((folder / "manifest.json").read_bytes())
            self.assertEqual(manifest["status"], "failed")
            self.assertNotIn("test-secret", (folder / "manifest.json").read_text())
            self.assertFalse((Path(name) / "data/price-history/current.json").exists())


class PriceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.assignment_patch = patch(
            "price_history.request_assignments", return_value=b"[]"
        )
        self.assignment_request = self.assignment_patch.start()
        self.addCleanup(self.assignment_patch.stop)
        self.temp = tempfile.TemporaryDirectory(prefix="gaming-price-admission-test-")
        self.root = Path(self.temp.name).resolve()
        contract = json.loads(
            (history.ROOT / "data/benchmarking-contract.json").read_bytes()
        )
        for relative in (
            "sql",
            "data/price-history/discovery-20261006",
            contract["model_release_path"],
        ):
            shutil.copytree(
                history.ROOT / relative,
                self.root / relative,
                ignore=shutil.ignore_patterns("*.sqlite"),
            )
        (self.root / "docs").mkdir()
        shutil.copyfile(
            history.ROOT / "docs/benchmark-metrics.csv",
            self.root / "docs/benchmark-metrics.csv",
        )
        for relative in (
            "data/benchmarking-contract.json",
            "data/price-history/source-contract.json",
            "data/price-history/accepted-runs.json",
        ):
            shutil.copyfile(history.ROOT / relative, self.root / relative)

        def event(at, price):
            return {
                "timestamp": at,
                "shop": {"id": 61, "name": "Steam"},
                "deal": {
                    "price": {
                        "amount": price / 100,
                        "amountInt": price,
                        "currency": "GBP",
                    },
                    "regular": {"amount": 10, "amountInt": 1000, "currency": "GBP"},
                    "cut": 100 * (1000 - price) / 1000,
                },
            }

        self.raw = json.dumps(
            [
                event("2026-09-20T12:00:00Z", 1000),
                event("2026-09-21T12:00:00Z", 500),
                event("2026-09-23T12:00:00Z", 1000),
            ]
        ).encode()
        with patch(
            "price_history.request_history", return_value=self.raw
        ), contextlib.redirect_stdout(io.StringIO()):
            self.run = history.collect(self.root, key="fixture-secret")
        self.register = self.root / "data/price-history/accepted-runs.json"

    def tearDown(self):
        if (
            Path(self.temp.name).resolve() != self.root
            or self.root.parent != Path(tempfile.gettempdir()).resolve()
            or not self.root.name.startswith("gaming-price-admission-test-")
        ):
            raise RuntimeError("Unsafe price admission cleanup")
        self.temp.cleanup()

    def accept(self):
        self.register.write_bytes(
            history.canonical(
                {
                    "accepted_runs": [
                        {
                            "run_id": self.run.name,
                            "status": "accepted",
                            "manifest_sha256": history.sha(
                                (self.run / "manifest.json").read_bytes()
                            ),
                        }
                    ]
                }
            )
            + b"\n"
        )

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return history.build_analysis(self.root)

    def rows(self, release, name):
        import csv

        with (release / name).open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_unreviewed_history_cannot_publish(self):
        with self.assertRaisesRegex(ValueError, "reviewed history run"):
            self.build()
        self.assertFalse((self.root / "data/pricing-analysis/current.json").exists())

    def test_admitted_history_outputs_preserve_exclusion_and_unavailable_response(self):
        self.accept()
        release = self.build()
        rows = self.rows(release, "price_history_coverage.csv")
        self.assertEqual(len(rows), 32)
        excluded = next(r for r in rows if r["app_id"] == "1144200")
        self.assertEqual(excluded["returned_event_count"], "")
        self.assertEqual(excluded["recorded_discount_sequence_count"], "")
        self.assertEqual(excluded["history_status"], "not_requested_mapping_unresolved")
        self.assertEqual(
            excluded["coverage_status"], "not_requested_mapping_unresolved"
        )
        sequences = self.rows(release, "recorded_discount_sequences.csv")
        self.assertEqual(len(sequences), 31)
        self.assertTrue(
            all(
                r["during_player_dates"] == "0"
                and r["player_response_change_percent"] == ""
                for r in sequences
            )
        )
        self.assertTrue(
            all(r["causal_uplift_status"] == "not_identified" for r in sequences)
        )

    def test_raw_tamper_blocks_admission(self):
        self.accept()
        path = next((self.run / "responses").glob("*.json"))
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "Raw history hash"):
            self.build()

    def test_normalised_tamper_blocks_admission(self):
        self.accept()
        path = self.run / "events.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "events hash"):
            self.build()

    def test_reviewed_failed_manifest_cannot_enter_analysis(self):
        m = json.loads((self.run / "manifest.json").read_bytes())
        m["status"] = "failed"
        (self.run / "manifest.json").write_bytes(history.canonical(m) + b"\n")
        self.accept()
        with self.assertRaisesRegex(ValueError, "did not pass"):
            self.build()

    def test_empty_returned_log_is_not_zero_promotions(self):
        with patch(
            "price_history.request_history", return_value=b"[]"
        ), contextlib.redirect_stdout(io.StringIO()):
            self.run = history.collect(self.root, key="fixture-secret")
        self.accept()
        rows = self.rows(self.build(), "price_history_coverage.csv")
        mapped = [
            r
            for r in rows
            if r["identity_status"] == "eligible_app_linked_game_context"
        ]
        self.assertTrue(
            all(
                r["returned_event_count"] == "0"
                and r["recorded_discount_sequence_count"] == ""
                and r["coverage_status"] == "empty_returned_log_no_price_state_observed"
                for r in mapped
            )
        )

    def test_repeat_analysis_is_byte_identical(self):
        self.accept()
        release = self.build()
        hashes = {p.name: history.sha(p.read_bytes()) for p in release.iterdir()}
        self.assertEqual(release, self.build())
        self.assertEqual(
            hashes, {p.name: history.sha(p.read_bytes()) for p in release.iterdir()}
        )

    def change(self, gid=None):
        from email.utils import format_datetime
        from datetime import datetime, timezone

        return {
            "id": 7,
            "product_id": "018d937f-0680-71f6-a2c0-30660ed59d79",
            "old_game_id": gid
            or history.load_contract(self.root)[1][0]["itad_game_id"],
            "new_game_id": "018d937f-0681-7345-8d53-d0b6170cf842",
            "timestamp": 1789905600,
            "date": format_datetime(datetime.fromtimestamp(1789905600, timezone.utc)),
        }

    def test_assignment_reassignment_excludes_touched_title_and_preserves_raw(self):
        # UUID comparison must preserve exclusion despite valid source casing differences.
        raw = json.dumps(
            [self.change(gid=self.change()["old_game_id"].upper())]
        ).encode()
        self.assignment_request.return_value = raw
        with patch(
            "price_history.request_history", return_value=self.raw
        ), contextlib.redirect_stdout(io.StringIO()):
            self.run = history.collect(self.root, key="fixture-secret")
        self.accept()
        rows = self.rows(self.build(), "price_history_coverage.csv")
        affected = next(
            r for r in rows if r["itad_game_id"] == self.change()["old_game_id"]
        )
        self.assertEqual(affected["coverage_status"], "not_requested_assignment_review")
        self.assertEqual(affected["returned_event_count"], "")
        self.assertEqual((self.run / "assignment-changes.json").read_bytes(), raw)
        manifest = json.loads((self.run / "manifest.json").read_bytes())
        self.assertEqual(manifest["eligible_title_count"], 30)
        self.assertEqual(manifest["mapping_exclusion_count"], 1)
        self.assertEqual(manifest["assignment_exclusion_count"], 1)

    def test_assignment_raw_tamper_blocks_admission(self):
        self.accept()
        (self.run / "assignment-changes.json").write_bytes(b"[{}]")
        with self.assertRaises(ValueError):
            self.build()

    def test_assignment_cap_blocks_history_requests_and_admission(self):
        self.assignment_request.return_value = json.dumps(
            [self.change()] * 1000
        ).encode()
        with patch(
            "price_history.request_history"
        ) as fetch, contextlib.redirect_stdout(io.StringIO()):
            self.run = history.collect(self.root, key="fixture-secret")
        fetch.assert_not_called()
        self.accept()
        with self.assertRaisesRegex(ValueError, "did not pass"):
            self.build()
        self.assertFalse((self.root / "data/pricing-analysis/current.json").exists())

    def test_assignment_failure_blocks_history_and_secret_diagnostics(self):
        self.assignment_request.side_effect = RuntimeError("fixture-secret")
        with patch(
            "price_history.request_history"
        ) as fetch, contextlib.redirect_stdout(io.StringIO()):
            self.run = history.collect(self.root, key="fixture-secret")
        fetch.assert_not_called()
        self.assertNotIn("fixture-secret", (self.run / "manifest.json").read_text())

    def recollect_for_postflight(self, second):
        self.assignment_request.side_effect = [b"[]", second]
        with patch(
            "price_history.request_history", return_value=self.raw
        ), contextlib.redirect_stdout(io.StringIO()):
            self.run = history.collect(self.root, key="fixture-secret")

    def test_postflight_source_failure_blocks_admission_and_keeps_existing_release(
        self,
    ):
        self.accept()
        self.build()
        pointer = self.root / "data/pricing-analysis/current.json"
        before = pointer.read_bytes()
        self.recollect_for_postflight(RuntimeError("fixture-secret"))
        self.accept()
        with self.assertRaisesRegex(ValueError, "did not pass"):
            self.build()
        self.assertNotIn("fixture-secret", (self.run / "manifest.json").read_text())
        self.assertEqual(pointer.read_bytes(), before)

    def test_postflight_cap_blocks_admission_and_preserves_payload(self):
        raw = json.dumps([self.change()] * 1000).encode()
        self.recollect_for_postflight(raw)
        self.accept()
        with self.assertRaisesRegex(ValueError, "did not pass"):
            self.build()
        self.assertEqual(
            (self.run / "assignment-changes-postflight.json").read_bytes(), raw
        )

    def test_new_postflight_reassignment_invalidates_collected_history(self):
        raw = json.dumps([self.change()]).encode()
        self.recollect_for_postflight(raw)
        self.accept()
        with self.assertRaisesRegex(ValueError, "did not pass"):
            self.build()
        manifest = json.loads((self.run / "manifest.json").read_bytes())
        affected = next(
            t
            for t in manifest["title_coverage"]
            if t["itad_game_id"] == self.change()["old_game_id"]
        )
        self.assertEqual(
            affected["history_status"], "excluded_assignment_changed_during_collection"
        )
        self.assertEqual(
            (self.run / "assignment-changes-postflight.json").read_bytes(), raw
        )

    def test_postflight_timestamp_before_final_retrieval_blocks_admission(self):
        manifest = json.loads((self.run / "manifest.json").read_bytes())
        manifest["postflight_assignment_check"]["checked_through_utc"] = manifest[
            "started_at_utc"
        ]
        (self.run / "manifest.json").write_bytes(history.canonical(manifest) + b"\n")
        self.accept()
        with self.assertRaisesRegex(ValueError, "final history retrieval"):
            self.build()

    def test_postflight_raw_tamper_blocks_admission(self):
        self.accept()
        (self.run / "assignment-changes-postflight.json").write_bytes(b"[] ")
        with self.assertRaisesRegex(ValueError, "Postflight assignment evidence"):
            self.build()

    def test_assignment_malformed_future_and_date_mismatch_are_rejected(self):
        contract, scope = history.load_contract(self.root)
        for payload in (
            {"data": []},
            [{}],
            [dict(self.change(), date="Wed, 01 Jan 2020 00:00:00 +0000")],
            [dict(self.change(), timestamp=True)],
            [dict(self.change(), old_game_id="bad")],
        ):
            with self.subTest(payload=payload), self.assertRaises(
                (ValueError, TypeError)
            ):
                history.assignment_check(
                    json.dumps(payload).encode(),
                    scope,
                    contract,
                    "2026-10-06T23:00:00Z",
                )
        with self.assertRaises(ValueError):
            history.assignment_check(
                json.dumps([self.change()]).encode(),
                scope,
                contract,
                "2025-12-31T00:00:00Z",
            )

    @patch("price_history.time.sleep")
    @patch("price_history.requests.get")
    def test_assignment_request_uses_header_and_explicit_unix_since(self, get, sleep):
        self.assignment_patch.stop()
        get.return_value = Mock(status_code=200, content=b"[]")
        contract, _ = history.load_contract(self.root)
        history.request_assignments(contract, "fixture-secret")
        self.assertEqual(get.call_args.args[0], contract["assignment_endpoint"])
        self.assertEqual(
            get.call_args.kwargs["params"],
            {
                "since": int(history.instant(contract["window_start_utc"]).timestamp())
                - 1
            },
        )
        self.assertEqual(
            get.call_args.kwargs["headers"]["ITAD-API-Key"], "fixture-secret"
        )

    def test_source_failure_never_overwrites_existing_analysis(self):
        self.accept()
        self.build()
        pointer = self.root / "data/pricing-analysis/current.json"
        before = pointer.read_bytes()
        with patch(
            "price_history.request_history", side_effect=RuntimeError("fixture-secret")
        ), contextlib.redirect_stdout(io.StringIO()):
            self.run = history.collect(self.root, key="fixture-secret")
        self.accept()
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(pointer.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
