# Metric dictionary

| Metric | Definition | Decision use | Caveat |
|---|---|---|---|
| Lifetime review positivity | Positive reviews / total reviews | Long-run player perception | Self-selected reviewers |
| Review score | Steam review score field | Comparable Steam quality signal | Platform-specific |
| Review velocity | Change in valid cumulative review counts per elapsed period | Attention proxy; planned in Issue 2 | Requires comparable query versions and adequate time separation; not sales |
| Current players | Concurrent players at snapshot time | Current engagement pulse | Strong time-of-day effects |
| Estimated owners | Public external owner range | Scale benchmark | Estimate, not actual units |
| Peak CCU | Not acquired in Stage 1 | Pending a documented historical source | Do not substitute current concurrency or SteamSpy CCU |
| Average playtime | Third-party benchmark mean minutes, when available | Context only | Stage 1 zero fields are unavailable, not measured behaviour |
| Median playtime | Third-party benchmark median minutes, when available | Context only | Unavailable in the initial benchmark |
| List price | Current non-discounted storefront price | Price positioning | Region-specific |
| Discount depth | 1 - final price / list price | Promotion intensity | Current snapshot until history is added |
| Price index | Title price / peer median price | Relative positioning | Peer selection matters |
| Lifecycle role | New / growth / mature / back catalogue | Commercial interpretation | Analytical classification |
| Review momentum | Recent positivity - lifetime positivity | Direction of perception | Needs consistent review windows |

## Availability

Stage 1 supports observed price, lifetime review counts, derived positivity and point-in-time concurrency. Owner bands are external estimates requiring suitability review. Review momentum, peak concurrency, promotional response and trend claims are not available from the baseline. Lifecycle labels are curated business labels; calculated title age and analytical lifecycle rules belong in Issue 2.
