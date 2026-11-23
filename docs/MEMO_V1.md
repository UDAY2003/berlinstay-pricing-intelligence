# Memo: Pricing a Berlin short-term rental - what the market data says

**To:** Berlin hosts and small property managers | **From:** BerlinStay Pricing Intelligence (V1) | **Data:** Inside Airbnb, Berlin, scrape 19 Sep 2026 (CC BY 4.0)
**Read this first:** occupancy and revenue below are *estimates* from a review-rate model, not bookings or tax data. The calendar cannot tell booked from blocked nights, has no prices in this release, and locations are anonymised. Aggregated results only; no host is identified. This is market analysis, not legal or tax advice.

## 1. The market in one paragraph
Inside Airbnb lists 12,376 Berlin listings, but only **6,456 (52%) are priced, short-stay listings** (the benchmark used below); 34% have no price (not bookable) and 13.5% are mid-term (28+ nights). Mitte and Friedrichshain-Kreuzberg hold 43% of priced supply, so competition is concentrated where prices are highest. Review activity in January-August 2026 is 15.4% above the same months of 2025 (after de-duplicating repeated review records), so demand is still growing.

## 2. How to set a price
Start from the median of your *segment*, not the city average (city mean 182 EUR is pulled up by luxury listings).

| Entire home, guests | 1-2 | 3-4 | 5-6 | 7+ |
|---|---|---|---|---|
| Median EUR / night | 141 | 172 | 231 | 315 |

| Room type | Median EUR/night | Middle half (p25-p75) |
|---|---|---|
| Entire home/apt | 181 | 135-256 |
| Private room | 91 | 72-120 |

District matters too (entire-home medians): Mitte 205, Pankow 185, Friedrichshain-Kreuzberg 184, Charlottenburg-Wilmersdorf 178, Neukoelln 166, Treptow-Koepenick 147, Reinickendorf 115. Treat districts with fewer than about 60 entire-home listings (Spandau 56, Reinickendorf 46, Marzahn-Hellersdorf 44) as indicative. Within a district the p25-p75 band is wide (for Mitte entire homes 149-284 EUR), so use the band: price near the median if you have average amenities and reviews, toward p75 only with clear advantages. Guest capacity is the strongest price correlate (Spearman 0.61), review scores barely matter (0.06). V2 will test whether a model can beat a simple district x room-type median.

## 3. What income is realistic (estimates, gross)
| Entire homes (benchmark) | Low | Base | High |
|---|---|---|---|
| Median estimated revenue, EUR/year | 16.8k | 26.0k | 29.1k |
Private rooms: 7.9k / 13.8k / 15.6k. Across all benchmark listings the median is about 19.6k and the mean 25.7k; the top 10% earn about a third of the total, so **plan on the median and budget with the low case**. By size (entire homes, base): 1-2 guests 16.6k, 3-4 guests 27.0k, 5-6 guests 34.7k, 7+ guests 55.7k. Figures are before platform fees, cleaning, taxes, furnishing and rent/mortgage; they apply today's price to the past 12 months; and listings with no review in the last year (about 12%) are counted as zero nights, which understates some quiet-but-booked listings. Among entire homes with at least one review, the median estimated nights per year are 239-252 in Mitte, Friedrichshain-Kreuzberg and Pankow versus 139-164 in Neukoelln, Tempelhof-Schoeneberg and Charlottenburg-Wilmersdorf (base model, capped at 255 nights, so the top end is compressed by the cap).

## 4. Seasonality and events
Using review dates as a demand proxy (2023-2025 average), September (index 1.25), July (1.22), June (1.21) and October (1.18) are the strongest months; January (0.63) and February (0.70) the weakest. Reviews follow stays, so true demand likely peaks a few weeks earlier. In the forward calendar, the Festival of Lights (+8 pp), Christmas/New Year (+8 pp), the Marathon weekend (+5 pp) and Easter (+4 pp) windows are less available than ordinary days in the same months; Berlinale, ITB and Pride show no uplift. **Caveats:** event dates marked indicative must be checked against official calendars; unavailable includes host-blocked nights; and near-term nights are naturally fuller than far-future ones. This release has no calendar prices, so **we cannot quantify a price premium** for any season or event; test it with your own booking data.

## 5. Competition and professionalisation
Hosts with four or more listings are about 10% of hosts but hold 42% of benchmark listings and about 47% of estimated revenue. Per-listing median income is similar across host types (single-listing hosts 18.1k, 4-10 listings 22.0k, 11+ 19.9k), so scale alone does not guarantee higher income per property. Growth in review activity (Jan-Aug 2026 vs 2025) is strongest in Charlottenburg-Wilmersdorf (+25%) and Mitte (+20%), and weakest in Reinickendorf (flat) and Marzahn-Hellersdorf (-10%); Spandau's +53% rests on only 707 reviews.

## 6. Local rules (verify before acting)
The `license` field in the data is free text typed by hosts: 42% of benchmark entire-home entries look like registration numbers, others state a legal entity or person, and some are empty or "exempt". This is **descriptive only and not a compliance check** of any listing. Berlin has a registration-number requirement and further limits (for example on second homes) whose details have changed over time; confirm current rules with the official Berlin sources (Senate/district offices) before pricing or investing. V2 adds a clearly labelled *scenario* for a 90-night annual cap; on the base estimate about 63% of benchmark entire-home listings exceed 90 estimated nights a year, which shows why the question matters, but whether any given listing is affected depends on legal facts this dataset does not contain.

## 7. Recommendations
1. Anchor on the segment median (district x room type x capacity); move within p25-p75 based on quality and reviews.
2. Budget on the low-case income; treat anything above the median as upside.
3. Keep calendars open and minimum stays short in June-July and September-October; expect to compete on price in January-February.
4. Plan event dates (Festival of Lights, Christmas/New Year, Easter) after verifying them, and measure your own premium.
5. Before expanding in Mitte or Friedrichshain-Kreuzberg, weigh the highest prices against the densest supply; look at fast-growing districts with enough listings (Charlottenburg-Wilmersdorf).
6. Confirm registration and any usage limits with the official sources first.

*Sources and method:* `docs/DATA_MODEL.md`, `docs/DATA_QUALITY_REPORT.md`, `sql/`, `notebooks/01_eda.ipynb`. Data: Inside Airbnb (insideairbnb.com), CC BY 4.0.
