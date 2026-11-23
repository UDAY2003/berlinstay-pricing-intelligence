select listing_id from {{ ref('dim_listing') }}
where is_benchmark and (not has_price or is_mid_term or is_price_outlier)
