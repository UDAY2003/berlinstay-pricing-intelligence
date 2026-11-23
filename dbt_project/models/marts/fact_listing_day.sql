-- Grain: listing x future day. is_available = false means booked OR blocked by host (cannot be separated).
select listing_id, cast(strftime(cal_date, '%Y%m%d') as integer) as date_key, is_available, minimum_nights
from {{ ref('stg_calendar') }}
