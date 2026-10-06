# Metric contract

The [machine-readable dictionary](metric-dictionary.csv) defines 20 implemented fields/measures: evidence class, grain, source, definition, units, availability and decision limits. It is loaded into dim_metric.

| Evidence class | Treatment |
|---|---|
| Observed | Validated source values, including genuine zero |
| Estimated | External sampled/modelled measures, kept separate from observed Steam activity |
| Derived | SQL calculations from admitted values with explicit gates |
| Assumption | Reserved for later scenarios; none introduced here |

Supported measures include UK prices/discounts, lifetime review counts and positivity, point-in-time concurrency, as-of Steam title age and lifecycle. Direct-reference price positioning is available only where coverage qualifies.

Player change and net review velocity remain NULL until four consecutive comparable weeks exist. Same-day runs do not qualify. Recent sentiment, historical peak CCU, promotion uplift, forecasts and publisher revenue are not implemented.

SteamSpy ownership retains requires_review. Baseline playtime is NULL and cannot support engagement-depth conclusions.

GBP conversion follows source currency validation. Positivity is NULL with no reviews. Undefined ratios are never replaced by zero or infinity. Review velocity is net cumulative-count change, not newly authored reviews or sales. Player change compares point samples, not average weekly activity or retention.

The [model specification](Data%20model.md) defines reference thresholds, UTC slots, freshness limits, lifecycle boundaries and admission. These are declared analytical policies.
