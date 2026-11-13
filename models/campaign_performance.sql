with first_purchase as (
    select order_id, row_number() over (
        partition by customer_key order by order_ts, order_id
    ) as purchase_rank
    from {{ ref('orders') }}
),
credit as (
    select model, channel, campaign,
        sum(credited_revenue) as credited_revenue,
        sum(weight) as credited_orders,
        sum(case when f.purchase_rank = 1 then weight else 0 end) as credited_new_customers
    from {{ ref('attribution') }} a
    join first_purchase f on a.order_id = f.order_id
    group by model, channel, campaign
),
spend_by_campaign as (
    select channel, campaign, sum(cost_usd) as spend
    from {{ source('inputs', 'spend') }}
    where spend_date between '2020-11-01' and '2021-01-31'
    group by channel, campaign
),
models as (
    select 'First touch' as model union all select 'Last touch'
    union all select 'Linear' union all select 'Time decay'
),
keys as (
    select model, channel, campaign from credit
    union
    select model, channel, campaign from spend_by_campaign cross join models
)
select k.*, coalesce(c.credited_revenue, 0) as credited_revenue,
    coalesce(c.credited_orders, 0) as credited_orders,
    coalesce(c.credited_new_customers, 0) as credited_new_customers,
    s.spend,
    coalesce(c.credited_revenue, 0) / nullif(s.spend, 0) as roas,
    (coalesce(c.credited_revenue, 0) * {{ var('gross_margin', 0.55) }} - s.spend)
        / nullif(s.spend, 0) as roi,
    s.spend / nullif(c.credited_new_customers, 0) as cpa
from keys k
left join credit c on k.model = c.model and k.channel = c.channel and k.campaign = c.campaign
left join spend_by_campaign s on k.channel = s.channel and k.campaign = s.campaign
