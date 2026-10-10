# Method: from AI idea to measured value

This kit runs every AI idea through the same five steps. Each step ends with an
explicit decision, so weak ideas are stopped early and cheaply, and the ideas
that go ahead carry their evidence with them.

> All names, figures and examples in this repository are **fictional**. They
> describe a made-up company, "Northwind Aero Services", and are not based on
> any real organisation.

```mermaid
flowchart LR
    A[1. Intake] --> B[2. Triage]
    B -->|pass| C[3. Prioritisation]
    B -->|park / reject| X[Decision record]
    C -->|top-ranked| D[4. Business case]
    C -->|below the line| X
    D -->|go / pilot| E[5. Value tracking]
    D -->|park / reject| X
    E -->|scale / fix / stop| X
```

| Step | Question it answers | Main output | Decision at the end |
|---|---|---|---|
| 1. Intake | Is this a real, measurable problem? | Completed intake form | Accept into triage, or return to the submitter |
| 2. Triage | Are there blockers, and what AI Act category applies? | Triage result, gate result | Pass, park or reject |
| 3. Prioritisation | Which cases are worth working on first? | Ranking, value-vs-feasibility matrix | Shortlist for a business case |
| 4. Business case | Does it pay back, and under which assumptions? | Business case, decision record | Go, pilot, park or reject |
| 5. Value tracking | Did it deliver what was planned? | Monthly value tracking, dashboard | Scale, fix or stop |

## Roles

The same roles appear in every step. One person can hold several roles in a
small organisation, but the process owner and the data owner must be named
people, not departments.

| Role | Responsibility in this method |
|---|---|
| **Portfolio lead** | Runs the method, keeps the use-case register, facilitates scoring, keeps decision records. |
| **Process owner** | Owns the business process and its KPIs. Provides volumes, times and error rates. Accountable for the benefit. |
| **Data owner** | Accountable for the data sources: access, quality, history, classification. |
| **IT / security** | Assesses integration, hosting, information security and data classification (including export control). |
| **Legal / compliance** | Confirms the AI Act classification and other legal duties (data protection, works council, export control). |
| **Finance / controlling** | Provides cost rates and the discount rate, checks benefit logic, validates realised value. |
| **Sponsor** | Owns the budget, takes the go/no-go decision, removes blockers. |

---

## Step 1: Intake

**Purpose:** capture each idea in a standard form, so that every idea is
described as a business problem with a measurable cost before anyone discusses
technology.

**Inputs**
- An idea from a business function, in any form (e-mail, workshop note, request).
- Rough figures on the current process: volumes, handling time, error rate.

**Outputs**
- A completed [`templates/intake_form.md`](templates/intake_form.md).
- A use-case ID (`UC-nn`) and one row in the use-case register
  (`examples/use_cases.csv` in this kit).

**Who is involved**
- Submitter and process owner: write the form.
- Data owner: fills in the data section.
- Portfolio lead: checks completeness and assigns the ID.

**Decision at the end:** *accept into triage* or *return to the submitter*. A
form is returned when the problem statement has no measurable cost, when no
process owner is named, or when the "does it decide about people" question is
unanswered.

**Typical failure modes**

| Failure mode | How it shows | Countermeasure |
|---|---|---|
| Solution looking for a problem | The form starts with "use generative AI to…" and the problem statement is vague. | Problem statement and its cost come first; the technique is the last field filled in. |
| Not an AI problem | The issue is a missing ERP field, a bad master-data rule or a missing report. | Ask "would a rule, a report or a configuration change fix this?" If yes, route it to the normal IT backlog. |
| Benefit not quantified | "Saves a lot of time." | Require a number and the assumption behind it, even if rough. Low confidence is acceptable; no number is not. |
| No owner | The process owner field says "Purchasing" instead of a person. | Return the form. Ownerless cases are parked at triage anyway. |
| Duplicates | Two functions submit the same idea with different names. | The portfolio lead checks the register for similar process names and techniques before assigning an ID. |

---

## Step 2: Triage

**Purpose:** find hard blockers before anyone spends time on scoring or a
business case, and give each case a first EU AI Act risk category.

