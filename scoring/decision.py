"""Decision records for use cases, built from a decision file and the computed results.

Usage (from the repository root): the records are built for all examples by

    python -m scoring.build_examples

A decision record mixes two kinds of content:
- judgement, written by people in ``decision.yaml``: the decision, the reason
  for each score, risks, conditions and how the review-gate metrics are
  measured;
- facts, computed here so that they cannot drift from the numbers: the scores,
  rank and gate result (scoring/score.py), the AI Act screening category
  (scoring/triage.py) and the business case figures
  (scoring/business_case.py).

Downside rule (see templates/business_case.md): if the 3-year NPV is negative
in any scenario, the case cannot be a plain "go". It can only be approved with
conditions ("go_with_conditions" or "pilot"), with a review gate
REVIEW_GATE_MONTHS months after go-live or pilot start, and stop or rework if
adoption or time saved fall to their pessimistic values. The pessimistic NPV
is shown in the record.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

from scoring import business_case as bc
from scoring.errors import InputError

DECISIONS = {
    "go": "Go",
    "go_with_conditions": "Go with conditions",
    "pilot": "Pilot",
    "park": "Park",
    "reject": "Reject",
}
APPROVING = ("go", "go_with_conditions", "pilot")
LEVELS = ("L", "M", "H")
CATEGORY_LABELS = {
    "not_ai_system": "Not an AI system",
    "excluded": "Excluded (Art. 2(3))",
    "prohibited": "Prohibited",
    "high": "High-risk",
    "limited": "Limited risk (transparency)",
    "minimal": "Minimal risk",
}


def add_months(day: dt.date, months: int) -> dt.date:
    """Same day of the month, ``months`` later (clamped to the month's last day)."""
    year, month = divmod(day.month - 1 + months, 12)
    year, month = day.year + year, month + 1
    for last in (31, 30, 29, 28):
        try:
            return dt.date(year, month, min(day.day, last))
        except ValueError:
            continue
    raise ValueError(day)


def _date(value, field: str, source: str, errors: list[str]) -> dt.date | None:
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        errors.append(f"{source}: '{field}' must be a date (YYYY-MM-DD), got '{value}'.")
        return None


def load_decision(path: Path) -> dict:
    """Read decision.yaml and check the fields that do not depend on the results."""
    path = Path(path)
    if not path.is_file():
        raise InputError([f"Decision file not found: {path}"])
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    errors: list[str] = []
    for field in ("use_case_id", "decision", "decision_date", "decision_makers", "stage",
                  "summary", "score_reasons", "risks", "review"):
        if raw.get(field) in (None, "", [], {}):
            errors.append(f"{path}: '{field}' is required.")
    if raw.get("decision") not in DECISIONS:
        errors.append(f"{path}: 'decision' must be one of {', '.join(DECISIONS)}, got '{raw.get('decision')}'.")
    if raw.get("decision_date"):
        raw["decision_date"] = _date(raw["decision_date"], "decision_date", str(path), errors)
    if raw.get("start_date"):
        raw["start_date"] = _date(raw["start_date"], "start_date", str(path), errors)
    for i, risk in enumerate(raw.get("risks") or [], start=1):
        for field in ("risk", "likelihood", "impact", "mitigation", "owner"):
            if not risk.get(field):
                errors.append(f"{path}: risk {i} needs '{field}'.")
        for field in ("likelihood", "impact"):
            if risk.get(field) and str(risk[field]).upper() not in LEVELS:
                errors.append(f"{path}: risk {i} {field} must be L, M or H.")
    if raw.get("decision") == "park" and not (raw.get("review") or {}).get("reopening_trigger"):
        errors.append(f"{path}: a park decision needs review.reopening_trigger.")
    if errors:
        raise InputError(errors)
    raw["source"] = str(path)
    return raw


def check_decision(decision: dict, ranked_row: dict, downside: dict) -> None:
    """Rules that tie the decision to the computed results."""
    src, kind = decision["source"], decision["decision"]
    errors = []
    gate = ranked_row["gate_result"]
    if gate == "reject" and kind != "reject":
        errors.append(f"{src}: the hard gate rejects this case; the decision must be 'reject'.")
    if gate == "park" and kind not in ("park", "reject"):
        errors.append(f"{src}: the hard gate parks this case; the decision must be 'park' or 'reject'.")
    if downside["negative_scenarios"] and kind == "go":
        errors.append(
            f"{src}: the 3-year NPV is negative in the {', '.join(downside['negative_scenarios'])} scenario "
            f"(pessimistic NPV {bc._eur(downside['pessimistic_npv'])}). A plain 'go' is not allowed: use "
            "'go_with_conditions' or 'pilot' with a review gate.")
    if "base" in downside["negative_scenarios"] and kind in ("go", "go_with_conditions"):
        errors.append(f"{src}: the base case NPV is negative; the case cannot be approved for go-live. "
                      "Rework it, run it as a pilot, or park or reject it.")
    if gate_applies(decision, downside):
        if not decision.get("start_date"):
            errors.append(f"{src}: 'start_date' (go-live or pilot start) is needed to date the review gate.")
        metrics = decision.get("gate_metrics") or {}
        missing = [k for k in downside["trigger_inputs"] if not metrics.get(k)]
        if missing:
            errors.append(f"{src}: gate_metrics must say how each trigger is measured: {', '.join(missing)}.")
    if errors:
        raise InputError(errors)


def gate_applies(decision: dict, downside: dict) -> bool:
    """The review gate is required for an approving decision with a negative scenario."""
    return bool(downside["negative_scenarios"]) and decision["decision"] in APPROVING


def gate_date(decision: dict) -> dt.date | None:
    start = decision.get("start_date")
    return add_months(start, bc.REVIEW_GATE_MONTHS) if start else None


def _cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def render_decision_record(decision: dict, ranked_row: dict, n_cases: int, criteria, triage_result,
                           case: bc.CaseInputs, results: dict[str, dict]) -> str:
    """Render the one-page decision record (structure of templates/decision_record.md)."""
    d = bc.downside(case, results)
    check_decision(decision, ranked_row, d)
    kind = decision["decision"]
    gated = gate_applies(decision, d)
    rank = ranked_row.get("rank")
    rank_text = "not ranked (stopped at the hard gate)" if rank is None or str(rank) in ("<NA>", "nan") \
        else f"{int(rank)} of {n_cases}"

    lines = [f"# Decision record: {case.use_case_id} {case.title}", ""]
    if decision.get("fictional", True):
        lines += ["> **Fictional example.** \"Northwind Aero Services\" is a fictional MRO and spare-parts "
                  "company. All names, dates and figures are invented.", ""]
    lines += [
        "Generated by `scoring/build_examples.py` from `decision.yaml` and the computed scores, triage and "
        "business case. Edit `decision.yaml`, not this file.",
        "",
        "## 1. Decision",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Use-case ID and title | {case.use_case_id} {case.title} |",
        f"| Decision | **{DECISIONS[kind]}** |",
        f"| Decision date | {decision['decision_date'].isoformat()} |",
        f"| Decision makers | {'; '.join(decision['decision_makers'])} |",
        f"| Decision stage | {decision['stage']} |",
        "",
        _cell(decision["summary"]),
        "",
        "## 2. Scores",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Gate result | {ranked_row['gate_result']}"
        + (f", reason: {ranked_row['gate_reason']}" if ranked_row.get("gate_reason") else "") + " |",
        f"| Weighted score (out of 100) | {ranked_row['weighted_score']:.1f} |",
        f"| Rank in the portfolio | {rank_text} |",
        f"| Matrix quadrant | {ranked_row['quadrant']} |",
        "",
        "| Criterion | Weight | Score (1–5) | Reason for the score |",
        "|---|---|---|---|",
    ]
    reasons = decision["score_reasons"]
    missing = [c for c in criteria.ids if not reasons.get(c)]
    if missing:
        raise InputError([f"{decision['source']}: score_reasons missing for {', '.join(missing)}."])
    for cid in criteria.ids:
        lines.append(f"| {criteria.names[cid]} | {criteria.weights[cid]:g} | {ranked_row['score_' + cid]} | "
                     f"{_cell(reasons[cid])} |")

    lines += [
        "",
        "## 3. AI Act category",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Screening category | {CATEGORY_LABELS[triage_result.category]} (`{triage_result.category}`) |",
        f"| Main reason and article reference | {_cell(' '.join(triage_result.reasons))} |",
        f"| Legal/compliance review | {_cell(decision.get('legal_review', 'not stated'))} |",
        f"| Obligations carried into the project | {_cell(' '.join(triage_result.obligations))} |",
        "",
        "The screening category is not legal advice. Any category other than \"minimal risk\", and any "
        "borderline case, needs confirmation by legal or compliance. Details: `triage.md`.",
        "",
        "## 4. Business case summary",
        "",
        "| Field | Pessimistic | Base | Optimistic |",
        "|---|---|---|---|",
    ]

    def row(label, key, fmt=bc._eur):
        cells = ["not within 36 months" if results[sc][key] is None else fmt(results[sc][key])
                 for sc in bc.SCENARIOS]
        return f"| {label} | " + " | ".join(cells) + " |"

    lines += [
        row("Annual benefit (€)", "annual_benefit_steady"),
        row("One-off cost (€)", "one_off_cost"),
        row("Annual run cost (€)", "annual_run_cost"),
        row("Payback (months)", "payback_month", lambda v: f"{v:.0f}"),
        row("3-year NPV (€)", "npv_3y"),
        "",
        "Link to the business case: [`business_case.md`](business_case.md). Main assumptions and their "
        "confidence are in its assumptions log.",
        "",
        "## 5. Downside and review gate",
        "",
    ]
    lines += _gate_section(decision, d, gated)

    lines += ["", "## 6. Key risks and mitigations", "",
              "| Risk | Likelihood (L/M/H) | Impact (L/M/H) | Mitigation | Owner |", "|---|---|---|---|---|"]
    for r in decision["risks"]:
        lines.append(f"| {_cell(r['risk'])} | {str(r['likelihood']).upper()} | {str(r['impact']).upper()} | "
                     f"{_cell(r['mitigation'])} | {_cell(r['owner'])} |")

    conditions = list(decision.get("conditions") or [])
    if gated:
        conditions.insert(0, f"Review gate on {gate_date(decision).isoformat()} ({bc.REVIEW_GATE_MONTHS} months "
                             f"after {'pilot start' if kind == 'pilot' else 'go-live'}): stop or rework if a "
                             "trigger in section 5 is reached.")
    lines += ["", "## 7. Conditions attached", ""]
    lines += [f"- {_cell(c)}" for c in conditions] or ["- None."]

    review = decision["review"]
    review_date = gate_date(decision) if gated else review.get("date")
    lines += [
        "",
        "## 8. Review",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Review date | {review_date.isoformat() if isinstance(review_date, dt.date) else review_date or 'not set'} |",
        f"| What will be reviewed | {_cell(review.get('what', ''))} |",
        f"| Reopening trigger (park only) | {_cell(review.get('reopening_trigger', 'not applicable'))} |",
        "",
    ]
    return "\n".join(lines)


def _gate_section(decision: dict, d: dict, gated: bool) -> list[str]:
    pess = bc._eur(d["pessimistic_npv"])
    if not d["negative_scenarios"]:
        return [f"The 3-year NPV is positive in every scenario (pessimistic NPV: {pess}). The downside rule "
                "adds no review gate; the standard value review in section 8 applies."]
    head = (f"**The 3-year NPV is negative in the {', '.join(d['negative_scenarios'])} scenario"
            f"{'s' if len(d['negative_scenarios']) > 1 else ''}. Pessimistic NPV: {pess}.**")
    if not gated:
        return [head, "",
                f"No review gate now, because the decision is {DECISIONS[decision['decision']].lower()} and nothing "
                "is built. If the case is reopened, the downside rule applies: approval only with conditions, a "
                f"review gate {bc.REVIEW_GATE_MONTHS} months after go-live, and stop or rework if adoption or time "
                "saved fall to their pessimistic values."]
    metrics = decision.get("gate_metrics") or {}
    out = [
        head,
        "",
        f"Because a scenario is negative, the decision carries a review gate on "
        f"**{gate_date(decision).isoformat()}**, {bc.REVIEW_GATE_MONTHS} months after "
        f"{'the pilot start' if decision['decision'] == 'pilot' else 'go-live'} "
        f"({decision['start_date'].isoformat()}).",
        "",
        "| Trigger | How it is measured at the gate | Base plan | Stop or rework if | NPV if only this input is pessimistic |",
        "|---|---|---|---|---|",
    ]
    for r in d["drivers"]:
        if not r["trigger"]:
            continue
        base = (f"{bc.minutes(r['time_saved_base'])} saved per transaction"
                if "time_saved_base" in r else bc._fmt(r["input"], r["base"]))
        out.append(f"| {r['label']} | {_cell(metrics[r['input']])} | {base} | {bc.trigger_text(r)} | "
                   f"{bc._eur(r['npv_if_only_this'])} |")
    monitored = [r for r in d["drivers"] if not r["trigger"]]
    combined = (f"If {'all triggers are' if len(d['trigger_inputs']) > 1 else 'the trigger is'} reached, "
                f"the NPV falls to {bc._eur(d['npv_at_triggers'])}")
    if monitored:
        combined += (f"; if {', '.join(r['label'].lower() for r in monitored)} is also at its pessimistic "
                     f"value (the full pessimistic scenario), to {pess}.")
    else:
        combined += " (the full pessimistic scenario)."
    out += [
        "",
        combined,
        "",
        "**At the gate:** if no trigger is reached, the case continues to the standard value review. If a "
        "trigger is reached, the sponsor decides to **stop**, or to **rework** (named actions, owner, date) and "
        "re-run the business case on the measured values. The case continues only if that re-run has a "
        "positive NPV, recorded in a new decision record.",
    ]
    if monitored:
        out += ["", "Monitored at the gate but not a trigger: "
                + "; ".join(f"{r['label']} (pessimistic {bc._fmt(r['input'], r['pessimistic'])}, NPV if only "
                            f"this input is pessimistic {bc._eur(r['npv_if_only_this'])})" for r in monitored) + "."]
    return out
