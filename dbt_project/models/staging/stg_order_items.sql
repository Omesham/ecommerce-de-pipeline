-- Flags orphaned product_ids (bad FK from source system) instead of
-- silently dropping them, so downstream marts can decide how to handle it.

with source as (
    select * from {{ source('raw', 'raw_order_items') }}
),

flagged as (
    select
        oi.order_item_id,
        oi.order_id,
        oi.product_id,
        cast(oi.quantity as integer)       as quantity,
        cast(oi.unit_price as decimal(10, 2)) as unit_price,
        p.product_id is null               as is_orphaned_product
    from source oi
    left join {{ source('raw', 'raw_products') }} p on oi.product_id = p.product_id
)

select * from flagged
