# Games commercial intelligence

## Commercial decision

Monitor and investigate the twelve selected portfolio titles before changing promotional spend or allocation. The evidence identifies product, expectation and offer questions, but cannot establish which investment would generate an incremental return. Each title has a distinct investigation path; a shared Monitor action does not imply equivalent economics.

The scope is twelve selected 505 Games titles on Steam, with twenty configured market references. This is independent public-data analysis of a defined set, not a representative market survey or publisher performance account. The [executive memo](Commercial%20decision%20memo.md) sets the allocation gates. The [Power BI Desktop report](../dashboard/README.md) presents the evidence across five pages, including title drill-through and explicit scenario assumptions.

## What changes the commercial conversation

| Finding | Evidence and interpretation | Decision implication |
|---|---|---|
| Product response warrants diagnosis | WUCHANG and Assetto Corsa EVO have lifetime positive recommendation shares of 57.33% and 58.95% in the accepted snapshot. Audited examples raise different encounter/readability and progression/performance questions. | Check current-build product and support evidence before treating reported experiences as verified defects, widespread concerns or reasons to change spend. |
| Eiyuden has the only qualifying direct-reference group | Its dated £13.49 final price sits below the £14.75 direct-reference median, while lifetime positive response is 13.24 percentage points below the 88.58% median. The three references are Chained Echoes, Sea of Stars and OCTOPATH TRAVELER II. Comparisons remain lifecycle-unadjusted. | Investigate expectation and usability questions. A lower observed price alongside weaker response does not demonstrate the effect of discounting. |
| Returned discount depth adds bounded context | Eiyuden's maximum provider-reported cut among returned records is 70%, versus a three-reference median of 60%. The window is 15 September–6 October 2026. | Reconcile historical SKU and campaign context before interpreting offers. No annual frequency, full-period extremum, promotion response or optimal discount is established. |
| Catalogue activity deserves follow-up | Assetto Corsa, Competizione and DEATH STRANDING show 13,017, 3,117 and 2,574 concurrent players at retrieval, with lifetime positive recommendation shares above 92%. | Obtain comparable repeated activity and actual sales/contribution evidence. These observations do not establish sustained demand, retention or an efficient promotional opportunity. |
| Price cuts impose a volume requirement | Under the declared scenario normalization, a hypothetical £10 to £9 cut needs 11.1% more paid units to preserve gross storefront transaction value, before costs. Actual title thresholds use prices rounded to pennies. | Use the scenario as a requirement to test against internal economics, not as expected sales, a forecast or cost break-even. Engagement assumptions remain separate from paid units. |

Numeric evidence is traceable to the [positioning release](../data/positioning/releases/13d024216f341692/), [bounded price-context release](../data/pricing-review/releases/d805e08327a98488/) and [conditional scenario release](../data/scenarios/releases/1a2624a982917ec1/). Review examples and their coded audit references are in the [twelve-title investigation brief](Player%20feedback%20investigation%20brief.md). Price, recommendation response, review scale and point concurrency remain separate signals; there is no composite performance ranking.

## Title-level decision trace

All twelve recommendations are **Monitor: investigation only, no spending approval**. Audit numbers below refer to the frozen [context-check notes](../data/review-refinement/audit/context-check-v1-20261008.json), not population counts. These were selected diagnostic examples; text, votes and hardware/roadmap assertions are retrieval-current reports. The [investigation brief](Player%20feedback%20investigation%20brief.md) gives the full qualification for each example.

