with ranked as (
    select *,
        row_number() over (
            partition by session_id
            order by case when channel is null then 1 else 0 end, ts, channel, campaign
        ) as channel_rank,
        min(ts) over (partition by session_id) as session_ts,
        count(*) over (partition by session_id) as events
    from {{ ref('events_resolved') }}
    where session_id is not null
)
select session_id, customer_key, identity_status, session_ts, events,
    coalesce(channel, 'Direct') as channel,
    coalesce(campaign, '(unassigned)') as campaign
from ranked
where channel_rank = 1
