select
    order_date,
    channel,
    count(distinct order_id)                                    as order_count,
    sum(order_revenue)                                          as revenue,
    sum(order_margin)                                           as margin,
    round(sum(order_revenue) / nullif(count(distinct order_id), 0), 2) as avg_order_value
from {{ ref('fact_orders') }}
where order_status != 'cancelled'
group by 1, 2
order by 1
