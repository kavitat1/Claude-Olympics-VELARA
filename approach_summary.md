# VELARA Launch Risk Assessment — Approach Summary

## Overview

The VELARA launch tracker challenge presented a fictional new medicine launching across 30 countries, tracked through four monthly Excel extracts (January–April 2026) plus reference tables for countries, SKUs, and packaging sites. A traffic-light dashboard claimed 29 of 30 markets were GREEN. Our task: determine whether that dashboard was telling the truth, quantify the real slippage for each country, rank them by impact, and surface every data defect we could find.

The short answer is that the dashboard was deeply misleading. Eleven of the 30 countries have genuine slippage, ranging from 18 to 158 days. The United States alone carries an impact score of 505.6 million (158 days × 3.2M forecast volume). Nineteen distinct defects span regulatory sequencing errors, supply chain timing violations, manufacturing capacity constraints, and data quality problems that allowed the dashboard to paint a false picture of readiness.

## Data Cleaning and Preparation

The first phase was normalizing the four monthly tracker extracts into a consistent, comparable form. Three data quality issues had to be resolved before any analysis could begin:

**Date serialization.** The entire Expected Launch Shipment Date column in the March 2026 extract was stored as Excel serial numbers (e.g., 46485 instead of 2027-04-30). We built a normalization function anchored to the Excel epoch (1899-12-30) that detects numeric values and converts them to proper datetime objects.

**Country name whitespace.** Korea appeared with a trailing space in the February and March extracts ("Korea "), which would split it into a separate entity during any grouping operation. All country names were stripped before comparison.

**Status value drift.** Finland's Launch Status varied across extracts — "active " (with trailing space), "ACTIVE", "ACTIVE " — instead of the standard "Active". Ireland had a completely invalid entry ("Invalid Entry") on one SKU row, which is likely why the dashboard flagged it as the single RED market.

## Slippage Methodology

Slippage measures the gap between a country's claimed earliest ship date and the real earliest date that is physically and regulatorily possible. For each country, we computed the real earliest date as the maximum (latest) of four independent constraints:

**1. Regulatory approval (MTS countries only).** Make-to-stock countries cannot ship product before regulatory approval because there is no bonded warehouse mechanism. If the target approval date has not yet passed and falls after the claimed ship date, the approval date becomes the binding constraint. This caught Germany (50 days), Poland (90 days), and Czechia (85 days). Crucially, MTO (make-to-order) countries were excluded from this check — they legitimately ship to bonded warehouses before approval.

