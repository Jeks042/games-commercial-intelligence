import base64
import contextlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import build_executive_report as report


class ExecutiveReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="games-executive-test-")
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "dashboard"

    def build(self, root=report.ROOT):
        with contextlib.redirect_stdout(io.StringIO()):
            return report.build(root, self.output)

    def test_embedded_model_reconciles_all_tables_and_preserves_nulls(self):
        self.build()
        model = json.loads(
            (self.output / "Games.SemanticModel/model.bim").read_bytes()
        )["model"]
        expected = {
            "Portfolio": 12,
            "References": 38,
            "PeerBenchmark": 48,
            "Price": 12,
            "PriceComparison": 12,
            "Reviews": 12,
            "ReviewCohorts": 24,
            "Scenarios": 48,
            "Forecast": 12,
            "Investigation": 12,
            "Recommendations": 12,
            "DecisionPolicy": 5,
            "Summary": 1,
        }
        for table in model["tables"]:
            expression = "\n".join(table["partitions"][0]["source"]["expression"])
            encoded = re.search(r'Binary.FromText\("([^"]+)"', expression).group(1)
            embedded = json.loads(base64.b64decode(encoded))
            aggregate = json.loads(
                (self.output / "aggregates" / (table["name"] + ".json")).read_bytes()
            )
            self.assertEqual(embedded, aggregate)
            self.assertEqual(len(embedded), expected[table["name"]])
            self.assertNotIn("File.Contents", expression)
            self.assertNotIn("Web.Contents", expression)
        forecasts = json.loads((self.output / "aggregates/Forecast.json").read_bytes())
        self.assertTrue(
            all(
                r["forecast_mae"] is None
                and r["roi"] is None
                and r["predicted_paid_units"] is None
                for r in forecasts
            )
        )
        summary = json.loads((self.output / "aggregates/Summary.json").read_bytes())[0]
        self.assertEqual(summary["qualified_direct_group_titles"], 1)
        self.assertEqual(summary["budget_approvals"], 0)

    def test_filter_model_uses_unique_portfolio_identity_and_single_direction(self):
        self.build()
        model = json.loads(
            (self.output / "Games.SemanticModel/model.bim").read_bytes()
        )["model"]
        portfolio = json.loads((self.output / "aggregates/Portfolio.json").read_bytes())
        keys = {r["app_id"] for r in portfolio}
        self.assertEqual(len(keys), 12)
        for rel in model["relationships"]:
            self.assertEqual(rel["toTable"], "Portfolio")
            self.assertEqual(rel["crossFilteringBehavior"], "oneDirection")
            rows = json.loads(
                (self.output / "aggregates" / (rel["fromTable"] + ".json")).read_bytes()
            )
            self.assertTrue(all(r[rel["fromColumn"]] in keys for r in rows))

    def test_rebuild_is_identical_and_does_not_mutate_source_contract(self):
        before = (report.ROOT / "data/executive-input-contract.json").read_bytes()
        self.build()
        files = {
            p.relative_to(self.output): p.read_bytes()
            for p in self.output.rglob("*")
            if p.is_file()
        }
        self.build()
        self.assertEqual(
            files,
            {
                p.relative_to(self.output): p.read_bytes()
                for p in self.output.rglob("*")
                if p.is_file()
            },
        )
        self.assertEqual(
            before, (report.ROOT / "data/executive-input-contract.json").read_bytes()
        )

    def test_edited_dashboard_is_preserved_instead_of_overwritten(self):
        self.build()
        p = self.output / "Games.SemanticModel/model.bim"
        p.write_bytes(b"user edit")
        with self.assertRaisesRegex(ValueError, "preserve edits"):
            self.build()
        self.assertEqual(p.read_bytes(), b"user edit")

    def test_visual_fields_resolve_and_title_drillthrough_binds_shared_dimension(self):
        self.build()
        model = json.loads(
            (self.output / "Games.SemanticModel/model.bim").read_bytes()
        )["model"]
        lookup = {
            t["name"]: {
                "Column": {c["name"] for c in t["columns"]},
                "Measure": {m["name"] for m in t["measures"]},
            }
            for t in model["tables"]
        }
        for file in self.output.glob(
            "Games.Report/definition/pages/*/visuals/*/visual.json"
        ):
            v = json.loads(file.read_bytes())
            for projection in (
                v["visual"]
                .get("query", {})
                .get("queryState", {})
                .get("Values", {})
                .get("projections", [])
            ):
                kind, expr = next(iter(projection["field"].items()))
                self.assertIn(
                    expr["Property"],
                    lookup[expr["Expression"]["SourceRef"]["Entity"]][kind],
                )
            p = v["position"]
            self.assertTrue(
                p["x"] >= 0
                and p["y"] >= 0
                and p["x"] + p["width"] <= 1440
                and p["y"] + p["height"] <= 900
            )
        page = json.loads(
            (
                self.output / "Games.Report/definition/pages/02_Title/page.json"
            ).read_bytes()
        )
        self.assertEqual(page["type"], "Drillthrough")
        self.assertEqual(
            page["pageBinding"]["parameters"][0]["boundFilter"],
            page["filterConfig"]["filters"][0]["name"],
        )
        self.assertEqual(
            page["pageBinding"]["parameters"][0]["fieldExpr"],
            report.field("Portfolio", "title"),
        )

    def test_dated_recommendations_have_bound_evidence_without_spending_approval(self):
        self.build()
        rows = json.loads(
            (self.output / "aggregates/Recommendations.json").read_bytes()
        )
        self.assertEqual(len(rows), 12)
        self.assertTrue(
            all(
                r["action"] == "Monitor"
                and r["budget_approval"] == "none"
                and r["audit_indices"]
                and r["next_validation"]
                for r in rows
            )
        )

    def test_tampered_pinned_source_fails_before_publication(self):
        root = Path(self.temp.name) / "root"
        contract = json.loads(
            (report.ROOT / "data/benchmarking-contract.json").read_bytes()
        )
        for name in ["sql", contract["model_release_path"]]:
            shutil.copytree(report.ROOT / name, root / name)
        (root / "docs").mkdir(exist_ok=True)
        for name in [
            "docs/benchmark-metrics.csv",
            "data/benchmarking-contract.json",
            "data/executive-input-contract.json",
        ]:
            shutil.copyfile(report.ROOT / name, root / name)
        pinned = json.loads((root / "data/executive-input-contract.json").read_bytes())
        for b in pinned["files"].values():
            target = root / b["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(report.ROOT / b["path"], target)
        target = root / pinned["files"]["scenarios"]["path"]
        target.write_bytes(target.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Pinned executive input differs"):
            self.build(root)
        self.assertFalse(self.output.exists())

    def test_typed_conversion_retains_genuine_zero_and_unavailable(self):
        data, types = report.typed(
            [{"value": "0", "missing": ""}, {"value": "1.5", "missing": ""}]
        )
        self.assertEqual(data[0]["value"], 0)
        self.assertIsNone(data[0]["missing"])
        self.assertEqual(types["value"], "double")


if __name__ == "__main__":
    unittest.main()
