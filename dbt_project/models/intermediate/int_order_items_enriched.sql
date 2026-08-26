-- Line items joined to product attributes, with orphaned-FK rows excluded
-- and margin calculated. This is the grain we build the order-item fact from.

with items as (
    select * from {{ ref('stg_order_items') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

joined as (
    select
        i.order_item_id,
        i.order_id,
        i.product_id,
        p.product_name,
        p.category,
        i.quantity,
        i.unit_price,
        p.unit_cost,
        round(i.quantity * i.unit_price, 2)                    as line_revenue,
        round(i.quantity * (i.unit_price - p.unit_cost), 2)    as line_margin
    from items i
    inner join products p on i.product_id = p.product_id
    where not i.is_orphaned_product
)

select * from joined
