import contextlib
import csv
import io
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import benchmark_portfolio as analysis


class PositioningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gaming-positioning-test-")
        self.root = Path(self.temp.name).resolve()
        self.data = self.root / "data"
        self.data.mkdir()
        shutil.copytree(analysis.ROOT / "sql", self.root / "sql")
        (self.root / "docs").mkdir()
        shutil.copyfile(
            analysis.ROOT / "docs" / "benchmark-metrics.csv",
            self.root / "docs" / "benchmark-metrics.csv",
        )
        contract = json.loads(
            (analysis.ROOT / "data" / "benchmarking-contract.json").read_text()
        )
        release_path = contract["model_release_path"]
        shutil.copytree(
            analysis.ROOT / release_path,
            self.root / release_path,
            ignore=shutil.ignore_patterns("*.sqlite"),
        )
        self.contract_path = self.data / "benchmarking-contract.json"
        self.contract_path.write_text(json.dumps(contract))
        self.output = self.data / "positioning"
        _, release, manifest = analysis.verified_inputs(self.root, self.contract_path)
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        analysis.load_model(self.connection, self.root, release, manifest)
        self.connection.executescript(
            (self.root / "sql" / "benchmarking" / "01_positioning.sql").read_text()
        )

    def tearDown(self):
        self.connection.close()
        if Path(self.temp.name).resolve() != self.root or not self.root.name.startswith(
            "gaming-positioning-test-"
        ):
            raise RuntimeError("Unsafe positioning fixture cleanup")
        self.temp.cleanup()

    def benchmark(self, metric, app_id=1658280):
        return dict(
            self.connection.execute(
                "SELECT * FROM v_direct_peer_benchmark WHERE app_id=? AND metric=?",
                (app_id, metric),
            ).fetchone()
        )

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return analysis.build(self.root, self.output, self.contract_path)

    def test_complete_baseline_without_overall_classification(self):
        rows = self.connection.execute(
            "SELECT * FROM v_portfolio_positioning"
        ).fetchall()
        self.assertEqual(len(rows), 12)
        self.assertTrue(
            all(
                r["overall_performance_classification"] == "not_assessed_snapshot_only"
                for r in rows
            )
        )
        self.assertTrue(
            all(
                r["player_change_3weeks_percent"] is None
                and r["review_velocity_per_day"] is None
                for r in rows
            )
        )
        self.assertTrue(
            all(r["engagement_depth_status"] == "unavailable_playtime" for r in rows)
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM v_reference_pair_context"
            ).fetchone()[0],
            38,
        )

    def test_known_jrpg_medians_and_reference_percentiles(self):
        price = self.benchmark("final_price_gbp")
        self.assertEqual(price["direct_peer_median"], 14.75)
        self.assertEqual(price["target_to_median_ratio"], 0.9146)
        self.assertEqual(price["reference_empirical_percentile"], 33.3333)
        reviews = self.benchmark("lifetime_review_positive_percent")
        self.assertEqual(reviews["direct_peer_median"], 88.5819)
        self.assertEqual(reviews["target_minus_median"], -13.2397)
        self.assertIsNone(reviews["target_to_median_ratio"])
        self.assertEqual(reviews["lifecycle_context"], "mixed_lifecycle_unadjusted")
        self.assertEqual(
            self.benchmark("lifetime_review_count")["direct_peer_median"], 15646
        )
        self.assertEqual(self.benchmark("current_players")["direct_peer_median"], 385)

    def test_sparse_reference_sets_do_not_generate_group_statistics(self):
        rows = self.connection.execute(
            "SELECT * FROM v_direct_peer_benchmark WHERE app_id<>1658280"
        ).fetchall()
        self.assertEqual(len(rows), 44)
        self.assertTrue(
            all(r["benchmark_status"] == "insufficient_direct_peers" for r in rows)
        )
        for r in rows:
            for col in (
                "direct_peer_median",
                "target_minus_median",
                "target_to_median_ratio",
                "reference_empirical_percentile",
            ):
                self.assertIsNone(r[col])

    def test_adjacent_and_leader_references_never_fill_sparse_groups(self):
        row = self.benchmark("current_players", 2277560)
        self.assertEqual(row["expected_reference_count"], 2)
        self.assertIsNone(row["direct_peer_median"])
        self.assertEqual(
            self.connection.execute(
                "SELECT COUNT(*) FROM v_reference_pair_context WHERE portfolio_app_id=2277560"
            ).fetchone()[0],
            4,
        )

    def test_missing_quote_suppresses_price_only(self):
        self.connection.execute(
            "UPDATE fact_steam_observation SET price_status='unavailable',currency=NULL,list_price_minor=NULL,final_price_minor=NULL,discount_percent_reported=NULL WHERE app_id=1229240"
        )
        self.assertEqual(
            self.benchmark("final_price_gbp")["benchmark_status"],
            "incomplete_comparable_coverage",
        )
        self.assertIsNone(self.benchmark("final_price_gbp")["direct_peer_median"])
        self.assertEqual(
            self.benchmark("current_players")["benchmark_status"],
            "available_unadjusted_snapshot",
        )

    def test_low_review_count_suppresses_positivity_only(self):
        self.connection.execute(
            "UPDATE fact_steam_observation SET total_positive_reviews=99,total_negative_reviews=0,total_reviews=99 WHERE app_id=1229240"
        )
        self.assertEqual(
            self.benchmark("lifetime_review_positive_percent")["benchmark_status"],
            "incomplete_comparable_coverage",
        )
        self.assertEqual(
            self.benchmark("lifetime_review_count")["benchmark_status"],
            "available_unadjusted_snapshot",
        )

    def test_different_retrieval_window_suppresses_player_comparison(self):
        self.connection.execute(
            "UPDATE fact_steam_observation SET current_players_retrieved_at_utc='2026-10-06T20:46:00+00:00' WHERE app_id=1229240"
        )
        self.assertEqual(
            self.benchmark("current_players")["benchmark_status"],
            "incomplete_comparable_coverage",
        )
        self.assertEqual(
            self.benchmark("final_price_gbp")["benchmark_status"],
            "available_unadjusted_snapshot",
        )

    def test_different_source_date_suppresses_even_near_midnight(self):
        self.connection.execute(
            "UPDATE fact_steam_observation SET current_players_retrieved_at_utc='2026-10-06T23:59:30+00:00' WHERE app_id=1658280"
        )
        self.connection.execute(
            "UPDATE fact_steam_observation SET current_players_retrieved_at_utc='2026-10-07T00:00:30+00:00' WHERE app_id IN (1229240,1244090,1971650)"
        )
        self.assertIsNone(self.benchmark("current_players")["direct_peer_median"])

    def test_different_review_contract_suppresses_review_comparison(self):
        columns = [r[1] for r in self.connection.execute("PRAGMA table_info(dim_run)")]
        row = dict(
            self.connection.execute(
                "SELECT * FROM dim_run WHERE source_layer='steam'"
            ).fetchone()
        )
        row["run_id"], row["review_contract_sha256"] = (
            "test-new-contract",
            "different-contract",
        )
        self.connection.execute(
            "INSERT INTO dim_run VALUES (" + ",".join("?" for _ in columns) + ")",
            [row[col] for col in columns],
        )
        self.connection.execute(
            "UPDATE fact_steam_observation SET run_id='test-new-contract' WHERE app_id=1229240"
        )
        self.assertIsNone(
            self.benchmark("lifetime_review_positive_percent")["direct_peer_median"]
        )
        self.assertIsNone(self.benchmark("lifetime_review_count")["direct_peer_median"])
        self.assertEqual(
            self.benchmark("current_players")["benchmark_status"],
            "available_unadjusted_snapshot",
        )

    def test_zero_players_are_valid_without_division_by_zero(self):
        self.connection.execute(
            "UPDATE fact_steam_observation SET current_players=0 WHERE app_id IN (1229240,1244090,1971650)"
        )
        row = self.benchmark("current_players")
        self.assertEqual(row["direct_peer_median"], 0)
        self.assertIsNone(row["target_to_median_ratio"])
        self.assertEqual(row["ratio_status"], "zero_reference_median")
        self.assertEqual(row["reference_empirical_percentile"], 100)

    def test_zero_target_keeps_valid_zero_ratio(self):
        self.connection.execute(
            "UPDATE fact_steam_observation SET current_players=0 WHERE app_id=1658280"
        )
        self.assertEqual(self.benchmark("current_players")["target_to_median_ratio"], 0)
        self.assertEqual(self.benchmark("current_players")["ratio_status"], "available")

    def test_midpoint_ties_are_explicit(self):
        self.connection.execute(
            "UPDATE fact_steam_observation SET current_players=100 WHERE app_id IN (1658280,1229240,1244090,1971650)"
        )
        self.assertEqual(
            self.benchmark("current_players")["reference_empirical_percentile"], 50
        )

    def test_even_median_uses_both_central_values(self):
        row = dict(
            self.connection.execute(
                "SELECT * FROM dim_title WHERE app_id=1229240"
            ).fetchone()
        )
        row["app_id"], row["title"] = 999999, "Synthetic fourth JRPG reference"
        self.connection.execute(
            "INSERT INTO dim_title VALUES (" + ",".join("?" for _ in row) + ")",
            list(row.values()),
        )
        fact = dict(
            self.connection.execute(
                "SELECT * FROM fact_steam_observation WHERE app_id=1229240"
            ).fetchone()
        )
        fact["app_id"], fact["current_players"] = 999999, 500
        self.connection.execute(
            "INSERT INTO fact_steam_observation VALUES ("
            + ",".join("?" for _ in fact)
            + ")",
            list(fact.values()),
        )
        self.connection.execute(
            "INSERT INTO bridge_title_reference VALUES (1658280,999999,'direct_peer','Synthetic fourth reference for even-median validation')"
        )
        self.assertEqual(self.benchmark("current_players")["direct_peer_median"], 442.5)

    def test_early_access_is_preserved_without_lifecycle_adjustment(self):
        rows = self.connection.execute(
            "SELECT * FROM v_portfolio_positioning WHERE early_access_genre_flag=1"
        ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["analytical_lifecycle"] == "early_access" for r in rows))
        pair = self.connection.execute(
            "SELECT * FROM v_reference_pair_context WHERE portfolio_app_id=3058630 AND reference_app_id=2399420"
        ).fetchone()
        self.assertEqual(pair["lifecycle_context"], "different_lifecycle_unadjusted")

    def test_all_comparisons_expose_counts_roles_and_source_times(self):
        row = self.benchmark("current_players")
        for col in (
            "target_at_utc",
            "first_reference_at_utc",
            "last_reference_at_utc",
            "run_id",
            "peer_role",
            "lifecycle_context",
        ):
            self.assertTrue(row[col])
        self.assertEqual(row["expected_reference_count"], 3)
        self.assertEqual(row["valid_reference_count"], 3)

    def test_model_manifest_tamper_is_rejected(self):
        contract = json.loads(self.contract_path.read_text())
        manifest = self.root / contract["model_release_path"] / "build-manifest.json"
        manifest.write_bytes(manifest.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "manifest hash"):
            self.build()

    def test_source_export_tamper_is_rejected_and_pointer_preserved(self):
        self.build()
        pointer = (self.output / "current.json").read_bytes()
        contract = json.loads(self.contract_path.read_text())
        csv_path = (
            self.root / contract["model_release_path"] / "fact_steam_observation.csv"
        )
        csv_path.write_bytes(csv_path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "input hash"):
            self.build()
        self.assertEqual((self.output / "current.json").read_bytes(), pointer)

    def test_unaccepted_contract_is_rejected(self):
        contract = json.loads(self.contract_path.read_text())
        contract["status"] = "pending"
        self.contract_path.write_text(json.dumps(contract))
        with self.assertRaisesRegex(ValueError, "accepted benchmark contract"):
            self.build()

    def test_pinned_model_sql_drift_is_rejected(self):
        path = self.root / "sql" / "02_reporting_views.sql"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "model SQL hash"):
            self.build()

    def test_metric_dictionary_drift_is_rejected(self):
        path = self.root / "docs" / "benchmark-metrics.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "metric dictionary hash"):
            self.build()

    def test_build_repeats_byte_identically_and_checks_quality(self):
        first = self.build()
        hashes = {p.name: analysis.sha(p.read_bytes()) for p in first.iterdir()}
        self.assertEqual(first, self.build())
        self.assertEqual(
            hashes, {p.name: analysis.sha(p.read_bytes()) for p in first.iterdir()}
        )
        manifest = json.loads((first / "build-manifest.json").read_text())
        self.assertTrue(
            all(value == 0 for value in manifest["quality_checks"].values())
        )
        with (first / "v_direct_peer_benchmark.csv").open(newline="") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 48)

    def test_existing_output_tamper_is_rejected(self):
        release = self.build()
        path = release / "v_portfolio_positioning.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Existing positioning release differs"):
            self.build()

    def test_quality_gate_failure_leaves_no_published_pointer(self):
        path = self.root / "sql" / "benchmarking" / "02_quality_checks.sql"
        path.write_text("SELECT 'forced_quality_violation',1;")
        with self.assertRaisesRegex(ValueError, "Positioning quality gate"):
            self.build()
        self.assertFalse((self.output / "current.json").exists())


if __name__ == "__main__":
    unittest.main()
