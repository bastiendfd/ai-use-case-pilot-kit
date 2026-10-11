# Data

`value_tracking.csv`: **fictional** monthly value tracking for the four use
cases of the fictional company "Northwind Aero Services" that started (UC-01,
UC-02, UC-03, UC-05). Each case runs from its go-live or pilot start month to
December 2027, the month of the story's as-of date (31 December 2027, set in
`examples/portfolio.yaml`), or to the month it was stopped. UC-04 (park) and
UC-06 (reject) never started, so they have no rows.

| Column | Meaning |
|---|---|
| `use_case_id` | Use-case ID, as in `examples/use_cases.csv`. |
| `month` | First day of the month (YYYY-MM-01). |
| `planned_benefit_eur` | Monthly benefit of the **original** base business case, including the adoption ramp-up. Not changed after a rework, so the gap stays visible. |
| `realised_benefit_eur` | Monthly benefit measured and validated by controlling, with the same counting rules as the business case (only redeployed hours count as cash). |
| `adoption_rate` | Share of the volume processed with the AI solution. |
| `incidents` | Number of incidents in the month (wrong outputs found downstream, outages). |
| `notes` | What explains the month, in particular any gap to plan and any review gate. |

| Case | Months | Realised vs. plan | Story |
|---|---|---|---|
| UC-01 | Jan–Dec 2027 | 93% | Close to plan. Gate on 2027-04-11 and value review on 2027-07-11: continue. |
| UC-02 | Dec 2026–Dec 2027 | 101% | On plan. Value reviews: continue (June), scale (December). |
| UC-03 | Dec 2026–Dec 2027 | 47% | Under-delivers. Pilot gate fires on 2027-03-01 (rework), passes on 2027-06-01; new decision on 2027-06-10 (go with conditions, `decision_record_2.md`); roll-out gate on 2027-10-01: continue. |
| UC-05 | Jan–Apr 2027 | 46% | Pilot stopped at its gate on 2027-04-11 (adoption 30%, stop threshold 35%). |

`python -m scoring.build_examples` checks that every started case has one row
per month from its start to the as-of (or stop) month. Charts:
`python dashboard/charts.py`.
