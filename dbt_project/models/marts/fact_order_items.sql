-- Grain: one row per order line item. This is the most granular fact table
-- and the base for revenue/margin analysis by product, category, or time.

select
    oi.order_item_id,
    oi.order_id,
    o.customer_id,
    o.order_date,
    o.order_status,
    o.channel,
    oi.product_id,
    oi.product_name,
    oi.category,
    oi.quantity,
    oi.unit_price,
    oi.line_revenue,
    oi.line_margin
from {{ ref('int_order_items_enriched') }} oi
inner join {{ ref('int_orders_with_payments') }} o on oi.order_id = o.order_id
