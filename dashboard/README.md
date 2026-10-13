# Games Commercial Intelligence report

Open [Games.pbip](Games.pbip) in Power BI Desktop. The project uses the documented PBIR report format and an import semantic model with embedded, publicly shareable coded tables. Refresh loads that frozen evidence without API keys or machine-specific paths. It does not fetch live observations.

After opening, click **Refresh** to load the embedded evidence. The five pages cover portfolio decisions, title investigation/drill-through, pricing context, player-feedback investigation and conditional scenarios. Select a title on the detail pages; select one planning case on the scenario page. Measures with an ambiguous grain remain blank. Right-click a portfolio title and choose **Drill through → Title investigation**. Native Desktop refresh, page rendering, title filtering and scenario-grain behaviour have been checked; the [native receipt](../docs/verification/executive-native-20261013.json) records the tested paths.

[Input contract](../data/executive-input-contract.json) pins every source and accepted review/scenario receipt. [Build manifest](build-manifest.json) records every generated file hash and table count. Rebuild with `python src/build_executive_report.py`; edited files are preserved and a conflicting rebuild fails. Native cache and user settings stay outside Git.

Prices and point concurrency are dated 6 October 2026, provider-container pricing is bounded to 15 September–6 October, and retrieved reviews do not establish historical sentiment or population concern prevalence. Scenario paid units are assumptions; forecasts, predictive validation, elasticity and ROI are unavailable. Monitor is a title-specific investigation action, not spending approval.

Native execution and hosted 210-test source/artifact verification are complete. Final independent acceptance of the repaired package remains pending. Power BI Service publication has not been performed.

Format reference: [Microsoft Power BI project report documentation](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report).
