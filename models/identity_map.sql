select i.anonymous_id,
    case when count(distinct i.customer_id) = 1 then min(c.customer_id) end as customer_id,
    case
        when count(distinct i.customer_id) > 1 then 'conflict'
        when count(c.customer_id) = 0 then 'unknown_crm'
        else 'linked'
    end as identity_status
from {{ source('inputs', 'identify') }} i
left join {{ source('inputs', 'crm') }} c on i.customer_id = c.customer_id
where i.anonymous_id is not null and i.customer_id is not null
group by i.anonymous_id
