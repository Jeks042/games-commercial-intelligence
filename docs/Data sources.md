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

`https://store.steampowered.com/appreviews/{APP_ID}?json=1`

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

The scheduled workflow stores repeated snapshots so we can build our own longitudinal series.

Limitation: current concurrent players are not DAU, MAU, active owners or retention.

## 4. SteamSpy market benchmark

Endpoint pattern:

`https://steamspy.com/api.php?request=appdetails&appid={APP_ID}`

Use:
- estimated owner range
- public CCU estimate
- average / median playtime
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

This is intentionally not required for Stage 1 because it needs a separate API credential / setup. Once connected, it will be used for promotion timing and historical price depth.

## 8. Optional external commercial estimates

Sources such as Gamalytic or Video Game Insights may be considered later.

Rule: any estimated units / revenue must be labelled clearly as third-party estimates and never presented as internal or audited revenue.
