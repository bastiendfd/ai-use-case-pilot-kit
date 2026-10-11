# Decision record

**How to use this record:** fill in one record for every go/no-go decision on a
use case, including park and reject decisions. Keep it to one page. Copy it to
`examples/<ID>_<short_name>/decision_record.md`, or write a `decision.yaml`
and generate the record with `python -m scoring.build_examples` (scores,
triage and business case figures are then filled in automatically, and the
downside rule is checked). Reviews held under this decision (review-gate
outcomes: continue, rework or stop; later value or park reviews: continue,
scale, fix, stop, remain parked or reopen) are added to section 9 of the same
record. Any other new decision on the same use case (for example pilot → go
with conditions after the pilot gate) gets a new record that links to the old
one (`decision_2.yaml`, `decision_3.yaml` ...); do not overwrite the old one.

> **Fictional examples only.** Records in `examples/` describe the fictional
> company "Northwind Aero Services".

---

## 1. Decision

| Field | Value |
|---|---|
| Use-case ID and title | `<UC-nn> <title>` |
| Decision | `<go / go with conditions / pilot / park / reject>` |
| Decision date | `<YYYY-MM-DD>` |
| Decision makers | `<role: name>` (sponsor, process owner, other members) |
| Decision stage | `<triage / business case / value review>` |

**Meaning of each decision**

| Decision | Meaning |
|---|---|
| **Go** | Build and deploy at the agreed scope. Value tracking starts at go-live. Not allowed when any scenario has a negative 3-year NPV. |
| **Go with conditions** | Build and deploy, with named conditions. Required instead of *go* when any scenario has a negative 3-year NPV: a review gate 3 months after go-live, with stop or rework if adoption or time saved fall to their pessimistic values (section 5). |
| **Pilot** | Time-boxed trial with a limited scope, explicit success criteria and stop criteria. Ends with a new decision record. With a negative scenario, the pilot ends at a 3-month review gate (section 5). |
| **Park** | Not now. The trigger that reopens the case is stated (for example an owner assigned, enough data history, an approved hosting environment). |
| **Reject** | Do not pursue. The reason is stated. Reopened only with a materially new intake. |

## 2. Scores

| Field | Value |
|---|---|
| Gate result | `<pass / park / reject>`, reason: `<...>` |
| Weighted score (out of 100) | `<nn.n>` |
| Rank in the portfolio | `<n> of <N>` |
| Matrix quadrant | `<quick win / strategic bet / fill-in / avoid>` |

| Criterion | Weight | Score (1–5) | Reason for the score |
|---|---|---|---|
| Business value | 30 | | |
| Feasibility | 20 | | |
| Data maturity | 20 | | |
| AI maturity / proof | 10 | | |
| Risk (inverted) | 10 | | |
| Strategic fit | 10 | | |

## 3. AI Act category

| Field | Value |
|---|---|
| Screening category | `<not an AI system / minimal / limited (transparency) / high-risk / prohibited>` |
| Main reason and article reference | `<e.g. Annex III point ... / Article 50(...)>` |
| Legal/compliance review | `<not required / requested on YYYY-MM-DD / confirmed by role on YYYY-MM-DD>` |
| Obligations carried into the project | `<e.g. transparency notice, human oversight, logging>` |

The screening category is not legal advice. Any category other than "minimal
risk", and any borderline case, needs confirmation by legal or compliance.

## 4. Business case summary

| Field | Pessimistic | Base | Optimistic |
|---|---|---|---|
| Annual benefit (€) | | | |
| One-off cost (€) | | | |
| Annual run cost (€) | | | |
| Payback (months) | | | |
| 3-year NPV (€) | | | |

Link to the business case: `<path>`. Main assumptions and their confidence are
in its assumptions log.

## 5. Downside and review gate

Fill in when the 3-year NPV is negative in any scenario. **Always state the
pessimistic NPV**, even when it is positive.

| Field | Value |
|---|---|
| Pessimistic 3-year NPV | `<€>` |
| Scenarios with a negative NPV | `<none / pessimistic / ...>` |
| Review gate date | `<go-live or pilot start + 3 months>` |

| Trigger | How it is measured at the gate | Base plan | Stop or rework if | NPV if only this input is pessimistic |
|---|---|---|---|---|
| Time saved | `<e.g. time study on 50 transactions, same method as the baseline>` | `<minutes saved>` | `<at or below the pessimistic value>` | `<€>` |
| Adoption | `<e.g. share of volume the tool can process in month 3>` | `<%>` | `<at or below the pessimistic value>` | `<€>` |

At the gate: if no trigger is reached, the case continues to the standard value
review. If a trigger is reached, the sponsor decides to **stop**, or to
**rework**. A rework is allowed only if the business case, re-run on the
measured values with the expected effect and cost of the rework actions, has a
positive NPV; otherwise the case stops. Record the outcome in section 9.

Measure adoption on what the steady value means (for example the share of
volume the tool can process), not against the ramp-up plan, which is lower by
design.

## 6. Key risks and mitigations

| Risk | Likelihood (L/M/H) | Impact (L/M/H) | Mitigation | Owner |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## 7. Conditions attached

List the conditions that must hold for the decision to stand. For a pilot,
include success criteria and stop criteria with numbers.

- `<condition 1, e.g. "Extraction accuracy ≥ 95% on a 500-note test sample before go-live">`
- `<condition 2, e.g. "Baseline handling time measured over 4 weeks before the pilot">`
- `<condition 3>`

## 8. Review

| Field | Value |
|---|---|
| Review date | `<YYYY-MM-DD>` |
| What will be reviewed | `<e.g. realised vs. planned value, adoption, incidents>` |
| Reopening trigger (park only) | `<e.g. "data owner assigned", "24 months of demand history available">` |

## 9. Review history

Every review held under this decision, in date order, then the status on the
date the record is read. No review due may be missing.

**Review gates** (only when section 5 sets a review gate). One block per gate held.

| Trigger | Stop or rework if | Measured | Reached? |
|---|---|---|---|
| `<trigger>` | `<threshold from section 5>` | `<measured value>` | `<yes / no>` |

- 3-year NPV re-run on the measured values: `<€>`.
- Rework only: re-run with the rework plan and its cost: `<€>` (must be positive).
- Gate decision: `<continue / rework / stop>`, with the reason.
- Rework only: actions (action, owner, due date) and the next gate date (within 3 months).
- Continue only: the next review date (value review).

**Other reviews** (value reviews after go-live, park reviews).

| Date | Review | Outcome | What was found | Next review |
|---|---|---|---|---|
| `<YYYY-MM-DD>` | `<value review / park review>` | `<continue / scale / fix / stop / remain parked / reopen>` | `<one or two sentences>` | `<YYYY-MM-DD, or none after stop or reopen>` |

**Status as of `<YYYY-MM-DD>`:** `<next review due on ... / stopped on ... / superseded on ... by ...>`
