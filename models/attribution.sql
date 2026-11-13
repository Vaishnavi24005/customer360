with eligible as (
    select o.order_id, o.customer_key, o.order_ts, o.revenue,
        coalesce(s.session_id, '') as session_id,
        coalesce(s.channel, 'Unattributed') as channel,
        coalesce(s.campaign, '(unassigned)') as campaign,
        coalesce(s.session_ts, o.order_ts) as touch_ts
    from {{ ref('orders') }} o
    left join {{ ref('sessions') }} s on o.customer_key = s.customer_key
        and s.session_ts between o.order_ts - 30 * 86400 and o.order_ts
),
ranked as (
    select *,
        row_number() over (partition by order_id order by touch_ts, session_id) as first_rank,
        row_number() over (partition by order_id order by touch_ts desc, session_id desc) as last_rank,
        count(*) over (partition by order_id) as touches,
        power(0.5, (order_ts - touch_ts) / (7.0 * 86400)) as decay
    from eligible
),
models as (
    select 'First touch' as model union all select 'Last touch'
    union all select 'Linear' union all select 'Time decay'
),
weights as (
    select r.*, m.model,
        case m.model
            when 'First touch' then case when first_rank = 1 then 1.0 else 0.0 end
            when 'Last touch' then case when last_rank = 1 then 1.0 else 0.0 end
            when 'Linear' then 1.0 / touches
            else decay / sum(decay) over (partition by order_id, m.model)
        end as weight
    from ranked r cross join models m
)
select order_id, customer_key, order_ts, session_id, channel, campaign, model,
    weight, revenue * weight as credited_revenue
from weights where weight > 0
