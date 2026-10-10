# Decision record

**How to use this record:** fill in one record for every go/no-go decision on a
use case, including park and reject decisions. Keep it to one page. Copy it to
`examples/<ID>_<short_name>/decision_record.md`. A new decision on the same use
case (for example at a value review) gets a new record; do not overwrite the
old one.

> **Fictional examples only.** Records in `examples/` describe the fictional
> company "Northwind Aero Services".

---

## 1. Decision

| Field | Value |
|---|---|
| Use-case ID and title | `<UC-nn> <title>` |
| Decision | `<go / pilot / park / reject>` |
| Decision date | `<YYYY-MM-DD>` |
| Decision makers | `<role: name>` (sponsor, process owner, other members) |
| Decision stage | `<triage / business case / value review>` |

**Meaning of each decision**

| Decision | Meaning |
|---|---|
| **Go** | Build and deploy at the agreed scope. Value tracking starts at go-live. |
| **Pilot** | Time-boxed trial with a limited scope, explicit success criteria and stop criteria. Ends with a new decision record. |
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

## 5. Key risks and mitigations

| Risk | Likelihood (L/M/H) | Impact (L/M/H) | Mitigation | Owner |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## 6. Conditions attached

List the conditions that must hold for the decision to stand. For a pilot,
include success criteria and stop criteria with numbers.

- `<condition 1, e.g. "Extraction accuracy ≥ 95% on a 500-note test sample before go-live">`
- `<condition 2, e.g. "Baseline handling time measured over 4 weeks before the pilot">`
- `<condition 3>`

## 7. Review

| Field | Value |
|---|---|
| Review date | `<YYYY-MM-DD>` |
| What will be reviewed | `<e.g. realised vs. planned value, adoption, incidents>` |
| Reopening trigger (park only) | `<e.g. "data owner assigned", "24 months of demand history available">` |