| Title | Investigation evidence | Internal evidence that could change the decision |
|---|---|---|
| Assetto Corsa | Setup difficulty (1) alongside customization praise (7, 10); both review frames capped. | Device-specific support and setup completion, reproducible base-versus-mod tests; then paid-unit and contribution evidence to assess allocation. |
| Assetto Corsa Competizione | Controller settings reports (12, 17), with positive social/price impressions (18, 15). | Supported-controller onboarding tests and support outcomes; verify the cost and commercial materiality of any confirmed friction. |
| Ghostrunner | Challenge expectations (21, 25) and narrative/pacing qualifications (22, 26). | Structured research by experience/accessibility needs, traffic-to-purchase expectations and contribution before changing messaging investment. |
| Miasma Chronicles | Party/difficulty and narrative questions (32, 33, 34, 36); both cohorts below comparison threshold. | Targeted design research and usability evidence; sufficient denominators to distinguish isolated experiences from a material issue. |
| Eiyuden Chronicle: Hundred Heroes | Party/narrative and inventory reports (37, 40, 42), with character/music praise (38, 41); only qualified direct group. | Menu/recruitment usability checks, verified SKU, traffic, conversion, paid units, refunds and contribution; controlled response evidence before promotion. |
| DEATH STRANDING DIRECTOR'S CUT | Pacing contrasts (44, 49, 47, 51, 53) and crash report (50); recent frame capped. | Reproducible configuration-specific QA, build/platform support and expectation research; repeated catalogue activity plus sales/contribution. |
| Blades of Fire | Input, difficulty and collision reports (55, 56, 59), with qualified praise (57, 61); low-count cohorts. | Current-build input/collision QA and difficulty-setting research; verified sales and contribution rather than a reviewer's financial assertion. |
| Ghostrunner 2 | Performance/structure (63, 67), retry/motorcycle friction (69), learning appeal (65). | Controlled performance and usability tests, current hardware guidance and sequel-expectation research; materiality linked to actual purchase/support outcomes. |
| WUCHANG: Fallen Feathers | Encounter/combat reports (70, 71, 75, 77), alongside qualified praise (73, 74, 80). | Encounter/build QA, input/readability research and support/telemetry denominators; measure product and commercial effects before reallocating spend. |
| Crime Boss: Rockay City | Lobby/input reports (84, 87) and technical reports within positive recommendations (85, 89). | Reproducible lobby, input and stability checks with structured support evidence; verified purchase/refund and contribution measures. |
| Assetto Corsa EVO | Progression expectations (90–93), launch/performance reports (96–97), physics qualification and first impressions (98, 99). | Current feature specification and build QA, controlled hardware tests, progression research and paid-unit/refund economics; roadmap claims require verification. |
| Assetto Corsa Rally | Setup/handling (101, 102, 106), replay/settings/feature questions (100, 109, 105), reported advice/build praise (104, 107). | Supported-feature verification and current-build controller, settings and replay QA; test claimed fixes and their commercial materiality. |

These paths are neither severity rankings nor estimated return rankings. Invest requires verified incremental returns and capacity; Promote requires a reconciled contribution case and governed response test; Maintain requires the actual allocation and operating objectives; Deprioritise requires opportunity-cost and strategic evidence. The [decision policy](../data/commercial-decision-policy.json) preserves those gates. None is satisfied by the public evidence alone.

## Evidence dates and limits

The frozen Steam/SteamSpy baseline was retrieved on **6 October 2026**. GB/GBP storefront prices and point concurrency are retrieval-time observations; review totals are lifetime, all-language, all-purchase-origin recommendation context under the admitted query. SteamSpy owner bands are third-party estimates kept separate from observed Steam metrics.

The accepted pricing run was retrieved on **7 October**, with context restricted to **15 September–6 October 2026**. Twenty-seven contexts meet bounded suitability requirements. Three have empty returns; Ready or Not is excluded for mapping ambiguity; EA SPORTS WRC's zero/zero state is quarantined. Historical SKU continuity, annual history, complete promotion coverage, elasticity and ROI remain unavailable.

The fixed player-review source was retrieved on **7 October**, covering two adjacent 30-day creation cohorts for twelve titles, with **3,572 coded records**. Twenty-one cohorts are complete and three capped; seven title vote comparisons pass the descriptive coverage/count gates, while five remain unavailable. Steam's English label is unverified. Text and votes can change after creation. The fresh 110-record diagnostic audit supports qualified investigation examples, not validated themes, concern prevalence, aspect sentiment, population brand perception or historical change. Public code can rebuild the coded outputs; exact text-to-code replay needs the private immutable source archive.

The scenario layer has one accepted Steam observation per title and zero qualifying weekly history. Paid units and engagement indices are declared assumptions, not observed baselines. Forecasts, measured forecast error, prediction intervals, causal promotional response, retention, publisher net receipts and spending approval remain unavailable.

## Delivery and operating use

The release connects immutable source manifests and admission registers to a governed SQL model, reference-aware analysis, coded investigation evidence, declared scenarios and a portable Power BI Desktop project. NULL retains unavailability; genuine zero remains zero. Contract fingerprints and validation stop incompatible inputs reaching the report.

The [reproduction guide](Reproduction%20guide.md) distinguishes the frozen public rebuild from fresh acquisition and private source replay. The [release findings](Stage%208%20release%20findings.md) record clean-environment verification, independent review and publication status. The Desktop report was refreshed and interacted with natively on 13 October; Power BI Service publication has not been performed. A refresh of its embedded tables loads frozen evidence, not live prices or reviews.

For an operational extension, reconcile dated SKU/platform/country paid-unit sales, publisher receipts, tax/fees/refunds and contribution costs; add campaign exposure/spend and comparable product/support evidence. Only then evaluate governed promotional experiments and a suitable time-series forecasting target. Further automated review semantics require a new method and untouched holdout excluding the 203 already inspected development/audit records. Those are next evidence requirements, not work represented as completed by this release.
