# Player-feedback context

## Commercial position

The next decision is where player feedback warrants investigation before changing product messaging or acquisition priorities. The collected reviews contain useful diagnostic examples, but the initial automated screening is not reliable enough to estimate the prevalence of specific concerns. No spend allocation or product-performance conclusion is approved from these tags.

The context check points to questions worth validating: input setup and controller usability for the racing titles; stability reports for Assetto Corsa EVO; expectations, menus and writing for Eiyuden; and combat feel for WUCHANG. Positive recommendations can also contain technical complaints. These are individual reported experiences, not verified defects or representative customer findings. Product/support evidence, hardware, build version and a governed language/theme assessment are needed before deciding priority.

## Collected evidence

The successful source run contains **3,572 coded review records** from the twelve portfolio titles, with **81 private raw responses** retained and replayed byte for byte to the public features. Two adjacent 30-day creation cohorts end on 7 October 2026 at 15:00 UTC. The current text and recommendation state were observed at retrieval; neither is a historical snapshot at the review's creation date.

All queries use Steam's English label, all purchase origins, both recommendation states and the off-topic filter enabled. **Steam-labelled English is not verified English text.** The lifetime summary is retrieval-current, uses the same language/purchase filters and remains separate from the accepted all-language baseline.

| Portfolio title | Recent returned reviews | Prior returned reviews | Returned coverage |
|---|---:|---:|---|
| Assetto Corsa | 500 | 490 | Both capped; prior count equals the initial total but terminal exhaustion was not verified |
| Assetto Corsa Competizione | 217 | 149 | Both complete |
| Ghostrunner | 73 | 71 | Both complete |
| Miasma Chronicles | 23 | 11 | Both complete; below comparison threshold |
| Eiyuden Chronicle: Hundred Heroes | 21 | 11 | Both complete; below comparison threshold |
| DEATH STRANDING DIRECTOR'S CUT | 499 | 255 | Recent capped; prior complete |
| Blades of Fire | 22 | 12 | Both complete; below comparison threshold |
| Ghostrunner 2 | 41 | 39 | Both complete |
| WUCHANG: Fallen Feathers | 134 | 157 | Both complete |
| Crime Boss: Rockay City | 117 | 91 | Both complete |
| Assetto Corsa EVO | 165 | 181 | Both complete |
| Assetto Corsa Rally | 207 | 86 | Both complete |

There are **21 complete returned cohorts and three capped cohorts**. Completeness means the source frame was exhausted, unique counts reconciled and matching counts stayed stable. It does not include deleted, private or filtered reviews. Capped frames are the latest returned creation records, not representative samples. Descriptive recommendation contrasts require both complete cohorts and at least 30 reviews each; five title contrasts remain unavailable. Even a qualifying contrast is an unadjusted difference between creation cohorts, not evidence of improvement, decline or a campaign effect.

## Screening and context check

The versioned dictionary screens performance, value, content, controls, difficulty and updates. Texts shorter than five words remain in recommendation counts but are outside theme screening. The audit design was fixed before interpreting results: one review from each nonempty title/cohort/recommendation/matched-or-unmatched stratum, selected by the lowest project review key. It selected **93 reviews**.

The AI-assisted text and keyword-context check found five clearly non-English texts despite the source label, contextual false positives and missed concepts. Examples include FPS as a genre rather than frame rate, wheel as an idiom rather than an input device, and update as editing a review rather than a game patch. The check is not independent human ground truth or an estimate of classifier accuracy. [Selection and provenance](../data/player-reviews/audit/selection-20261007.json) and [context-check notes](../data/player-reviews/audit/context-check-20261007.json) retain the evidence without publishing original text or author identities.

Keyword counts therefore remain **provisional screening context**. Confirmed concern prevalence, aspect sentiment, theme changes and lifetime theme trends remain unavailable. A Steam recommendation is kept separate from sentiment about any particular aspect. Refinements must be versioned, applied to all titles and audited again; they must not be tuned to produce a preferred title comparison.

## Reproduction and acceptance

### Fresh context check — 8 October

The separate [refinement method](Review%20refinement%20method.md) was frozen before private derivation. It replays the same admitted source without changing the collector, source contract or original features. Six narrow context rules flag misleading lexical uses; Unicode letter-script checks flag language uncertainty. Latin-script text is still not certified English, and these flags do not remove reviews or change recommendation denominators.

