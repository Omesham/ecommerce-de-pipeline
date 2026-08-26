with source as (
    select * from {{ source('raw', 'raw_orders') }}
)

select
    order_id,
    customer_id,
    cast(order_timestamp as timestamp) as order_timestamp,
    cast(order_timestamp as date)      as order_date,
    lower(trim(status))                as status,
    lower(trim(channel))               as channel
from source
