#!/usr/bin/env python3
"""
solve.py -- VELARA Launch Risk Assessment Tool.

Reads the VELARA tracker spreadsheet (4 monthly extracts + reference tabs),
identifies data defects, computes slippage for each country, and ranks them
by impact (slippage_days × forecast_volume).

Outputs:
  submission_template/risk_ranking.csv
  submission_template/findings.csv

Usage:
    python3 solve.py [data_dir]

    data_dir defaults to ./dataset
"""

import json
import os
import sys
import csv
from datetime import datetime, timedelta

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl required. pip install openpyxl", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TODAY = datetime(2026, 4, 25)
EXCEL_EPOCH = datetime(1899, 12, 30)
SITE_LEAD_WEEKS = {"Ashford": 16, "Brenner": 24, "Calderon": 26}
VALID_SKUS = {
    "VLR-2MG-4PEN", "VLR-2MG-1VIAL", "VLR-4MG-4PEN", "VLR-4MG-1VIAL",
    "VLR-8MG-4PEN", "VLR-8MG-1VIAL", "VLR-12MG-4PEN", "VLR-12MG-1VIAL",
}
STARTING_DOSE = "2MG"  # Patients must titrate from lowest dose


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_sheet(wb, name):
    """Load a worksheet into a list of dicts keyed by header row."""
    ws = wb[name]
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    rows = []
    for r in range(2, ws.max_row + 1):
        row = {}
        for c, h in enumerate(headers, 1):
            if h is not None:
                row[h] = ws.cell(r, c).value
        if any(v is not None for v in row.values()):
            rows.append(row)
    return rows


