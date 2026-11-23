select
    cast(strftime(d, '%Y%m%d') as integer)          as date_key,
    d::date                                         as date,
    year(d)                                         as year,
    quarter(d)                                      as quarter,
    month(d)                                        as month,
    strftime(d, '%b')                               as month_name,
    date_trunc('month', d)::date                    as month_start,
    date_trunc('week', d)::date                     as week_start,
    isodow(d)                                       as iso_day_of_week,
    isodow(d) >= 6                                  as is_weekend,
    case when month(d) in (12,1,2) then 'Winter' when month(d) in (3,4,5) then 'Spring'
         when month(d) in (6,7,8) then 'Summer' else 'Autumn' end as season,
    month(d) in (6,7,8)                             as is_summer,
    (month(d) = 12 and day(d) >= 20) or (month(d) = 1 and day(d) <= 2) as is_christmas_window,
    e.event_name,
    coalesce(e.is_indicative, false)                as event_is_indicative
from generate_series(date '2009-01-01', date '2027-12-31', interval 1 day) as g(d)
left join {{ ref('event_window') }} e on d::date between e.start_date and e.end_date
