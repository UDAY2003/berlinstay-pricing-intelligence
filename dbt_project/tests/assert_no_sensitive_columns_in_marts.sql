-- fails if a banned column name exists in any mart table (host_key is allowed ONLY in dim_listing and is never exported)
select table_name, column_name from information_schema.columns
where table_schema = 'dbt_mart'
  and column_name in ('host_id','host_name','name','description','license','comments','reviewer_name','listing_url')
