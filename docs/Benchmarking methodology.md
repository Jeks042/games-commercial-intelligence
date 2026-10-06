# Portfolio benchmarking contract

This analysis reads the explicitly accepted Stage 2 release pinned in [benchmarking-contract.json](../data/benchmarking-contract.json). It verifies the manifest and all 13 model CSV hashes, reconstructs typed facts and dimensions using the hash-matched model SQL, and reruns the model quality gates before calculating positioning. It does not read a mutable history CSV or select a newer model simply because it exists.

The [signal dictionary](benchmark-metrics.csv) defines the four separate measures. Source measures keep the Stage 2 definitions; benchmarking adds interpretation and coverage rules. No composite score, sales estimate, engagement rate or overall performance classification is calculated.

## Comparisons and eligibility

All 38 governed relationships remain visible as individual references, with role, rationale, source run IDs, retrieval timestamps and lifecycle context. Category leaders, adjacent references and lifecycle references provide context; they never fill a direct-peer group.

Group measures require at least three configured direct peers and complete comparable coverage for the metric. Every pair must share its source UTC date and be collected within 300 seconds. Price comparisons require available GBP quotes; both review measures require the same query contract. Review positivity additionally requires at least 100 lifetime reviews for both title and reference. This is a declared stability policy, not a claim about statistical confidence or sample representativeness. Review volume can retain a genuine zero.

Changing one source's availability suppresses that metric only. Sparse or incomplete groups have NULL medians, differences, ratios and percentiles. The outputs expose expected and valid reference counts and the reason a measure is unavailable. A pair can remain useful context even when the group statistic is suppressed.

## Calculations

The median is the central value, or the mean of the two central values for an even reference count. The portfolio title is excluded from its reference distribution.

- Difference = target minus reference median, in the metric's unit. Positivity differences are percentage points.
- Ratio = target divided by reference median for price, review count and current players. A zero denominator produces NULL with a zero-reference status; a genuine zero target produces zero when the denominator is positive. Positivity uses a percentage-point difference instead of a ratio.
- Reference-set empirical percentile = `100 * (references below the target + 0.5 * references equal to the target) / valid reference count`.

Percentiles describe only the configured references. At n = 3, a result can move in steps of 33.3 points without ties; it is a coarse descriptive position, not a genre or market percentile. A zero percentile means the target falls below the three observed values; it does not mean zero commercial potential. Higher is not inherently better across these different measures.

## Lifecycle and time

The model retains as-of Steam age, observed Early Access and the declared analytical lifecycle buckets. Individual pairs show both lifecycles; group outputs show target age, reference age range and same-bucket reference count. Even a shared bucket does not adjust for exact age, budget, genre details, platform scope or release history.

All measures are explicitly unadjusted snapshot context. There is no valid launch cohort in the accepted portfolio baseline: Blades of Fire is 145 Steam days old and classified early_lifecycle; two racing products are observed Early Access. Lifetime review counts are not divided by age to manufacture a current demand rate. Cross-lifecycle and cross-genre differences cannot establish relative performance.

The portfolio output carries model momentum availability unchanged. No qualifying weekly history exists here, so sustained activity and trend claims are unavailable. Public concurrent players lack a reliable active-base denominator; unavailable SteamSpy playtime cannot support engagement depth. Ownership estimates remain excluded pending suitability review. Previous-day SteamSpy peak context is not substituted for current Steam players.

## Reproduce and consume

```bash
python src/benchmark_portfolio.py
python -m unittest discover -s tests -v
```

The builder publishes five CSVs, a reproducible SQLite database and a manifest under a content/runtime fingerprint. SQL is under `sql/benchmarking/`, separate from the frozen Stage 2 scripts. The [current positioning release](../data/positioning/current.json) points to an immutable output directory only after all checks pass. An identical rerun verifies existing bytes. A failed input check or quality gate leaves the last pointer intact. The database is regenerated locally and retained in hosted artifacts; CSVs and manifest are versioned in Git.

| Output | Grain and purpose |
|---|---|
| v_portfolio_positioning | One portfolio title; source observations and readiness |
| v_reference_pair_context | One governed title/reference pair; roles, lifecycle and timestamps |
| v_reference_metric_context | One pair/metric; gated individual difference and ratio |
| v_direct_peer_benchmark | One portfolio title/metric; gated group measures and n |
| v_lifecycle_coverage | Cohort/lifecycle inventory; no cross-genre performance ranking |

CSV empty fields mean SQL NULL; numeric zero remains zero. Consumers must retain statuses, roles and denominators with displayed values. Benchmarks and pair comparisons have different grains and must not be summed together. Reference-set percentiles are non-additive. The [findings memo](Stage%203%20benchmarking%20findings.md) is the commercial interpretation of this frozen observation period.
