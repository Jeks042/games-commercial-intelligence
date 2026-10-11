import contextlib
from copy import deepcopy
import csv
from decimal import Decimal
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import commercial_scenarios as scenarios


class ScenarioMathTests(unittest.TestCase):
    def test_ten_percent_cut_requires_eleven_percent_extra_units_before_costs(self):
        r = scenarios.calculate(1000, "0.9", "1", "1")
        self.assertEqual(r["hypothetical_price_minor"], 900)
        self.assertEqual(r["gross_receipts_neutral_paid_unit_factor"], "1.111111")
        self.assertEqual(r["conditional_gross_receipts_index"], "90.000000")
        self.assertIn("not_supported", r["budget_decision"])

    def test_volume_above_required_threshold_can_raise_conditional_receipts(self):
        self.assertEqual(
            scenarios.calculate(1000, ".9", "1.2", "1")[
                "conditional_gross_receipts_index"
            ],
            "108.000000",
        )

    def test_engagement_never_changes_receipts_or_implies_paid_units(self):
        low = scenarios.calculate(1000, ".9", "1.2", ".8")
        high = scenarios.calculate(1000, ".9", "1.2", "1.2")
        self.assertEqual(
            low["conditional_gross_receipts_index"],
            high["conditional_gross_receipts_index"],
        )
        self.assertNotEqual(
            low["hypothetical_engagement_index"], high["hypothetical_engagement_index"]
        )

    def test_price_rounding_uses_pence_then_ratio_not_unrounded_percentage(self):
        r = scenarios.calculate(159, ".9", "1", "1")
        self.assertEqual(r["hypothetical_price_minor"], 143)
        self.assertEqual(r["rounded_price_factor"], "0.899371")
        self.assertEqual(r["gross_receipts_neutral_paid_unit_factor"], "1.111888")
        self.assertEqual(
            scenarios.calculate(5, ".9", "1", "1")["hypothetical_price_minor"], 5
        )

    def test_zero_paid_units_is_genuine_zero_receipts_under_positive_anchor(self):
        self.assertEqual(
            scenarios.calculate(1000, ".9", "0", "1")[
                "conditional_gross_receipts_index"
            ],
            "0.000000",
        )

    def test_zero_or_missing_baseline_never_becomes_infinite_break_even_or_fake_zero(
        self,
    ):
        for anchor in (0, None):
            r = scenarios.calculate(anchor, ".9", "1", "1")
            self.assertIsNone(r["conditional_gross_receipts_index"])
            self.assertIsNone(r["gross_receipts_neutral_paid_unit_factor"])

    def test_zero_hypothetical_price_preserves_zero_receipts_but_undefined_threshold(
        self,
    ):
        r = scenarios.calculate(1000, "0", "1", "1")
        self.assertEqual(r["conditional_gross_receipts_index"], "0.000000")
        self.assertIsNone(r["gross_receipts_neutral_paid_unit_factor"])
        self.assertIn("undefined", r["arithmetic_status"])

    def test_invalid_and_nonfinite_factors_rejected(self):
        for value in ("NaN", "Infinity", "-0.1", True, "nonsense"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scenarios.calculate(1000, ".9", value, "1")
        with self.assertRaises(ValueError):
            scenarios.calculate(1000, "1.1", "1", "1")
        with self.assertRaises(ValueError):
            scenarios.calculate("1.5", "1", "1", "1")


class ScenarioPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gaming-scenarios-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        contract = json.loads(
            (scenarios.ROOT / "data/benchmarking-contract.json").read_bytes()
        )
        for name in ("sql", contract["model_release_path"]):
            shutil.copytree(scenarios.ROOT / name, self.root / name)
        (self.root / "docs").mkdir()
        for name in (
            "docs/benchmark-metrics.csv",
            "data/benchmarking-contract.json",
            "data/scenario-contract.json",
        ):
            shutil.copyfile(scenarios.ROOT / name, self.root / name)
        self.model = self.root / contract["model_release_path"]

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return scenarios.build(self.root)

    def rows(self, release, name):
        return list(
            csv.DictReader(io.StringIO((release / name).read_text(encoding="utf-8")))
        )

    def test_public_build_has_scope_null_forecasts_and_identical_rerun(self):
        prior = {p.name: p.read_bytes() for p in self.model.iterdir()}
        release = self.build()
        before = {p.name: p.read_bytes() for p in release.iterdir()}
        self.assertEqual(self.build(), release)
        self.assertEqual(before, {p.name: p.read_bytes() for p in release.iterdir()})
        self.assertEqual(prior, {p.name: p.read_bytes() for p in self.model.iterdir()})
        expected = {
            "observed_anchors.csv": 12,
            "commercial_scenarios.csv": 48,
            "scenario_sensitivity.csv": 432,
            "receipts_neutral_thresholds.csv": 36,
            "forecast_readiness.csv": 12,
        }
        self.assertEqual(
            json.loads(before["build-manifest.json"])["row_counts"], expected
        )
        contract = json.loads((self.root / "data/scenario-contract.json").read_bytes())
        for r in self.rows(release, "forecast_readiness.csv"):
            self.assertEqual(r["qualifying_comparable_weeks"], "0")
            self.assertEqual(r["accepted_observation_count"], "1")
            self.assertTrue(all(r[k] == "" for k in contract["unsupported_measures"]))
        for r in self.rows(release, "commercial_scenarios.csv"):
            self.assertEqual(r["forecast_status"], "not_a_forecast")

    def test_tampered_model_cannot_publish(self):
        p = self.model / "v_latest_steam_metrics.csv"
        p.write_bytes(p.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Model input hash differs"):
            self.build()
        self.assertFalse((self.root / "data/scenarios/current.json").exists())

    def evaluate_changed_observation(self, **changes):
        def read(name):
            with (self.model / name).open(encoding="utf-8", newline="") as handle:
                return list(csv.DictReader(handle))

        observations = read("v_latest_steam_metrics.csv")
        target = next(r for r in observations if r["cohort"] == "portfolio")
        target.update(changes)
        readiness = {r["app_id"]: r for r in read("v_momentum_readiness.csv")}
        contract = json.loads((self.root / "data/scenario-contract.json").read_bytes())
        outputs = scenarios.evaluate(observations, readiness, {}, contract)
        rows = list(
            csv.DictReader(io.StringIO(outputs["commercial_scenarios.csv"].decode()))
        )
        return target, [r for r in rows if r["app_id"] == target["app_id"]]

    def test_wrong_currency_and_unavailable_price_do_not_enter_economics(self):
        for changes in (
            {"currency": "USD"},
            {"price_status": "unavailable"},
            {"coming_soon": "1"},
            {"steam_store_status": "error"},
        ):
            with self.subTest(changes=changes):
                _, rows = self.evaluate_changed_observation(**changes)
                self.assertTrue(
                    all(r["conditional_gross_receipts_index"] == "" for r in rows)
                )

    def test_missing_observed_price_is_unavailable_not_zero(self):
        _, rows = self.evaluate_changed_observation(final_price_minor="")
        self.assertTrue(
            all(
                r["hypothetical_price_minor"] == ""
                and r["conditional_gross_receipts_index"] == ""
                for r in rows
            )
        )

    def test_duplicate_title_rows_cannot_duplicate_scenario_scope(self):
        with (self.model / "v_latest_steam_metrics.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            observations = list(csv.DictReader(handle))
        observations.append(next(r for r in observations if r["cohort"] == "portfolio"))
        contract = json.loads((self.root / "data/scenario-contract.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "duplicated"):
            scenarios.evaluate(observations, {}, {}, contract)

    def test_unaccepted_model_contract_cannot_publish(self):
        p = self.root / "data/benchmarking-contract.json"
        c = json.loads(p.read_bytes())
        c["status"] = "pending"
        p.write_text(json.dumps(c), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "accepted benchmark contract"):
            self.build()

    def test_existing_release_tamper_does_not_move_pointer(self):
        release = self.build()
        pointer = self.root / "data/scenarios/current.json"
        before = pointer.read_bytes()
        (release / "commercial_scenarios.csv").write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "release differs"):
            self.build()
        self.assertEqual(before, pointer.read_bytes())

    def test_contract_changes_create_separate_release_without_overwriting_prior(self):
        release = self.build()
        before = {p.name: p.read_bytes() for p in release.iterdir()}
        p = self.root / "data/scenario-contract.json"
        c = json.loads(p.read_bytes())
        c["scenarios"][2]["paid_unit_factor"] = "1.3"
        p.write_text(json.dumps(c), encoding="utf-8")
        changed = self.build()
        self.assertNotEqual(changed, release)
        self.assertEqual(before, {p.name: p.read_bytes() for p in release.iterdir()})

    def test_unsupported_measure_inventory_cannot_be_removed(self):
        c = json.loads((self.root / "data/scenario-contract.json").read_bytes())
        c["unsupported_measures"].remove("roi")
        with self.assertRaisesRegex(ValueError, "inventory"):
            scenarios.validate_contract(c)

    def test_duplicate_grid_cells_and_nonunit_hold_reference_rejected(self):
        c = json.loads((self.root / "data/scenario-contract.json").read_bytes())
        d = deepcopy(c)
        d["sensitivity"]["price_factors"].append("1.0")
        with self.assertRaisesRegex(ValueError, "unique"):
            scenarios.validate_contract(d)
        c["scenarios"][0]["paid_unit_factor"] = "1.1"
        with self.assertRaisesRegex(ValueError, "Hold reference"):
            scenarios.validate_contract(c)


if __name__ == "__main__":
    unittest.main()
