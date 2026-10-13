# VELARA Launch Tracker Analysis

## Challenge: Claude Olympics - VELARA Launch Risk Assessment

Analysis of the VELARA medicine launch across 30 countries, identifying data defects, calculating slippage, and ranking countries by risk impact.

## Files

### Submission
- `submission_template/risk_ranking.csv` — All 30 countries ranked by impact (slippage × forecast volume)
- `submission_template/findings.csv` — 19 defects identified using standardized finding codes

### Source Data
- `dataset/VELARA_tracker.xlsx` — Four monthly tracker extracts (Jan–Apr 2026) plus reference tabs
- `dataset/dashboard_status.csv` — Current dashboard red/green status
- `finding_codes.md` — 25 finding codes (6 are not present in this dataset)

## Key Results

- **11 countries** have genuine slippage (ranging from 18 to 158 days)
- **United States** is the highest-risk country (158 days slippage × 3.2M volume = 505.6M impact)
- **19 distinct defects** identified across regulatory, supply chain, manufacturing, and data quality domains
- The dashboard's claim of 97% green (29/30) is significantly overstated — only 19 of 30 countries are genuinely on track

## Approach

The analysis cross-referenced all four monthly extracts against reference data, checking each of the five leads' concerns systematically: regulatory approval accuracy, demand loading timing vs site lead times, plant capacity constraints, readiness field completeness, shipment date drift, and starting dose availability for patient initiation.
