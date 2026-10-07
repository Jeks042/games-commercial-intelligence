# Player-feedback evidence contract

The commercial question is which player concerns warrant investigation before further acquisition spend or changes to product messaging. Reviewers are self-selected; this analysis does not measure brand perception across all customers, conversion, refund rates or marketing return.

## Source and creation cohorts

The [official Valve review interface](https://partner.steamgames.com/doc/webapi/IUserReviewsService) supplies dated creation filters, chronological pagination, recommendation state and review text. This extension covers the **12 portfolio titles in the accepted model**. Market-reference text is outside this delivery; existing governed reference groups remain unchanged.

The fixed cutoff is **7 October 2026 at 15:00 UTC**. Two adjacent, non-overlapping 30-day creation cohorts use the same English-language, all-purchase-origin, all-recommendation and off-topic-filtered query. The recent cohort is 7 September–7 October; the preceding cohort is 8 August–7 September, with exact inclusive timestamp boundaries retained in the manifest. There are at most five pages of 100 records per title/cohort. The cursor is followed until an empty page or that budget is reached. A full budget with no empty terminal page is explicitly capped, even if the last count happens to equal a reported total.

An exhausted returned cohort qualifies as complete only when matching counts remain stable and its unique record count equals the initial matching count. This is completeness of the retrieved source frame, not a claim that deleted, private or filtered reviews are represented. Duplicate records, changed creation order, cursor loops, out-of-window timestamps, malformed values and source failures stop admission. Source counts that change during retrieval remain unavailable for period-change measures.

Current review text and recommendation state are retrieved after the creation window; reviews can be edited. The dates describe when reviews were created, not historical versions of text or recommendations at that date. Same-query English lifetime totals are a separate contextual summary. They must not be confused with the accepted all-language snapshot or a lifetime text corpus.

## Text and interpretation

Unicode, formatting and whitespace are normalised for deterministic keyword screening. Six declared dictionaries identify provisional mentions of performance, value, content, controls, difficulty and updates. A keyword is not an aspect-sentiment label, verified issue or causal explanation. A negative Steam recommendation with a content keyword does not establish negative sentiment about that aspect. Short texts remain in recommendation denominators but are separately marked unsuitable for thematic screening.

Theme rates and changes are provisional keyword-screening measures until a context audit establishes a suitable interpretation. Review text must be inspected for negation, praise, sarcasm, irrelevant uses and multiple aspects before making title-level commercial claims. Recommendation-rate contrasts require both creation cohorts to have complete returned coverage and at least 30 reviews each; otherwise the change remains NULL. No lifetime theme-change statistic is supplied without a lifetime corpus.

## Privacy and reproduction

Original response bytes, text and author identifiers are stored only under the ignored `data/raw/player-reviews/` archive. The public run retains request parameters, retrieval times, raw hashes and coded review features with hashed review keys. No author profiles, full texts or long quotations are published. Public coded features contain timestamps, recommendation flags, word counts and declared keyword matches. Source-to-feature replay requires the private immutable archive; it is not a clean-clone capability. The analytical stage can be rebuilt from explicitly admitted public coded features, while a fresh acquisition is a new dated run and cannot recreate mutable historical text.

The screening rules are version 1 and frozen in the collector's code hash before successful collection. The context-audit design is also fixed before interpreting results: among texts with at least five words, select the lowest hashed review key in each nonempty title × creation cohort × recommendation × any-keyword-match stratum. This includes matched and unmatched texts, with one review per nonempty stratum. It checks interpretation and obvious missed mentions; it does not establish classifier accuracy or aspect-sentiment validity. Public features use creation/update dates, while exact timestamps remain private for boundary and ordering validation. Edits after the creation-window end remain explicitly flagged. The no-date-filter English lifetime summary is retrieval-current context, not a frozen-as-of lifetime value.

Explicit independent source/method review and raw-byte replay precede source admission. Versioned analytical output, repeat-build checks and hosted CSV verification precede final acceptance. Historical SKU, price response, sales, elasticity and ROI claims remain unavailable.
