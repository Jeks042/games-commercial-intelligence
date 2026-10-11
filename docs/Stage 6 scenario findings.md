# Commercial scenarios and forecast readiness

## Decision implication

A lower storefront price creates a volume requirement. Public price, review and concurrency evidence cannot show whether a title will meet that requirement, so no promotional budget or price change is approved from these scenarios. The useful output is a transparent threshold for a proposed test, with the data needed to decide whether the test is economically justified.

For a £10 anchor, a hypothetical 10% price reduction needs approximately 11.1% more paid units to preserve gross transaction value, before costs. The declared base case assumes 20% more paid units and produces an index of 108; the downside assumes 10% fewer and produces 81; the upside assumes 40% more and produces 126. These values are conditional arithmetic, not estimated outcomes. Penny rounding slightly changes the thresholds for actual title anchors.

The [scenario specification](Commercial%20scenario%20contract.md) and [assumption contract](../data/scenario-contract.json) expose the normalization, price rounding, equations and decision boundaries. The price anchor is the accepted 6 October Steam final storefront price. It can already be discounted and is not a live quote or a continuous historical SKU price.

## Delivered package

The builder verifies the pinned accepted model before producing twelve dated anchor/readiness rows, 48 scenario rows, 432 sensitivity combinations and 36 receipts-neutral thresholds. Price and paid-unit assumptions affect the conditional transaction-value index. Engagement varies independently and never becomes a purchase or retention estimate. The [built release](../data/scenarios/current.json) binds the source/model, builder, contract and output hashes; public rebuilds need no API key.

Forecasts are unavailable for every portfolio title. Each has one accepted Steam observation and zero qualifying comparable weeks. There is no paid-unit series or untouched holdout. Forecast values, MAE, WAPE, prediction intervals, elasticity and ROI remain empty. Scenario bounds are not predictive uncertainty. The specification defines an internal-data validation plan rather than claiming it has been executed.

## Validation and delivery state

Local and [hosted validation](https://github.com/Jeks042/games-commercial-intelligence/actions/runs/38150259475) passed 199 tests, including 18 scenario arithmetic, input-suitability, missingness and publication-control checks. Public scenario builds produced identical files and pointers on rerun. The tests cover penny rounding, unchanged receipts under different engagement assumptions, genuine zero versus unavailable values, model tampering, contract changes and immutable-release corruption.

The [verification receipt](verification/scenarios-38150259475.json) records the downloaded artifact digest and byte checks. All eight scenario files match committed local bytes across Python 3.13.7 and 3.13.16. Sixteen prior source/refinement files and all 28 prior consumer outputs are unchanged; private raw data is absent from the 195-entry artifact. These are arithmetic, evidence-integrity and publication checks, not empirical forecast validation.

Final independent Stage 6 review remains pending. Issue 6 stays open until the reviewer accepts the bounded scenario/readiness objective or identifies a concrete outstanding criterion. No final acceptance, validated forecast or completed Power BI report is claimed. Issue 7 has not started.

The prior source, model, references, pricing and player-review contracts remain unchanged. Provider-container Steam-shop GB/GBP context is still limited to 15 September–6 October 2026; historical SKU continuity, annual history, promotional response and causal effects remain unavailable. Review diagnostics do not establish population sentiment, concern prevalence or demand. Internal paid units, publisher receipts, refunds, contribution costs, promotion calendars and experiment evidence are needed before these conditional requirements can become a spending decision.
