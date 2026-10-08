# Player-feedback context diagnostics

This layer reduces specific lexical distractions when selecting reviews for investigation. It does not estimate how many customers have a concern, certify English text or label sentiment. The admitted source, original keyword features, recommendation counts and earlier analytical releases remain intact.

## Frozen method

[Method v1](../data/review-refinement/method-v1.json) declares six narrow occurrence-level exclusions: FPS genre phrases, the wheel idiom, review edits, content creators and a story idiom. Each occurrence is evaluated independently. A term remains a candidate mention when another occurrence survives. All fired rule IDs are retained, including when the same term also survives. Other ambiguous uses, praise and negation remain unvalidated mentions. There is no new topic dictionary or title-specific exception.

The accepted collector's hash-bound normalisation is reused. The separate producer binds the source manifest, original features, rule file, development selection, its own code and Unicode database version. Private derivation first replays the original raw archive exactly. Every derived row retains the original project key and text fingerprint; original matches remain available by joining that key to the admitted source features. No original text, author profile or source review ID is published.

Language flags inspect Unicode letter scripts only. Latin letters do not establish English: French, German and Portuguese can pass that diagnostic. A non-Latin letter flags uncertainty, including foreign names in English or mixed-language text. Short texts are unassessed. These flags never remove a review or change recommendation denominators. No English-only denominator is created.

## Fresh context check

Rules are committed before the full private derivation and selection. The previous 93 diagnostic review keys are mechanically excluded from the fresh check; they are development examples rather than validation evidence. Selection uses the lowest salted project-key hash in each nonempty title × creation cohort × recommendation × original match × retained match × any context exclusion × language-risk stratum. The additional exclusion stratum also captures records that lose one mention while retaining another.

The selected private full texts must be checked for remaining ambiguity, missed concepts and language suitability. Selection alone is not a completed audit. This targeted stratified check cannot estimate general classifier accuracy or population prevalence. Any rule change after inspecting those texts requires v2 and a new untouched selection excluding both development and v1 audit keys.

## Reproduction and release boundary

`python src/review_refinement.py --derive-private` requires the immutable private archive and creates a candidate package plus a private audit-text file outside the source-run directory. `python src/review_refinement.py --candidate <candidate-id>` rebuilds its public cohort diagnostics and fresh selection without private text. Both paths reject conflicting immutable bytes. No accepted/current pointer is created: the package remains a candidate until the fresh audit and independent review are complete.

The public rebuild verifies hash bindings and structural controls; it cannot independently reclassify text that is deliberately private. Hosted validation retains the public coded package and diagnostic evidence only. Concern prevalence, aspect sentiment, theme change, historical sentiment, lifetime theme comparison and commercial effects remain unavailable. Final Stage 5 commercial acceptance is a separate gate.
