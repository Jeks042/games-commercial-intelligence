# Data sources

## 1. Steam Store App Details API

Endpoint pattern:

`https://store.steampowered.com/api/appdetails?appids={APP_ID}&cc=gb&l=english`

Use:
- title
- developer / publisher
- release date
- genres / categories
- base and final price
- discount percentage
- Metacritic where present
- Steam recommendation count where present

Limitation: Steam storefront data only; price can vary by region and time.

## 2. Steam Reviews API

Endpoint pattern:

`https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/`

Parameters use `input_json`: numeric app ID, all languages, all purchase origins, all review types and Steam's off-topic filter enabled. The collector retains the lifetime query summary only. See [Valve's interface and migration contract](https://partner.steamgames.com/doc/webapi/IUserReviewsService). The earlier appreviews endpoint is deprecated; legacy observations remain explicitly versioned. Anonymous responses can be cached for up to ten minutes.

Use:
- positive / negative review counts
- total review count
- review score
- later: review timestamps, playtime-at-review and review text for player / brand analysis

Limitation: reviewers are self-selected. Review sentiment is not the same as customer satisfaction for the entire player base.

## 3. Steam current-player API

Endpoint pattern:

`https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={APP_ID}`

Use:
- point-in-time concurrent player count

The scheduled workflow retains run artifacts. The owner reviews and publishes accepted runs to extend the longitudinal series.

Limitation: current concurrent players are not DAU, MAU, active owners or retention.

## 4. SteamSpy market benchmark

Endpoint pattern:

`https://steamspy.com/api.php?request=appdetails&appid={APP_ID}`

Use:
- estimated owner range
- reported previous-day peak CCU; exact source observation day is not supplied
- average / median playtime only when available; zero values are treated as unavailable
- positive / negative review counts
- price and genre fields

This benchmark is collected separately from the live Steam snapshot so estimated owner/playtime data is never confused with first-party storefront metrics.

Limitation: SteamSpy extrapolates from sampled public profiles. Its own documentation warns that owner estimates can be unreliable for small or newly released games. “Owned” also does not mean the same thing as paid unit sales.

## 5. Hugging Face Steam games dataset — backup / research benchmark

Dataset:
https://huggingface.co/datasets/Z02Z/steam-games-dataset

Licence shown by the dataset: CC BY 4.0.

This source is useful as a broad market research dataset, but it is not used as the live weekly benchmark because the dataset server timed out during the first automated acquisition run.

## 6. 505 Games / Digital Bros public reporting

Use later for:
- company-level and franchise-level context
- premium-games revenue mix
- strategic priorities
- disclosed franchise performance

Do not infer title-level accounting revenue unless directly disclosed.

## 7. Historical price / promotion source — Milestone 4

Preferred source: IsThereAnyDeal API.

The source adapter is prepared; authenticated history acquisition is pending. See the [history contract](Price%20history%20contract.md) and [pricing delivery state](Stage%204%20pricing%20findings.md). Official app/shop lookup has been verified for the scope. History will be explicit GB/GBP Steam-shop context, with SKU and temporal coverage limits; it cannot establish publisher campaign timing by itself.

## 8. Optional external commercial estimates

Sources such as Gamalytic or Video Game Insights may be considered later.

Rule: any estimated units / revenue must be labelled clearly as third-party estimates and never presented as internal or audited revenue.

## SteamSpy field contract clarification

The [SteamSpy API contract](https://steamspy.com/api.php) defines ccu as the previous day's peak, prices in US cents, and daily data refresh. Reported peak CCU is kept as secondary observed context with an unresolved effective date, separate from estimated ownership/playtime and validated current Steam players. US prices are excluded from the GBP price comparison. Retrieval time does not establish the source's update/observation day.
