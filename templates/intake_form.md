# AI use-case intake form

**How to use this form:** copy it to `examples/<ID>_<short_name>/intake.md`
and replace each *Example* with your own answer. Fill in the problem and the
current process first; describe the AI solution last. Every number needs the
assumption behind it. A rough number with low confidence is acceptable; no
number is not.

> **Fictional example.** The examples in this form describe UC-01 at
> "Northwind Aero Services", a fictional MRO and spare-parts company. All
> names and figures are invented for illustration.

---

## 1. Identification

| Field | Guidance | Example (fictional) |
|---|---|---|
| Use-case ID | Assigned by the portfolio lead, format `UC-nn`. | UC-01 |
| Title | Short, describes the outcome, not the technology. | Supplier delivery notes captured into the ERP without manual typing |
| Business function | The function that owns the process. | Logistics / goods receipt |
| Process name | The process as named in the process map. | Goods receipt of purchased spare parts |
| Process owner | A named person, accountable for the process KPIs. | J. Doe, Head of Goods Receipt (fictional) |

## 2. Problem statement

| Field | Guidance | Example (fictional) |
|---|---|---|
| What goes wrong today | The problem in one or two sentences, without naming a solution. | Clerks retype part numbers, quantities and batch numbers from paper and PDF delivery notes into the ERP. Typing errors create stock discrepancies. |
| How often | Frequency or volume of the problem. | About 3,000 delivery notes per month; about 3% contain at least one keying error. |
| Measurable cost | The cost today, in hours, euros or a KPI, with the assumption. | About 300 hours per month of typing (3,000 notes × 6 minutes), plus about 90 errors per month at an estimated €50 of rework each (€4,500 per month). |

## 3. Current process

| Field | Guidance | Example (fictional) |
|---|---|---|
| Steps | The main steps, in order, as they happen today. | 1. Receive goods and delivery note. 2. Open the purchase order in the ERP. 3. Type part number, quantity, batch and serial numbers. 4. Post goods receipt. 5. File the note. |
| Volume per month | Transactions, documents or cases per month. | 3,000 delivery notes from about 400 suppliers; about 60% are PDFs, 40% paper scans. |
| Handling time | Average time per transaction for the step the AI would change. | 6 minutes per note for steps 2–3. |
| Error rate | Share of transactions with an error, and how errors are found. | About 3%, found at stock counts or when a part is picked. |

## 4. Proposed AI solution

| Field | Guidance | Example (fictional) |
|---|---|---|
| Solution in plain words | What the system does, who sees the output, what changes for the user. | The system reads each delivery note, extracts the fields and pre-fills the goods receipt. The clerk checks and confirms. Low-confidence fields are highlighted. |
| AI technique family | One of: OCR/document AI, classification, forecasting, anomaly detection, generative AI/LLM assistant, optimisation. | OCR/document AI |

## 5. Users and affected people

| Field | Guidance | Example (fictional) |
|---|---|---|
| Users | Who works with the output. | 8 goods-receipt clerks. |
| Affected people | Who is affected by the output without using it (employees, applicants, customers, suppliers). | Suppliers indirectly (correct receipt postings). No individuals are assessed. |
| Does the system make or support decisions about people? | Yes/No, and which decisions. This answer drives the AI Act triage (for example recruitment, performance evaluation, access to services). | No. It processes documents about parts, not about people. |

## 6. Data

| Field | Guidance | Example (fictional) |
|---|---|---|
| Sources | Systems and documents the solution needs. | Delivery notes (PDF and scans) from the shared inbox; purchase orders and part master in the ERP. |
| Data owner | A named person accountable for the data. | A. Smith, ERP Master Data Lead (fictional) |
| Volume | Records or documents available. | About 36,000 notes per year. |
| History length | How far back usable data goes. | 24 months of PDFs archived; paper notes scanned since last year. |
| Quality issues | Known gaps, formats, duplicates, inconsistencies. | About 400 supplier layouts; some scans are skewed or low resolution; handwritten corrections on about 5% of notes. |
| Personal data | Yes/No. If yes, which categories. | Minimal: driver name and signature on some notes. Not used by the solution; to be masked or ignored. |
| Export-controlled data | Yes/No/Unknown. Confirm with IT/security or the export-control officer. | No. Commercial civil spare parts only (to be confirmed by the export-control officer). |

## 7. Expected benefits

Give a number and the assumption behind it for each benefit. Do not count the
same benefit twice. Hours saved are not cash unless the hours are redeployed to
valued work or a cost is avoided.

| Field | Guidance | Example (fictional) |
|---|---|---|
| Hours saved | Hours per month or year, and what the time will be used for. | 200 hours per month (3,000 notes × 4 minutes saved; checking takes 2 minutes instead of 6). Hours redeployed to supplier claims work that is currently backlogged. |
| Errors avoided | Errors avoided and cost per error. | Error rate from 3% to 1%: about 60 errors avoided per month × €50 = €3,000 per month. |
| Lead time | Change in throughput or waiting time. | Goods available in stock about half a day earlier on average. Not monetised. |
| Quality | Effect on quality KPIs. | Fewer stock discrepancies at counts. |
| Compliance | Effect on traceability or audit findings. | More complete batch and serial number capture, which supports parts traceability. |

## 8. Constraints

| Field | Guidance | Example (fictional) |
|---|---|---|
| IT and integration | Systems to integrate with, and how. | Pre-filled goods receipt through the ERP's standard inbound interface. |
| Security | Security requirements and classification of the data. | Internal data. Standard supplier security assessment for any SaaS tool. |
| Data residency | Where the data may be stored and processed. | EU only. |
| On-premise requirement | Yes/No, and why. | No. |

## 9. Human oversight

| Field | Guidance | Example (fictional) |
|---|---|---|
| Who checks the output | The role that reviews the AI output before it takes effect. | The goods-receipt clerk confirms each pre-filled receipt before posting. |
| What happens if the AI is wrong | The effect of an error and how it is caught. | A wrong quantity or part number is posted. Caught by the clerk's check, by the three-way match with the invoice, or at stock counts. Effect is the same as a typing error today. |

## 10. Sponsor and decision

| Field | Guidance | Example (fictional) |
|---|---|---|
| Sponsor | The person who owns the budget and takes the decision. | Director of Supply Chain (fictional) |
| Requested decision date | When a decision is needed, and why. | End of next quarter, to align with the ERP release calendar. |

---

## Completeness check (portfolio lead)

The form enters triage only when all items are ticked.

- [ ] The problem statement has a measurable cost.
- [ ] The process owner and the data owner are named people.
- [ ] "Does the system make or support decisions about people?" is answered.
- [ ] Personal data and export-controlled data are answered (yes, no or unknown).
- [ ] Every benefit has a number and an assumption.
- [ ] Human oversight is described.