**Inputs**
- The completed intake form.
- The triage checklist ([`triage/triage_checklist.yaml`](triage/triage_checklist.yaml))
  and the decision tree ([`triage/ai_act_triage.md`](triage/ai_act_triage.md)).

**Outputs**
- A screening AI Act category: prohibited, high-risk, limited risk
  (transparency), minimal risk, or not an AI system.
- A gate result: *pass*, *park* or *reject*, with the reason.
- The list of obligations and conditions to carry into the business case
  (for example, a transparency notice or an on-premise hosting requirement).

**Who is involved**
- Portfolio lead: runs the checklist with the process owner.
- Data owner and IT/security: confirm data availability, personal data, export
  control and hosting options.
- Legal/compliance: confirms any category other than "minimal risk", and any
  borderline case.

**Hard gates** (applied before scoring, whatever the expected value):

| Gate | Result |
|---|---|
| The screening category is "prohibited" | **Reject** |
| No data owner or no process owner | **Park** until both are assigned |
| Export-controlled or classified data, and only a public-cloud option exists | **Park** until an approved environment exists |

**Decision at the end:** *pass to prioritisation*, *park* (with the trigger that
reopens the case) or *reject* (with the reason). Parked and rejected cases get a
decision record.

**Typical failure modes**

| Failure mode | How it shows | Countermeasure |
|---|---|---|
| "Internal use, so the AI Act does not apply" | Triage skipped for internal tools. | Deployers have obligations too: AI literacy for all AI systems (Article 4) and specific duties for high-risk systems (Article 26) [1]. Run the checklist for every case. |
| Blanket defence exclusion | "We are a defence company, so we are out of scope." | The exclusion covers systems used *exclusively* for military, defence or national security purposes (Article 2(3)) [1]. It depends on the purpose of the system, not on the company: HR, finance or maintenance tools are civil uses. See the triage file. |
| Triage done once, never revisited | An internal assistant is later used to evaluate employees. | Re-run triage whenever the purpose, the users or the affected people change. |
| Export control found late | The data classification is discovered during the build. | Ask the export-control question at intake and confirm it with IT/security at triage. |
| Legal call made by the project team | A borderline case is self-classified as minimal risk. | The screening result is not legal advice. Borderline and non-minimal cases go to legal/compliance. |

---

## Step 3: Prioritisation

**Purpose:** rank the cases that passed triage, using the same weighted criteria
for all of them, so the shortlist can be explained and challenged.

**Inputs**
- The cases with gate result *pass*.
- The criteria and weights in [`scoring/criteria.yaml`](scoring/criteria.yaml):
  business value, feasibility, data maturity, AI maturity, risk (inverted) and
  strategic fit, each scored from 1 to 5.

**Outputs**
- `outputs/ranking.csv` and `outputs/ranking.md`: the weighted score out of 100,
  the contribution of each criterion and a one-line rationale per case.
- A value-vs-feasibility matrix (quick wins, strategic bets, fill-ins, avoid).
- A sensitivity check: does the top 3 change if a weight moves by ±10 points?

**Who is involved**
- Portfolio lead: facilitates a scoring session.
- Process owner, data owner and IT: score their part of the criteria using the
  level descriptions.
- Sponsor: confirms the weights before scoring and the shortlist after.

**Decision at the end:** the shortlist of cases that get a business case,
usually the top-ranked cases that fit the available capacity.

**Typical failure modes**

| Failure mode | How it shows | Countermeasure |
|---|---|---|
| Submitter scores their own idea | Every case scores 4 or 5 on value. | Score in a group, use the level descriptions, and record the reason for each score. |
| Weights tuned to reach a wanted answer | Weights change after the ranking is seen. | Fix the weights with the sponsor before scoring. Use `--weights` only for an explicit what-if. |
| False precision | 62.4 vs. 61.8 is read as a real difference. | Read the ranking in bands and check the sensitivity output. Close scores are a tie. |
| Value counted twice | The same benefit drives "business value" and "strategic fit". | Strategic fit scores the link to a stated goal, not the size of the benefit. |

---

## Step 4: Business case

**Purpose:** show what a shortlisted case costs, what it returns, when it pays
back, and which assumptions the answer depends on.

**Inputs**
- Volumes, handling times and error rates from the intake form, confirmed by the
  process owner.
