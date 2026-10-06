# Portfolio and market-reference positioning

## Commercial readout

The accepted 6 October 2026 Steam snapshot supports three areas for further investigation: player-response diagnosis for WUCHANG and Assetto Corsa EVO; Eiyuden's response gap against its configured JRPG references; and the observed activity of established catalogue products. These are evidence-led investigation priorities, not a budget allocation or a ranking of commercial returns.

Only Eiyuden has enough configured direct peers for group statistics. The other 11 portfolio titles retain individual reference context, with group measures suppressed. No title is classified as an overall outperformer or underperformer. The evidence does not resolve relative commercial performance, growth or engagement depth.

The reproducible SQL outputs cover all 12 selected portfolio titles and 38 governed reference relationships. [Methodology](Benchmarking%20methodology.md), [signal definitions](benchmark-metrics.csv), [pinned input contract](../data/benchmarking-contract.json) and the [current output release](../data/positioning/current.json) document the measurement basis.

## Observed portfolio position

Figures below are the frozen observation period, not live prices or player counts. Steam sources were retrieved during approximately 19:45–19:47 UTC on 6 October. Each exported row retains exact per-source timestamps. Positivity is lifetime review response under the admitted query contract; concurrent players are a point sample.

| Title | Analytical lifecycle | Final UK price | Discount | Lifetime reviews | Positive | Current players | Direct peers |
|---|---|---:|---:|---:|---:|---:|---:|
| Assetto Corsa | Back catalogue | £3.87 | 75% | 174,877 | 92.87% | 13,017 | 2 |
| Assetto Corsa Competizione | Back catalogue | £8.74 | 75% | 48,703 | 92.70% | 3,117 | 2 |
| Ghostrunner | Back catalogue | £6.24 | 75% | 67,005 | 91.18% | 142 | 1 |
| Miasma Chronicles | Back catalogue | £8.99 | 70% | 3,075 | 79.77% | 48 | 1 |
| Eiyuden Chronicle: Hundred Heroes | Established | £13.49 | 70% | 4,676 | 75.34% | 67 | 3 |
| DEATH STRANDING DIRECTOR'S CUT | Back catalogue | £8.74 | 75% | 69,434 | 92.17% | 2,574 | 0 |
| Blades of Fire | Early lifecycle | £17.49 | 50% | 715 | 75.24% | 35 | 2 |
| Ghostrunner 2 | Established | £6.99 | 80% | 11,665 | 79.96% | 50 | 1 |
| WUCHANG: Fallen Feathers | Established | £31.49 | 30% | 106,618 | 57.33% | 448 | 2 |
| Crime Boss: Rockay City | Established | £1.59 | 90% | 10,653 | 68.32% | 169 | 1 |
| Assetto Corsa EVO | Early Access | £26.39 | 20% | 21,521 | 58.95% | 1,267 | 2 |
| Assetto Corsa Rally | Early Access | £19.99 | 20% | 10,903 | 87.73% | 988 | 1 |

Discounts are rounded from observed list/final prices; source rounding explains small deviations from whole percentages. Direct-peer counts describe the configured reference set, not all competitors in the market. Every row has unavailable momentum and playtime-derived engagement depth.

## Eiyuden: a measurable response gap, with lifecycle limits

The configured direct references are Chained Echoes, Sea of Stars and OCTOPATH TRAVELER II. All three pass the metric-specific collection and review-contract gates. Eiyuden's final price was £1.26 below their £14.75 median, an index of 0.9146. That is discounted price positioning; it does not establish value for money or an optimal selling price.

| Separate signal | Eiyuden | Direct-reference median (n = 3) | Difference / ratio | Reference-set percentile |
|---|---:|---:|---|---:|
| Final GBP price | £13.49 | £14.75 | £1.26 lower; ratio 0.9146 | 33.33 |
| Lifetime review positivity | 75.34% | 88.58% | 13.24 percentage points lower | 0 |
| Lifetime review count | 4,676 | 15,646 | Ratio 0.2989 | 0 |
| Current players at retrieval | 67 | 385 | Ratio 0.1740 | 0 |

These are coarse percentiles within three selected references, not market percentiles. A zero position means below those observed reference values. Price, response and activity are kept separate; they are not combined into a performance score.

Eiyuden was 896 Steam days old; the references were 1,135–1,398 days old and in a different analytical lifecycle bucket. Lifetime review volume reflects accumulated attention across unequal exposure periods. No age adjustment or current-demand inference is applied. Even the positivity gap may reflect differences in expectations, audience and release history.

The appropriate next investigation is review-theme and recent-versus-lifetime response analysis, followed by a check against internal platform sales, traffic and conversion. A price change or promotional prescription is premature without that evidence.

## Player response and product diagnosis

WUCHANG records 57.33% positive lifetime reviews across 106,618 reviews. Its two direct references record 67.98% for Lords of the Fallen and 91.61% for Lies of P. These are individual comparisons; n = 2 is insufficient for a group statistic. WUCHANG's accumulated review scale alongside its lower positive share makes response diagnosis a useful investigation, but it does not prove that the same issues still affect today's players. ELDEN RING remains a category-scale reference and Black Myth: Wukong an adjacent reference, excluded from direct-peer measures.

