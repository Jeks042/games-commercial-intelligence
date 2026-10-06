# Stage 2 modelling findings

## Delivery state

The SQL model is accepted. Local verification, GitHub execution, downloaded-artifact checks and independent read-only review passed. Issue 2 is complete.

The [current analytical release](../data/analytical/current.json) admits the two owner-reviewed Stage 1 runs. It contains 32 titles, seven groups, 365 calendar dates, two run records, 38 governed reference relationships, 32 observed Steam facts, 32 external benchmark facts and 20 metric definitions.

## Assurance

Forty-four regression tests passed: 20 acquisition tests and 24 model tests. Coverage includes accepted-run/hash admission, failed or partial v2 runs, zero/NULL semantics, SQL review reconciliation, price arithmetic, immutable release publication, byte-identical reruns, sparse/missing reference prices, Early Access classification and comparable-week/query/freshness/revision rules.

All 13 table/view CSV hashes and the generated database hash were independently checked. SQL quality gates passed. Source admission reads immutable reviewed runs; 64 legacy history rows and unregistered automation observations are excluded.

## Baseline availability

One portfolio title has enough configured direct references for the price-index gate; 11 do not. This records measurement eligibility, not product performance. Small groups are not ranked.

All 32 titles have unavailable momentum measures. The baseline has no comparable scheduled weekly history. Same-day collections cannot be counted as weeks.

SteamSpy ownership remains requires_review and all baseline playtime fields are NULL. Its reported previous-day peak CCU is secondary observed context with an unresolved effective date, separate from estimated ownership and validated current Steam players. US-cent prices are excluded from the UK comparison.

Analytical lifecycle is calculated as of Store retrieval using Steam's listed release date and observed Early Access genre. Curated business labels are retained separately; the rules do not assert a global launch date or industry standard.

## Consumer and next delivery

The SQL database and matching CSV exports share definitions, grain, lineage and availability gates. Power BI should consume one release with explicit dimension/fact relationships, avoiding duplicated measures from simultaneously loading base facts and convenience views.

Issue 3 uses the admitted model to assess portfolio/reference positioning and develop qualified findings. See the [benchmarking findings](Stage%203%20benchmarking%20findings.md). No commercial ranking, investment recommendation, forecast or promotion-effect claim is approved in this modelling release. Sparse direct-peer coverage, unavailable playtime and insufficient weekly history remain explicit constraints on that analysis.

## Hosted verification

[GitHub run 37526644848](https://github.com/Jeks042/games-commercial-intelligence/actions/runs/37526644848) passed all 44 tests, model construction, an identical repeat build and artifact upload. The downloaded artifact passed ZIP/CSV/database hash checks, database integrity, foreign-key checks and all 13 SQL quality checks.

The hosted Python 3.13.15 / SQLite 3.45.1 build produced identical hashes for all 13 CSV outputs to the published Python 3.13.7 / SQLite 3.50.4 release. Runtime fingerprints intentionally differ; analytical outputs agree. The [verification receipt](../data/analytical/verification-37526644848.json) records both runtimes and counts. A durable private artifact copy is retained.

## Review outcome

Independent read-only review found no blocking modelling issue. Admission and hash binding, fact separation, dimensional grain, zero/NULL semantics, provenance, reference gates, lifecycle rules, temporal protections, reproducibility, quality checks and the consumer contract were accepted. The review also confirmed the hosted verification evidence.

Different runtime fingerprints are documented and do not affect the matching consumer CSVs. A future separation of content and runtime fingerprints is optional; it is not required for acceptance. [Issue 2](https://github.com/Jeks042/games-commercial-intelligence/issues/2) records the completion evidence and handoff.
