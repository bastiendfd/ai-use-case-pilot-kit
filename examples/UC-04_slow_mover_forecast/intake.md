# Intake form: UC-04 Demand forecast for slow-moving spare parts

> **Fictional example.** "Northwind Aero Services" is a fictional MRO and
> spare-parts company. All names and figures are invented for illustration.

Template: [`templates/intake_form.md`](../../templates/intake_form.md).

## 1. Identification

| Field | Answer |
|---|---|
| Use-case ID | UC-04 |
| Title | Demand forecast for slow-moving spare parts |
| Business function | Supply chain |
| Process name | Monthly materials planning for slow movers |
| Process owner | Head of Materials Planning (fictional) |

## 2. Problem statement

| Field | Answer |
|---|---|
| What goes wrong today | Reorder points for slow-moving parts are set by judgement. Some parts run out and must be expedited; others sit in stock for years. |
| How often | 2,500 slow-moving part numbers planned each month; about 50 stock-outs per month (2%). |
| Measurable cost | About €50,000 per month in expedite freight and late-delivery penalties (50 × €1,000), plus 125 planner hours per month. Excess stock is not quantified. |

## 3. Current process

| Field | Answer |
|---|---|
| Steps | 1. Planner reviews the demand history of each part. 2. Sets or confirms the reorder point. 3. Releases purchase proposals. |
| Volume per month | 2,500 part numbers. |
| Handling time | About 3 minutes per part number. |
| Error rate | About 2% of part numbers run out each month. |

## 4. Proposed AI solution

| Field | Answer |
|---|---|
| Solution in plain words | A forecasting model for intermittent demand proposes a reorder point for each part. The planner reviews and accepts or overrides it. |
| AI technique family | Forecasting |

## 5. Users and affected people

| Field | Answer |
|---|---|
| Users | 5 materials planners. |
| Affected people | Customers indirectly (fewer delays). No individuals are assessed. |
| Does the system make or support decisions about people? | No. |

## 6. Data

| Field | Answer |
|---|---|
| Sources | Demand and stock movements in the ERP; supplier lead times. |
| Data owner | ERP Master Data Lead (fictional) |
| Volume | About 12,000 slow-moving part numbers, 2,500 planned per month. |
| History length | **Only 14 months of clean history since the ERP migration.** Older history exists in the old system but was not migrated cleanly. |
| Quality issues | Short history; demand for slow movers is intermittent (many zero months); lead times are incomplete for 15% of suppliers. |
| Personal data | No. |
| Export-controlled data | No (civil parts; confirmed by the export-control officer). |

## 7. Expected benefits

| Field | Answer |
|---|---|
| Hours saved | About 42 hours per month (2,500 × 1 minute); half redeployed to supplier follow-up. |
| Errors avoided | Stock-outs from 2.0% to 1.6%: about 10 per month × €1,000. |
| Lead time | Fewer customer delays from missing parts. |
| Quality | Not applicable. |
| Compliance | Not applicable. Lower excess stock is likely but **not counted** (the model has no inventory term). |

## 8. Constraints

| Field | Answer |
|---|---|
| IT and integration | Forecasting module with the ERP's planning interface. |
| Security | Internal data. |
| Data residency | EU only. |
| On-premise requirement | No. |

## 9. Human oversight

| Field | Answer |
|---|---|
| Who checks the output | The planner reviews every proposed reorder point. |
| What happens if the AI is wrong | Too low a reorder point leads to a stock-out; too high to excess stock. Both are visible in standard reports. |

## 10. Sponsor and decision

| Field | Answer |
|---|---|
| Sponsor | Director of Supply Chain (fictional) |
| Requested decision date | 2026-10-20 (portfolio board). |

## Completeness check (portfolio lead)

- [x] The problem statement has a measurable cost.
- [x] The process owner and the data owner are named.
- [x] "Does the system make or support decisions about people?" is answered.
- [x] Personal data and export-controlled data are answered.
- [x] Every benefit has a number and an assumption.
- [x] Human oversight is described.
