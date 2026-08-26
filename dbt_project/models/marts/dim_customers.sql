-- Current-state customer dimension, sourced from the SCD2 snapshot.
-- dbt_valid_to is null for the currently active record of each customer.

select
    customer_id,
    first_name,
    last_name,
    email,
    country,
    signup_date,
    dbt_valid_from  as valid_from,
    dbt_valid_to    as valid_to,
    dbt_valid_to is null as is_current
from {{ ref('customers_snapshot') }}
