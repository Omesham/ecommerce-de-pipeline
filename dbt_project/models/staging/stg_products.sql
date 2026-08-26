with source as (
    select * from {{ source('raw', 'raw_products') }}
)

select
    product_id,
    trim(product_name)                 as product_name,
    trim(category)                     as category,
    cast(unit_cost as decimal(10, 2))  as unit_cost,
    cast(unit_price as decimal(10, 2)) as unit_price,
    cast(created_at as date)           as created_at
from source
