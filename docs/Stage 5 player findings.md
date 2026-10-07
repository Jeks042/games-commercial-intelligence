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

The [review contract](Review%20analysis%20contract.md) defines source filters, boundaries, sampling, interpretation and privacy. The [private replay receipt](../data/player-reviews/verification/private-replay-20261007.json) records the source hashes. Exact source-to-feature reproduction requires the privately retained immutable archive. Public analytical rebuilds use coded features and do not require review text; fresh acquisition cannot recreate mutable historical text.

The implementation passes **159 tests locally and on GitHub**, including date/filter/pagination checks, privacy projection, exact raw replay, missingness, capped/low-count comparison gates and immutable publication. [Hosted validation](https://github.com/Jeks042/games-commercial-intelligence/actions/runs/37643119050) also rebuilt the previously accepted model, positioning and pricing outputs. The new production review build was deliberately skipped because no review run has been admitted yet.

**Issue 5 remains in progress.** Independent source/control acceptance, governed language/theme refinement, admitted analytical outputs and final commercial review are still required. Issue 6 has not started.
