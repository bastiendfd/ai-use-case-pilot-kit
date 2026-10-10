# Data

`value_tracking.csv`: **fictional** monthly value tracking for three use
cases of the fictional company "Northwind Aero Services" (UC-01, UC-02,
UC-03), 12 months each, starting in the go-live or pilot start month.

| Column | Meaning |
|---|---|
| `use_case_id` | Use-case ID, as in `examples/use_cases.csv`. |
| `month` | First day of the month (YYYY-MM-01). |
| `planned_benefit_eur` | Monthly benefit of the **original** base business case, including the adoption ramp-up. Not changed after a rework, so the gap stays visible. |
| `realised_benefit_eur` | Monthly benefit measured and validated by controlling, with the same counting rules as the business case (only redeployed hours count as cash). |
| `adoption_rate` | Share of the volume processed with the AI solution. |
| `incidents` | Number of incidents in the month (wrong outputs found downstream, outages). |
| `notes` | What explains the month, in particular any gap to plan and any review gate. |

UC-03 is the under-delivering case: its 3-month review gate fires and leads
to a rework (see `examples/UC-03_work_order_classification/decision_record.md`,
section 9). Charts: `python dashboard/charts.py`.
