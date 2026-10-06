# Stage 1 acquisition findings

## Status

Baseline acquisition is complete for the initial scoped portfolio.

- 12 505 Games portfolio titles
- 20 commercial peer titles
- 32 titles in total
- two successful live Steam snapshots are now stored in the repository
- one complete SteamSpy market benchmark is stored separately

Latest baseline collection: 6 October 2026 (UTC).

## Source coverage

### Steam Store metadata and price
Coverage: 32 / 32 titles.

Collected fields include live title name, developer, publisher, release date, GBP list price, GBP current price, discount percentage, genres, categories and Metacritic score where available.

### Steam review summary
Coverage: 32 / 32 titles.

Collected fields include positive reviews, negative reviews, total reviews, review-score category and positive-review percentage.

### Current Steam players
Coverage: 32 / 32 titles.

This is a point-in-time concurrent-player measure. It is useful as an engagement pulse but must not be treated as DAU, MAU, retention or total active players.

### SteamSpy market benchmark
Coverage: 32 / 32 titles.

Collected fields include estimated owner range, public CCU estimate, price, positive/negative counts and playtime fields exposed by the endpoint.

## Important data-quality findings

1. The first automated Hugging Face benchmark attempt timed out. The live collection pipeline was therefore separated from the market-estimate layer and the benchmark source was changed to SteamSpy.

2. SteamSpy owner ranges are not decision-grade for newly released / low-sample titles. For example, several recent titles are returned in the lowest owner band even when their Steam review counts are already substantial. SteamSpy itself warns that its estimates can be unreliable for recent or small-sample games.

3. SteamSpy playtime fields were returned as zero in this baseline pull. We will treat them as unavailable rather than interpreting zero as genuine player behaviour.

4. Steam Store price fields are regional snapshots. The project currently collects the UK storefront and stores monetary amounts in minor GBP units.

5. Steam review data is all-time and self-selected. Recent-review windows and review text will be acquired separately in the player / brand milestone.

6. Current-player values are sensitive to collection time. Repeated weekly snapshots are required before any momentum conclusion is made.

7. Public data cannot provide internal publisher net revenue, platform fees, refunds, marketing spend, wishlist conversion or acquisition cost. Those will remain explicit missing-data constraints.

## Stage 1 decision

The public Steam data is strong enough to proceed with:
- portfolio and peer benchmarking
- live price / discount positioning
- review and sentiment comparisons
- point-in-time engagement monitoring
- building our own weekly history

The public data is not strong enough to support:
- audited revenue estimates
- marketing ROI
- cross-platform performance conclusions
- causal claims about promotions
- reliable owner estimates for every recent title

## Next step

Build the analytical data model and metric dictionary so the live Steam snapshot and the separate benchmark layer can be joined without mixing observed first-party storefront metrics with third-party estimates.
