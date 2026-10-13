# Finding codes

Use these exact codes in the `what` column of `findings.csv`. Twenty-five are listed. **Not all
describe problems that exist in this data.** Each code you claim that is not present costs one raw
point (raw points are scaled into the 30-point Defect Detection score).

`where` is required — semicolon-separated market names, or a column name for dataset-wide
issues. A finding with no `where` scores zero and counts as a false alarm.

For each finding your `where` list is compared to the markets where the problem is genuinely
real. Several of these patterns appear in markets where they are entirely legitimate. Check the
`Demand Strategy`, `Regulatory Pathway`, `Supply Route` and `Site Role` columns before listing
a market.

| Code | What it would mean |
|---|---|
| `APPROVAL_BEFORE_SUBMISSION` | An approval date earlier than the submission date for the same row |
| `APPROVAL_TARGET_NOT_ACTUAL` | A target approval date has already passed while the actual approval date is still blank, and the target is being treated as if approval happened |
| `BLANK_TREATED_AS_PASS` | A readiness field is blank rather than "No", and the blank is being counted as satisfied |
| `COUNTRY_NAME_WHITESPACE` | A market name carries leading or trailing whitespace, splitting it into two entities when grouped |
| `CURRENCY_UNIT_MISMATCH` | Monetary values recorded in inconsistent currencies or units |
| `DATE_MOVED_WITHOUT_RECORD` | A market's expected shipment date moves between extracts with no entry in the Shipment Date Change Log |
| `DATE_PASSED_NO_REPLAN` | A committed date has passed with no revised date submitted |
| `DATE_STORED_AS_NUMBER` | A date column stored as a serial number, loading as an integer rather than a date |
| `DEMAND_LOADED_TOO_LATE` | Demand reached the planning system with less time remaining than the site's lead time requires |
| `DEMAND_NEVER_LOADED` | Demand was never loaded into the planning system at all |
| `DUPLICATE_ROW` | The same market and pack size appears more than once, with conflicting values |
| `FLAG_YES_BUT_NO_DATE` | A readiness flag says "Yes" while its corresponding date field is blank |
| `NEGATIVE_QUANTITY` | A quantity or volume recorded as a negative number |
| `PLACEHOLDER_DATE_VALUE` | A date field filled with a default or placeholder rather than a real value |
| `PLANT_CAPACITY_EXCEEDED` | The markets assigned to a site require more units than the site can produce in the period they need them |
| `ROLLUP_ANY_NOT_ALL` | A market is reported as ready when only some of its pack sizes qualify |
| `ROW_COUNT_INCONSISTENT` | Markets carry different numbers of rows without explanation |
| `SETUP_DATE_AFTER_SHIPMENT` | A plant or warehouse setup date falls after the expected shipment date |
| `SHIPMENT_BEFORE_APPROVAL` | An expected or actual shipment date falls before the approval date |
| `SHIPMENT_DATE_MISSING` | An actual shipment date is absent where one should be recorded |
| `SKU_NOT_IN_REFERENCE` | A pack code appears in the tracker but not in the pack reference tab |
| `STARTING_DOSE_UNAVAILABLE` | The initiation dose is unavailable, so the market cannot begin treating patients |
| `STATUS_INVALID_ENTRY` | A status field contains a value that is not a real status |
| `STATUS_VALUE_DRIFT` | The same status recorded with inconsistent spelling or casing |
| `TIMEZONE_OFFSET_DRIFT` | Timestamps shifted by a timezone offset, moving dates by a day |
