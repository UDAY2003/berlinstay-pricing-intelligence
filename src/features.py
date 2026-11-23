"""Feature engineering for the nightly-price model. Reads the dbt marts (dbt_mart schema).

Target: price_eur (benchmark listings only, 10-1,000 EUR, short-stay).
Two feature sets:
  * LISTING_FEATURES  - what a host knows BEFORE listing: size, type, location, amenities, host profile. Used for the main model.
  * +PERFORMANCE      - adds review scores/counts. These are outcomes of past pricing/demand, so they are NOT available
                        for a new listing and may leak demand information. Used only as an ablation.
"""
import duckdb
import numpy as np
import pandas as pd
from src.config import DB_PATH

CATEGORICAL = ["room_type", "property_type_grp", "district", "neighbourhood"]
NUMERIC = ["accommodates", "bedrooms", "beds", "bathrooms", "has_shared_bath", "amenities_count",
           "is_superhost", "host_listings_count", "latitude", "longitude", "dist_center_km",
           "minimum_nights_avg", "is_entire_home", "people_per_bedroom"]
PERFORMANCE = ["review_scores_rating", "review_scores_location", "review_scores_value", "number_of_reviews", "number_of_reviews_ltm"]
LISTING_FEATURES = CATEGORICAL + NUMERIC
ALL_FEATURES = LISTING_FEATURES + PERFORMANCE
CENTER = (52.5208, 13.4095)   # Alexanderplatz, a simple reference point for distance-to-centre


def haversine_km(lat, lon, lat0=CENTER[0], lon0=CENTER[1]):
    p = np.pi / 180
    a = 0.5 - np.cos((lat - lat0) * p) / 2 + np.cos(lat0 * p) * np.cos(lat * p) * (1 - np.cos((lon - lon0) * p)) / 2
    return 12742 * np.arcsin(np.sqrt(a))


def load_model_frame(db_path=DB_PATH, top_property_types: int = 12) -> pd.DataFrame:
    con = duckdb.connect(str(db_path), read_only=True)
    df = con.execute("""
        SELECT f.listing_id, f.price_eur, d.host_key, d.room_type, d.property_type, n.district, n.neighbourhood,
               d.capacity_band, d.accommodates, d.bedrooms, d.beds, d.bathrooms, d.has_shared_bath::INT AS has_shared_bath,
               d.amenities_count, d.is_superhost::INT AS is_superhost, h.min_listings AS host_bucket_min,
               li.host_listings_count, d.latitude, d.longitude,
               COALESCE(f.minimum_nights_avg_ntm, f.minimum_nights) AS minimum_nights_avg,
               f.review_scores_rating, f.review_scores_location, f.review_scores_value,
               f.number_of_reviews, f.number_of_reviews_ltm
        FROM dbt_mart.fact_listing f
        JOIN dbt_mart.dim_listing d USING (listing_id)
        JOIN dbt_mart.dim_neighbourhood n ON n.neighbourhood_key = d.neighbourhood_key
        JOIN dbt_mart.dim_host_type h ON h.host_type_key = d.host_type_key
        JOIN dbt_int.int_listings_flagged li USING (listing_id)
        WHERE d.is_benchmark
    """).df()
    con.close()
    top = df.property_type.value_counts().head(top_property_types).index
    df["property_type_grp"] = np.where(df.property_type.isin(top), df.property_type, "Other")
    df["dist_center_km"] = haversine_km(df.latitude.values, df.longitude.values)
    df["is_entire_home"] = (df.room_type == "Entire home/apt").astype(int)
    df["people_per_bedroom"] = df.accommodates / df.bedrooms.clip(lower=1)
    for c in CATEGORICAL:
        df[c] = df[c].astype("category")
    return df
