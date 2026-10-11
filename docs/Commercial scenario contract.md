# Commercial scenario specification

The decision is whether a proposed price test has a plausible economic requirement and what evidence is needed before approving it. The scenario layer calculates conditional requirements from dated Steam price anchors and explicit assumptions. It does not estimate demand or approve spend.

## Evidence and assumptions

The [versioned assumption contract](../data/scenario-contract.json) is separate from the accepted model and its metric dictionary. The builder verifies the pinned model manifest, all exported CSV hashes, SQL and helper code before using its twelve portfolio rows. Observed price, currency, retrieval timestamp and source run stay in a separate anchor table. The prices were retrieved on 6 October 2026; they are not live quotes. They may already reflect a discount. Hypothetical reductions are relative to those final prices, not additional percentage points off list price.

No paid-unit baseline has been observed. A relative paid-unit index of 100 is a normalization assumption. Engagement has its own assumed index of 100 and stays outside the transaction-value equation. Point-in-time concurrent players remain observed context only; they are not used to infer paid units, active-user cohorts or retention.

| Planning case | Price relative to dated final-price anchor | Assumed paid units relative to unobserved baseline | Separate engagement index |
|---|---:|---:|---:|
| Hold reference | 100% | 100% | 100 |
| Downside | 90% | 90% | 80 |
| Base | 90% | 120% | 100 |
| Upside | 90% | 140% | 120 |

These are analyst-selected stress cases, not measured responses, probabilities or recommendations. “Base” is the name of a planning case, not an expected result. The sensitivity grid varies price at 100/90/80%, paid units at 80/100/120/140%, and engagement at 80/100/120. Changing engagement leaves the economic result unchanged.

## Equations and thresholds

Hypothetical prices are rounded to integer pence with Decimal ROUND_HALF_UP. The effective price ratio uses the rounded price, so a small-price title's ratio can differ slightly from the nominal assumption.

`conditional gross receipts index = 100 × rounded hypothetical price / anchor price × assumed paid-unit factor`

This is a normalized gross storefront transaction-value calculation. It does not model tax remittance, refunds, fees, costs, currency movements, edition mix or publisher receipts. It is not net revenue or profit. No absolute unit count or currency revenue total is produced.

`gross-receipts-neutral paid-unit factor = anchor price / rounded hypothetical price`

Above, equal to, or below index 100 describes conditional arithmetic relative to holding price and units constant. The neutral threshold is not cost break-even. It cannot justify an Invest or Promote decision without paid-unit response and contribution economics. Missing/unsuitable anchors produce unavailable economic measures. A genuine zero anchor is retained as observed but cannot define a relative value baseline. A zero hypothetical price has zero conditional receipts under a positive anchor and an undefined neutral-unit threshold, never infinity.

For a £10 anchor, a hypothetical £9 price requires 1.111111 times the units, or approximately 11.1% more. At 1.2 times the units, its gross transaction-value index would be 108. Neither calculation estimates how buyers will respond.

## Outputs and admission

Run `python src/commercial_scenarios.py`. [Current built package](../data/scenarios/current.json) points to an immutable release containing:

- `observed_anchors.csv`: 12 dated price anchors with observed/source status and an unobserved paid-unit baseline.
- `commercial_scenarios.csv`: 48 conditional cases, including a hold reference.
- `scenario_sensitivity.csv`: 432 price/volume/engagement combinations.
- `receipts_neutral_thresholds.csv`: 36 conditional price thresholds.
- `forecast_readiness.csv`: 12 title-level availability assessments with unsupported forecasts, errors and intervals left empty.

The manifest binds the accepted model, contract, builder and every output hash. No new source is collected and no peer role, source admission or prior suitability rule is changed. Build status is a creation-time record, not independent acceptance. The subsequent [verification receipt](verification/scenarios-38150259475.json) records hosted artifact evidence and final independent bounded acceptance on 11 October 2026; consumers must retain that scope when using the package. Repeated builds must be byte-identical; a differing existing release fails without moving the pointer.

## Forecast validation and uncertainty

The current model has one accepted Steam observation per title and zero qualifying comparable weeks. It has no paid-unit target series or untouched forecast holdout. Current retrieved review text is not historical sentiment, review counts are not sales, and provider-container price records do not establish SKU continuity or promotional response. Predictive targets, MAE, WAPE, intervals, elasticity and ROI remain unavailable. A stress range is not a confidence or prediction interval.

With internal data, the preferred target is weekly net paid units at a stable title/SKU × platform × country grain, with a separate realised-net-revenue series and reconciliation to refunds and accounts. Public weekly point concurrency and net review-count change could support their own descriptive signal models if coverage later qualifies; they would still not forecast units or publisher revenue. Four comparable weeks meet an existing momentum gate, not a forecasting sufficiency standard.

The proposed internal-data validation design needs agreement with the data owner before implementation:

1. Require at least 52 contiguous training weeks plus 12 untouched holdout weeks, stable definitions, documented missingness and promotion/launch regimes. This is an initial design requirement, not proof that a model will be suitable. Longer history is needed for reliable annual seasonality.
2. Fix a four-week horizon and weekly rolling origins before looking at holdout outcomes. Fit on data available at each origin; reserve at least nine origins with complete four-week outcomes. Compare last-observation and trailing-four-week-mean baselines before assessing more complex models. Do not use revised future observations or future campaign knowledge as historical features.
3. Report MAE by horizon and title; use WAPE only with a positive sum of actual paid units, otherwise leave it unavailable. Show signed bias and performance relative to baselines. Aggregate only reconciled units at compatible grains; do not hide title-level failure in a portfolio total.
4. Estimate predictive intervals from a declared method using training data, then assess nominal coverage and width on untouched outcomes. Scenario bounds cannot serve as predictive intervals. Record the realised validation results before accepting a forecast; no results have been obtained here.
5. Reassess regime changes, cold-start titles and inadequate history separately. Promotion causality requires a suitable experiment or governed comparison design beyond predictive validation.

For budget decisions, internal price/calendar and paid-unit response replace assumed volume; publisher net receipts, fees, tax, refunds, contribution costs and marketing spend replace the gross-value proxy. Player cohorts and support records validate engagement and product hypotheses separately. Confirm SKU identity, platform/country coverage and current price before any test. A robust contribution case, operational capacity and an approved experiment are required before allocating money.

The accepted ITAD evidence remains provider-container Steam-shop GB/GBP context for 15 September–6 October 2026. It is not annual price history, a validated price-response series or SKU-continuous promotion evidence. Stage 5 remains a qualified player-feedback investigation agenda; its diagnostic examples do not supply volume forecasts or measured commercial effects.
