with source as (
    select * from {{ source('raw', 'raw_payments') }}
)

select
    payment_id,
    order_id,
    lower(trim(payment_method))            as payment_method,
    cast(amount as decimal(10, 2))         as amount,
    lower(trim(payment_status))            as payment_status,
    cast(payment_timestamp as timestamp)   as payment_timestamp
from source
