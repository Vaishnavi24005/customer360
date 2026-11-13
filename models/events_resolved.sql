select e.*,
    coalesce(concat('crm:', i.customer_id), concat('anon:', e.anonymous_id)) as customer_key,
    coalesce(i.identity_status, 'anonymous') as identity_status
from {{ ref('stg_events') }} e
left join {{ ref('identity_map') }} i on e.anonymous_id = i.anonymous_id
