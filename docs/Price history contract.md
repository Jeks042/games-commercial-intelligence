# Historical price evidence

The source adapter uses the [IsThereAnyDeal API](https://docs.isthereanydeal.com/), with [official history schema](https://github.com/IsThereAnyDeal/API/blob/master/docs/routes/games/history.v2.yaml) and [usage terms](https://github.com/IsThereAnyDeal/API/blob/master/TERMS_OF_SERVICE.md). This is independent public portfolio analysis, with no affiliation to IsThereAnyDeal. Original response bytes and source values are retained; derived interpretations are separate from the supplied data. This repository is not a price-comparison service.

## Identity and coverage

The [source contract](../data/price-history/source-contract.json) pins discovery evidence and the accepted analytical model. Official Steam shop discovery, forward `app/{id}` lookup and inverse lookup cover all 32 scoped titles. Raw source bytes, query routes, retrieval times and hashes are retained under `data/price-history/discovery-20261006/`.

Thirty-one current mappings have one Steam app identity. Ready or Not also maps to app/840820 and is excluded pending identity review. Package/sub aliases are preserved for every title. ITAD history does not identify the individual purchase SKU that generated a row. Products can also be reassigned between game containers. Admissible evidence is therefore **current ITAD game-container history for Steam shop 61 in GB/GBP; historical Steam-app association and exact SKU/edition attribution are not independently verified**. Current app linkage is discovery evidence, not proof that every past row belongs to that Steam title.

Before requesting prices, the collector queries the official [Game Changes endpoint](https://docs.isthereanydeal.com/#tag/Unstable/operation/unstable-games-dots-v1), `/unstable/games/dots/v1`, with an explicit Unix `since` one second before the historical window. It preserves and hashes the raw response, validates change IDs, product/game UUIDs and source timestamps, and excludes any scoped game touched by a reassignment through the check's recorded retrieval time. Every shop's reassignment is considered because the change record does not identify a shop. Replay admission repeats the check and verifies its hash. A failed, malformed or capped response blocks the run before price requests.

The endpoint is unstable and returns at most 1,000 changes. A response reaching that cap is rejected: the documented `last` parameter retrieves newer IDs and does not establish a way to retrieve omitted older changes. An uncapped response with no scoped reassignment means **no scoped reassignment returned by this source for the requested interval**. It is not an independent guarantee of historical identity continuity, source-log retention or SKU attribution. These limitations remain in the output basis even after the check passes.

History requests explicitly set `country=GB`, `shops=61` and `since=2025-10-06T00:00:00+00:00`; the API's US and three-month defaults are not used. The analysis cutoff is the accepted Steam run's finish on 6 October 2026. Later source changes are retained in raw evidence and excluded from this frozen analysis. The documented route returns an array with no paging contract; wrapped/paged shapes are rejected pending adaptation.

Returned currency must be GBP and shop must be Steam/61. Decimal amounts and integer penny representations must agree; prices, regular prices and cuts must reconcile. Original offsets and timestamps remain alongside UTC-normalised event times. `deal=null` means removed/unavailable price state; it is never changed to full price or zero. Identical duplicate events are deduplicated for analysis; conflicting states at one UTC time fail validation.

A successful request proves a returned change log, not continuous monitoring or complete historical campaign coverage. The price before the first returned event is unknown. Empty history means no events returned for this request, not that the title was never discounted. Coverage remains explicit per title.

## Recorded discount sequences

An analytical sequence starts with an available price below the reported regular price. A deeper cut within a discounted state stays in the same sequence, with the price-state change counted. Identical repeated states do not add a change. An observed return to full price ends the sequence; a later discount starts another.

An unavailable state breaks the sequence and coverage. The next discount has an unknown left boundary. A first returned discount is also left-censored. A final discount without an observed end remains open at the cutoff. Duration is reported only for an observed start transition and full-price end; uncertain boundaries remain NULL. These are recorded discount-state sequences, not verified campaign durations or counts.

## Collection, admission and publication

Use a registered ITAD API key in the process environment or the ignored local `.env` as `ITAD_API_KEY`. Authentication is header-only. Neither keys nor request headers are written to run manifests. Non-success bodies and exception text are excluded from diagnostics. Requests have three attempts maximum, bounded backoff and pacing; authentication failures are not retried.

```bash
python src/price_history.py
```

The collector creates immutable run evidence: original assignment and per-title responses, normalised events, title-level coverage and a manifest with source/code hashes. Current-mapping and reassignment exclusions are declared separately; any eligible title's failed history request makes the run failed. Collection alone does not publish an analytical release.

After reviewing coverage, identity exclusions and source payloads, admit one run in `data/price-history/accepted-runs.json` with `run_id`, `status=accepted` and the exact manifest-file SHA-256. The registry is currently empty. Failed or unreviewed runs are rejected. Admission verifies raw and event hashes, scope, contract, code, timestamps and counts, then independently reprocesses raw responses to matching event bytes.

```bash
python src/price_history.py --analyse
```

The analytical builder publishes versioned coverage, recorded events and discount-sequence CSVs plus a manifest under `data/pricing-analysis/`. Publication and the current pointer are atomic; repeat builds compare immutable bytes. An empty response does not produce a zero-promotion count. Unresolved mapping and unavailable price measures remain NULL.

## Response evidence boundary

The builder inventories distinct admitted observation dates in the 14 days before a sequence, during it and the 14 days after an observed end. It uses each source's actual retrieval time; repeated same-day samples do not become independent days. An open sequence has no completed post window. Counts describe evidence availability, not a balanced event study.

The accepted model has one dated observation period. Player/review response change remains NULL, and no retrospective baseline is fabricated. A descriptive response estimator is not yet released. Additional comparable dated observations, product-scope checks, campaign/update context and a declared comparison design are required. Incremental uplift, elasticity, ROI and causal effects require further treatment/counterfactual evidence and internal commercial measures.

Steam player and review observations describe global activity, while these prices describe the UK storefront. They cannot establish a UK-specific response to a price change without geographic commercial evidence.
