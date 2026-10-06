# GitHub issue plan

These are the delivery milestones for the project.

## Issue 1 — Acquire and validate baseline commercial data

**Goal:** establish a reliable title universe, peer groups and repeatable acquisition pipeline.

Tasks:
- validate 505 portfolio title list and Steam app IDs
- validate competitor app IDs and peer-group rationale
- run Steam Store, review-summary and current-player collectors
- acquire and validate a separate SteamSpy benchmark; retain Hugging Face as a research fallback
- record source, retrieval time and failures
- confirm no field is being interpreted as internal sales / revenue

Done when:
- baseline snapshot exists for the scoped titles
- source coverage and gaps are documented
- acquisition can be rerun without manual edits

## Issue 2 — Build analytical model and metric dictionary

Tasks:
- design title, date, peer-group and snapshot tables
- standardise price, review and engagement fields
- define lifecycle logic
- define benchmark and momentum measures
- add data-quality checks
- create SQL / analytical-ready outputs

Done when:
- typed facts, dimensions and reporting views from one accepted release can feed Python and Power BI
- metric definitions are documented and reproducible
- local and hosted builds, quality checks and independent review pass

## Issue 3 — Benchmark portfolio and market performance

Tasks:
- compare eligible direct-peer medians and configured-reference percentiles with counts and coverage gates
- assess separate review-response, cumulative review-scale and concurrent-player snapshot signals
- retain as-of lifecycle context and explicitly unavailable engagement-depth or trend measures
- document supported contrasts and ambiguous cases without unsupported overall performance labels
- publish reproducible SQL outputs and qualified commercial findings with evidence follow-ups

## Issue 4 — Analyse pricing, promotions and commercial response

Tasks:
- connect a historical price source
- build price / discount history
- measure review / player movement around promotions
- distinguish temporary spikes from sustained momentum
- avoid causal claims where no valid counterfactual exists
- create pricing / promotion recommendations

## Issue 5 — Analyse player reviews and brand perception

Tasks:
- acquire a reproducible review sample
- clean review text and timestamps
- classify themes such as performance, value, content, controls, difficulty and updates
- compare recent versus lifetime themes
- identify issues that could make acquisition spend inefficient
- produce title-level player insight summaries

## Issue 6 — Build forecasts and commercial scenarios

Tasks:
- choose forecast targets that public data can actually support
- create base / upside / downside scenarios
- separate observed metrics from assumptions
- test sensitivity to price, demand and engagement inputs
- define decision thresholds
- document where internal data would replace public proxies

## Issue 7 — Build Power BI executive report and recommendation

Tasks:
- executive portfolio page
- title drill-through
- pricing / promotion page
- player / brand page
- scenario page
- final Invest / Promote / Maintain / Monitor / Deprioritise recommendations
- one-page commercial decision memo

## Issue 8 — Verify reproducibility and publish commercial case study

Tasks:
- rerun acquisition and analysis from a clean environment
- add validation tests
- document limitations and source dates
- polish README around the commercial decision
- publish portfolio case study
- publish the commercial decision memo and evidence traceability
