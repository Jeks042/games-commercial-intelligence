# Games Commercial Intelligence

Commercial portfolio analysis of 12 selected 505 Games titles and 20 market reference titles on Steam. The analysis assesses price positioning, player response and engagement signals to support decisions about portfolio attention and promotional priorities.

**Status:** Stage 1 acquisition accepted on 6 October 2026. The validated baseline covers all 32 scoped titles. Analytical modelling is next; performance recommendations and the Power BI report are pending.

## Evidence base

| Source | Coverage | Measures |
|---|---|---|
| Steam Store | 32 scoped titles | UK storefront price, discount, publisher, developer and release metadata |
| Steam reviews | 32 scoped titles | Lifetime positive and negative counts, review category and positivity |
| Steam player API | 32 scoped titles | Concurrent players at retrieval time |
| SteamSpy | Separate benchmark | Estimated owner bands and supporting market fields, subject to suitability review |

[Acquisition findings](docs/Stage%201%20acquisition%20findings.md) record the accepted runs, field availability and quality decisions. [Source contracts](docs/Data%20sources.md) and [acquisition controls](docs/Acquisition%20controls.md) define how evidence is collected and released.

## Commercial scope

The planned analysis compares titles within documented reference groups, distinguishes lifecycle effects from product performance, and evaluates pricing and player response before proposing actions. Historical promotion analysis and scenarios require additional evidence and are tracked in the [delivery backlog](https://github.com/Jeks042/games-commercial-intelligence/issues).

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
