"""Create a portable Power BI project from pinned, accepted public evidence."""

import base64
import csv
from decimal import Decimal
import io
import json
from pathlib import Path
import re
import uuid

from benchmark_portfolio import verified_inputs
from build_model import ROOT, canonical, sha

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/"


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_inputs(root):
    _, _, _ = verified_inputs(root, root / "data/benchmarking-contract.json")
    contract = json.loads((root / "data/executive-input-contract.json").read_bytes())
    sources = {}
    for name, binding in contract["files"].items():
        path = (root / binding["path"]).resolve()
        if not path.is_relative_to(root) or sha(path.read_bytes()) != binding["sha256"]:
            raise ValueError(f"Pinned executive input differs: {name}")
        sources[name] = path
    for name, expected in [
        (
            "scenario_acceptance",
            "accepted_bounded_conditional_scenarios_and_forecast_readiness",
        ),
        ("review_acceptance", "accepted_bounded_player_feedback_investigation"),
    ]:
        receipt = json.loads(sources[name].read_bytes())
        actual = receipt.get("independent_review_status", receipt.get("verdict"))
        if actual != expected:
            raise ValueError(f"Independent input acceptance differs: {name}")
    return contract, sources


def typed(rows):
    """Preserve CSV NULLs; infer numbers only where all nonempty values are numeric."""
    types = {}
    for field in rows[0]:
        values = [r[field] for r in rows if r[field] is not None and r[field] != ""]
        numeric = values and all(
            re.fullmatch(r"-?\d+(?:\.\d+)?", str(v)) for v in values
        )
        integer = numeric and all(re.fullmatch(r"-?\d+", str(v)) for v in values)
        types[field] = "int64" if integer else "double" if numeric else "string"
    converted = []
    for row in rows:
        converted.append(
            {
                k: (
                    None
                    if v is None or v == ""
                    else (
                        int(v)
                        if types[k] == "int64"
                        else float(v) if types[k] == "double" else str(v)
                    )
                )
                for k, v in row.items()
            }
        )
    return converted, types


def lineage(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "games-commercial-intelligence/" + name))


def table(name, rows, measures=None):
    data, types = typed(rows)
    encoded = base64.b64encode(canonical(data)).decode()
    mtypes = {"int64": "Int64.Type", "double": "type number", "string": "type text"}
    conversions = ", ".join(
        "{" + json.dumps(k) + ", " + mtypes[v] + "}" for k, v in types.items()
    )
    expression = [
        "let",
        f' Source = Table.FromRecords(Json.Document(Binary.FromText("{encoded}", BinaryEncoding.Base64))),',
        " Typed = Table.TransformColumnTypes(Source, {" + conversions + "})",
        "in",
        " Typed",
    ]
    return {
        "name": name,
        "lineageTag": lineage(name),
        "description": "Pinned public coded evidence; source hashes in dashboard/build-manifest.json. No live acquisition.",
        "columns": [
            {
                "name": k,
                "dataType": v,
                "sourceColumn": k,
                "summarizeBy": "none",
                "lineageTag": lineage(name + "/" + k),
            }
            for k, v in types.items()
        ],
        "measures": [
            {
                "name": n,
                "expression": e,
                "formatString": f,
                "lineageTag": lineage(name + "/measure/" + n),
            }
            for n, e, f in (measures or [])
        ],
        "partitions": [
            {
                "name": name,
                "mode": "import",
                "source": {"type": "m", "expression": expression},
            }
        ],
    }, data


def measure(name, table_name, column, fmt="0.0", percent=False):
    value = f"SELECTEDVALUE('{table_name}'[{column}])"
    if percent:
        value = f"DIVIDE({value}, 100)"
    return (name, f"IF(COUNTROWS('{table_name}') = 1, {value})", fmt)


