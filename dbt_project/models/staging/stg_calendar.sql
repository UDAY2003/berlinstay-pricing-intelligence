select listing_id, date as cal_date, available as is_available, minimum_nights, maximum_nights
from {{ source('raw', 'calendar') }}
