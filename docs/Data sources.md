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

## 4. Hugging Face Steam games benchmark

Dataset:
https://huggingface.co/datasets/Z02Z/steam-games-dataset

Licence shown by the dataset: CC BY 4.0.

The repository uses the Hugging Face Dataset Server to retrieve only the selected app IDs rather than downloading the full dataset.

Useful fields:
- estimated owners
- peak CCU
- positive / negative counts
- recommendations
- average playtime
- median playtime
- price
- genres / tags

Limitation: these are external public estimates / snapshots and may not match publisher systems.

## 5. 505 Games / Digital Bros public reporting

Use later for:
- company-level and franchise-level context
- premium-games revenue mix
- strategic priorities
- disclosed franchise performance

Do not infer title-level accounting revenue unless directly disclosed.

## 6. Historical price / promotion source — Milestone 4

Preferred source: IsThereAnyDeal API.

This is intentionally not required for Stage 1 because it needs a separate API credential / setup. Once connected, it will be used for promotion timing and historical price depth.

## 7. Optional external commercial estimates

Sources such as Gamalytic or Video Game Insights may be considered later.

Rule: any estimated units / revenue must be labelled clearly as third-party estimates and never presented as internal or audited revenue.