def field(entity, prop, kind="Column"):
    return {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def literal(value):
    return {"expr": {"Literal": {"Value": value}}}


def color(value):
    return {"solid": {"color": literal("'" + value + "'")}}


def container(title):
    return {
        "background": [
            {
                "properties": {
                    "show": literal("true"),
                    "color": color("#FFFFFF"),
                    "transparency": literal("0D"),
                }
            }
        ],
        "title": [
            {
                "properties": {
                    "show": literal("true" if title else "false"),
                    "text": literal("'" + title.replace("'", "''") + "'"),
                    "fontSize": literal("13D"),
                    "fontColor": color("#132F45"),
                    "bold": literal("true"),
                }
            }
        ],
    }


def visual(name, kind, x, y, w, h, title="", fields=None, text=None):
    v = {"visualType": kind, "visualContainerObjects": container(title)}
    if text is not None:
        v["objects"] = {
            "general": [
                {
                    "properties": {
                        "paragraphs": [
                            {
                                "textRuns": [
                                    {
                                        "value": text,
                                        "textStyle": {
                                            "fontFamily": "Segoe UI",
                                            "fontSize": "12pt",
                                            "color": "#243F50",
                                        },
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
        v["visualContainerObjects"]["background"][0]["properties"]["show"] = literal(
            "false"
        )
    if fields:
        v["query"] = {
            "queryState": {
                "Values": {
                    "projections": [
                        {
                            "field": field(t, c, k),
                            "queryRef": t + "." + c,
                            "nativeQueryRef": label,
                            "displayName": label,
                            **({"active": True} if kind == "slicer" else {}),
                        }
                        for t, c, k, label in fields
                    ]
                }
            }
        }
    if kind == "tableEx":
        v["objects"] = {
            "grid": [
                {
                    "properties": {
                        "rowPadding": literal("4D"),
                        "textSize": literal("11D"),
                    }
                }
            ],
            "total": [{"properties": {"totals": literal("false")}}],
            "columnHeaders": [
                {
                    "properties": {
                        "fontColor": color("#132F45"),
                        "backColor": color("#E6EFF3"),
                        "fontSize": literal("11D"),
                    }
                }
            ],
            "values": [
                {
                    "properties": {
                        "fontSize": literal("11D"),
                        "wordWrap": literal("true"),
                    }
                }
            ],
        }
    if kind == "slicer":
        v["objects"] = {
            "selection": [
                {
                    "properties": {
                        "singleSelect": literal("true"),
                        "selectAllCheckboxEnabled": literal("false"),
                    }
                }
            ],
            "data": [{"properties": {"mode": literal("'Dropdown'")}}],
        }
    if kind == "card":
        v["objects"] = {
            "labels": [
                {
                    "properties": {
                        "fontSize": literal("28D"),
                        "color": color("#007F82"),
                        "labelDisplayUnits": literal("1D"),
                    }
                }
            ],
            "categoryLabels": [{"properties": {"show": literal("false")}}],
        }
    return {
        "$schema": SCHEMA + "item/report/definition/visualContainer/2.12.0/schema.json",
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": int(y * 10 + x),
            "width": w,
            "height": h,
            "tabOrder": int(y * 10 + x),
        },
        "visual": v,
    }


def build(root=ROOT, output_dir=None):
    root = Path(root).resolve()
    contract, sources = load_inputs(root)
    evidence = {
        name: read_csv(path) for name, path in sources.items() if path.suffix == ".csv"
    }
    portfolio = evidence["portfolio"]
    apps = {r["app_id"] for r in portfolio}
    if len(portfolio) != 12 or len(apps) != 12:
        raise ValueError("Require exactly twelve unique portfolio titles")
    rows = [
        line.split("|")[1:-1]
        for line in sources["investigation_brief"]
        .read_text(encoding="utf-8")
        .splitlines()
        if line.startswith("|")
    ][2:]
    titles = {r["title"]: r["app_id"] for r in portfolio}
    audit = {
        e["audit_index"]: e
        for e in json.loads(sources["context_audit"].read_bytes())["entries"]
    }
    investigation = []
    for title, question, qualification, validation in rows:
        app = titles[title.strip()]
        indices = set()
        for low, high in re.findall(r"\b(\d+)(?:–(\d+))?\b", qualification):
            indices.update(range(int(low), int(high or low) + 1))
        if not indices or any(str(audit[i]["app_id"]) != app for i in indices):
            raise ValueError("Investigation audit/title binding differs")
        investigation.append(
            {
                "app_id": app,
                "question": question.strip(),
                "qualification": qualification.strip(),
                "validation_needed": validation.strip(),
                "coded_audit_indices": ", ".join(map(str, sorted(indices))),
                "scope": "individual reported experiences; not prevalence, verified defects or population sentiment",
            }
        )
    if {r["app_id"] for r in investigation} != apps or len(investigation) != 12:
        raise ValueError("Investigation coverage differs")
    policy = json.loads(sources["decision_policy"].read_bytes())
    if (
        policy["default_current_action"] != "Monitor"
        or policy["current_budget_approval"] != "none"
    ):
        raise ValueError("Unsupported public-evidence budget action")
    recommendations = [
        {
            "app_id": r["app_id"],
            "action": "Monitor",
            "commercial_question": r["question"],
            "next_validation": r["validation_needed"],
            "audit_indices": r["coded_audit_indices"],
            "budget_approval": "none",
            "basis": "accepted snapshot + qualified individual review examples; internal economics unavailable",
        }
        for r in investigation
    ]
    definitions = [
        (
            "Portfolio",
            portfolio,
            [
                measure("Dated GBP price", "Portfolio", "final_price_gbp", "£0.00"),
                measure(
                    "Lifetime positive share",
                    "Portfolio",
                    "lifetime_review_positive_percent",
                    "0.0%",
                    True,
                ),
                measure(
                    "Point concurrent players", "Portfolio", "current_players", "#,0"
                ),
                measure("Lifetime review count", "Portfolio", "total_reviews", "#,0"),
                measure(
                    "Snapshot discount",
                    "Portfolio",
                    "discount_depth_percent",
                    "0.0%",
                    True,
                ),
            ],
        ),
        ("References", evidence["references"], []),
        ("PeerBenchmark", evidence["peer_benchmark"], []),
        ("Price", [r for r in evidence["price"] if r["app_id"] in apps], []),
        ("PriceComparison", evidence["price_comparison"], []),
        ("Reviews", evidence["reviews"], []),
        ("ReviewCohorts", evidence["review_cohorts"], []),
        (
            "Scenarios",
            evidence["scenarios"],
            [
                measure(
                    "Conditional receipts index",
                    "Scenarios",
                    "conditional_gross_receipts_index",
                ),
                measure(
                    "Required unit increase",
                    "Scenarios",
                    "required_paid_unit_change_percent",
                    "0.0%",
                    True,
                ),
                measure(
                    "Separate engagement index",
                    "Scenarios",
                    "hypothetical_engagement_index",
                ),
            ],
        ),
        ("Forecast", evidence["forecast"], []),
        ("Investigation", investigation, []),
        ("Recommendations", recommendations, []),
        ("DecisionPolicy", policy["categories"], []),
        (
            "Summary",
            [
                {
                    "portfolio_titles": 12,
                    "qualified_direct_group_titles": sum(
                        r["benchmark_status"] == "available_unadjusted_snapshot"
                        and r["metric"] == "final_price_gbp"
                        for r in evidence["peer_benchmark"]
                    ),
                    "validated_forecasts": 0,
                    "budget_approvals": 0,
                }
            ],
            [
                ("Portfolio titles", "MAX('Summary'[portfolio_titles])", "0"),
                (
                    "Qualified direct groups",
                    "MAX('Summary'[qualified_direct_group_titles])",
                    "0",
                ),
                ("Validated forecasts", "MAX('Summary'[validated_forecasts])", "0"),
                ("Budget approvals", "MAX('Summary'[budget_approvals])", "0"),
            ],
        ),
    ]
    tables, aggregates, relationships = [], {}, []
    for name, data, measures in definitions:
        # Keep machine-readable provenance while presenting readable labels.
        data = [dict(row) for row in data]
        for row in data:
            for key, value in list(row.items()):
                if key.endswith("_status") or key in {
                    "window_coverage",
                    "analytical_lifecycle",
                    "reference_lifecycle",
                }:
                    row[key + "_label"] = (
                        None
                        if value in {None, ""}
                        else str(value).replace("_", " ").capitalize()
                    )
        t, values = table(name, data, measures)
        tables.append(t)
        aggregates[name] = values
        key = "portfolio_app_id" if name == "References" else "app_id"
        if name not in {"Portfolio", "Summary", "DecisionPolicy"}:
            if any(str(r[key]) not in apps for r in data):
                raise ValueError(f"Unscoped reporting identity: {name}")
            relationships.append(
                {
                    "name": lineage(name + "/relationship"),
                    "fromTable": name,
                    "fromColumn": key,
                    "toTable": "Portfolio",
                    "toColumn": "app_id",
                    "crossFilteringBehavior": "oneDirection",
                }
            )
    outputs = {}

    def put(path, value):
        outputs[path] = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        )

    put(
        "Games.pbip",
        {
            "$schema": SCHEMA + "pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": "Games.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    put(
        "Games.SemanticModel/definition.pbism",
        {
            "$schema": SCHEMA
            + "item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {},
        },
    )
    put(
        "Games.SemanticModel/model.bim",
        {
            "compatibilityLevel": 1606,
            "model": {
                "name": "GamesCommercialIntelligence",
                "culture": "en-GB",
                "defaultPowerBIDataSourceVersion": "powerBI_V3",
                "discourageImplicitMeasures": True,
                "annotations": [{"name": "PBI_ProTooling", "value": '["DevMode"]'}],
                "tables": tables,
                "relationships": relationships,
            },
        },
    )
    put(
        "Games.Report/definition.pbir",
        {
            "$schema": SCHEMA + "item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byPath": {"path": "../Games.SemanticModel"}},
        },
    )
    put(
        "Games.Report/definition/version.json",
        {
            "$schema": SCHEMA
            + "item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        },
    )
    put(
        "Games.Report/definition/report.json",
        {
            "$schema": SCHEMA + "item/report/definition/report/3.3.0/schema.json",
            "themeCollection": {},
            "settings": {"useEnhancedTooltips": False},
        },
    )
    pages = [
        ("01_Portfolio", "Portfolio decisions"),
        ("02_Title", "Title investigation"),
        ("03_Pricing", "Pricing context"),
        ("04_Players", "Player feedback"),
        ("05_Scenarios", "Conditional scenarios"),
    ]
    put(
        "Games.Report/definition/pages/pages.json",
        {
            "$schema": SCHEMA
            + "item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": [n for n, _ in pages],
            "activePageName": pages[0][0],
        },
    )

    def f(t, c, label=None, kind="Column"):
        if kind == "Column" and (
            c.endswith("_status")
            or c in {"window_coverage", "analytical_lifecycle", "reference_lifecycle"}
        ):
            return (t, c + "_label", kind, label or c)
        return (t, c, kind, label or c)

    for page_name, label in pages:
        page = {
            "$schema": SCHEMA + "item/report/definition/page/2.0.0/schema.json",
            "name": page_name,
            "displayName": label,
            "displayOption": "FitToPage",
            "width": 1440,
            "height": 900,
            "objects": {
                "background": [
                    {
                        "properties": {
                            "color": color("#F0F5F7"),
                            "transparency": literal("0D"),
                        }
                    }
                ]
            },
        }
        if page_name == "02_Title":
            page.update(
                {
                    "type": "Drillthrough",
                    "filterConfig": {
                        "filters": [
                            {
                                "name": "TitleFilter",
                                "field": field("Portfolio", "title"),
                                "type": "Categorical",
                                "howCreated": "Drillthrough",
                            }
                        ]
                    },
                    "pageBinding": {
                        "name": "TitleDrillthrough",
                        "type": "Drillthrough",
                        "parameters": [
                            {
                                "name": "Title",
                                "boundFilter": "TitleFilter",
                                "fieldExpr": field("Portfolio", "title"),
                            }
                        ],
                        "acceptsFilterContext": "Default",
                    },
                }
            )
        put("Games.Report/definition/pages/" + page_name + "/page.json", page)
        specs = [
            visual(
                "heading",
                "textbox",
                24,
                12,
                1390,
                42,
                text="GAMES COMMERCIAL INTELLIGENCE | " + label.upper(),
            ),
            visual(
                "boundary",
                "textbox",
                24,
                58,
                1390,
                64,
                text="Steam snapshot: 6 Oct 2026. Price history: bounded provider-container context, 15 Sep–6 Oct. Reviews: current retrieved creation cohorts, not historical sentiment. No sales, ROI or validated forecasts.",
            ),
            visual(
                "footer",
                "textbox",
                24,
                850,
                1390,
                36,
                text="Independent public-data decision support | Monitor means investigate; no budget approval | Source hashes and acceptance scope in the repository",
            ),
        ]
        if page_name == "01_Portfolio":
            for i, n in enumerate(
                [
                    "Portfolio titles",
                    "Qualified direct groups",
                    "Validated forecasts",
                    "Budget approvals",
                ]
            ):
                specs.append(
                    visual(
                        "card" + str(i),
                        "card",
                        24 + i * 352,
                        135,
                        336,
                        100,
                        n,
                        [f("Summary", n, kind="Measure")],
                    )
                )
            specs += [
                visual(
                    "portfolio",
                    "tableEx",
                    24,
                    250,
                    1390,
                    370,
                    "Separate snapshot signals | right-click a title for investigation",
                    [
                        f("Portfolio", "title", "Title"),
                        f("Portfolio", "analytical_lifecycle", "Lifecycle"),
                        f("Portfolio", "Dated GBP price", kind="Measure"),
                        f("Portfolio", "Lifetime positive share", kind="Measure"),
                        f("Portfolio", "Point concurrent players", kind="Measure"),
                        f("Recommendations", "action", "Action"),
                    ],
                ),
                visual(
                    "decisions",
                    "tableEx",
                    24,
                    636,
                    1390,
                    190,
                    "Evidence gates before allocation",
                    [
                        f("DecisionPolicy", "action", "Action"),
                        f("DecisionPolicy", "current_status", "Current eligibility"),
                        f("DecisionPolicy", "gate", "Evidence required"),
                    ],
                ),
            ]
        else:
            specs.append(
                visual(
                    "title_selector",
                    "slicer",
                    24,
                    132,
                    530,
                    84,
                    "Select one portfolio title",
                    [f("Portfolio", "title", "Title")],
                )
            )
        if page_name == "02_Title":
            specs += [
                visual(
                    "question",
                    "tableEx",
                    24,
                    236,
                    1390,
                    170,
                    "Question and qualifying evidence",
                    [
                        f("Portfolio", "title", "Title"),
                        f("Investigation", "question", "Investigation question"),
                        f("Investigation", "coded_audit_indices", "Audit references"),
                        f("Investigation", "qualification", "Qualifying evidence"),
                    ],
                ),
                visual(
                    "validation",
                    "tableEx",
                    24,
                    424,
                    1390,
                    150,
                    "Next validation before action",
                    [
                        f("Recommendations", "action", "Action"),
                        f(
                            "Recommendations",
                            "next_validation",
                            "Product/support evidence needed",
                        ),
                        f("Recommendations", "budget_approval", "Budget approval"),
                    ],
                ),
                visual(
                    "peers",
                    "tableEx",
                    24,
                    594,
                    1390,
                    230,
                    "Individual reference context | role and lifecycle retained",
                    [
                        f("References", "reference_title", "Reference"),
                        f("References", "peer_role", "Role"),
                        f("References", "reference_lifecycle", "Lifecycle"),
                        f("References", "reference_price_gbp", "Dated GBP price"),
                        f(
                            "References",
                            "reference_positive_percent",
                            "Lifetime positive %",
                        ),
                        f("References", "lifecycle_context", "Comparison limit"),
                    ],
                ),
            ]
        if page_name == "03_Pricing":
            specs += [
                visual(
                    "prices",
                    "tableEx",
                    24,
                    236,
                    1390,
                    220,
                    "Returned provider-container price states | not annual extrema",
                    [
                        f("Portfolio", "title", "Title"),
                        f("Price", "suitability_status", "Suitability"),
                        f("Price", "minimum_recorded_price_gbp", "Min returned GBP"),
                        f(
                            "Price",
                            "maximum_source_reported_cut_percent",
                            "Max returned cut %",
                        ),
                        f("Price", "window_coverage", "Window coverage"),
                    ],
                ),
                visual(
                    "comparison",
                    "tableEx",
                    24,
                    476,
                    1390,
                    230,
                    "Direct-reference coverage gates | only one title qualifies",
                    [
                        f("PriceComparison", "title", "Title"),
                        f(
                            "PriceComparison",
                            "usable_direct_reference_count",
                            "Usable direct references",
                        ),
                        f(
                            "PriceComparison",
                            "target_minus_reference_median_cut_pp",
                            "Returned-cut difference pp",
                        ),
                        f("PriceComparison", "comparison_status", "Availability"),
                        f("PriceComparison", "response_status", "Promotion response"),
                    ],
                ),
                visual(
                    "price_limit",
                    "textbox",
                    24,
                    722,
                    1390,
                    100,
                    text="The latest price was corroborated only as bounded container context. Historical SKU continuity, left-edge state, annual history, promotional response and elasticity remain unavailable. Do not rank same-date historical prices or approve discounts from returned states.",
                ),
            ]
        if page_name == "04_Players":
            specs += [
                visual(
                    "cohorts",
                    "tableEx",
                    24,
                    236,
                    1390,
                    260,
                    "Current retrieved recommendation state by creation cohort",
                    [
                        f("Portfolio", "title", "Title"),
                        f("ReviewCohorts", "creation_cohort", "Creation cohort"),
                        f("ReviewCohorts", "returned_review_count", "Returned reviews"),
                        f(
                            "ReviewCohorts",
                            "observed_recommendation_percent",
                            "Retrieved positive %",
                        ),
                        f("ReviewCohorts", "coverage_status", "Returned coverage"),
                        f(
                            "ReviewCohorts",
                            "edited_after_creation_window_count",
                            "Edited after cohort",
                        ),
                    ],
                ),
                visual(
                    "language",
                    "textbox",
                    24,
                    510,
                    1390,
                    80,
                    text="Steam-labelled English is not verified English text. Returned reviews are self-selected. Recommendation direction is not aspect sentiment. Capped/low-count contrasts remain unavailable; qualified contrasts are composition-unadjusted, not improvement or decline.",
                ),
                visual(
                    "review_questions",
                    "tableEx",
                    24,
                    610,
                    1390,
                    214,
                    "Player-feedback investigation agenda | no concern prevalence",
                    [
                        f("Investigation", "question", "Question"),
                        f("Investigation", "validation_needed", "Evidence needed"),
                        f("Investigation", "coded_audit_indices", "Coded references"),
                    ],
                ),
            ]
        if page_name == "05_Scenarios":
            specs.append(
                visual(
                    "case_selector",
                    "slicer",
                    578,
                    132,
                    530,
                    84,
                    "Select a planning case; base is not an expected result",
                    [f("Scenarios", "scenario", "Case")],
                )
            )
            for i, n in enumerate(
                [
                    "Conditional receipts index",
                    "Required unit increase",
                    "Separate engagement index",
                ]
            ):
                specs.append(
                    visual(
                        "casecard" + str(i),
                        "card",
                        24 + i * 468,
                        236,
                        448,
                        105,
                        n,
                        [f("Scenarios", n, kind="Measure")],
                    )
                )
            specs += [
                visual(
                    "cases",
                    "tableEx",
                    24,
                    360,
                    1390,
                    200,
                    "Explicit assumptions | units baseline unobserved",
                    [
                        f("Portfolio", "title", "Title"),
                        f("Scenarios", "scenario", "Case"),
                        f("Scenarios", "assumed_price_factor", "Price factor"),
                        f(
                            "Scenarios",
                            "assumed_paid_unit_factor",
                            "Assumed unit factor",
                        ),
                        f(
                            "Scenarios",
                            "assumed_engagement_factor",
                            "Separate engagement factor",
                        ),
                        f(
                            "Scenarios",
                            "conditional_gross_receipts_index",
                            "Conditional value index",
                        ),
                    ],
                ),
                visual(
                    "readiness",
                    "tableEx",
                    24,
                    578,
                    1390,
                    150,
                    "Predictive forecasts unavailable | scenario ranges are not intervals",
                    [
                        f(
                            "Forecast",
                            "accepted_observation_count",
                            "Accepted observations",
                        ),
                        f(
                            "Forecast",
                            "qualifying_comparable_weeks",
                            "Comparable weeks",
                        ),
                        f("Forecast", "forecast_status", "Forecast eligibility"),
                        f("Forecast", "validation_status", "Predictive validation"),
                    ],
                ),
                visual(
                    "economic_limit",
                    "textbox",
                    24,
                    746,
                    1390,
                    80,
                    text="Index 100 normalizes an unobserved paid-unit baseline. Gross storefront transaction value is not net revenue or profit; taxes, refunds, fees, mix and costs are not modelled. Engagement never enters the receipts equation. Missing/ambiguous selections stay blank. No spending approval.",
                ),
            ]
        for spec in specs:
            put(
                "Games.Report/definition/pages/"
                + page_name
                + "/visuals/"
                + spec["name"]
                + "/visual.json",
                spec,
            )
    for name, rows in aggregates.items():
        put("aggregates/" + name + ".json", rows)
    manifest = {
        "status": "built_pending_native_verification_and_independent_review",
        "builder_sha256": sha(Path(__file__).read_bytes()),
        "input_contract_sha256": sha(
            (root / "data/executive-input-contract.json").read_bytes()
        ),
        "source_files": contract["files"],
        "output_sha256": {name: sha(body) for name, body in outputs.items()},
        "table_row_counts": {name: len(rows) for name, rows in aggregates.items()},
        "native_refresh_status": "not_verified",
        "native_render_status": "not_verified",
        "drillthrough_status": "not_verified",
        "service_publication": "not_performed",
        "data_policy": "Embedded public coded tables from pinned accepted releases; no private text, API keys or machine paths. Build does not validate native Power BI execution.",
    }
    put("build-manifest.json", manifest)
    output = Path(output_dir or root / "dashboard")
    if output.exists() and any(
        (output / name).exists() and (output / name).read_bytes() != body
        for name, body in outputs.items()
    ):
        raise ValueError(
            "Existing dashboard differs; preserve edits and rebuild in a separate directory"
        )
    for name, body in outputs.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    print(
        json.dumps(
            {
                "files": len(outputs),
                "tables": manifest["table_row_counts"],
                "status": manifest["status"],
            }
        ),
        flush=True,
    )
    return output


if __name__ == "__main__":
    build()
