# VELARA Launch Tracker Analysis

## Challenge: Claude Olympics - VELARA Launch Risk Assessment

Analysis of the VELARA medicine launch across 30 countries, identifying data defects, calculating slippage, and ranking countries by risk impact.

## Quick Start

```bash
pip install -r requirements.txt
python3 solve.py
```

Or with Docker:

```bash
docker build -t velara-analysis .
docker run velara-analysis
```

## Files

### Solution
- `solve.py` — Main analysis script; reads the dataset and generates both output CSVs
- `goldentarget_config.json` — Runtime configuration for automated evaluation
- `requirements.txt` — Python dependencies
- `Dockerfile` — Container build for reproducible execution

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

## Methodology

### Slippage Computation
For each country, the real earliest possible ship date is computed from multiple constraints:
1. **Regulatory**: MTS countries cannot ship before approval (MTO can via bonded warehouse)
2. **Demand lead time**: Direct-route countries need demand loaded + site lead time (Ashford 16wk, Brenner 24wk, Calderon 26wk)
3. **Starting dose**: Patients must titrate from 2MG; if 2MG ships much later than other doses, effective launch is delayed
4. **Plant setup**: Product code must be set up at plant before production begins

Slippage = max(0, real_earliest − claimed_earliest). Impact = slippage_days × forecast_volume_year1.

### What Was NOT Flagged
- **MTO shipping before approval**: Legitimate — product goes to bonded warehouse
- **Via Hub blank readiness fields**: Legitimate — hub handles logistics, not the country
- **Reliance/Mutual Recognition approval before submission**: Legitimate — these pathways allow pre-approval
- **Date drift with achievable final dates**: Japan and Korea dates drift monthly but current claims are still feasible

### Areas of Uncertainty
- The ask_lead MCP server was unavailable; 2MG as starting dose was inferred from data patterns
- Ashford capacity constraint is flagged qualitatively; exact per-month allocation unknown
- Portugal's Dec 31 approval date may be legitimate rather than a placeholder
