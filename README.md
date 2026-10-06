# Games Commercial Intelligence

**Status: Stage 1 complete — baseline data acquired and validated**

This is an independent portfolio project built around a commercial analytics question:

> How should a premium games publisher use player demand, pricing, product performance and market signals to decide where to invest, promote, monitor or deprioritise across its portfolio?

The initial case portfolio uses a curated set of 505 Games titles on Steam and a peer set of comparable premium games. The project is not affiliated with 505 Games, Digital Bros, Valve, Steam or any competitor publisher.

## Why this project exists

The goal is not to build another games dashboard. The goal is to recreate the type of decision support expected from a commercial insight / BI analyst working with a Head of Commercial or premium-products team.

The analysis will eventually connect:

- portfolio and market performance
- player demand and engagement
- pricing and promotion
- player reviews and brand perception
- commercial forecasting and scenario analysis
- clear investment and product recommendations

## Stage 1 data foundation

The repository starts with:

- 12 505 Games portfolio titles across new release, growth, mature and back-catalogue stages
- 20 comparable games grouped by commercial peer set
- Steam Store metadata and pricing acquisition
- Steam review-summary acquisition
- current-player snapshots
- a separate SteamSpy market benchmark for estimated owner / CCU fields, kept apart from observed Steam metrics
- a scheduled GitHub Actions collector so the project can build its own weekly time series

Run locally:

```bash
pip install -r requirements.txt
python src/collect_snapshot.py
```

The output is appended to:

`data/snapshots/commercial-snapshot-history.csv`

## Commercial questions

1. Which titles are outperforming or underperforming their peer group?
2. Where is player sentiment improving or deteriorating?
3. Which back-catalogue titles still show durable demand?
4. Which products appear over- or under-positioned on price relative to peers?
5. How do promotions and price changes relate to player/review momentum?
6. Which titles should receive additional commercial support?
7. What evidence would be needed before making a real revenue or acquisition decision?

## Milestones

1. Acquire and validate the baseline data.
2. Build the analytical model and metric dictionary.
3. Benchmark portfolio and market performance.
4. Analyse pricing, promotions and commercial response.
5. Analyse player reviews and brand perception.
6. Build forecasts and commercial scenarios.
7. Build the Power BI executive report and recommendation.
8. Verify reproducibility and publish the portfolio case study / interview pack.

## Analytical safeguards

Public data does **not** equal internal publisher data.

- Estimated owners are treated as estimates, not unit sales.
- Public player counts are engagement proxies, not DAU or MAU.
- Steam reviews are self-selected and do not represent every player.
- Observed promotional movements are not automatically causal.
- Any external revenue estimate will be labelled as an estimate or scenario, never as 505 Games' actual revenue.
- Steam-only analysis will be clearly separated from conclusions about console or total portfolio performance.

See `docs/Data limitations.md` for the full boundary conditions.


## Current progress

Stage 1 is complete. The initial acquisition pipeline collected live Steam data for all 32 scoped titles and a separate market benchmark. See [Stage 1 acquisition findings](docs/Stage%201%20acquisition%20findings.md) for coverage, limitations and the decision on which fields are safe to use.
