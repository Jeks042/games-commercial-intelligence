# Games Commercial Intelligence

Commercial portfolio analysis of 12 selected 505 Games titles and 20 market reference titles on Steam. The analysis assesses price positioning, player response and engagement signals to support decisions about portfolio attention and promotional priorities.

**Status:** Acquisition, the SQL analytical model, snapshot portfolio benchmarking and bounded recorded-price analysis are accepted. The frozen baseline covers 32 scoped titles; usable price context covers 27 for 15 September–6 October 2026. Promotional effectiveness remains unavailable without comparable dated response evidence. [Player-review analysis](docs/Stage%205%20player%20findings.md) is in progress; the Power BI report follows later.

## Evidence base

| Source | Coverage | Measures |
|---|---|---|
| Steam Store | 32 scoped titles | UK storefront price, discount, publisher, developer and release metadata |
| Steam reviews | 32 scoped titles | Lifetime positive and negative counts, review category and positivity |
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

The analysis keeps reference roles, lifecycle context and availability alongside each result. Bounded discount-depth comparison is available for Eiyuden and three direct references; the other 11 portfolio comparisons remain unavailable. Promotional effectiveness and scenarios require additional evidence and are tracked in the [delivery backlog](https://github.com/Jeks042/games-commercial-intelligence/issues).

The [pricing findings](docs/Stage%204%20pricing%20findings.md) and [history contract](docs/Price%20history%20contract.md) document the accepted bounded analysis, suitability controls and remaining data requirements. The published outputs can be rebuilt from admitted source files without an API key:

```bash
python src/price_history.py --analyse
python src/pricing_context.py
```

Public Steam signals do not establish publisher revenue, units sold, retention or marketing return. SteamSpy estimates remain separate from observed Steam measures. Small reference groups support contextual comparison; they do not constitute a representative market sample.

## Reproduce the acquisition

Python 3.13; dependencies are pinned.

```bash
python -m venv .venv
# Activate the environment for your operating system.
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/collect_snapshot.py
python src/collect_market_benchmark.py
```

Each collector saves an immutable observation file and manifest under `data/runs/`. Complete, validated runs update the Steam history or latest benchmark; failed runs retain diagnostic evidence and leave published data intact.

Scheduled collection produces downloadable GitHub Actions artifacts. Accepted observations must be reviewed and committed by the repository owner to extend the published history. Artifacts expire after 90 days; the schedule is a weekly engagement pulse, not continuous monitoring.

## Repository guide

- [Business brief](docs/Business%20brief.md): decision scope and deliverables.
- [Title universe](data/portfolio-titles.csv) and [market reference set](data/competitor-titles.csv): scoped products and comparison rationale.
- [Steam observation history](data/snapshots/commercial-snapshot-history.csv): versioned source observations.
- [SteamSpy benchmark](data/benchmarks/steamspy-market-benchmark.csv): external estimates and availability flags.
- [Metric dictionary](docs/Metric%20dictionary.md): current and planned measures.
- [Evidence limitations](docs/Data%20limitations.md): interpretation boundaries.

Independent public-data analysis; no affiliation with the publishers or platforms referenced.