**2. Demand loading plus site lead time.** For Direct supply route countries, demand must be loaded into the planning system, and the packaging site then needs its full lead time (Ashford: 16 weeks / 112 days, Brenner: 24 weeks / 168 days, Calderon: 26 weeks / 182 days). If demand was loaded late, we computed the earliest possible ship date as the demand-loaded date plus lead time. If demand was never loaded at all, we assumed it could be loaded "today" (April 25, 2026) and computed accordingly. This identified Brazil (18 days late), Norway (109 days — demand never loaded, Calderon's 182-day lead time), and Finland (85 days — same root cause).

**3. Starting dose availability.** Through data pattern analysis, we determined that 2MG is the required starting dose for patient titration. In most countries, 2MG ships as the earliest or concurrent SKU. However, in the United States, Turkey, and Slovakia, 2MG ships 150–158 days after other doses. Even if higher doses arrive on time, patients cannot begin treatment without the starting dose. This was the binding constraint for the top-risk country (US: 158 days) and the third-ranked (Turkey: 154 days).

**4. Plant setup timing.** If a plant's setup date falls after the claimed ship date, production cannot start. This caught Turkey (secondary driver), Spain (30 days), and Croatia (19 days).

The final slippage is the maximum delay across all four constraints. Impact score equals slippage days multiplied by the country's Year 1 forecast volume from the reference table.

## What Was NOT Flagged (and Why)

Avoiding false positives was as important as finding real defects. Several patterns that look suspicious are actually legitimate under the right conditions:

**MTO shipments before approval.** Make-to-order countries ship product to a bonded warehouse ahead of regulatory approval. This is standard pharmaceutical practice, not a defect. Countries like China (shipped August 2024, approved December 2024) and Italy (shipped February 2024, approved July 2024) follow this pattern correctly.

**Via Hub blank readiness fields.** Countries using the Via Hub supply route do not manage their own plant setup, warehouse setup, or demand loading — the hub handles logistics. Blank readiness fields for these countries (Estonia, Czechia for some fields) are expected, not defects.

**Reliance/Mutual Recognition approval before submission.** For countries using Reliance or Mutual Recognition regulatory pathways, approval can precede the country's own submission because the approval is based on a reference country's assessment. This is legitimate and was not flagged. Only National pathway countries (Peru, Mexico) were flagged for APPROVAL_BEFORE_SUBMISSION, where independent assessment makes this sequence impossible.

**Date drift with achievable final dates.** Japan and Korea show ship dates moving approximately 45 days later in each monthly extract — a pattern worth noting (flagged as DATE_MOVED_WITHOUT_RECORD for the missing change log). However, their current April 2026 claimed dates remain achievable given demand loading timing and lead times, so no slippage was assigned.

## Dashboard Assessment

The dashboard's claim of 29 GREEN and 1 RED (Ireland) is significantly misleading. Ireland's RED status stems from a data quality issue — a single row with Launch Status set to "Invalid Entry" — rather than a genuine operational problem. Meanwhile, at least 10 additional countries that the dashboard marks GREEN have serious unresolved risks: the United States has no regulatory approval with a target date that passed seven weeks ago; Germany plans to ship MTS product two months before its own target approval; Finland and Norway have never loaded demand into the planning system despite needing 26 weeks of Calderon lead time. The dashboard achieves its optimistic picture through two mechanisms: it treats blank readiness fields as passing (BLANK_TREATED_AS_PASS), and it rolls up to GREEN if any SKU appears on track, even when the starting dose — the one SKU patients actually need first — ships months later (ROLLUP_ANY_NOT_ALL).

## Key Findings

The 18 defects cluster into four categories:

**Regulatory sequencing (4 findings):** Approval targets passed without actual dates recorded (US, Turkey, Slovakia); MTS countries claiming ship dates before approval (Germany, Poland, Czechia); National pathway countries with approval before submission (Peru, Mexico). The approval issues are particularly concerning for the US and Turkey, which together represent over 3.4 million units of Year 1 forecast volume.

**Supply chain timing (4 findings):** Demand loaded too late relative to site lead time (Germany, Brazil, Poland); demand never loaded for Direct-route countries (Finland, Norway); readiness fields blank but treated as satisfied (Finland, Norway); readiness flag "Yes" with no corresponding date (Malaysia, Vietnam, US). The Finland and Norway situation is acute: both use Direct supply routes through Calderon (26-week lead time), yet neither has loaded demand. Even if corrected immediately, the earliest possible shipment would be October 24, 2026 — three months after their claimed dates.

**Manufacturing constraints (3 findings):** Plant setup dates after claimed ship dates (Turkey, Spain, Croatia); Ashford site capacity exceeded (4.54M unshipped demand against 5.02M annual capacity, compressed into approximately 5 months); starting dose unavailable for patient initiation (US, Turkey, Slovakia). The starting dose issue is the single highest-impact defect in the dataset, responsible for the top and third-ranked countries by impact score.

**Data quality (7 findings):** Date stored as serial numbers (March extract); country name whitespace (Korea); status value drift (Finland); invalid status entry (Ireland); duplicate rows with conflicting dates (Slovakia in March); phantom SKU not in reference (Norway: VLR-16MG-4PEN); placeholder approval date (Portugal: December 31); shipment dates moving without change log entries (Japan, Korea). While these findings do not directly cause slippage, they erode trust in the tracker as a reliable source and explain how the dashboard could misrepresent readiness so thoroughly.

## Areas of Uncertainty

The ask_lead MCP server referenced in the challenge brief was unavailable in our environment, so the determination that 2MG is the starting dose was inferred from data patterns rather than confirmed through stakeholder interviews. Specifically, in 27 of 30 countries, 2MG ships as the earliest or concurrent dose, while the three outlier countries (US, Turkey, Slovakia) show 2MG shipping 150+ days later — a pattern consistent with a production sequencing error rather than intentional design.

The Ashford capacity finding is qualitative. We identified that unshipped demand (4.54M units) approaches annual capacity (5.02M units) and is compressed into a roughly 5-month production window, but without monthly allocation data, we cannot compute exact per-country delays from the bottleneck.

Portugal's December 31, 2023 approval date may be a legitimate approval rather than a placeholder. The product has already shipped, so this finding has no operational impact but represents a data quality concern.

## Tools and Reproducibility

The analysis is implemented in a single `solve.py` script that reads the VELARA_tracker.xlsx file and programmatically generates both required output CSVs (risk_ranking.csv and findings.csv). The script outputs valid JSON to stdout for automated evaluation. It runs on Python 3.11 with openpyxl as its only dependency. A Dockerfile and velara_config.json are provided following the sample repository convention for automated grading.

Repository: https://github.com/kavitat1/Claude-Olympics-VELARA
