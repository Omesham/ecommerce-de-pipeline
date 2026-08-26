-- Grain: one row per order. Aggregates line items up to order level and
-- brings in payment outcome -- the table most BI tools/dashboards query.

with order_totals as (
    select
        order_id,
        sum(line_revenue) as order_revenue,
        sum(line_margin)  as order_margin,
        count(*)          as item_count
    from {{ ref('int_order_items_enriched') }}
    group by 1
)

select
    o.order_id,
    o.customer_id,
    o.order_timestamp,
    o.order_date,
    o.order_status,
    o.channel,
    o.payment_method,
    o.payment_status,
    o.payment_amount,
    o.days_to_payment,
    coalesce(t.order_revenue, 0) as order_revenue,
    coalesce(t.order_margin, 0)  as order_margin,
    coalesce(t.item_count, 0)    as item_count
from {{ ref('int_orders_with_payments') }} o
left join order_totals t on o.order_id = t.order_id
