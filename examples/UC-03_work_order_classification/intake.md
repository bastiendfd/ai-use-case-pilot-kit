# Intake form: UC-03 Failure codes suggested from maintenance work-order free text

> **Fictional example.** "Northwind Aero Services" is a fictional MRO and
> spare-parts company. All names and figures are invented for illustration.

Template: [`templates/intake_form.md`](../../templates/intake_form.md).

## 1. Identification

| Field | Answer |
|---|---|
| Use-case ID | UC-03 |
| Title | Failure codes suggested from maintenance work-order free text |
| Business function | Maintenance |
| Process name | Work-order close-out |
| Process owner | Head of Maintenance Planning (fictional) |

## 2. Problem statement

| Field | Answer |
|---|---|
| What goes wrong today | At close-out, planners read the technician's free text and pick one of about 400 failure codes. About one code in five is wrong or too generic, so reliability analyses are noisy and investigations start in the wrong place. |
| How often | 5,000 work orders closed per month; about 20% wrongly coded (audit of 300 work orders). |
| Measurable cost | About 167 hours per month of coding (5,000 × 2 minutes), plus about 1,000 wrong codes per month at an estimated €15 of downstream rework each. |

## 3. Current process

| Field | Answer |
|---|---|
| Steps | 1. Technician writes the finding and the action. 2. Planner reads the text. 3. Planner searches the code list and picks a code. 4. Work order closed. |
| Volume per month | 5,000 work orders. |
| Handling time | About 2 minutes per work order for steps 2–3. |
| Error rate | About 20% wrong or generic codes. |

## 4. Proposed AI solution

| Field | Answer |
|---|---|
| Solution in plain words | A text classifier reads the finding and the action and suggests the most likely failure code with a confidence level. The planner confirms or corrects it. Low-confidence cases show no suggestion. |
| AI technique family | Classification |

## 5. Users and affected people

| Field | Answer |
|---|---|
| Users | 25 maintenance planners. |
| Affected people | Reliability engineers use the codes. No individuals are assessed; the text is not used to evaluate technicians. |
| Does the system make or support decisions about people? | No. |

## 6. Data

| Field | Answer |
|---|---|
| Sources | Closed work orders (free text and final code) in the maintenance system; the failure-code list. |
| Data owner | Maintenance Data Manager (fictional) |
| Volume | About 180,000 closed work orders over 3 years. |
| History length | 3 years. |
| Quality issues | Short texts with abbreviations and two languages; the code list has duplicates and retired codes; 20% of historical labels are wrong, so training labels must be cleaned. |
| Personal data | Technician IDs on work orders; removed before training. |
| Export-controlled data | No (civil aircraft types only; confirmed by the export-control officer). |

## 7. Expected benefits

| Field | Answer |
|---|---|
| Hours saved | 125 hours per month (5,000 × 1.5 minutes). Only 30% counted as cash (reduced planned overtime); the rest is spread across 25 people. |
| Errors avoided | Wrong codes from 20% to 8%: about 600 per month × €15. |
| Lead time | None. |
| Quality | Cleaner reliability statistics and better-targeted investigations. |
| Compliance | Supports the reliability programme's data-quality requirement. |

## 8. Constraints

| Field | Answer |
|---|---|
| IT and integration | Suggestion shown in the existing work-order screen through its extension interface. |
| Security | Internal data; model hosted in-house. |
| Data residency | EU only. |
| On-premise requirement | Preferred (maintenance data stays in-house). |

## 9. Human oversight

| Field | Answer |
|---|---|
| Who checks the output | The planner confirms or corrects every suggested code. |
| What happens if the AI is wrong | A wrong code is stored, as today. Caught by the monthly audit sample; no effect on airworthiness release. |

## 10. Sponsor and decision

| Field | Answer |
|---|---|
| Sponsor | Director of Maintenance (fictional) |
| Requested decision date | 2026-10-20 (portfolio board). |

## Completeness check (portfolio lead)

- [x] The problem statement has a measurable cost.
- [x] The process owner and the data owner are named.
- [x] "Does the system make or support decisions about people?" is answered.
- [x] Personal data and export-controlled data are answered.
- [x] Every benefit has a number and an assumption.
- [x] Human oversight is described.