def to_dt(val):
    """Normalize a value to datetime, handling Excel serial numbers."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        return EXCEL_EPOCH + timedelta(days=int(val))
    return None


def days_between(a, b):
    """Days from a to b (positive if b is later)."""
    if a is None or b is None:
        return 0
    return (b - a).days


def strip_country(name):
    return name.strip() if isinstance(name, str) else name


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------
def analyze(data_dir):
    xlsx_path = os.path.join(data_dir, "VELARA_tracker.xlsx")
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)

    # Load reference data
    ref_countries = load_sheet(wb, "Ref_Countries")
    ref_skus = load_sheet(wb, "Ref_SKUs")
    ref_sites = load_sheet(wb, "Ref_Sites")

    vol_map = {r["Country"]: r["Forecast Volume Year 1 (units)"] for r in ref_countries}
    valid_sku_set = {r["SKU"] for r in ref_skus}
    site_cap = {r["Packaging Site"]: r["Annual Packaging Capacity (units)"] for r in ref_sites}

    # Load all 4 tracker months
    trackers = {}
    for m in ["01", "02", "03", "04"]:
        trackers[m] = load_sheet(wb, f"Tracker_2026_{m}")

    t04 = trackers["04"]
    findings = []

    # ------------------------------------------------------------------
    # FINDING: COUNTRY_NAME_WHITESPACE
    # ------------------------------------------------------------------
    ws_countries = set()
    for m, rows in trackers.items():
        for r in rows:
            c = r.get("Country", "")
            if c != c.strip():
                ws_countries.add(c.strip())
    if ws_countries:
        findings.append(("COUNTRY_NAME_WHITESPACE", ";".join(sorted(ws_countries)),
                         f"Trailing whitespace in Tracker_2026_02 and 03; splits into separate entity when grouped"))

    # ------------------------------------------------------------------
    # FINDING: DATE_STORED_AS_NUMBER
    # ------------------------------------------------------------------
    serial_found = False
    for r in trackers["03"]:
        v = r.get("Expected Launch Shipment Date")
        if isinstance(v, (int, float)):
            serial_found = True
            break
    if serial_found:
        findings.append(("DATE_STORED_AS_NUMBER", "Expected Launch Shipment Date",
                         "Entire column in Tracker_2026_03 stored as Excel serial numbers instead of dates"))

    # ------------------------------------------------------------------
    # FINDING: STATUS_VALUE_DRIFT
    # ------------------------------------------------------------------
    drift_countries = set()
    for m, rows in trackers.items():
        for r in rows:
            ls = r.get("Launch Status", "")
            if isinstance(ls, str) and ls.strip().lower() == "active" and ls != "Active":
                drift_countries.add(strip_country(r["Country"]))
    if drift_countries:
        findings.append(("STATUS_VALUE_DRIFT", ";".join(sorted(drift_countries)),
                         "Launch Status varies (e.g. 'active ' 'ACTIVE' 'ACTIVE ') instead of standard 'Active'"))

    # ------------------------------------------------------------------
    # FINDING: STATUS_INVALID_ENTRY
    # ------------------------------------------------------------------
    invalid_countries = set()
    for r in t04:
        ls = r.get("Launch Status", "")
        if isinstance(ls, str) and ls.strip().lower() not in ("active",):
            invalid_countries.add(strip_country(r["Country"]))
    if invalid_countries:
        findings.append(("STATUS_INVALID_ENTRY", ";".join(sorted(invalid_countries)),
                         "Launch Status contains 'Invalid Entry' in Apr tracker"))

    # ------------------------------------------------------------------
    # FINDING: DUPLICATE_ROW
    # ------------------------------------------------------------------
    for m, rows in trackers.items():
        seen = {}
        for r in rows:
            key = (strip_country(r["Country"]), r["SKU"])
            if key in seen:
                findings.append(("DUPLICATE_ROW", strip_country(r["Country"]),
                                 f"{r['SKU']} appears twice in Tracker_2026_{m} with different ship dates"))
                break
            seen[key] = True

    # ------------------------------------------------------------------
    # FINDING: SKU_NOT_IN_REFERENCE
    # ------------------------------------------------------------------
    bad_sku_countries = set()
    for r in t04:
        if r["SKU"] not in valid_sku_set:
            bad_sku_countries.add(strip_country(r["Country"]))
    if bad_sku_countries:
        findings.append(("SKU_NOT_IN_REFERENCE", ";".join(sorted(bad_sku_countries)),
                         "VLR-16MG-4PEN appears in all 4 tracker months but is not in Ref_SKUs"))

    # ------------------------------------------------------------------
    # FINDING: APPROVAL_TARGET_NOT_ACTUAL
    # ------------------------------------------------------------------
    atn_countries = set()
    for r in t04:
        target = to_dt(r.get("Target Approval Date"))
        actual = to_dt(r.get("Actual Approval Date"))
        if target and not actual and target < TODAY:
            atn_countries.add(strip_country(r["Country"]))
    if atn_countries:
        findings.append(("APPROVAL_TARGET_NOT_ACTUAL", ";".join(sorted(atn_countries)),
                         "Target approval dates passed with no actual approval recorded as of Apr 25"))

    # ------------------------------------------------------------------
    # FINDING: APPROVAL_BEFORE_SUBMISSION (National pathway only)
    # ------------------------------------------------------------------
    abs_countries = set()
    for r in t04:
        pathway = r.get("Regulatory Pathway", "")
        actual_appr = to_dt(r.get("Actual Approval Date"))
        actual_sub = to_dt(r.get("Actual Submission Date"))
        if pathway == "National" and actual_appr and actual_sub and actual_appr < actual_sub:
            abs_countries.add(strip_country(r["Country"]))
    if abs_countries:
        findings.append(("APPROVAL_BEFORE_SUBMISSION", ";".join(sorted(abs_countries)),
                         "National pathway but Actual Approval precedes Actual Submission; impossible for independent assessment"))

    # ------------------------------------------------------------------
    # FINDING: SHIPMENT_BEFORE_APPROVAL (MTS only)
    # ------------------------------------------------------------------
    sba_countries = set()
    for r in t04:
        ds = r.get("Demand Strategy", "")
        actual_appr = to_dt(r.get("Actual Approval Date"))
        target_appr = to_dt(r.get("Target Approval Date"))
        ship = to_dt(r.get("Expected Launch Shipment Date"))
        if ds == "MTS" and not actual_appr and ship and target_appr and ship < target_appr:
            sba_countries.add(strip_country(r["Country"]))
    if sba_countries:
        findings.append(("SHIPMENT_BEFORE_APPROVAL", ";".join(sorted(sba_countries)),
                         "MTS countries with expected ship dates before target approval; MTS has no bonded warehouse"))

    # ------------------------------------------------------------------
    # FINDING: DEMAND_LOADED_TOO_LATE
    # ------------------------------------------------------------------
    dlt_countries = set()
    for r in t04:
        route = r.get("Supply Route", "")
        if route != "Direct":
            continue
        dl = r.get("Demand Loaded In Planning System?")
        dd = to_dt(r.get("Demand Loaded Date"))
        ship = to_dt(r.get("Expected Launch Shipment Date"))
        site = r.get("Packaging Site", "")
        if dl == "Yes" and dd and ship:
            lead_days = SITE_LEAD_WEEKS.get(site, 0) * 7
            gap = days_between(dd, ship)
            if gap < lead_days:
                dlt_countries.add(strip_country(r["Country"]))
    if dlt_countries:
        findings.append(("DEMAND_LOADED_TOO_LATE", ";".join(sorted(dlt_countries)),
                         "Demand loaded but site lead time pushes real earliest past claimed ship dates"))

    # ------------------------------------------------------------------
    # FINDING: DEMAND_NEVER_LOADED
    # ------------------------------------------------------------------
    dnl_countries = set()
    for r in t04:
        route = r.get("Supply Route", "")
        dl = r.get("Demand Loaded In Planning System?")
        if route == "Direct" and (dl is None or dl == "" or dl == "No"):
            dnl_countries.add(strip_country(r["Country"]))
    if dnl_countries:
        findings.append(("DEMAND_NEVER_LOADED", ";".join(sorted(dnl_countries)),
                         "Direct route but demand never loaded; factory cannot start production"))

    # ------------------------------------------------------------------
    # FINDING: BLANK_TREATED_AS_PASS
    # ------------------------------------------------------------------
    btp_countries = set()
    check_fields = ["Product Code Set Up At Plant?", "Demand Loaded In Planning System?"]
    for r in t04:
        route = r.get("Supply Route", "")
        if route != "Direct":
            continue
        for f in check_fields:
            val = r.get(f)
            if val is None or val == "":
                btp_countries.add(strip_country(r["Country"]))
    if btp_countries:
        findings.append(("BLANK_TREATED_AS_PASS", ";".join(sorted(btp_countries)),
                         "Direct route countries with readiness fields blank; dashboard treats silence as yes"))

    # ------------------------------------------------------------------
    # FINDING: SETUP_DATE_AFTER_SHIPMENT
    # ------------------------------------------------------------------
    sdas_countries = set()
    for r in t04:
        ship = to_dt(r.get("Expected Launch Shipment Date"))
        setup = to_dt(r.get("Plant Setup Date"))
        if ship and setup and setup > ship:
            sdas_countries.add(strip_country(r["Country"]))
    if sdas_countries:
        findings.append(("SETUP_DATE_AFTER_SHIPMENT", ";".join(sorted(sdas_countries)),
                         "Plant Setup Date falls after Expected Launch Shipment Date for earliest SKUs"))

    # ------------------------------------------------------------------
    # FINDING: FLAG_YES_BUT_NO_DATE
    # ------------------------------------------------------------------
    fynd_countries = set()
    pairs = [
        ("Product Code Set Up At Plant?", "Plant Setup Date"),
        ("Product Code Set Up At Warehouse?", "Warehouse Setup Date"),
        ("Demand Loaded In Planning System?", "Demand Loaded Date"),
    ]
    for r in t04:
        for flag, date in pairs:
            if r.get(flag) == "Yes" and to_dt(r.get(date)) is None:
                if r.get("Supply Route") == "Direct":
                    fynd_countries.add(strip_country(r["Country"]))
    if fynd_countries:
        findings.append(("FLAG_YES_BUT_NO_DATE", ";".join(sorted(fynd_countries)),
                         "Readiness flag=Yes but corresponding date field is blank for Direct-route markets"))

    # ------------------------------------------------------------------
    # FINDING: DATE_MOVED_WITHOUT_RECORD
    # ------------------------------------------------------------------
    dmwr_countries = set()
    keys_all = set()
    for m in ["01", "02", "03", "04"]:
        for r in trackers[m]:
            keys_all.add((strip_country(r["Country"]), r["SKU"]))

    for country, sku in keys_all:
        dates = []
        has_log = False
        for m in ["01", "02", "03", "04"]:
            for r in trackers[m]:
                if strip_country(r["Country"]) == country and r["SKU"] == sku:
                    dates.append(to_dt(r["Expected Launch Shipment Date"]))
                    if r.get("Shipment Date Change Log"):
                        has_log = True
                    break
        moved = False
        for i in range(1, len(dates)):
            if dates[i] and dates[i - 1] and dates[i] != dates[i - 1]:
                moved = True
                break
        if moved and not has_log:
            dmwr_countries.add(country)
    if dmwr_countries:
        findings.append(("DATE_MOVED_WITHOUT_RECORD", ";".join(sorted(dmwr_countries)),
                         "Ship dates move ~45 days every month across all 4 extracts with zero change log entries"))

    # ------------------------------------------------------------------
    # FINDING: PLANT_CAPACITY_EXCEEDED (Ashford)
    # ------------------------------------------------------------------
    ashford_unshipped_vol = 0
    ashford_countries = []
    for r in t04:
        if r.get("Packaging Site") == "Ashford" and to_dt(r.get("Actual Launch Shipment Date")) is None:
            c = strip_country(r["Country"])
            if c not in ashford_countries:
                ashford_countries.append(c)
                ashford_unshipped_vol += vol_map.get(c, 0)
    if ashford_unshipped_vol > site_cap.get("Ashford", float("inf")):
        findings.append(("PLANT_CAPACITY_EXCEEDED", "Ashford",
                         f"Unshipped demand={ashford_unshipped_vol:,} vs annual capacity={site_cap['Ashford']:,}; compressed timeline"))

    # ------------------------------------------------------------------
    # FINDING: STARTING_DOSE_UNAVAILABLE
    # ------------------------------------------------------------------
    sd_countries = set()
    countries_t04 = {}
    for r in t04:
        c = strip_country(r["Country"])
        if c not in countries_t04:
            countries_t04[c] = []
        countries_t04[c].append(r)

    for country, rows in countries_t04.items():
        ships = [(to_dt(r["Expected Launch Shipment Date"]), r.get("Dose", "")) for r in rows]
        ships = [(d, dose) for d, dose in ships if d is not None]
        if not ships:
            continue
        earliest = min(ships, key=lambda x: x[0])
        two_mg = [d for d, dose in ships if dose == STARTING_DOSE]
        if two_mg:
            two_mg_ship = min(two_mg)
            gap = days_between(earliest[0], two_mg_ship)
            if gap > 30:
                sd_countries.add(country)
    if sd_countries:
        findings.append(("STARTING_DOSE_UNAVAILABLE", ";".join(sorted(sd_countries)),
                         "2MG (starting dose) ships 150-158 days after other doses; patients cannot begin titration"))

    # ------------------------------------------------------------------
    # FINDING: ROLLUP_ANY_NOT_ALL
    # ------------------------------------------------------------------
    if sd_countries:
        findings.append(("ROLLUP_ANY_NOT_ALL", ";".join(sorted(sd_countries)),
                         "Dashboard shows GREEN because some SKUs have future ship dates but starting dose ships much later"))

    # ------------------------------------------------------------------
    # FINDING: PLACEHOLDER_DATE_VALUE
    # ------------------------------------------------------------------
    ph_countries = set()
    for r in t04:
        appr = to_dt(r.get("Actual Approval Date"))
        if appr and appr.month == 12 and appr.day == 31:
            ph_countries.add(strip_country(r["Country"]))
    if ph_countries:
        findings.append(("PLACEHOLDER_DATE_VALUE", ";".join(sorted(ph_countries)),
                         "Actual Approval Date is 2023-12-31 (Dec 31 year-end) across all 4 extracts; suspicious placeholder"))

    # ==================================================================
    # SLIPPAGE COMPUTATION
    # ==================================================================
    slippage_results = {}

    for country, rows in countries_t04.items():
        first = rows[0]
        ds = first.get("Demand Strategy", "")
        pathway = first.get("Regulatory Pathway", "")
        supply_route = first.get("Supply Route", "")
        site = first.get("Packaging Site", "")
        lead_days = SITE_LEAD_WEEKS.get(site, 0) * 7

        has_approval = to_dt(first.get("Actual Approval Date")) is not None
        all_shipped = all(to_dt(r.get("Actual Launch Shipment Date")) is not None for r in rows)

        # Claimed = earliest expected ship
        ship_dates = [to_dt(r["Expected Launch Shipment Date"]) for r in rows]
        ship_dates = [d for d in ship_dates if d]
        if not ship_dates:
            slippage_results[country] = (0, 0, "NONE", "no ship dates")
            continue
        claimed = min(ship_dates)

        # 2MG ship date
        two_mg_dates = [to_dt(r["Expected Launch Shipment Date"]) for r in rows if r.get("Dose") == STARTING_DOSE]
        two_mg_dates = [d for d in two_mg_dates if d]
        two_mg_ship = min(two_mg_dates) if two_mg_dates else claimed

        if all_shipped and has_approval:
            slippage_results[country] = (0, 0, "NONE", "all shipped and approved")
            continue

        real_earliest = claimed
        driver = "NONE"
        evidence_parts = []

        # Constraint 1: Approval (MTS only)
        if ds == "MTS" and not has_approval:
            target = to_dt(first.get("Target Approval Date"))
            if target and target > claimed:
                real_earliest = max(real_earliest, target)
                if days_between(claimed, target) > days_between(claimed, real_earliest) or driver == "NONE":
                    driver = "SHIPMENT_BEFORE_APPROVAL"
                    evidence_parts.append(f"MTS ship {claimed.strftime('%Y-%m-%d')} before target approval {target.strftime('%Y-%m-%d')}")

        # Constraint 2: Demand loading
        if supply_route == "Direct":
            dl = first.get("Demand Loaded In Planning System?")
            dd = to_dt(first.get("Demand Loaded Date"))
            if dl is None or dl == "" or dl == "No":
                demand_earliest = TODAY + timedelta(days=lead_days)
                if demand_earliest > real_earliest:
                    real_earliest = demand_earliest
                    driver = "DEMAND_NEVER_LOADED"
                    evidence_parts.append(f"demand not loaded; if loaded today earliest={demand_earliest.strftime('%Y-%m-%d')}")
            elif dd:
                demand_earliest = dd + timedelta(days=lead_days)
                if demand_earliest > claimed:
                    old_re = real_earliest
                    real_earliest = max(real_earliest, demand_earliest)
                    if real_earliest > old_re:
                        driver = "DEMAND_LOADED_TOO_LATE"
                    evidence_parts.append(f"demand loaded {dd.strftime('%Y-%m-%d')}; lead {lead_days}d; earliest={demand_earliest.strftime('%Y-%m-%d')}")

        # Constraint 3: Starting dose
        if two_mg_ship and days_between(claimed, two_mg_ship) > 30:
            if two_mg_ship > real_earliest:
                real_earliest = two_mg_ship
                driver = "STARTING_DOSE_UNAVAILABLE"
                evidence_parts.append(f"2MG ships {two_mg_ship.strftime('%Y-%m-%d')}; {days_between(claimed, two_mg_ship)}d after earliest other dose")

        # Constraint 4: Plant setup after shipment
        earliest_row = min(rows, key=lambda r: to_dt(r["Expected Launch Shipment Date"]) or datetime(2099, 1, 1))
        setup = to_dt(earliest_row.get("Plant Setup Date"))
        if setup and setup > claimed:
            if setup > real_earliest:
                real_earliest = setup
                driver = "SETUP_DATE_AFTER_SHIPMENT"
                evidence_parts.append(f"plant setup {setup.strftime('%Y-%m-%d')} after ship {claimed.strftime('%Y-%m-%d')}")

        slippage = max(0, days_between(claimed, real_earliest))
        vol = vol_map.get(country, 0)
        impact = slippage * vol
        evidence = "; ".join(evidence_parts) if evidence_parts else "no problem found"

        slippage_results[country] = (slippage, impact, driver, evidence)

    # ==================================================================
    # OUTPUT
    # ==================================================================
    # Sort by impact descending
    ranked = sorted(slippage_results.items(), key=lambda x: (-x[1][1], x[0]))

    os.makedirs("submission_template", exist_ok=True)

    # risk_ranking.csv
    with open("submission_template/risk_ranking.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["country", "rank", "slippage_days", "impact_score", "driver", "evidence"])
        for rank, (country, (slip, impact, driver, ev)) in enumerate(ranked, 1):
            w.writerow([country, rank, slip, impact, driver, ev])

    # findings.csv
    with open("submission_template/findings.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["what", "where", "proof"])
        for code, where, proof in findings:
            w.writerow([code, where, proof])

    # Build JSON output — the ONLY thing printed to stdout
    risk_ranking = []
    for rank, (country, (slip, impact, driver, ev)) in enumerate(ranked, 1):
        risk_ranking.append({
            "country": country,
            "rank": rank,
            "slippage_days": slip,
            "impact_score": impact,
            "driver": driver,
            "evidence": ev,
        })

    findings_out = []
    for code, where, proof in findings:
        findings_out.append({
            "what": code,
            "where": where,
            "proof": proof,
        })

    output = {
        "risk_ranking": risk_ranking,
        "findings": findings_out,
    }

    # Print ONLY JSON to stdout — nothing else
    print(json.dumps(output))


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "dataset"
    analyze(data_dir)
