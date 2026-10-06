# Pricing and promotion analysis

## Delivery state

Issue 4 is in progress. Source identity discovery, a validated history collector, reviewed-run admission and deterministic recorded-discount sequence construction are implemented. Live historical-price acquisition requires an IsThereAnyDeal API key; no historical run is accepted and no pricing-analysis output is published yet.

The available evidence remains the accepted October 6 snapshot and the Stage 3 positioning findings. This stage has no new historical pricing or promotional-response conclusion to report.

## Source discovery

All 32 scoped Steam app IDs resolve and reverse-check through official IsThereAnyDeal lookup. Thirty-one have a unique app association. Ready or Not has an additional app association and remains excluded from history until reviewed. Complete inverse mappings and package/sub aliases are preserved.

The source is current ITAD game-container history for Steam shop 61 in GB/GBP. Historical Steam-app association and exact SKU/edition attribution are not independently verified. This limit applies even to currently uniquely app-linked titles.

Foundation review identified that current lookup alone cannot establish historical identity continuity. The collector now checks and preserves the official assignment-change log before and after price collection, excludes touched game entries, and blocks capped, failed or malformed evidence. A newly detected reassignment fails the run and requires recollection; admission proves that the postflight check covers the final price retrieval. A clean returned log remains source evidence rather than independent proof of continuity. Coverage labels distinguish mapping exclusions, reassignment exclusions, empty returned logs and observed records.

The [contract](Price%20history%20contract.md) defines the explicit history window, as-of cutoff, currency checks, source timestamps, unknown boundaries, empty histories, source removals and sequence rules. The [source evidence](../data/price-history/discovery-20261006/manifest.json) records request and hash provenance.

## Validation and remaining evidence

Forty-one price-history tests exercise source validation, duplicate/conflict handling, missing and zero prices, explicit dates, censoring, sequence changes, bounded retries, secret-safe diagnostics, assignment/reassignment and cap controls, admission/tamper controls, repeated publication and exclusion of a current snapshot from historical response. These fixtures demonstrate processing behavior; they are not real historical observations or findings.

[Hosted validation](https://github.com/Jeks042/games-commercial-intelligence/actions/runs/37544809642) passed all 108 tests, including the post-collection assignment controls, rebuilt the prior-stage model and positioning outputs, and verified identical reruns. The initial corrective-run artifact matches all six committed pricing source-foundation inputs and contains no accepted history run or live pricing release. The [verification receipt](verification/pricing-foundation-37544130387.json) records the initial artifact digest and the final corrective commit and validation scope.

Separate source-foundation review accepted corrective commit `c3436d9`, including the post-collection temporal coverage control. This acceptance applies to the tested foundation only; no live data or final Stage 4 findings are signed off.

The next gates are live API access, successful collection and payload review, explicit admission, real output verification, peer-context interpretation and independent sign-off. Commercial response remains unavailable until independently dated evidence and a defensible comparison design exist. Pricing or promotion recommendations will state the evidence they depend on; source availability cannot substitute for evidence of effectiveness.

Issue 5 remains unstarted.
