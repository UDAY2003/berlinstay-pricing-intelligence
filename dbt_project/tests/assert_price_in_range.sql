select listing_id from {{ ref('fact_listing') }} where price_eur is not null and price_eur not between 10 and 1000
