# Commercial release verification

The release brings together a frozen analytical package, five-page Power BI Desktop report, [commercial decision memo](Commercial%20decision%20memo.md) and [case study](Commercial%20case%20study.md). The supported action remains title-specific investigation before spend or allocation changes. All earlier source and suitability boundaries remain in force.

## Reproduction and acquisition

On 14 October 2026, a fresh public clone at accepted commit `ec421f5c7f547c3667b151fc061d1571cd5dad82` and a new Python 3.13.7 virtual environment installed the pinned requirements, passed dependency checks and passed all 210 existing tests. The new public verifier rebuilt eight layers twice, matched 104 rebuilt files to accepted evidence and verified 119 accepted files unchanged. That initial check ran the new verifier before its publication. A further fresh public clone at release commit `b59bd370d06a7f0a991799996a256348dc7f052c`, with a new pinned-dependency environment, passed all **212 tests**, repeated the complete public verification and left its working tree clean.

Two further independent clean public clones executed the existing live collectors. Steam storefront, review-summary and concurrent-player coverage passed for all 32 scoped titles; SteamSpy also returned all 32. Their manifests report a clean source tree and the accepted collector revision. The [fresh-acquisition receipt](verification/release-acquisition-20261014.json) records run identifiers, dates, coverage and source fingerprints. New observations are not admitted, and the accepted baseline is unchanged.

Frozen price analysis and public coded review outputs rebuild without secrets. Historical ITAD retrieval was not rerun, and exact text-to-code replay still requires the private archive. Fresh retrieval cannot reconstruct historical quotes, votes or mutable text. Public reproduction verifies the admitted coded evidence rather than certifying inaccessible private content.

## Hosted release verification

[Run 38587519964](https://github.com/Jeks042/games-commercial-intelligence/actions/runs/38587519964) passed all 212 tests at release commit `b59bd370d06a7f0a991799996a256348dc7f052c`. The downloaded 265-entry artifact matches GitHub's SHA-256 digest. Its complete reproduction results match the clean Windows run across Python 3.13.7 and 3.13.16. All 67 dashboard files, 28 prior consumer outputs, 16 source/refinement files and eight scenario files match the accepted evidence. Private raw text, secrets and native caches are absent; the two rebuilt public SQLite databases are legitimate analytical outputs. The [verification receipt](verification/release-38587519964.json) records these checks.

## Release controls and review

The new `src/verify_release.py` isolates builds in temporary public-input copies and preserves accepted sources and pointers. It verifies the SQL model, positioning, pricing analysis/context, coded reviews, v1 refinement diagnostics, conditional scenarios and 67 generated dashboard files. Runtime-dependent release IDs and database/build metadata can differ; accepted consumer bytes must match. Every repeated build in the same runtime must remain identical.

Two added regression checks exercise complete public reproduction with pointer preservation and rejection of tampered frozen evidence. The validation workflow now runs the complete verifier and retains its receipt alongside the public analytical artifacts. Workflow success and artifact-byte verification are required; an uploaded artifact alone is insufficient evidence of a passing run.

The case study traces every title's investigation to coded audit examples and identifies the internal evidence that could change the decision. It separates descriptive findings from assumed scenarios, preserves unavailable forecasts and makes no sales, realised return, population sentiment or causal-effect claim. Existing native Desktop evidence applies to unchanged generated report definitions; no new Service publication is claimed.

**Final independent acceptance and issue closure are pending.** The clean-environment/hosted receipt is published. Completion requires the final read-only review in the existing project-planning conversation. The issue will remain open until those checks resolve.
