with ranked as (
    select *,
        row_number() over (
            partition by order_id order by ts, anonymous_id, session_id, revenue desc
        ) as order_rank
    from {{ ref('events_resolved') }}
    where event_name in ('purchase', 'in_app_purchase')
        and order_id is not null and order_id not in ('', '(not set)', '<Other>')
        and revenue >= 0
)
select order_id, customer_key, ts as order_ts, revenue
from ranked where order_rank = 1
