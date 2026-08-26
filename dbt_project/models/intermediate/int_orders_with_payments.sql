-- One row per order with its payment outcome. An order can have more than
-- one payment attempt (e.g. a failed attempt followed by a success), so we
-- pick the most recent payment per order as the order's effective payment.

with orders as (
    select * from {{ ref('stg_orders') }}
),

payments as (
    select * from {{ ref('stg_payments') }}
),

ranked_payments as (
    select
        *,
        row_number() over (
            partition by order_id
            order by payment_timestamp desc
        ) as rn
    from payments
),

latest_payment as (
    select * from ranked_payments where rn = 1
)

select
    o.order_id,
    o.customer_id,
    o.order_timestamp,
    o.order_date,
    o.status          as order_status,
    o.channel,
    lp.payment_method,
    lp.payment_status,
    lp.amount         as payment_amount,
    lp.payment_timestamp,
    datediff('day', o.order_timestamp, lp.payment_timestamp) as days_to_payment
from orders o
left join latest_payment lp on o.order_id = lp.order_id
