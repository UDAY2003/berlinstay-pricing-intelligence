-- Business flags. Rows are flagged, never dropped.
-- Benchmark population = priced, short-stay (<28 nights avg minimum), price 10-1000 EUR.
select
    *,
    price_raw is not null                                              as has_price,
    (price_raw is not null and (price_raw < 10 or price_raw > 1000))   as is_price_outlier,
    case when price_raw between 10 and 1000 then price_raw end         as price_eur,
    coalesce(minimum_nights_avg_ntm, minimum_nights) >= 28             as is_mid_term,
    -- coalesce: SQL three-valued logic would otherwise give NULL (not FALSE) for unpriced listings (fixed vs V1)
    coalesce(price_raw between 10 and 1000
        and coalesce(minimum_nights_avg_ntm, minimum_nights) < 28, false) as is_benchmark
from {{ ref('stg_listings') }}
