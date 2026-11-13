# Tableau reporting guide

Connect to [campaign_performance.csv](../demo/campaign_performance.csv) and [segments.csv](../demo/segments.csv) as two independent Text File data sources. These exports contain the tested offline results. Use the equivalent warehouse exports after a cloud run. [Tableau text file connection](https://help.tableau.com/current/pro/desktop/en-us/examples_text.htm)

| View | Tableau setup |
|---|---|
| Attribution comparison | Columns = Model, then SUM(credited_revenue). Rows = Channel. Color = Model. Keep all four models visible. |
| Campaign scorecard | Rows = Channel, Campaign. Text = Measure Values for credited_revenue, spend, ROI and CPA. Show Model as a single-select filter. Format ROI as percent and amounts as USD. |
| Customer segments | Rows = Segment. Columns = SUM(customers). Label = SUM(customers). Tooltip = AVG(avg_annualized_ltv). |

For grouped views, derive ROI and CPA from their underlying amounts. Use a single model and limit the ratio to campaigns with recorded positive spend. Add a model filter to the scorecard only so the first view can display model sensitivity.

```text
Campaign ROI
IF SUM([spend]) > 0 THEN
    (0.55 * SUM([credited_revenue]) - SUM([spend])) / SUM([spend])
END

Campaign CPA
IF SUM([credited_new_customers]) > 0 THEN
    SUM([spend]) / SUM([credited_new_customers])
END
```

Build a 1200 × 800 dashboard with the comparison and scorecard across the top, then segments and a text box for the budget experiment. Use the recommendations in [findings](findings.md). Save as a packaged workbook if you need to share the report and its CSVs together. [Tableau packaged workbooks](https://help.tableau.com/current/pro/desktop/en-us/save_savework_packagedworkbooks.htm)
