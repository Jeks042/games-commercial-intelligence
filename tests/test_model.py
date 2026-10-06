import contextlib
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import build_model as model


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gaming-model-test-")
        self.root = Path(self.temp.name).resolve()
        self.data = self.root / "data"
        self.data.mkdir()
        self.output = self.root / "analytical"
        for name in (
            "portfolio-titles.csv",
            "competitor-titles.csv",
            "title-references.csv",
            "accepted-runs.json",
        ):
            shutil.copyfile(model.ROOT / "data" / name, self.data / name)
        shutil.copytree(model.ROOT / "data" / "runs", self.data / "runs")
        self.register = json.loads(
            (self.data / "accepted-runs.json").read_text(encoding="utf-8")
        )
        self.steam_entry = next(
            e for e in self.register["accepted_runs"] if e["source_layer"] == "steam"
        )
        self.spy_entry = next(
            e for e in self.register["accepted_runs"] if e["source_layer"] == "steamspy"
        )

    def tearDown(self):
        if Path(self.temp.name).resolve() != self.root or not self.root.name.startswith(
            "gaming-model-test-"
        ):
            raise RuntimeError("Unsafe test-fixture cleanup path")
        self.temp.cleanup()

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return model.build_model(self.data, self.output)

    def rows(self, release, filename):
        with (release / filename).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def save_register(self):
        (self.data / "accepted-runs.json").write_text(
            json.dumps(self.register), encoding="utf-8"
        )

    def rewrite_run(self, entry, transform=None, manifest_transform=None):
        folder = self.data / "runs" / entry["run_id"]
        fields, rows = model.read_csv(folder / "observations.csv")
        if transform:
            transform(rows)
        with (folder / "observations.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        manifest["observations_sha256"] = model.sha(
            (folder / "observations.csv").read_bytes()
        )
        if manifest_transform:
            manifest_transform(manifest)
        (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        entry["observations_sha256"] = manifest["observations_sha256"]
        entry["manifest_canonical_sha256"] = model.sha(model.canonical(manifest))
        self.save_register()

    def weekly_runs(
        self,
        weeks=4,
        start="2026-09-07",
        review_additions=None,
        first_players=100,
        change_last_query=False,
    ):
        source = self.data / "runs" / self.steam_entry["run_id"]
        original_manifest = json.loads(
            (source / "manifest.json").read_text(encoding="utf-8")
        )
        fields, original_rows = model.read_csv(source / "observations.csv")
        for index in range(weeks):
            stamp = datetime.fromisoformat(start).replace(
                hour=6, minute=15, tzinfo=timezone.utc
            ) + timedelta(weeks=index)
            run_id = f"steam-fixture-{index}"
            folder = self.data / "runs" / run_id
            folder.mkdir()
            rows = [dict(row) for row in original_rows]
            addition = review_additions[index] if review_additions else 100 * index
            for row in rows:
                row["run_id"] = run_id
                row["snapshot_timestamp_utc"] = stamp.isoformat()
                for source_name in ("steam_store", "steam_reviews", "current_players"):
                    row[source_name + "_retrieved_at_utc"] = (
                        stamp + timedelta(minutes=1)
                    ).isoformat()
                row["current_players"] = str(
                    first_players if index == 0 else 100 + 10 * index
                )
                row["total_positive_reviews"] = str(
                    int(row["total_positive_reviews"]) + addition
                )
                row["total_reviews"] = str(int(row["total_reviews"]) + addition)
                if change_last_query and index == weeks - 1:
                    row["review_query_version"] = "fixture-other-purchase-contract"
            with (folder / "observations.csv").open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            manifest = json.loads(json.dumps(original_manifest))
            manifest.update(
                run_id=run_id,
                started_at_utc=stamp.isoformat(),
                finished_at_utc=(stamp + timedelta(minutes=2)).isoformat(),
                observations_sha256=model.sha(
                    (folder / "observations.csv").read_bytes()
                ),
            )
            if change_last_query and index == weeks - 1:
                manifest["source_contracts"]["steam_reviews"][
                    "query_version"
                ] = "fixture-other-purchase-contract"
                manifest["source_contracts"]["steam_reviews"]["purchase_type"] = 0
            (folder / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            self.register["accepted_runs"].append(
                {
                    **self.steam_entry,
                    "run_id": run_id,
                    "observations_sha256": manifest["observations_sha256"],
                    "manifest_canonical_sha256": model.sha(model.canonical(manifest)),
                }
            )
        self.save_register()

    def test_baseline_has_only_accepted_facts_and_null_trends(self):
        release = self.build()
        manifest = json.loads((release / "build-manifest.json").read_text())
        self.assertEqual(manifest["row_counts"]["fact_steam_observation"], 32)
        self.assertEqual(manifest["row_counts"]["fact_external_benchmark"], 32)
        self.assertEqual(manifest["row_counts"]["bridge_title_reference"], 38)
        self.assertEqual(len(self.rows(release, "dim_date.csv")), 365)
        self.assertTrue(
            all(
                r["player_change_3weeks_percent"] == ""
                and r["comparable_week_count"] == "0"
                for r in self.rows(release, "v_momentum_readiness.csv")
            )
        )
        self.assertTrue(
            all(
                r["average_playtime_forever_minutes"] == ""
                and r["owner_estimate_status"] == "requires_review"
                for r in self.rows(release, "fact_external_benchmark.csv")
            )
        )
        self.assertTrue(all(n == 0 for n in manifest["quality_checks"].values()))

    def test_rerun_is_byte_identical_and_does_not_duplicate_facts(self):
        release = self.build()
        before = {p.name: p.read_bytes() for p in release.iterdir()}
        self.assertEqual(self.build(), release)
        self.assertEqual(before, {p.name: p.read_bytes() for p in release.iterdir()})

    def test_unregistered_passed_run_never_enters_model_or_changes_release(self):
        release = self.build()
        shutil.copytree(
            self.data / "runs" / self.steam_entry["run_id"],
            self.data / "runs" / "unreviewed-run",
        )
        self.assertEqual(self.build(), release)
        self.assertEqual(len(self.rows(release, "fact_steam_observation.csv")), 32)

    def test_changed_observation_hash_blocks_publication(self):
        release = self.build()
        pointer = (self.output / "current.json").read_bytes()
        source = self.data / "runs" / self.steam_entry["run_id"] / "observations.csv"
        with source.open("a", encoding="utf-8") as handle:
            handle.write("unexpected\n")
        with self.assertRaisesRegex(ValueError, "Observation hash"):
            self.build()
        self.assertEqual((self.output / "current.json").read_bytes(), pointer)
        self.assertTrue(release.exists())

    def test_changed_manifest_blocks_admission(self):
        source = self.data / "runs" / self.steam_entry["run_id"] / "manifest.json"
        manifest = json.loads(source.read_text(encoding="utf-8"))
        manifest["status"] = "failed"
        source.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "reviewed acceptance"):
            self.build()

    def test_reviewed_but_failed_v2_run_is_rejected(self):
        self.rewrite_run(
            self.steam_entry, manifest_transform=lambda m: m.update(status="failed")
        )
        with self.assertRaisesRegex(ValueError, "passed schema-v2"):
            self.build()

    def test_partial_coverage_rejected_even_with_reviewed_hash(self):
        self.rewrite_run(
            self.steam_entry,
            manifest_transform=lambda m: m["coverage"].update(steam_reviews=31),
        )
        with self.assertRaisesRegex(ValueError, "incomplete source coverage"):
            self.build()

    def test_failed_row_cannot_become_zero(self):
        self.rewrite_run(
            self.steam_entry,
            lambda rows: rows[0].update(
                current_players_status="source_failed", current_players="0"
            ),
        )
        with self.assertRaisesRegex(ValueError, "failed source"):
            self.build()

    def test_valid_zero_players_preserved_and_zero_reviews_ratio_is_null(self):
        self.rewrite_run(
            self.steam_entry,
            lambda rows: rows[0].update(
                current_players="0",
                total_reviews="0",
                total_positive_reviews="0",
                total_negative_reviews="0",
            ),
        )
        release = self.build()
        zero = next(
            r
            for r in self.rows(release, "v_steam_metrics.csv")
            if r["total_reviews"] == "0"
        )
        self.assertEqual(zero["current_players"], "0")
        self.assertEqual(zero["lifetime_review_positive_percent"], "")

    def test_review_reconciliation_is_enforced_in_sql(self):
        self.rewrite_run(
            self.steam_entry,
            lambda rows: rows[0].update(
                total_reviews=str(int(rows[0]["total_reviews"]) + 1)
            ),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.build()

    def test_price_quality_failure_keeps_previous_release(self):
        self.build()
        pointer = (self.output / "current.json").read_bytes()
        self.rewrite_run(
            self.steam_entry, lambda rows: rows[0].update(discount_percent="99")
        )
        with self.assertRaisesRegex(ValueError, "quality gate"):
            self.build()
        self.assertEqual((self.output / "current.json").read_bytes(), pointer)

    def test_zero_playtime_cannot_leak_as_measured_value(self):
        self.rewrite_run(
            self.spy_entry,
            lambda rows: rows[0].update(average_playtime_forever_minutes="0"),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.build()

    def test_peer_median_and_index_with_full_three_peer_coverage(self):
        prices = {"1971650": 1000, "1244090": 2000, "1229240": 4000, "1658280": 3000}

        def transform(rows):
            for row in rows:
                if row["app_id"] in prices:
                    row.update(
                        list_price_minor=str(prices[row["app_id"]]),
                        final_price_minor=str(prices[row["app_id"]]),
                        discount_percent="0",
                    )

        self.rewrite_run(self.steam_entry, transform)
        release = self.build()
        report = next(
            r
            for r in self.rows(release, "v_price_reference.csv")
            if r["app_id"] == "1658280"
        )
        self.assertEqual(float(report["direct_reference_median_price_gbp"]), 20)
        self.assertEqual(float(report["direct_reference_price_index"]), 1.5)
        self.assertEqual(report["reference_status"], "available")

    def test_missing_direct_quote_suppresses_price_reference(self):
        def transform(rows):
            for row in rows:
                if row["app_id"] == "1244090":
                    row.update(
                        price_status="unavailable",
                        currency="",
                        list_price_minor="",
                        final_price_minor="",
                        discount_percent="",
                    )

        self.rewrite_run(self.steam_entry, transform)
        report = next(
            r
            for r in self.rows(self.build(), "v_price_reference.csv")
            if r["app_id"] == "1658280"
        )
        self.assertEqual(report["reference_status"], "incomplete_same_day_coverage")
        self.assertEqual(report["direct_reference_price_index"], "")

    def test_nonconsecutive_periods_do_not_release_momentum(self):
        self.weekly_runs(weeks=5, start="2026-08-31")
        self.register["accepted_runs"] = [
            e
            for e in self.register["accepted_runs"]
            if e["run_id"] != "steam-fixture-2"
        ]
        self.save_register()
        report = self.rows(self.build(), "v_momentum_readiness.csv")[0]
        self.assertEqual(report["comparable_week_count"], "4")
        self.assertEqual(report["player_momentum_status"], "nonconsecutive_periods")
        self.assertEqual(report["player_change_3weeks_percent"], "")

    def test_sparse_reference_group_returns_null_not_a_rank(self):
        release = self.build()
        report = next(
            r
            for r in self.rows(release, "v_price_reference.csv")
            if r["app_id"] == "1649010"
        )
        self.assertEqual(report["reference_status"], "insufficient_reference_count")
        self.assertEqual(report["direct_reference_price_index"], "")
        self.assertEqual(report["direct_reference_median_price_gbp"], "")

    def test_early_access_and_curated_lifecycle_are_distinct(self):
        release = self.build()
        report = next(
            r
            for r in self.rows(release, "v_steam_metrics.csv")
            if r["app_id"] == "3058630"
        )
        self.assertEqual(report["analytical_lifecycle"], "early_access")
        self.assertEqual(report["curated_lifecycle_role"], "Growth / early access")
        self.assertGreater(int(report["title_age_days"]), 0)

    def test_naive_and_non_utc_timestamps_rejected(self):
        for value in ("2026-10-06T12:00:00", "2026-10-06T12:00:00+01:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                model.utc(value)

    def test_four_consecutive_comparable_weeks_release_derived_metrics(self):
        self.weekly_runs()
        report = self.rows(self.build(), "v_momentum_readiness.csv")[0]
        self.assertEqual(report["comparable_week_count"], "4")
        self.assertEqual(report["player_momentum_status"], "available")
        self.assertEqual(float(report["player_change_3weeks_percent"]), 30)
        self.assertAlmostEqual(
            float(report["review_velocity_per_day"]), 300 / 21, places=3
        )

    def test_three_weeks_are_insufficient(self):
        self.weekly_runs(weeks=3)
        report = self.rows(self.build(), "v_momentum_readiness.csv")[0]
        self.assertEqual(
            report["player_momentum_status"], "insufficient_comparable_history"
        )
        self.assertEqual(report["player_change_3weeks_percent"], "")

    def test_query_contract_change_cannot_manufacture_four_week_series(self):
        self.weekly_runs(change_last_query=True)
        report = self.rows(self.build(), "v_momentum_readiness.csv")[0]
        self.assertEqual(report["comparable_week_count"], "3")
        self.assertEqual(report["review_velocity_per_day"], "")

    def test_stale_comparable_series_is_unavailable(self):
        self.weekly_runs(start="2026-08-31")
        report = self.rows(self.build(), "v_momentum_readiness.csv")[0]
        self.assertEqual(report["player_momentum_status"], "stale_history")
        self.assertEqual(report["player_change_3weeks_percent"], "")

    def test_zero_baseline_change_is_undefined(self):
        self.weekly_runs(first_players=0)
        report = self.rows(self.build(), "v_momentum_readiness.csv")[0]
        self.assertEqual(report["player_momentum_status"], "zero_baseline")
        self.assertEqual(report["player_change_3weeks_percent"], "")

    def test_intermediate_review_count_revision_suppresses_velocity(self):
        self.weekly_runs(review_additions=[0, 100, 50, 300])
        report = self.rows(self.build(), "v_momentum_readiness.csv")[0]
        self.assertEqual(report["review_velocity_status"], "source_revision")
        self.assertEqual(report["review_velocity_per_day"], "")


if __name__ == "__main__":
    unittest.main()
