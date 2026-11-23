select neighbourhood_group as district, neighbourhood from {{ source('raw', 'neighbourhoods') }}
