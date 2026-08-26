-- Cleans raw customer records: normalizes country casing/whitespace,
-- casts types, and keeps every historical row (dedup happens in the
-- snapshot layer, not here) so we don't silently lose late-arriving data.

with source as (
    select * from {{ source('raw', 'raw_customers') }}
)

select
    customer_id,
    trim(first_name)                       as first_name,
    trim(last_name)                        as last_name,
    nullif(trim(email), '')                as email,
    {{ title_case('country') }}            as country,
    cast(signup_date as date)              as signup_date,
    is_active,
    cast(_updated_at as timestamp)         as updated_at,
    _source_file,
    cast(_loaded_at as timestamp)          as loaded_at
from source
