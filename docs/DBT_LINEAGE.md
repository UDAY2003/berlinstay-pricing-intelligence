# dbt lineage (generated)

Generated from `dbt_project/target/manifest.json` by `python -m src.dbt_lineage`. Arrows point from an input to the model that uses it.

```mermaid
flowchart LR
  subgraph sources["Raw sources (DuckDB schema raw)"]
    source_berlinstay_raw_calendar["calendar"]
    source_berlinstay_raw_listings["listings"]
    source_berlinstay_raw_neighbourhoods["neighbourhoods"]
    source_berlinstay_raw_reviews["reviews"]
  end
  subgraph staging["Staging (views)"]
    model_berlinstay_stg_calendar["stg_calendar"]
    model_berlinstay_stg_listings["stg_listings"]
    model_berlinstay_stg_neighbourhoods["stg_neighbourhoods"]
    model_berlinstay_stg_reviews["stg_reviews"]
  end
  subgraph intermediate["Intermediate (tables)"]
    model_berlinstay_int_listing_estimates["int_listing_estimates"]
    model_berlinstay_int_listings_flagged["int_listings_flagged"]
  end
  subgraph marts["Marts: star schema (tables)"]
    model_berlinstay_dim_date["dim_date"]
    model_berlinstay_dim_host_type["dim_host_type"]
    model_berlinstay_dim_listing["dim_listing"]
    model_berlinstay_dim_neighbourhood["dim_neighbourhood"]
    model_berlinstay_fact_availability_week["fact_availability_week"]
    model_berlinstay_fact_listing["fact_listing"]
    model_berlinstay_fact_listing_day["fact_listing_day"]
    model_berlinstay_fact_review_month["fact_review_month"]
  end
  subgraph analysis["Analysis answers (tables)"]
    model_berlinstay_forward_availability_events["forward_availability_events"]
    model_berlinstay_forward_availability_weekly["forward_availability_weekly"]
    model_berlinstay_license_status["license_status"]
    model_berlinstay_monthly_review_series["monthly_review_series"]
    model_berlinstay_multi_listing_hosts["multi_listing_hosts"]
    model_berlinstay_neighbourhood_summary["neighbourhood_summary"]
    model_berlinstay_occupancy_revenue["occupancy_revenue"]
    model_berlinstay_price_by_district_roomtype["price_by_district_roomtype"]
    model_berlinstay_review_demand_trends["review_demand_trends"]
    model_berlinstay_seasonal_index["seasonal_index"]
    model_berlinstay_supply_concentration["supply_concentration"]
  end
  subgraph seeds["Seeds (assumptions)"]
    seed_berlinstay_event_window["event_window"]
    seed_berlinstay_occupancy_assumptions["occupancy_assumptions"]
  end
  model_berlinstay_fact_listing_day --> model_berlinstay_forward_availability_events
  model_berlinstay_dim_date --> model_berlinstay_forward_availability_events
  model_berlinstay_dim_listing --> model_berlinstay_forward_availability_events
  model_berlinstay_fact_listing_day --> model_berlinstay_forward_availability_weekly
  model_berlinstay_dim_date --> model_berlinstay_forward_availability_weekly
  model_berlinstay_dim_listing --> model_berlinstay_forward_availability_weekly
  model_berlinstay_dim_listing --> model_berlinstay_license_status
  model_berlinstay_fact_listing --> model_berlinstay_license_status
  model_berlinstay_stg_reviews --> model_berlinstay_monthly_review_series
  model_berlinstay_dim_listing --> model_berlinstay_multi_listing_hosts
  model_berlinstay_fact_listing --> model_berlinstay_multi_listing_hosts
  model_berlinstay_dim_host_type --> model_berlinstay_multi_listing_hosts
  model_berlinstay_fact_listing --> model_berlinstay_neighbourhood_summary
  model_berlinstay_dim_listing --> model_berlinstay_neighbourhood_summary
  model_berlinstay_dim_neighbourhood --> model_berlinstay_neighbourhood_summary
  model_berlinstay_fact_listing --> model_berlinstay_occupancy_revenue
  model_berlinstay_dim_listing --> model_berlinstay_occupancy_revenue
  model_berlinstay_dim_neighbourhood --> model_berlinstay_occupancy_revenue
  model_berlinstay_fact_listing --> model_berlinstay_price_by_district_roomtype
  model_berlinstay_dim_listing --> model_berlinstay_price_by_district_roomtype
  model_berlinstay_dim_neighbourhood --> model_berlinstay_price_by_district_roomtype
  model_berlinstay_stg_reviews --> model_berlinstay_review_demand_trends
  model_berlinstay_dim_listing --> model_berlinstay_review_demand_trends
  model_berlinstay_dim_neighbourhood --> model_berlinstay_review_demand_trends
  model_berlinstay_stg_reviews --> model_berlinstay_seasonal_index
  model_berlinstay_dim_listing --> model_berlinstay_supply_concentration
  model_berlinstay_dim_neighbourhood --> model_berlinstay_supply_concentration
  seed_berlinstay_occupancy_assumptions --> model_berlinstay_int_listing_estimates
  model_berlinstay_int_listings_flagged --> model_berlinstay_int_listing_estimates
  seed_berlinstay_event_window --> model_berlinstay_dim_date
  source_berlinstay_raw_calendar --> model_berlinstay_stg_calendar
  source_berlinstay_raw_listings --> model_berlinstay_stg_listings
  source_berlinstay_raw_reviews --> model_berlinstay_stg_reviews
  model_berlinstay_stg_listings --> model_berlinstay_int_listings_flagged
  model_berlinstay_stg_neighbourhoods --> model_berlinstay_dim_neighbourhood
  model_berlinstay_int_listings_flagged --> model_berlinstay_dim_listing
  model_berlinstay_dim_neighbourhood --> model_berlinstay_dim_listing
  model_berlinstay_dim_host_type --> model_berlinstay_dim_listing
  model_berlinstay_stg_calendar --> model_berlinstay_fact_listing_day
  model_berlinstay_int_listing_estimates --> model_berlinstay_fact_listing
  model_berlinstay_dim_listing --> model_berlinstay_fact_listing
  model_berlinstay_stg_reviews --> model_berlinstay_fact_review_month
  model_berlinstay_fact_listing_day --> model_berlinstay_fact_availability_week
  model_berlinstay_dim_date --> model_berlinstay_fact_availability_week
  model_berlinstay_dim_listing --> model_berlinstay_fact_availability_week
  source_berlinstay_raw_neighbourhoods --> model_berlinstay_stg_neighbourhoods
```

25 models, 2 seeds, 4 sources, 46 dependencies. Tests (44) are defined in `models/*/schema.yml` and `dbt_project/tests/`.
