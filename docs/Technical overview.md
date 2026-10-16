# Technical overview

Python handles collection, validation and analytical builds; SQL provides the shared analytical model; Power BI Desktop presents the accepted evidence. The report uses a fixed, reviewed release rather than retrieving live observations when refreshed.

## Data and source admission

The accepted Steam and SteamSpy baseline was collected on 6 October 2026. Separate admission registers bind reviewed runs to their manifests and source hashes. New observations require explicit review before entering the analytical model. Missing values remain unavailable; genuine zero values are retained. SteamSpy estimates stay separate from observed Steam measures.

The price-history source provides bounded provider-container Steam-shop GB/GBP context for 15 September–6 October 2026. Historical SKU continuity, annual history and promotional response are unavailable. Player-review outputs describe retrieval-current records from two fixed creation cohorts. Language labels are unverified; capped or low-count cohorts cannot support the same comparisons as eligible complete cohorts. Diagnostic examples do not establish concern prevalence, aspect sentiment or population brand perception.

[Data sources](Data%20sources.md) · [Acquisition controls](Acquisition%20controls.md) · [Price-history contract](Price%20history%20contract.md) · [Review refinement method](Review%20refinement%20method.md)

## Analytical workflow

Run commands from the repository root after following the environment setup in the [reproduction guide](Reproduction%20guide.md).

| Component | Entry point | Detailed documentation |
|---|---|---|
| Governed SQL model | `python src/build_model.py` | [Model specification](Data%20model.md), [metric dictionary](Metric%20dictionary.md) |
| Portfolio positioning | `python src/benchmark_portfolio.py` | [Benchmarking methodology](Benchmarking%20methodology.md) |
| Accepted price-history analysis | `python src/price_history.py --analyse` | [Pricing findings](Stage%204%20pricing%20findings.md) |
| Curated price context | `python src/pricing_context.py` | [Price-history contract](Price%20history%20contract.md) |
| Public coded review analysis | `python src/review_analysis.py` | [Player-feedback findings](Stage%205%20player%20findings.md) |
| Public v1 review diagnostics | `python src/review_refinement.py --candidate 94c88909fe4c88a1` | [Refinement method](Review%20refinement%20method.md) |
| Conditional commercial scenarios | `python src/commercial_scenarios.py` | [Scenario contract](Commercial%20scenario%20contract.md) |
| Power BI source package | `python src/build_executive_report.py` | [Report guide](../dashboard/README.md) |

The model publishes versioned CSV outputs and verification manifests. Reference roles, source dates, lifecycle context and measure availability remain alongside results. Only Eiyuden qualifies for a direct-reference group comparison under the accepted coverage rules. There is no composite performance ranking.

Scenarios expose assumed paid-unit and engagement changes separately. They do not estimate demand or turn concurrent players into sales. Forecasts, empirical forecast error, predictive intervals, elasticity and ROI remain unavailable.

## Report and verification

The five-page Power BI Desktop project embeds thirteen public coded tables from pinned sources. Open `dashboard/Games.pbip` and click **Refresh** to load those tables. Native refresh, title drill-through, filtering and scenario selection were checked separately from automated source validation. Power BI Service publication has not been performed.

The completed release passed 212 tests in clean local and hosted environments. `python src/verify_release.py` rebuilds eight public layers twice in temporary directories, checks accepted output bytes and preserves source files and release pointers. The [release findings](Stage%208%20release%20findings.md) and [final acceptance receipt](verification/release-final-acceptance-20261014.json) record the verification and accepted scope.

Exact review text-to-code replay requires the private immutable archive. Public builds reproduce coded analytical evidence without exposing original text or author identifiers. API keys and native Power BI caches stay outside Git. Scheduled collectors retain GitHub Actions artifacts for 90 days; workflows validate and upload evidence without committing as a bot. The [reproduction guide](Reproduction%20guide.md) separates frozen public reproduction from fresh acquisition and private replay.
