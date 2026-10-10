# Intake form: UC-01 Supplier delivery notes captured into the ERP without manual typing

> **Fictional example.** "Northwind Aero Services" is a fictional MRO and
> spare-parts company. All names and figures are invented for illustration.

Template: [`templates/intake_form.md`](../../templates/intake_form.md).

## 1. Identification

| Field | Answer |
|---|---|
| Use-case ID | UC-01 |
| Title | Supplier delivery notes captured into the ERP without manual typing |
| Business function | Logistics / goods receipt |
| Process name | Goods receipt of purchased spare parts |
| Process owner | Head of Goods Receipt (fictional) |

## 2. Problem statement

| Field | Answer |
|---|---|
| What goes wrong today | Clerks retype part numbers, quantities and batch numbers from paper and PDF delivery notes into the ERP. Typing errors create stock discrepancies. |
| How often | About 3,000 delivery notes per month; about 3% contain at least one keying error. |
| Measurable cost | About 300 hours per month of typing (3,000 notes × 6 minutes), plus about 90 errors per month at an estimated €50 of rework each (€4,500 per month). |

## 3. Current process

| Field | Answer |
|---|---|
| Steps | 1. Receive goods and delivery note. 2. Open the purchase order in the ERP. 3. Type part number, quantity, batch and serial numbers. 4. Post goods receipt. 5. File the note. |
| Volume per month | 3,000 delivery notes from about 400 suppliers; about 60% are PDFs, 40% paper scans. |
| Handling time | 6 minutes per note for steps 2–3. |
| Error rate | About 3%, found at stock counts or when a part is picked. |

## 4. Proposed AI solution

| Field | Answer |
|---|---|
| Solution in plain words | The system reads each delivery note, extracts the fields and pre-fills the goods receipt. The clerk checks and confirms. Low-confidence fields are highlighted. |
| AI technique family | OCR/document AI |

## 5. Users and affected people

| Field | Answer |
|---|---|
| Users | 8 goods-receipt clerks. |
| Affected people | Suppliers indirectly (correct receipt postings). No individuals are assessed. |
| Does the system make or support decisions about people? | No. It processes documents about parts, not about people. |

## 6. Data

| Field | Answer |
|---|---|
| Sources | Delivery notes (PDF and scans) from the shared inbox; purchase orders and part master in the ERP. |
| Data owner | ERP Master Data Lead (fictional) |
| Volume | About 36,000 notes per year. |
| History length | 24 months of PDFs archived; paper notes scanned since last year. |
| Quality issues | About 400 supplier layouts; some scans are skewed or low resolution; handwritten corrections on about 5% of notes. |
| Personal data | Minimal: driver name and signature on some notes. Not used by the solution; to be ignored. |
| Export-controlled data | No. Commercial civil spare parts only (confirmed by the export-control officer). |

## 7. Expected benefits

| Field | Answer |
|---|---|
| Hours saved | 200 hours per month (3,000 notes × 4 minutes saved). Half is redeployed to the backlog of supplier claims; the rest is not counted as cash. |
| Errors avoided | Error rate from 3% to 1%: about 60 errors avoided per month × €50 = €3,000 per month. |
| Lead time | Goods available in stock about half a day earlier on average. Not monetised. |
| Quality | Fewer stock discrepancies at counts. |
| Compliance | More complete batch and serial number capture, which supports parts traceability. |

## 8. Constraints

| Field | Answer |
|---|---|
| IT and integration | Pre-filled goods receipt through the ERP's standard inbound interface. |
| Security | Internal data. Standard supplier security assessment for the SaaS tool. |
| Data residency | EU only. |
| On-premise requirement | No. |

## 9. Human oversight

| Field | Answer |
|---|---|
| Who checks the output | The goods-receipt clerk confirms each pre-filled receipt before posting. |
| What happens if the AI is wrong | A wrong quantity or part number is posted. Caught by the clerk's check, by the three-way match with the invoice, or at stock counts. Same effect as a typing error today. |

## 10. Sponsor and decision

| Field | Answer |
|---|---|
| Sponsor | Director of Supply Chain (fictional) |
| Requested decision date | 2026-10-20 (portfolio board), to align with the ERP release calendar. |

## Completeness check (portfolio lead)

- [x] The problem statement has a measurable cost.
- [x] The process owner and the data owner are named.
- [x] "Does the system make or support decisions about people?" is answered.
- [x] Personal data and export-controlled data are answered.
- [x] Every benefit has a number and an assumption.
- [x] Human oversight is described.
