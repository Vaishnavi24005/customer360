with people as (
    select customer_key from {{ ref('events_resolved') }}
    union
    select concat('crm:', customer_id) from {{ source('inputs', 'crm') }}
),
activity as (
    select customer_key, count(*) as sessions from {{ ref('sessions') }} group by customer_key
),
purchases as (
    select customer_key, count(*) as frequency, sum(revenue) as monetary,
        min(order_ts) as first_order_ts, max(order_ts) as last_order_ts
    from {{ ref('orders') }} group by customer_key
),
metrics as (
    select p.customer_key, c.market, coalesce(a.sessions, 0) as sessions,
        coalesce(o.frequency, 0) as frequency, coalesce(o.monetary, 0) as monetary,
        o.first_order_ts,
        floor(({{ var('as_of_ts', 1612137600) }} - o.last_order_ts) / 86400.0) as recency_days
    from people p
    left join activity a on p.customer_key = a.customer_key
    left join purchases o on p.customer_key = o.customer_key
    left join {{ source('inputs', 'crm') }} c on p.customer_key = concat('crm:', c.customer_id)
),
scored as (
    select *,
        case when frequency = 0 then 0 when recency_days <= 14 then 5
             when recency_days <= 30 then 4 when recency_days <= 45 then 3
             when recency_days <= 60 then 2 else 1 end as r_score,
        case when frequency >= 5 then 5 else frequency end as f_score,
        case when frequency = 0 then 0 when monetary >= 400 then 5
             when monetary >= 200 then 4 when monetary >= 100 then 3
             when monetary >= 50 then 2 else 1 end as m_score
    from metrics
)
select *,
    round(monetary * {{ var('gross_margin', 0.55) }}, 2) as observed_ltv,
    round(monetary * {{ var('gross_margin', 0.55) }} * 365.0 / 92, 2) as annualized_ltv_proxy,
    case when frequency = 0 then 'Prospect'
         when r_score >= 4 and f_score >= 3 and m_score >= 3 then 'Champions'
         when r_score <= 2 and f_score >= 2 then 'At risk'
         when frequency = 1 and r_score >= 4 then 'New buyer'
         when frequency >= 2 then 'Repeat buyer'
         else 'One-time buyer' end as segment
from scored
