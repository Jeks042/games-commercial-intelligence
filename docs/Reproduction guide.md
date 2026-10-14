# Reproduce the commercial release

## Frozen public package

Use a fresh clone and Python 3.13. Dependencies are pinned; no API key or private review archive is needed for public analytical reproduction.

```text
git clone https://github.com/Jeks042/games-commercial-intelligence.git
cd games-commercial-intelligence
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` in Windows PowerShell or `source .venv/bin/activate` on macOS/Linux, then:

```text
python -m pip install -r requirements.txt
python -m pip check
python -m unittest discover -s tests -v
python src/verify_release.py --receipt public-rebuild-receipt.json
```

The verification command checks 119 frozen accepted source, refinement, consumer and dashboard files against published receipts. It copies public inputs into a temporary directory, rebuilds all eight layers twice, compares consumer bytes with accepted evidence, and checks that the accepted files remain unchanged. It does not alter accepted source files or release pointers. The optional receipt is created only if that filename does not already exist; keep this local verification output out of commits.

Rebuilt layers are the SQL model, portfolio positioning, bounded price analysis, curated pricing context, coded player-review analysis, v1 diagnostic refinement, conditional scenarios and all 67 generated Power BI files. Runtime-dependent release IDs, SQLite/build manifests and build-time status values can differ from creation-time records. Accepted consumer bytes must match. Repeated builds in the same environment must be identical. Subsequent acceptance receipts govern the creation-time pending values.

The clean Windows run and hosted Linux validation are recorded in the [final release findings](Stage%208%20release%20findings.md). Existing model/scenario/report builders can also be run separately as documented in their contracts. They protect conflicting existing generated output; editing an accepted source requires a separately reviewed new release rather than rewriting its fingerprint.

## Power BI Desktop

Open `dashboard/Games.pbip` in Power BI Desktop and click **Refresh** to load the embedded frozen tables. Follow the [report guide](../dashboard/README.md) for title drill-through and title-plus-case scenario selection. Ambiguous scenario selections should leave cards blank. API keys and machine-specific paths are not embedded.

Native Desktop 2.158.1304 execution was separately checked on 13 October 2026. The unchanged report definitions preserve that evidence; Python/hosted validation does not substitute for native execution. Power BI Service publication has not been performed and is outside the accepted Desktop release scope.

## Fresh acquisition is a different operation

Run fresh acquisition in a separate disposable clone so it cannot change the frozen release's source history:

```text
python src/collect_snapshot.py
python src/collect_market_benchmark.py
```

These commands call live Steam and SteamSpy endpoints for the configured 32-title scope. They save dated observations/manifests under `data/runs/`; complete source coverage updates that clone's snapshot history or benchmark. Failed coverage retains diagnostics and leaves the preceding source output unchanged. New records are **not admitted to the analytical model** until their source contracts, suitability and manifests are reviewed and explicitly registered. Successful collection is not fitness approval.

Live retrieval does not reproduce a historical quote, vote state or player count. The Stage 8 fresh-acquisition check proves collector execution and coverage on its recorded date; it does not replace the 6 October accepted baseline, reconcile historical SKU identity or establish another accepted weekly point.

ITAD historical acquisition requires a private API key and a newly governed scope; `python src/price_history.py --analyse` rebuilds the accepted public price records without one. The Stage 8 run does not reretrieve the accepted historical ITAD payloads or claim an annual history. Live `review_collection.py` similarly cannot reconstruct old mutable text/votes. The [source contracts](Data%20sources.md), [pricing contract](Price%20history%20contract.md) and [review refinement method](Review%20refinement%20method.md) define these separate boundaries.

## Privacy and validation evidence

Public outputs include coded review features, selection/audit provenance, source hashes and qualified analytical context. Original text, author identifiers, API keys, local `.pbi` state, `.pbix` caches and private career material stay outside Git. Exact private text-to-code replay was verified in earlier stages; it is unavailable to a public clone and is not claimed by the public verification command.

GitHub Actions validates contracts and rebuilds public artifacts; it never commits observations as a bot. Downloadable artifacts expire after 90 days, so committed evidence, receipts and the report remain the durable public release. Success is established by the workflow job conclusion and verified artifact, not by artifact upload alone.
