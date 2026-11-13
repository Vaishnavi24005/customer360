# Findings and test evidence

## Synthetic demo results

The run produced 3,186 events, 2,596 sessions, 576 deduplicated orders, 481 customer profiles and $58,821 of purchase revenue. Each attribution model reconciled to the same revenue. The 481 keys include anonymous profiles and CRM profiles.

| Campaign | First-touch revenue | Last-touch revenue | Linear revenue | Time-decay revenue | Time-decay ROI | Time-decay CPA |
|---|---:|---:|---:|---:|---:|---:|
| Paid Social / prospecting | $22,492 | $1,970 | $10,219 | $7,202 | −46% | $143 |
| Paid Search / brand | $14,011 | $10,040 | $11,879 | $11,512 | −30% | $131 |
| Email / lifecycle | $5,964 | $29,719 | $17,478 | $21,109 | 428% | $20 |
| Paid Social / unconverted | $0 | $0 | $0 | $0 | −100% | Undefined |

Treat this as a budget decision exercise. The first move in the simulation is to pause the $450 unconverted campaign and use that amount to fund a controlled lifecycle email holdout. Paid Social prospecting gets 38% of first-touch revenue and 3% of last-touch revenue. Preserve its test budget while measuring incremental acquisition. Review Paid Search brand targeting and bid levels because estimated contribution ROI is negative under all four models. Real budget changes require real spend, margin and experiment outcomes.

Of 481 profiles, 24 Champions averaged $661 of annualized gross-profit LTV proxy. The 54 At risk profiles averaged $539. This suggests a retention test for At risk repeat buyers in the simulation.

## Metric definitions

- First and last touch give all credit to the earliest or latest eligible session. Linear splits credit evenly. Time decay weights each touch by `0.5 ^ (days before order / 7)` and normalizes the weights. The window is 30 days before and including the order time.
- Orders without an eligible session receive an Unattributed row in each model. The first observed order per customer contributes fractional new-customer credit.
- RFM uses recency from 1 February 2021, order frequency and gross observed purchase revenue. Scores run from 1 to 5 for buyers and are 0 for prospects. Cutoffs and segment priority appear in the customer profile model.
- Observed LTV is gross purchase revenue × assumed 55% gross margin. The annualized proxy multiplies that value by 365/92. Refunds, varying margin, acquisition cost and future retention are outside this estimate.
- ROAS is credited revenue ÷ recorded spend. ROI is (credited revenue × 55% − spend) ÷ spend. CPA is spend ÷ credited first observed customers. Blank spend means unknown cost. Zero denominators yield null ratios.
- Spend covers the report period. Select one model when aggregating spend or calculating portfolio ratios. GA4 web campaign labels use a separate namespace in the warehouse so simulated app costs only match app campaigns.

## Validation evidence

```text
PASS attribution_reconciles
PASS unique_grains
PASS conflict isolation, cross-device stitching, deduplication, spend-only campaigns, null ratios and journey coverage
{"stg_events": 3186, "sessions": 2596, "orders": 576, "customer_profile": 481, "attribution": 5178}
```

The tests check each order and model for unit weights and revenue conservation, along with session, order and customer grain. The model differences measure credit assignment under the same data. Attribution accuracy and campaign incrementality require separate ground truth or experiments.
