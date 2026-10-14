# Games Commercial Intelligence

Commercial portfolio analysis of 12 selected 505 Games titles and 20 market reference titles on Steam. The analysis assesses price positioning, player response and engagement signals to support decisions about portfolio attention and promotional priorities.

**Status:** Complete and independently accepted on 14 October 2026 within the frozen public-analysis and Power BI Desktop scope. The case study traces all twelve investigation paths to accepted evidence. Clean and hosted verification passed 212 tests; the baseline and generated report remain unchanged. No spending approval, validated forecast or Power BI Service publication is claimed.

[Commercial case study](docs/Commercial%20case%20study.md) · [Executive decision memo](docs/Commercial%20decision%20memo.md) · [Power BI report](dashboard/README.md) · [Reproduction guide](docs/Reproduction%20guide.md) · [Final release evidence](docs/Stage%208%20release%20findings.md)

## Evidence base

| Source | Coverage | Measures |
|---|---|---|
| Steam Store | 32 scoped titles | UK storefront price, discount, publisher, developer and release metadata |
| Steam reviews | 32 scoped titles | Lifetime positive and negative counts, review category and positivity |
| Dated Steam review cohorts | 12 portfolio titles; 3,572 coded records | Current retrieved recommendations and diagnostic text context from two fixed creation cohorts; Steam language labels are unverified |
| Steam player API | 32 scoped titles | Concurrent players at retrieval time |
| SteamSpy | Separate benchmark | Estimated owner bands and supporting market fields, subject to suitability review |
| IsThereAnyDeal | 27 suitable bounded contexts; exclusions documented | Recorded Steam-shop GB/GBP prices and source-reported cuts; historical SKU identity unverified |

[Acquisition findings](docs/Stage%201%20acquisition%20findings.md) record the accepted runs, field availability and quality decisions. [Source contracts](docs/Data%20sources.md) and [acquisition controls](docs/Acquisition%20controls.md) define how evidence is collected and released.

## Analytical model

The SQL model admits only explicitly accepted source runs, retains source/query provenance and separates observed Steam measures from external estimates. Governed reference roles, metric availability and publication checks are built into its reporting views.

```bash
python src/build_model.py
```

The builder publishes a versioned release with typed table/view CSVs and a verification manifest. See the [model specification](docs/Data%20model.md), [current release](data/analytical/current.json), [metric contract](docs/Metric%20dictionary.md) and [model verification findings](docs/Stage%202%20modelling%20findings.md). These outputs share one measurement definition across SQL, Python and Power BI.

## Commercial scope

[Portfolio positioning findings](docs/Stage%203%20benchmarking%20findings.md) assess the 12 selected portfolio titles using separate price, review-response, review-scale and current-player signals. The [benchmarking contract](docs/Benchmarking%20methodology.md) retains reference roles, lifecycle context and availability gates. Only one title currently qualifies for direct-peer group measures; sparse comparisons and trends remain unavailable.

```bash
python src/benchmark_portfolio.py
```

The analysis keeps reference roles, lifecycle context and availability alongside each result. Bounded discount-depth comparison is available for Eiyuden and three direct references; the other 11 portfolio comparisons remain unavailable. Promotional effectiveness requires additional evidence; conditional scenarios expose assumptions and are documented below. Delivery decisions are tracked in the [backlog](https://github.com/Jeks042/games-commercial-intelligence/issues).

The [pricing findings](docs/Stage%204%20pricing%20findings.md) and [history contract](docs/Price%20history%20contract.md) document the accepted bounded analysis, suitability controls and remaining data requirements. The published outputs can be rebuilt from admitted source files without an API key:

```bash
python src/price_history.py --analyse
python src/pricing_context.py
```

The [player-feedback findings](docs/Stage%205%20player%20findings.md) and [twelve-title investigation brief](docs/Player%20feedback%20investigation%20brief.md) connect reported experiences to concrete product/support checks. Final independent review accepted the bounded investigation framework on 10 October, including the source, descriptive analytical intermediate, context diagnostics, fresh 110-review check and twelve-title synthesis. The [acceptance receipt](docs/verification/review-final-acceptance-20261010.json) records the reviewed evidence and scope. Topic prevalence, aspect sentiment and theme trends remain unavailable. Original review text and author identifiers are retained privately; public outputs contain coded evidence and provenance.

```bash
python src/review_analysis.py
python src/review_refinement.py --candidate 94c88909fe4c88a1
```

These commands rebuild public coded analytical context and candidate diagnostics. Exact text-to-code replay requires the private immutable source archive. The [refinement method](docs/Review%20refinement%20method.md) defines that boundary; hosted validation passed 181 tests and byte-identical diagnostic rebuilds.

The independently accepted [commercial scenario layer](docs/Commercial%20scenario%20contract.md) calculates conditional price/volume requirements and separate engagement stress cases from dated accepted Steam anchors. Assumptions are explicit; forecasts, validation errors, predictive intervals, elasticity and ROI remain unavailable. [Scenario findings](docs/Stage%206%20scenario%20findings.md) and the [verification receipt](docs/verification/scenarios-38150259475.json) record the bounded acceptance and 199-test hosted validation.

```bash
python src/commercial_scenarios.py
```

Public Steam signals do not establish publisher revenue, units sold, retention or marketing return. SteamSpy estimates remain separate from observed Steam measures. Small reference groups support contextual comparison; they do not constitute a representative market sample.

The independently accepted [Power BI executive project](dashboard/README.md) has five pages connecting evidence to title-specific investigation and conditional requirements. Native refresh, title drill-through and scenario-selection behaviour were checked separately from hosted 210-test validation. The [commercial memo](docs/Commercial%20decision%20memo.md) defines allocation gates; [report findings](docs/Stage%207%20executive%20findings.md) state the acceptance scope. Open the project in Desktop and click Refresh to load the embedded frozen evidence. No spending approval or Service publication is claimed.

## Reproduce the release

Start with a fresh clone, Python 3.13 and pinned dependencies. Run the tests and `python src/verify_release.py` to rebuild all eight public layers twice and compare their accepted output bytes without changing release pointers. The [reproduction guide](docs/Reproduction%20guide.md) includes environment setup, native Desktop use, separate live acquisition and the private source-replay boundary.

Scheduled acquisition retains downloadable artifacts for 90 days. New observations require explicit owner review and source admission; workflows never commit as a bot. The committed frozen package and verification receipts are the durable evidence.

## Repository guide

- [Business brief](docs/Business%20brief.md): decision scope and deliverables.
- [Title universe](data/portfolio-titles.csv) and [market reference set](data/competitor-titles.csv): scoped products and comparison rationale.
- [Steam observation history](data/snapshots/commercial-snapshot-history.csv): versioned source observations.
- [SteamSpy benchmark](data/benchmarks/steamspy-market-benchmark.csv): external estimates and availability flags.
- [Metric dictionary](docs/Metric%20dictionary.md): current and planned measures.
- [Evidence limitations](docs/Data%20limitations.md): interpretation boundaries.

Independent public-data analysis; no affiliation with the publishers or platforms referenced.
