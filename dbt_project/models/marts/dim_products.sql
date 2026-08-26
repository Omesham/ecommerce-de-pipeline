select
    product_id,
    product_name,
    category,
    unit_cost,
    unit_price,
    round(unit_price - unit_cost, 2)                       as unit_margin,
    round((unit_price - unit_cost) / nullif(unit_price, 0), 4) as margin_pct,
    created_at
from {{ ref('stg_products') }}
