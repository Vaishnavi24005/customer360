select 'orders' as model, order_id as key from {{ ref('orders') }}
group by order_id having count(*) != 1
union all
select 'sessions', session_id from {{ ref('sessions') }}
group by session_id having count(*) != 1
union all
select 'customer_profile', customer_key from {{ ref('customer_profile') }}
group by customer_key having count(*) != 1
