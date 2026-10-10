# Intake form: UC-05 Internal policy Q&A assistant on an approved language model

> **Fictional example.** "Northwind Aero Services" is a fictional MRO and
> spare-parts company. All names and figures are invented for illustration.

Template: [`templates/intake_form.md`](../../templates/intake_form.md).

## 1. Identification

| Field | Answer |
|---|---|
| Use-case ID | UC-05 |
| Title | Internal policy Q&A assistant on an approved language model |
| Business function | Quality and compliance |
| Process name | Access to internal policies and procedures |
| Process owner | Head of Quality Management (fictional) |

## 2. Problem statement

| Field | Answer |
|---|---|
| What goes wrong today | Staff struggle to find the current version of a procedure. They search the intranet, read long documents or ask quality, HR or IT. Sometimes an outdated version is applied. |
| How often | About 2,000 policy questions per month across 600 staff (help-desk tickets and intranet search log). |
| Measurable cost | About 500 hours per month (2,000 × 15 minutes), plus about 40 wrongly applied procedures per month at about €200 each (audit findings and rework). |

## 3. Current process

| Field | Answer |
|---|---|
| Steps | 1. Search the intranet or document system. 2. Open and read the procedure. 3. If unclear, open a ticket or ask a colleague. 4. Apply the procedure. |
| Volume per month | About 2,000 questions. |
| Handling time | About 15 minutes per question. |
| Error rate | About 2% of questions lead to a wrongly applied procedure. |

## 4. Proposed AI solution

| Field | Answer |
|---|---|
| Solution in plain words | Staff ask a question in plain language. The assistant finds the relevant paragraphs in the current approved procedures and drafts a short answer that cites them, with a link to the source. Safety-relevant topics return the link only. |
| AI technique family | Generative AI / LLM assistant (retrieval-based), on an open-weight model hosted on-premise. |

## 5. Users and affected people

| Field | Answer |
|---|---|
| Users | 600 staff; pilot with 100 users. |
| Affected people | Staff only. |
| Does the system make or support decisions about people? | No. It answers questions about procedures; it does not assess staff. Questions are not used to evaluate users. |

## 6. Data

| Field | Answer |
|---|---|
| Sources | Approved policies and procedures in the document management system (about 1,200 documents). |
| Data owner | Document Control Lead (fictional) |
| Volume | About 1,200 documents, 15,000 pages. |
| History length | Not relevant; current approved versions only. |
| Quality issues | Old versions and duplicates in some folders; some procedures are scanned images. |
| Personal data | Question logs contain user IDs; kept 30 days for quality checks, then pseudonymised. |
| Export-controlled data | **Yes**: some procedures cover export-control handling. Processing only in the approved on-premise environment. |

## 7. Expected benefits

| Field | Answer |
|---|---|
| Hours saved | About 333 hours per month (2,000 × 10 minutes). Only 25% counted as cash (fewer help-desk tickets for quality and HR); the rest is spread across 600 people. |
| Errors avoided | Wrongly applied procedures from 2.0% to 1.5%: about 10 per month × €200. |
| Lead time | Faster answers. Not monetised. |
| Quality | Current version always cited. |
| Compliance | Fewer audit findings on outdated procedures. |

## 8. Constraints

| Field | Answer |
|---|---|
| IT and integration | Read-only connection to the document system; single sign-on; access rights mirrored. |
| Security | Export-controlled content: no public cloud model or external API. |
| Data residency | On-premise only. |
| On-premise requirement | **Yes**, because of export-controlled content. The approved on-premise environment exists (approved by IT security). |

## 9. Human oversight

| Field | Answer |
|---|---|
| Who checks the output | The user, who sees the cited paragraph; the quality team checks a monthly sample of 50 answers. |
| What happens if the AI is wrong | A wrong answer may lead to a wrongly applied procedure. Mitigated by citations, the link-only rule for safety topics, and audits. |

## 10. Sponsor and decision

| Field | Answer |
|---|---|
| Sponsor | Chief Operating Officer (fictional) |
| Requested decision date | 2026-10-20 (portfolio board). |

## Completeness check (portfolio lead)

- [x] The problem statement has a measurable cost.
- [x] The process owner and the data owner are named.
- [x] "Does the system make or support decisions about people?" is answered.
- [x] Personal data and export-controlled data are answered.
- [x] Every benefit has a number and an assumption.
- [x] Human oversight is described.
