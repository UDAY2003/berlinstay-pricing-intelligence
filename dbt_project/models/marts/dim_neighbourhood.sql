select row_number() over (order by district, neighbourhood) as neighbourhood_key, district, neighbourhood
from {{ ref('stg_neighbourhoods') }}
