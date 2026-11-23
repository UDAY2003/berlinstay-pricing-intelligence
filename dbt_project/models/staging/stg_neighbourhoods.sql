select neighbourhood_group as district, neighbourhood from {{ source('raw', 'neighbourhoods') }}
where neighbourhood is not null   -- the source CSV ends with a blank row
