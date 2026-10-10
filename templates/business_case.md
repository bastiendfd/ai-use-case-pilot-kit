# Business case template

**How to use this template.** Copy it to `examples/<ID>_<short_name>/business_case.md`,
or generate the filled version from an inputs file:

```bash
python -m scoring.business_case examples/<ID>_<short_name>/business_case_inputs.yaml \
    --md examples/<ID>_<short_name>/business_case.md
```

The workbook [`business_case.xlsx`](business_case.xlsx) implements the same
model with live Excel formulas. Change any input there and the results update.
It is generated from [`business_case_inputs.yaml`](business_case_inputs.yaml)
and holds the fictional UC-01 example.

> **Fictional example values.** The defaults describe UC-01 at "Northwind Aero
> Services", a fictional company. All figures are invented.

---

## Counting rules (read first)

1. **A benefit counts only once.** If the same hours or errors also appear in
   another use case, count them in one case only.
2. **Hours saved are not cash.** They count as cash only if they are
   redeployed to valued work or a cost is avoided (overtime, temporary staff,
   a planned hire). The share counted as cash is an explicit input
   (`share_hours_redeployed`). The rest is shown as "not counted" and stays
   out of the NPV.
3. **Benefits ramp up with adoption.** Nothing starts at 100% on day one.
4. **Run costs are part of the case:** licences, hosting, monitoring,
   support, retraining.
5. **Scenarios change only the three most uncertain inputs.** All other
   inputs stay at their base value.
6. **Every input has a source or reasoning and a confidence level** (low,
   medium, high) in the assumptions log.

---

## 1. Summary

| Result | Pessimistic | Base | Optimistic |
|---|---|---|---|
| Annual benefit at steady adoption | `<€>` | `<€>` | `<€>` |
| One-off cost | `<€>` | `<€>` | `<€>` |
| Annual run cost | `<€>` | `<€>` | `<€>` |
| Payback (months) | `<n>` | `<n>` | `<n>` |
| 3-year NPV | `<€>` | `<€>` | `<€>` |
| Simple ROI over 3 years | `<%>` | `<%>` | `<%>` |

## 2. Benefit logic

| Benefit | Mechanism | Per month at full adoption |
|---|---|---|
| Hours saved | `<hours>` hours; only the redeployed share is counted as cash | `<€>` |
| Errors avoided | `<n>` errors avoided × cost per error | `<€>` |
| **Total** | Scaled by adoption: `<initial %>` during the ramp-up, then `<steady %>` | `<€>` |

Not counted: the value of saved hours that are not redeployed (for information
only).

## 3. Inputs and assumptions log

| Input | Base value | Unit | Source or reasoning | Confidence |
|---|---|---|---|---|
| Transactions per month | | | | |
| Handling time per transaction today | | minutes | | |
| Handling time per transaction with the AI solution | | minutes | | |
| Fully loaded cost per hour | | EUR / hour | State the assumption, e.g. €70/hour (fictional). | |
| Share of saved hours redeployed or avoiding a cost | | 0–1 | Name where the time goes. | |
| Error rate today | | share | | |
| Error rate with the AI solution | | share | | |
| Cost per error | | EUR | | |
| Licence cost per year | | EUR / year | | |
| Internal build effort | | person-days | | |
| Internal day rate | | EUR / day | | |
| Other one-off costs | | EUR | Training, change management, integration partner. | |
| Run cost per year | | EUR / year | Hosting, maintenance, monitoring. | |
| Adoption during the ramp-up | | share | For example 50% in months 1–3. | |
| Length of the ramp-up | | months | | |
| Adoption after the ramp-up | | share | For example 80%. | |
| Discount rate | | per year | Default 8%; use the rate set by finance. | |

## 4. Scenarios

Pick the three inputs with the lowest confidence and the largest effect on the
result.

| Input | Pessimistic | Base | Optimistic | Why it is uncertain |
|---|---|---|---|---|
| `<input 1>` | | | | |
| `<input 2>` | | | | |
| `<input 3>` | | | | |

---

## How the model calculates

All amounts are per month unless stated. Horizon: 36 months, plus a month 0
for the one-off cost.

| Quantity | Formula |
|---|---|
| Hours saved at full adoption | volume × (minutes before − minutes after) / 60 |
| Cash value of hours | hours saved × share redeployed × hourly cost |
| Value of errors avoided | volume × (error rate before − error rate after) × cost per error |
| Monthly benefit in month *m* | (cash value of hours + value of errors avoided) × adoption(*m*) |
| Adoption(*m*) | initial rate if *m* ≤ ramp-up months, steady rate afterwards |
| One-off cost (month 0) | build days × day rate + other one-off costs |
| Monthly run cost | (licence + run cost per year) / 12 |
| Annual benefit | 12 × monthly benefit at full adoption × steady adoption |
| Payback | first month in which the cumulative net cash flow is ≥ 0 |
| 3-year NPV | Σ net cash flow(*m*) / (1 + discount rate)^(*m* / 12), for *m* = 0 … 36 |
| Simple ROI | (total benefit − total cost) / total cost, over 36 months |

Limits of the model: a single volume (no growth), one benefit mechanism for
time and one for errors, no tax and no inflation. Add lines in the workbook if
your case needs them, and record them in the assumptions log.
