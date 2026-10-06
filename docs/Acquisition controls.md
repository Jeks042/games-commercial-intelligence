# Acquisition controls

## Acceptance contract

A Steam run passes only when every scoped app returns valid Store metadata, a reconciled review summary and a successful current-player response. A SteamSpy run passes only when every scoped app returns a matching identity, a parseable owner band and required supporting fields. Benchmark response coverage does not establish estimate accuracy.

The title universe requires unique numeric app IDs, title names and peer groups. Source requests use bounded timeouts, at most three attempts for connection failures, HTTP 429 and server errors, and 1.1-second spacing per host. Permanent HTTP errors are not retried.

Declared schemas are independent of success or failure. Source statuses are `ok`, `invalid_payload`, `http_error` or `source_failed`; failed numeric observations remain blank. A validated zero is retained. Paid titles without prices have `price_status=unavailable`, while free titles are identified separately. SteamSpy zero playtime is conservatively stored as unavailable, not player behaviour. Owner estimates remain `requires_review` until suitability is established.

## Publication and history

Each run has a unique ID, one row per app, an immutable CSV and a JSON manifest. The manifest records expected scope, source coverage, failures, start/end UTC times, endpoints and query contracts, dependency versions, collector revision, source-file hashes, title-universe hash and observation-file hash. Hashes identify the acquisition inputs/code and stored observations; the mutable upstream APIs cannot recreate an earlier market state.

Steam history is replaced atomically only after its complete header and rows validate. Duplicate `run_id + app_id`, malformed row widths or unknown history columns stop publication. The benchmark is archived per run before the latest file is replaced. Incomplete runs exit unsuccessfully and do not update either published dataset.

The original 64 Steam observations are retained as `schema_version=legacy-1`. Their original bytes and the original 32-row benchmark are preserved under `data/runs/legacy-baseline/`. Legacy retrieval times and payload validation were not recorded per source; neither is invented retrospectively. The analytical model must exclude legacy rows by default or admit them through an explicit separate validation process. No legacy row is promoted silently to version 2.

## Time and query policy

Prices: UK Steam storefront, GBP minor units, tax treatment as returned by the Store. Reviews: all languages, all purchase origins, both positive and negative, lifetime summary, Steam's off-topic filter enabled. Only summary fields are stored; review text and user identifiers are not collected into these outputs.

Version 2 uses Valve's current IUserReviewsService endpoint. The old endpoint is deprecated. Version 1 and version 2 records are explicitly distinguished, and cross-version review deltas require reconciliation.

Source retrieval timestamps mark successful receipt/validation, or the time a failure was recorded. They are not SteamSpy update times or player event times. Anonymous review responses may be cached by Steam for up to ten minutes.

The scheduled slot is Monday 06:15 UTC. GitHub can delay scheduled jobs; use actual retrieval times in comparisons. Weekly concurrency is a pulse, not average weekly players, DAU, MAU or retention. Multiple same-day baseline runs do not establish momentum. Issue 2 must gate trends on distinct comparable weekly periods; promotion response needs finer history in Issue 4.

## Automation and ownership

The collection workflow has read-only repository access and uploads data plus manifests as artifacts, including diagnostic outputs when collection fails. It cannot commit or push. Both collectors must pass for the job to succeed.

The repository owner reviews coverage, hashes, estimate suitability and legacy separation before publishing new observations. Download accepted artifacts before the 90-day retention expires; the Git history remains the durable publication record. Never replace a newer history file with an older artifact: merge only unseen validated run IDs through the declared schema and rerun integrity checks.

The validation workflow runs the regression suite on changes to acquisition code, dependencies, tests or workflow files.