- Build, licence and run costs from IT or a vendor.
- Cost rates and the discount rate from finance/controlling.
- Obligations and conditions from triage (they often add cost: human review,
  logging, a transparency notice, an on-premise model).

**Outputs**
- A completed [`templates/business_case.xlsx`](templates/business_case.xlsx) and
  its summary [`templates/business_case.md`](templates/business_case.md):
  annual benefit, one-off cost, run cost, payback, 3-year NPV, simple ROI, and
  pessimistic / base / optimistic scenarios.
- An assumptions log with a source and a confidence level for every input.
- A [`templates/decision_record.md`](templates/decision_record.md).

**Who is involved**
- Process owner: owns the benefit assumptions.
- IT / vendor: owns the cost assumptions.
- Finance/controlling: checks the benefit logic and the rates.
- Sponsor: takes the decision.

**Decision at the end:** *go* (build and deploy), *pilot* (time-boxed, limited
scope, with success and stop criteria), *park* or *reject*. The decision, its
conditions and its review date go into the decision record.

**Typical failure modes**

| Failure mode | How it shows | Countermeasure |
|---|---|---|
| Benefit counted twice | The same saved hours appear in two cases, or as both hours and headcount. | One benefit, one case. Each benefit line names its mechanism (redeployed hours, avoided cost, avoided error). |
| Hours saved treated as cash | 2,000 hours × hourly rate is booked as savings. | Hours are cash only if they are redeployed to valued work or a cost is avoided. The template separates the two. |
| Run cost forgotten | Only the build cost is counted. | Include hosting, licences that scale with users, monitoring, retraining and support. |
| 100% adoption from day one | The benefit starts in full at go-live. | Use an adoption curve (for example 50% in months 1–3, 80% after). |
| Optimistic base case | The base case already assumes everything goes well. | Change only the three most uncertain inputs across scenarios, and decide on the pessimistic case too. |

---

## Step 5: Value tracking

**Purpose:** after go-live, compare planned and realised benefits every month,
and decide whether to scale, fix or stop.

**Inputs**
- The planned monthly benefit and adoption from the business case.
- A baseline measured **before** go-live (volumes, handling time, error rate).
- Monthly actuals: realised benefit, adoption rate, incidents, notes.

**Outputs**
- Monthly rows in `data/value_tracking.csv`.
- Charts and a management dashboard (`dashboard/`): cumulative planned vs.
  realised value, adoption per use case, portfolio overview.
- A review decision, recorded in the decision record.

**Who is involved**
- Process owner: reports the actuals and explains gaps.
- Finance/controlling: validates the realised benefit.
- Portfolio lead: consolidates the portfolio view.
- Sponsor: takes the scale / fix / stop decision at each review.

**Decision at the end of each review:** *scale* (extend to more sites, users or
document types), *fix* (named actions and a new review date) or *stop*.

Suggested review rule, to adjust to your context: after six months, if realised
value is below 50% of plan and there is no credible fix, stop; if it is above
80% of plan and incidents are stable, consider scaling.

**Typical failure modes**

| Failure mode | How it shows | Countermeasure |
|---|---|---|
| No baseline | Nobody can say what the process cost before go-live. | Measure the baseline during the pilot preparation, not after. |
| Activity measured instead of value | "3,000 queries per month" is reported as success. | Track the benefit mechanism from the business case: hours redeployed, errors avoided, cost avoided. |
| Attribution | Another improvement project changes the same KPI. | Note other changes in the `notes` column and agree the attribution with controlling. |
| Sunk-cost reasoning | A failing case continues because money has been spent. | Use the review rule above and decide on future cost and benefit only. |
| Silent degradation | Accuracy drops as suppliers or document formats change. | Track incidents and a quality sample every month, not only adoption. |

---

## Sources

[1] Regulation (EU) 2024/1689 (Artificial Intelligence Act), Official Journal of
the European Union, EUR-Lex: <https://eur-lex.europa.eu/eli/reg/2024/1689/oj>.
Detailed article references for the triage are in
[`triage/ai_act_triage.md`](triage/ai_act_triage.md).

This method is a structured screening and decision aid. It is not legal advice.
Any AI Act classification needs review by legal or compliance.
