with rollup as (
    select order_id, count(distinct model) as models,
        sum(weight) as total_weight, sum(credited_revenue) as total_revenue
    from {{ ref('attribution') }} group by order_id
)
select o.order_id from {{ ref('orders') }} o
left join rollup r on o.order_id = r.order_id
where coalesce(r.models, 0) != 4 or abs(r.total_weight - 4) > 0.000001
    or abs(r.total_revenue - o.revenue * 4) > 0.000001
union all
select a.order_id from {{ ref('attribution') }} a
join {{ ref('orders') }} o on a.order_id = o.order_id
group by a.order_id, a.model, o.revenue
having abs(sum(a.weight) - 1) > 0.000001
    or abs(sum(a.credited_revenue) - o.revenue) > 0.000001
