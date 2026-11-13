with web as (
    select concat('web:', user_pseudo_id) as anonymous_id,
        (select max(value.int_value) from unnest(event_params) where key = 'ga_session_id') as session_number,
        div(event_timestamp, 1000000) as ts,
        event_name,
        nullif(ecommerce.transaction_id, '(not set)') as order_id,
        coalesce(ecommerce.purchase_revenue_in_usd, 0) as revenue,
        lower((select max(value.string_value) from unnest(event_params) where key = 'medium')) as medium,
        lower((select max(value.string_value) from unnest(event_params) where key = 'source')) as source_name,
        lower((select max(value.string_value) from unnest(event_params) where key = 'campaign')) as campaign
    from {{ source('ga4', 'events') }}
    where _TABLE_SUFFIX between '20201101' and '20210131'
      and user_pseudo_id is not null and user_pseudo_id not in ('', '<Other>')
      and event_timestamp is not null
),
classified as (
    select anonymous_id, concat(anonymous_id, ':', cast(session_number as string)) as session_id,
        ts, event_name, nullif(order_id, '') as order_id, revenue,
        case
            when medium in ('cpc', 'ppc', 'paidsearch', 'paid_search') then 'Paid Search'
            when medium in ('paid_social', 'paidsocial', 'paid-social') then 'Paid Social'
            when medium = 'email' then 'Email'
            when medium = 'organic' then 'Organic Search'
            when medium in ('referral', 'social') then 'Referral'
            when medium in ('(none)', 'none') or source_name = '(direct)' then 'Direct'
            when medium is not null and medium not in ('', '(not set)', '<other>') then 'Other'
        end as channel,
        case when campaign in ('', '(not set)', '<other>') then null else concat('web:', campaign) end as campaign
    from web
    where session_number is not null or (event_name = 'purchase' and order_id is not null)
)
select * from classified
union all
select anonymous_id, session_id, ts, event_name, order_id, revenue, channel, campaign
from {{ source('inputs', 'app_events') }}