Assetto Corsa EVO records 58.95% positivity across 21,521 reviews, while Assetto Corsa Rally records 87.73% across 10,903. Both are observed Early Access products. Their audience, driving segment and development stage differ; this within-portfolio contrast is not a controlled performance comparison. EVO's direct references, Automobilista 2 and Le Mans Ultimate, also have different lifecycle context. Recent review themes and update history are needed before treating the lifetime response as a current product issue.

Ghostrunner 2 records 79.96% positivity compared with 91.18% for Ghostrunner. The shared franchise context can guide a diagnostic question, but the sequel's younger Steam age, different review population and release expectations prevent attributing the gap to a specific cause. Its single direct reference, Neon White, is context rather than a group benchmark.

Crime Boss records 68.32% positivity; its direct heist reference PAYDAY 3 records 46.35%. The higher percentage against one reference does not establish overall outperformance. The 90% snapshot discount also cannot establish promotion effectiveness without before/after evidence and an appropriate comparison.

## Catalogue activity and lifecycle context

Assetto Corsa, Assetto Corsa Competizione and DEATH STRANDING DIRECTOR'S CUT record 13,017, 3,117 and 2,574 current players respectively, alongside positivity above 92%. This establishes visible catalogue activity at retrieval. It does not establish sustained engagement, retention, revenue or promotional efficiency. Different play styles also make raw concurrency unsuitable as a cross-genre product-quality ranking.

Assetto Corsa's individual direct references record 376 players for rFactor 2 and 1,349 for Automobilista 2. The larger point sample is an observed contrast within the declared racing context; with two references and one observation period, it remains insufficient for a group ranking or a sustained-activity claim.

Miasma Chronicles records 48 current players and 79.77% positivity, versus 2,369 players and 88.34% for its single direct reference Jagged Alliance 3. The pair provides a question for closer investigation, not a tactical-RPG market benchmark. Ghostrunner's 142 current players and DEATH STRANDING's 2,574 are reported without ranking the unrelated player bases.

The portfolio contains five back-catalogue, four established, two Early Access and one early-lifecycle title. Blades of Fire is 145 Steam days old, with 715 reviews, 75.24% positivity and 35 current players. It is not a launch-period cohort observation. Comparing these products' cumulative review counts as if they had equal time in market would misstate performance. No age-normalised demand rate is fabricated.

## Evidence required for commercial action

| Investigation | Evidence established here | Next evidence | Decision it could inform |
|---|---|---|---|
| WUCHANG / EVO response diagnosis | Lifetime response and role-labelled reference context | Dated review themes; recent sentiment; update timeline; internal refund/support evidence | Whether current product issues should be addressed before further promotion |
| Eiyuden response and positioning | Eligible unadjusted three-reference gap; discounted price | Review themes; platform traffic/conversion; net sales; historical prices | Whether attention should go to product messaging, experience or pricing tests |
| Catalogue opportunity | Positive lifetime response and point-in-time player activity | Four comparable weekly pulses; internal sales/margin; audience and promotion history | Whether observed activity persists and can support a commercial opportunity |
| Sparse reference groups | Explicitly insufficient group coverage | Research and approve additional genuinely direct peers, where available | Whether a broader comparison is defensible; no automatic promotion of adjacent products |

Recent sentiment and review themes belong to Issue 5; historical pricing and promotional response belong to Issue 4. Those stages will need new, admitted evidence. No ownership-derived demand, engagement-depth, momentum, sales or causal claim is used in this memo.

## Delivery assurance

Issue 3 is accepted. The implementation passes 67 tests locally and on GitHub: 20 acquisition, 24 modelling and 23 positioning tests. All nine positioning SQL quality gates pass. Tests cover sparse/non-direct references, missing prices, low review counts, source-date/time and review-contract mismatches, median and tie handling, genuine zero and undefined ratios, lifecycle context, input/dictionary/output tampering and repeatable publication.

[Hosted validation](https://github.com/Jeks042/games-commercial-intelligence/actions/runs/37538939826) passed both the model and positioning builds, identical reruns and artifact upload. The downloaded artifact passed ZIP and database hashes, integrity and foreign-key checks, all 13 model checks and all nine positioning checks. All five positioning CSV hashes match the local release and independently regenerated exports from the hosted database. The pinned model's 13 CSV hashes were also verified.

Hosted Python 3.13.15 / SQLite 3.45.1 and local Python 3.13.7 / SQLite 3.50.4 produce matching consumer CSVs. Runtime fingerprints intentionally differ. The [verification receipt](../data/positioning/verification-37538939826.json) records the evidence; a durable private artifact copy is retained.

Independent read-only review accepted the implementation and findings contract with no blocking issue. It checked input lineage, reference roles and coverage, temporal comparability, review contracts, lifecycle context, zero/NULL semantics, percentiles, publication controls and interpretation. Downloaded-artifact verification satisfied the final acceptance condition. [Issue 3](https://github.com/Jeks042/games-commercial-intelligence/issues/3) records completion.

Issue 4 remains unstarted. Its next requirement is an appropriate historical pricing source and dated commercial-response observations; this snapshot is not promotion-effect evidence.