The [candidate diagnostics](../data/review-refinement/diagnostics/94c88909fe4c88a1/cohort_diagnostics.csv) retain all 3,572 records across 24 cohorts. Ten records have a context-exclusion flag; this is a screening count, not a complaint count. A [fresh deterministic selection](../data/review-refinement/diagnostics/94c88909fe4c88a1/fresh-audit-selection.json) contains 110 reviews and excludes all 93 development examples. It includes retained matches, unmatched texts, context exclusions and language-risk flags across the available title/cohort/recommendation strata.

All 110 private full texts received an AI-assisted context check. The [coded notes](../data/review-refinement/audit/context-check-v1-20261008.json) record ten clearly non-English examples, three mixed-language examples and one symbol-art example within that targeted selection. Those counts describe the check set, not the corpus or customer population. The five selected context-exclusion records have plausible exclusion contexts, but they do not cover every declared rule or establish general accuracy.

Material ambiguity remains: a utility name can look like a content mention; a confectionery reference can look like a game patch; narrative predictability and conversational idioms can look like difficulty or story feedback. Unmatched texts also contain usability, stability and feature-expectation questions. Positive recommendations can contain detailed criticism, and negative recommendations can praise particular aspects. Publisher-roadmap, hardware and defect assertions remain unverified.

The commercial implication is to investigate the reported experience with product/support evidence rather than rank acquisition priorities from tag counts. The frozen v1 package remains a diagnostic candidate. Further automated refinement requires v2 and a fresh untouched check set excluding both the development examples and this 110-review selection. Concern prevalence, aspect sentiment and theme-change measures remain unavailable. Final Stage 5 sign-off has not been obtained.

[Hosted validation](https://github.com/Jeks042/games-commercial-intelligence/actions/runs/37842049911) passed **181 tests** and an identical diagnostic rebuild. The downloaded artifact's eight refinement files and eight admitted source files match committed local bytes. All 24 prior model/positioning/pricing CSVs and the four accepted review-intermediate outputs remain identical. The [verification receipt](verification/review-refinement-37842049911.json) records the artifact digest, output hashes and pending independent refinement review. The artifact contains public coded evidence only; 81 raw source responses and the new full-text check are retained in a byte-verified private backup.

Independent review accepted the bounded source/control layer, and the source is explicitly admitted with its [private replay proof](../data/player-reviews/verification/private-replay-20261007.json). Exact source-to-feature replay requires the privately retained immutable archive. Public analytical rebuilds use admitted coded features; fresh acquisition cannot recreate mutable historical text. The [review contract](Review%20analysis%20contract.md) defines filters, boundaries, sampling, interpretation and pseudonymous fingerprints.

The [current analytical release](../data/review-analysis/current.json) contains 24 cohort summaries, 144 provisional screening rows, 12 title contexts and the 93-review audit selection. Seven recommendation contrasts meet the complete-frame and minimum-count rules; five remain unavailable. Every output and the build manifest explicitly flag Steam-labelled English as unverified text language. Concern prevalence and theme changes remain NULL.

The corrected [GitHub validation](https://github.com/Jeks042/games-commercial-intelligence/actions/runs/37645508179) passed **160 tests**, rebuilt the admitted analytical release and passed an identical rerun. All three review CSVs and the audit-selection JSON match local bytes. The previously accepted model, positioning and pricing consumer CSVs also remain unchanged. Runtime fingerprints differ across environments; the output bytes are identical. The [verification receipt](verification/review-analysis-37645508179.json) records source/output hashes and the downloaded artifact digest. A durable private copy retains that hosted evidence.

Independent final review of this gate accepted the corrected bounded analytical intermediate with no remaining blocker. This accepts descriptive recommendation context and diagnostic screening; it does not validate the theme classifier, English-language purity or concern prevalence.

**Issue 5 remains in progress.** The source/control foundation and bounded analytical intermediate are accepted. The separate v1 diagnostic refinement and fresh context check are published for review; residual ambiguity prevents a theme-validity upgrade. Independent refinement review, title-level commercial summaries and final Stage 5 acceptance remain required. Issue 6 has not started.
