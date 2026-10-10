# Intake form: UC-02 Monthly fleet reliability reports produced automatically, with anomaly flags

> **Fictional example.** "Northwind Aero Services" is a fictional MRO and
> spare-parts company. All names and figures are invented for illustration.

Template: [`templates/intake_form.md`](../../templates/intake_form.md).

## 1. Identification

| Field | Answer |
|---|---|
| Use-case ID | UC-02 |
| Title | Monthly fleet reliability reports produced automatically, with anomaly flags |
| Business function | Engineering / reliability |
| Process name | Monthly customer reliability reporting |
| Process owner | Head of Reliability Engineering (fictional) |

## 2. Problem statement

| Field | Answer |
|---|---|
| What goes wrong today | Engineers build 30 monthly customer reports by hand: extract removals and flight hours, compute failure rates and removals per 1,000 flight hours, copy charts, write comments. Copy errors force re-issues. |
| How often | 30 reports per month; about 10% are re-issued after a correction. |
| Measurable cost | 90 hours per month (30 × 3 hours), plus 3 re-issues per month at about €400 each. |

## 3. Current process

| Field | Answer |
|---|---|
| Steps | 1. Export removals and flight hours. 2. Clean and match them in a spreadsheet. 3. Compute rates per 1,000 flight hours. 4. Update charts. 5. Look for unusual trends by eye. 6. Write comments and send. |
| Volume per month | 30 reports (one per customer fleet under contract). |
| Handling time | About 180 minutes per report. |
| Error rate | About 10% of reports re-issued (re-issue log, 12 months). |

## 4. Proposed AI solution

| Field | Answer |
|---|---|
| Solution in plain words | The BI platform computes the rates and charts automatically every month. An anomaly-detection model flags removal rates that are unusual for the fleet and the part. The engineer reviews the flags, writes the comment and releases the report. |
| AI technique family | Anomaly detection (the rate calculation itself is rule-based). |

## 5. Users and affected people

| Field | Answer |
|---|---|
| Users | 6 reliability engineers. |
| Affected people | Customers receive the reports. No individuals are assessed. |
| Does the system make or support decisions about people? | No. |

## 6. Data

| Field | Answer |
|---|---|
| Sources | Removal records in the maintenance system; flight hours reported monthly by customers. |
| Data owner | Maintenance Data Manager (fictional) |
| Volume | About 1,500 removals per month across all fleets. |
| History length | 6 years of removals; 24 months used to set the anomaly thresholds. |
| Quality issues | One customer sends flight hours late; part-number changes need a mapping table. |
| Personal data | No. |
| Export-controlled data | No (civil fleets only; confirmed by the export-control officer). |

## 7. Expected benefits

| Field | Answer |
|---|---|
| Hours saved | 67.5 hours per month (30 × 135 minutes). 80% redeployed to the backlog of 12 open reliability investigations. |
| Errors avoided | Re-issues from 10% to 3%: about 2 per month × €400. |
| Lead time | Reports issued by working day 5 instead of day 9. Not monetised. |
| Quality | Unusual trends found systematically, not by eye. |
| Compliance | No change. |

## 8. Constraints

| Field | Answer |
|---|---|
| IT and integration | Existing BI platform; read-only access to the maintenance system. |
| Security | Customer data stays in the existing platform. |
| Data residency | EU only (unchanged). |
| On-premise requirement | No. |

## 9. Human oversight

| Field | Answer |
|---|---|
| Who checks the output | The reliability engineer reviews every flag and releases every report. |
| What happens if the AI is wrong | A missed or false flag. False flags cost review time; missed flags are no worse than today's review by eye. |

## 10. Sponsor and decision

| Field | Answer |
|---|---|
| Sponsor | Director of Engineering (fictional) |
| Requested decision date | 2026-10-20 (portfolio board), to go live before the January reporting cycle. |

## Completeness check (portfolio lead)

- [x] The problem statement has a measurable cost.
- [x] The process owner and the data owner are named.
- [x] "Does the system make or support decisions about people?" is answered.
- [x] Personal data and export-controlled data are answered.
- [x] Every benefit has a number and an assumption.
- [x] Human oversight is described.
