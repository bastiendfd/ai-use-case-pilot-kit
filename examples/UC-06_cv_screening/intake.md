# Intake form: UC-06 Ranking of job applicants from their CVs

> **Fictional example.** "Northwind Aero Services" is a fictional MRO and
> spare-parts company. All names and figures are invented for illustration.

Template: [`templates/intake_form.md`](../../templates/intake_form.md).

## 1. Identification

| Field | Answer |
|---|---|
| Use-case ID | UC-06 |
| Title | Ranking of job applicants from their CVs |
| Business function | Human resources |
| Process name | Recruitment: application screening |
| Process owner | Head of Talent Acquisition (fictional) |

## 2. Problem statement

| Field | Answer |
|---|---|
| What goes wrong today | Recruiters read every CV against the job requirements. In peak periods, screening takes several days and good candidates accept other offers. |
| How often | About 800 applications per month. |
| Measurable cost | About 80 hours per month (800 × 6 minutes). The cost of lost candidates is not measured. |

## 3. Current process

| Field | Answer |
|---|---|
| Steps | 1. Application arrives in the applicant tracking system. 2. Recruiter reads the CV. 3. Shortlists or rejects. 4. Hiring manager reviews the shortlist. |
| Volume per month | About 800 applications. |
| Handling time | About 6 minutes per application. |
| Error rate | Not measured. |

## 4. Proposed AI solution

| Field | Answer |
|---|---|
| Solution in plain words | A model scores each CV against the job requirements and ranks the applicants. The recruiter starts from the ranking but still reviews every CV. |
| AI technique family | Classification / ranking |

## 5. Users and affected people

| Field | Answer |
|---|---|
| Users | 4 recruiters. |
| Affected people | **Job applicants.** |
| Does the system make or support decisions about people? | **Yes.** It supports the selection of applicants (recruitment and selection). |

## 6. Data

| Field | Answer |
|---|---|
| Sources | CVs and job descriptions in the applicant tracking system. |
| Data owner | HR Systems Lead (fictional) |
| Volume | About 10,000 applications per year. |
| History length | 3 years of applications; past screening decisions are not recorded in a usable form. |
| Quality issues | Many CV formats; past decisions may reflect historical bias. |
| Personal data | **Yes**: CVs contain personal data, sometimes special categories (for example health or nationality). |
| Export-controlled data | No. |

## 7. Expected benefits

| Field | Answer |
|---|---|
| Hours saved | About 40 hours per month (800 × 3 minutes; the recruiter still reviews every CV). Half redeployed to interviews. |
| Errors avoided | None claimed: screening quality is not measured today. |
| Lead time | Shortlists one to two days earlier in peak periods. Not monetised. |
| Quality | Unknown; risk of unfair ranking. |
| Compliance | Adds obligations (see triage). |

## 8. Constraints

| Field | Answer |
|---|---|
| IT and integration | Applicant tracking system interface. |
| Security | Personal data; data protection impact assessment needed. |
| Data residency | EU only. |
| On-premise requirement | No. |

## 9. Human oversight

| Field | Answer |
|---|---|
| Who checks the output | The recruiter reviews every CV and every ranking. |
| What happens if the AI is wrong | A suitable applicant is ranked low and may be overlooked; hard to detect afterwards. |

## 10. Sponsor and decision

| Field | Answer |
|---|---|
| Sponsor | Chief Human Resources Officer (fictional) |
| Requested decision date | 2026-10-20 (portfolio board). |

## Completeness check (portfolio lead)

- [x] The problem statement has a measurable cost.
- [x] The process owner and the data owner are named.
- [x] "Does the system make or support decisions about people?" is answered.
- [x] Personal data and export-controlled data are answered.
- [x] Every benefit has a number and an assumption.
- [x] Human oversight is described.
