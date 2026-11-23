"""What-if revenue calculator (V2). Pure Python/pandas, no database needed at call time.

Given a listing profile and a nightly price, estimate a RANGE of annual nights and gross revenue from comparable
benchmark listings (same district x room type x capacity band, with fallbacks), using the estimated-occupancy assumptions.

Method
  1. comparable set = benchmark listings of the same district, room type and capacity band (falls back to district x room type,
     then room type if fewer than MIN_N listings)
  2. price position = your price / median price of the comparable set. Listings in the same price band (cheaper than 0.85x,
     0.85-1.15x, dearer than 1.15x the median) are used if at least MIN_N of them exist. This is an ASSOCIATION in the data
     (dearer listings tend to show fewer estimated nights), NOT a measured price elasticity.
  3. nights: low / base / high = 25th percentile / median / 75th percentile of est_nights_base across the comparable listings
     (the spread between similar listings). Separately, the MODEL-assumption uncertainty is reported as the median under the
     low and high occupancy scenarios (est_nights_low / est_nights_high).
  4. revenue = nights x price (gross). Optional platform fee % and fixed monthly costs give an indicative net figure.
  5. optional annual night cap (e.g. 90) truncates nights; break-even price shows what price keeps revenue unchanged.
All outputs are ESTIMATES from a review-based occupancy model (see docs/DATA_MODEL.md).
"""
from dataclasses import dataclass, field, asdict
import duckdb
import numpy as np
import pandas as pd
from src.config import DB_PATH

MIN_N = 30


def load_benchmark_frame(db_path=DB_PATH) -> pd.DataFrame:
    con = duckdb.connect(str(db_path), read_only=True)
    df = con.execute("""
        SELECT f.listing_id, n.district, d.room_type, d.capacity_band, d.license_status, d.host_type_key,
               f.price_eur, f.number_of_reviews_ltm, f.est_nights_low, f.est_nights_base, f.est_nights_high
        FROM dbt_mart.fact_listing f
        JOIN dbt_mart.dim_listing d USING (listing_id)
        JOIN dbt_mart.dim_neighbourhood n ON n.neighbourhood_key = d.neighbourhood_key
        WHERE d.is_benchmark""").df()
    con.close()
    return df


def capacity_band(accommodates: int) -> str:
    return "1-2" if accommodates <= 2 else "3-4" if accommodates <= 4 else "5-6" if accommodates <= 6 else "7+"


@dataclass
class Profile:
    district: str
    room_type: str
    accommodates: int
    price_eur: float
    max_nights: int | None = None      # annual cap (e.g. 90); None = no cap
    platform_fee_pct: float = 0.0      # YOU set this for your channel; default 0 means gross
    fixed_costs_per_month: float = 0.0


@dataclass
class Estimate:
    profile: dict
    comparable_set: str
    n_comparable: int
    segment_median_price: float
    price_position: float
    price_band_used: bool
    nights_low: float
    nights_base: float
    nights_high: float
    revenue_low: float
    revenue_base: float
    revenue_high: float
    revenue_median_model_low: float     # median revenue if the occupancy model's assumptions are pessimistic
    revenue_median_model_high: float    # ... optimistic
    occupancy_base: float
    net_base: float
    breakeven_price_for_cap: float | None
    warnings: list = field(default_factory=list)

    def as_dict(self):
        return asdict(self)


class RevenueCalculator:
    def __init__(self, frame: pd.DataFrame):
        self.df = frame

    def _comparable(self, p: Profile):
        d = self.df
        cb = capacity_band(p.accommodates)
        for label, mask in [("district x room type x capacity", (d.district == p.district) & (d.room_type == p.room_type) & (d.capacity_band == cb)),
                            ("district x room type", (d.district == p.district) & (d.room_type == p.room_type)),
                            ("room type (city-wide)", d.room_type == p.room_type)]:
            if mask.sum() >= MIN_N:
                return label, d[mask]
        return "all benchmark listings", d

    def estimate(self, p: Profile) -> Estimate:
        if p.price_eur < 10 or p.price_eur > 1000:
            raise ValueError("price must be between 10 and 1000 EUR per night (the range of the benchmark data)")
        label, seg = self._comparable(p)
        warn = []
        med = float(seg.price_eur.median())
        pos = p.price_eur / med
        lo, hi = 0.85, 1.15
        band = seg[seg.price_eur < lo * med] if pos < lo else seg[seg.price_eur > hi * med] if pos > hi else seg[(seg.price_eur >= lo * med) & (seg.price_eur <= hi * med)]
        used_band = len(band) >= MIN_N
        base = band if used_band else seg
        if not used_band:
            warn.append("Too few comparable listings at this price position; used all comparable listings (price effect on nights ignored).")
        if label != "district x room type x capacity":
            warn.append(f"Comparable set widened to: {label}.")
        if float(base.est_nights_base.median()) >= 250:
            warn.append("Median estimate sits at the model's 255-night cap: the model cannot distinguish very busy from fully busy listings.")
        if pos > 1.6 or pos < 0.5:
            warn.append("Your price is far from the comparable median; the estimate is an extrapolation.")
        n_lo, n_ba, n_hi = (float(np.percentile(base.est_nights_base, 25)), float(base.est_nights_base.median()), float(np.percentile(base.est_nights_base, 75)))
        m_lo, m_hi = float(base.est_nights_low.median()), float(base.est_nights_high.median())
        if p.max_nights is not None:
            n_lo, n_ba, n_hi, m_lo, m_hi = (min(x, p.max_nights) for x in (n_lo, n_ba, n_hi, m_lo, m_hi))
        rev = lambda n: round(n * p.price_eur, 0)
        net = rev(n_ba) * (1 - p.platform_fee_pct) - 12 * p.fixed_costs_per_month
        be = None
        if p.max_nights is not None and float(base.est_nights_base.median()) > p.max_nights:
            be = round(float(base.est_nights_base.median()) * p.price_eur / p.max_nights, 0)
            warn.append("Break-even price ignores that guests may react to higher prices.")
        return Estimate(asdict(p), label, int(len(base)), round(med, 1), round(pos, 2), used_band, round(n_lo), round(n_ba), round(n_hi),
                        rev(n_lo), rev(n_ba), rev(n_hi), rev(m_lo), rev(m_hi), round(n_ba / 365, 3), round(net, 0), be, warn)

    def price_curve(self, p: Profile, prices) -> pd.DataFrame:
        """Revenue range for a list of candidate prices (for charts)."""
        rows = []
        for x in prices:
            e = self.estimate(Profile(**{**asdict(p), "price_eur": float(x)}))
            rows.append({"price_eur": x, "nights_base": e.nights_base, "revenue_low": e.revenue_low, "revenue_base": e.revenue_base, "revenue_high": e.revenue_high})
        return pd.DataFrame(rows)


if __name__ == "__main__":
    calc = RevenueCalculator(load_benchmark_frame())
    e = calc.estimate(Profile("Friedrichshain-Kreuzberg", "Entire home/apt", 4, 170))
    for k, v in e.as_dict().items():
        print(f"{k}: {v}")
