select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.country,
    c.signup_date,
    count(distinct o.order_id)                              as lifetime_orders,
    coalesce(sum(o.order_revenue), 0)                        as lifetime_revenue,
    coalesce(sum(o.order_margin), 0)                         as lifetime_margin,
    min(o.order_date)                                        as first_order_date,
    max(o.order_date)                                        as last_order_date
from {{ ref('dim_customers') }} c
left join {{ ref('fact_orders') }} o
    on c.customer_id = o.customer_id and o.order_status != 'cancelled'
where c.is_current
group by 1, 2, 3, 4, 5
