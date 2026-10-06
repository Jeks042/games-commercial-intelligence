# Stage 1 acquisition findings

## Acceptance

Baseline acquisition passed the declared source checks on **6 October 2026 UTC**. This acceptance covers collection reliability and the fields listed below. Commercial benchmarking, trends, scenarios and recommendations remain subsequent deliveries.

The scope contains 12 selected 505 Games titles and 20 market reference titles. Steam app identities were validated against the returned Store payload; benchmark app identities were checked separately.

## Accepted evidence

| Source | Valid responses | Field availability |
|---|---|---|
| Steam Store | 32 / 32 | GBP list/current prices available for all 32; optional metadata can remain null |
| Steam review summary | 32 / 32 | Counts reconcile for all titles; all languages/purchase origins, off-topic filter enabled |
| Steam current players | 32 / 32 | Successful API result and nonnegative counts; retrieval times recorded per title |
| SteamSpy | 32 / 32 | Owner bands returned; estimate suitability unapproved; all playtime fields unavailable |

- [Steam run manifest](../data/runs/steam-20261006T194553640385Z-e09f1dd7/manifest.json), completed 19:47:04 UTC.
- [Steam observations](../data/runs/steam-20261006T194553640385Z-e09f1dd7/observations.csv).
- [SteamSpy run manifest](../data/runs/steamspy-20261006T194621705248Z-731944ee/manifest.json), completed 19:46:56 UTC.
- [SteamSpy observations](../data/runs/steamspy-20261006T194621705248Z-731944ee/observations.csv).

The accepted Steam run contributes 32 schema-version-2 rows. The published history contains 96 rows in total: these 32 accepted rows plus 64 explicitly versioned legacy observations. Default analytical ingestion must use accepted version-2 runs; legacy observations require a separate admission decision.

## Assurance changes

The earlier collector could append new columns without rewriting its header and convert invalid review responses into zero counts. The revised collector declares its schema, validates API payloads and atomically publishes only complete runs.

Required-source coverage is 100% of the scoped universe. Failed attempts retain diagnostic evidence, return an unsuccessful exit status and leave the prior history/latest benchmark intact. Duplicate run/app keys and malformed legacy row widths stop publication.

The original history and benchmark are retained byte-for-byte in [the legacy archive](../data/runs/legacy-baseline/manifest.json). Source statuses and retrieval times are not reconstructed for those records. Twenty regression tests passed in a fresh Python 3.13 environment with pinned dependencies. Stored observation hashes, collector source hashes and legacy archive hashes were independently checked after collection.

Valve's current review service replaces the deprecated appreviews endpoint. Query scope is explicit and versioned; cross-version review deltas must be reconciled before use.

Scheduled acquisition now saves downloadable artifacts with read-only repository permissions. Publication is an owner review step. The workflow no longer commits as the Actions bot. Artifact retention is 90 days; accepted weekly observations must be published before expiry to build durable history.

## Interpretation decisions

- SteamSpy response coverage is not estimate accuracy. Three titles returned the lowest owner band; all owner estimates remain `requires_review`. No title-level sales or revenue conclusion is approved.
- All four SteamSpy playtime fields were zero across the returned baseline and are stored as unavailable. They cannot support engagement-depth measures.
- A validated zero current-player count is a measurement; a failed endpoint is missing evidence.
- GBP prices describe the UK storefront at retrieval time.
- Lifetime reviews are self-selected; recent sentiment and review themes have not been acquired.
- Weekly current players are an engagement pulse. Same-day baseline runs do not support weekly momentum, retention or average weekly concurrency.
- Reference groups contain one to four peers. The tactical RPG comparison has one reference title; robust group ranking is not supported.
- Steam-only signals cannot establish cross-platform demand, publisher net revenue, marketing return or causal promotional uplift.

## Handoff to analytical modelling

Issue 2 should define separate observed and estimated fact tables, title/date dimensions and governed peer relationships. It must enforce NULL/status semantics, metric evidence classes, reproducible SQL builds and publication checks. Lifecycle age must be calculated from documented release-date rules rather than silently inheriting curated labels. Trend measures require comparable observations across sufficient distinct periods.

**Issue 2 has not started.** No performance recommendation is made from this baseline.
