select * from (values
    (1, 'Single-listing host',   1,  1),
    (2, 'Small multi (2-3)',     2,  3),
    (3, 'Professional (4-10)',   4, 10),
    (4, 'Commercial (11+)',     11, 100000)
) t(host_type_key, host_type, min_listings, max_listings)
