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
import re
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
# Portfolio status: the decision of the latest record, or "stopped" when a
# review ended the case.
STATUS_LABELS = {**DECISIONS, "stopped": "Stopped"}
# Colours used for decisions in every chart (colour-blind-safe Okabe-Ito palette).
DECISION_COLOURS = {
    "go": "#009E73",
    "go_with_conditions": "#56B4E9",
    "pilot": "#0072B2",
    "park": "#E69F00",
    "reject": "#D55E00",
    "stopped": "#4D4D4D",
}
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
    raw["gate_reviews"] = _load_gate_reviews(raw, str(path), errors)
    raw["review_log"] = _load_review_log(raw, str(path), errors)
    review = raw.get("review") or {}
    if isinstance(review, dict) and isinstance(review.get("date"), str) and review["date"][:1].isdigit():
        review["date"] = _date(review["date"], "review.date", str(path), errors)
    cost = raw.get("earlier_rework_cost_eur", 0)
    if not _number(cost) or cost < 0:
        errors.append(f"{path}: 'earlier_rework_cost_eur' must be a number of at least 0.")
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


def assess(decision: dict, ranked_row: dict, case: bc.CaseInputs, results: dict[str, dict]) -> dict:
    """Apply every rule to one decision and return what the record and the portfolio need."""
    d = bc.downside(case, results)
    check_decision(decision, ranked_row, d)
    gated = gate_applies(decision, d)
    evaluated = evaluate_gate_reviews(decision, case, d)
    history = review_history(decision, evaluated, gated)
    return {"downside": d, "gated": gated, "evaluated": evaluated, "history": history}


def render_decision_record(decision: dict, ranked_row: dict, n_cases: int, criteria, triage_result,
                           case: bc.CaseInputs, results: dict[str, dict], as_of: dt.date | None = None,
                           previous: dict | None = None, superseded_by: dict | None = None) -> str:
    """Render the one-page decision record (structure of templates/decision_record.md).

    ``previous`` and ``superseded_by`` link records of the same use case:
    {"file": "decision_record.md", "decision": "pilot", "date": date}.
    """
    a = assess(decision, ranked_row, case, results)
    d, gated, evaluated, history = a["downside"], a["gated"], a["evaluated"], a["history"]
    kind = decision["decision"]
    rank = ranked_row.get("rank")
    rank_text = "not ranked (stopped at the hard gate)" if rank is None or str(rank) in ("<NA>", "nan") \
        else f"{int(rank)} of {n_cases}"

    lines = [f"# Decision record: {case.use_case_id} {case.title}", ""]
    if decision.get("fictional", True):
        lines += ["> **Fictional example.** \"Northwind Aero Services\" is a fictional MRO and spare-parts "
                  "company. All names, dates and figures are invented.", ""]
    if superseded_by:
        lines += [f"> **Superseded** on {superseded_by['date'].isoformat()} by "
                  f"[`{superseded_by['file']}`]({superseded_by['file']}) "
                  f"({DECISIONS[superseded_by['decision']]}). Kept as the record of the earlier decision.", ""]
    if previous:
        lines += [f"> **Follows** [`{previous['file']}`]({previous['file']}) "
                  f"({DECISIONS[previous['decision']]}, {previous['date'].isoformat()}).", ""]
    source_name = Path(decision["source"]).name
    lines += [
        f"Generated by `scoring/build_examples.py` from `{source_name}` and the computed scores, triage and "
        f"business case. Edit `{source_name}`, not this file.",
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
    ]
    if evaluated:
        lines.append(f"| Review gate outcomes | {gate_status(decision, evaluated)}; see section 9 |")
    if decision.get("review_log"):
        lines.append(f"| Other reviews | {review_log_status(decision)}; see section 9 |")
    lines += [
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
    ]
    lines += _history_section(decision, evaluated, case, gated, history, as_of, superseded_by)
    lines.append("")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


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
        "trigger is reached, the sponsor decides to **stop**, or to **rework** (named actions, owner, date). A "
        "rework is allowed only if the business case, re-run on the measured values with the expected effect "
        "and cost of the rework, has a positive NPV; otherwise the case stops. Gate outcomes are recorded in "
        "section 9.",
    ]
    if monitored:
        out += ["", "Monitored at the gate but not a trigger: "
                + "; ".join(f"{r['label']} (pessimistic {bc._fmt(r['input'], r['pessimistic'])}, NPV if only "
                            f"this input is pessimistic {bc._eur(r['npv_if_only_this'])})" for r in monitored) + "."]
    return out


# ---------------------------------------------------------------------------
# Review gate outcomes
# ---------------------------------------------------------------------------

GATE_OUTCOMES = {"continue": "Continue", "rework": "Rework", "stop": "Stop"}


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _load_gate_reviews(raw: dict, path: str, errors: list[str]) -> list[dict]:
    """Validate the optional ``gate_reviews`` list of decision.yaml (fields only)."""
    reviews = raw.get("gate_reviews") or []
    if not isinstance(reviews, list):
        errors.append(f"{path}: 'gate_reviews' must be a list.")
        return []
    out = []
    for i, review in enumerate(reviews, start=1):
        tag = f"{path}: gate review {i}"
        if not isinstance(review, dict):
            errors.append(f"{tag} must be a mapping.")
            continue
        review = dict(review)
        review["date"] = _date(review.get("date"), f"gate_reviews[{i}].date", path, errors)
        if review.get("decision") not in GATE_OUTCOMES:
            errors.append(f"{tag}: 'decision' must be one of {', '.join(GATE_OUTCOMES)}.")
        if not review.get("summary"):
            errors.append(f"{tag}: 'summary' is required.")
        measured = review.get("measured")
        if not isinstance(measured, dict) or not measured or not all(_number(v) for v in measured.values()):
            errors.append(f"{tag}: 'measured' must map each trigger input to a measured number.")
        if review.get("next_review") is not None:
            if review.get("decision") != "continue":
                errors.append(f"{tag}: 'next_review' is only used after a continue.")
            review["next_review"] = _date(review["next_review"], f"gate_reviews[{i}].next_review", path, errors)
        if review.get("decision") == "rework":
            actions = review.get("actions") or []
            if not actions:
                errors.append(f"{tag}: a rework needs 'actions' (action, owner, due).")
            for j, action in enumerate(actions, start=1):
                for field in ("action", "owner", "due"):
                    if not (action or {}).get(field):
                        errors.append(f"{tag}: action {j} needs '{field}'.")
            if not review.get("next_gate"):
                errors.append(f"{tag}: a rework needs 'next_gate' (date of the next review gate).")
            else:
                review["next_gate"] = _date(review["next_gate"], f"gate_reviews[{i}].next_gate", path, errors)
            plan = review.get("rework_plan") or {}
            if not isinstance(plan, dict) or not all(_number(v) for v in plan.values()):
                errors.append(f"{tag}: 'rework_plan' must map inputs to the values expected after the rework.")
            review["rework_plan"] = plan if isinstance(plan, dict) else {}
            cost = review.get("rework_cost_eur", 0)
            if not _number(cost) or cost < 0:
                errors.append(f"{tag}: 'rework_cost_eur' must be a number of at least 0.")
            review["rework_cost_eur"] = cost if _number(cost) else 0
        out.append(review)
    return out


def evaluate_gate_reviews(decision: dict, case: bc.CaseInputs, d: dict) -> list[dict]:
    """Evaluate each recorded review gate against the triggers and re-run the business case.

    For each review:
    - a trigger is *hit* when its measured value is at or beyond the
      pessimistic value (the same thresholds as in section 5);
    - ``npv_measured``: the business case re-run with the measured values
      (and the cost of earlier reworks);
    - ``npv_rework`` (rework only): the re-run with the measured values, the
      values expected after the rework actions and the rework cost.

    Rules (raise InputError when broken):
    - a hit trigger means rework or stop; no hit means continue or stop;
    - a rework is allowed only if ``npv_rework`` is positive;
    - the first review is on the gate date; each later review is on the
      ``next_gate`` date of the previous rework; nothing follows a stop or a
      continue.
    The re-runs keep the original 36-month horizon and start date (a
    simplification: the delay caused by a rework is not modelled).
    """
    reviews = decision.get("gate_reviews") or []
    if not reviews:
        return []
    src = decision["source"]
    errors: list[str] = []
    if not gate_applies(decision, d):
        raise InputError([f"{src}: gate_reviews are only allowed when the decision carries a review gate."])
    base = case.values("base")
    expected_date = gate_date(decision)
    extra_cost = float(decision.get("earlier_rework_cost_eur", 0) or 0)
    out = []
    for i, review in enumerate(reviews, start=1):
        tag = f"{src}: gate review {i}"
        if review["date"] != expected_date:
            errors.append(f"{tag}: date is {review['date']}, expected {expected_date} "
                          f"({'the gate date' if i == 1 else 'the next_gate of the previous rework'}).")
        measured = {k: float(v) for k, v in review["measured"].items()}
        unknown = [k for k in measured if k not in case.inputs]
        missing = [k for k in d["trigger_inputs"] if k not in measured]
        if unknown:
            errors.append(f"{tag}: unknown measured input(s): {', '.join(unknown)}.")
        if missing:
            errors.append(f"{tag}: measured value missing for trigger(s): {', '.join(missing)}.")
        if unknown or missing:
            continue
        rows = []
        for r in d["drivers"]:
            if not r["trigger"]:
                continue
            m = measured[r["input"]]
            hit = m >= r["pessimistic"] if r["higher_is_worse"] else m <= r["pessimistic"]
            rows.append(dict(r, measured=m, hit=hit))
        earlier_cost = extra_cost
        values = dict(base, **measured)
        values["other_one_off_eur"] += earlier_cost
        npv_measured = bc.compute(values)["npv_3y"]
        any_hit = any(r["hit"] for r in rows)
        kind = review["decision"]
        npv_rework = None
        if any_hit and kind == "continue":
            errors.append(f"{tag}: a trigger is reached, so the gate decision must be rework or stop.")
        if not any_hit and kind == "rework":
            errors.append(f"{tag}: no trigger is reached, so the gate decision must be continue or stop.")
        if kind == "rework":
            plan = {k: float(v) for k, v in review["rework_plan"].items()}
            bad = [k for k in plan if k not in case.inputs]
            if bad:
                errors.append(f"{tag}: unknown rework_plan input(s): {', '.join(bad)}.")
                continue
            extra_cost += float(review["rework_cost_eur"])
            values = {**base, **measured, **plan}
            values["other_one_off_eur"] += extra_cost
            npv_rework = bc.compute(values)["npv_3y"]
            if npv_rework <= 0:
                errors.append(f"{tag}: the re-run with the rework plan has a negative NPV "
                              f"({bc._eur(npv_rework)}); the rule leaves only stop.")
            if review.get("next_gate") and review["next_gate"] > add_months(review["date"], bc.REVIEW_GATE_MONTHS):
                errors.append(f"{tag}: next_gate must be within {bc.REVIEW_GATE_MONTHS} months of this review.")
            expected_date = review.get("next_gate")
        elif i < len(reviews):
            errors.append(f"{tag}: a '{kind}' closes the gate sequence; no later review is allowed.")
        out.append(dict(review, rows=rows, any_hit=any_hit, npv_measured=npv_measured,
                        npv_rework=npv_rework, earlier_cost=earlier_cost))
    if errors:
        raise InputError(errors)
    return out


def gate_status(decision: dict, evaluated: list[dict]) -> str:
    """One-line status after the review gates, e.g. 'rework (2027-03-01), continue (2027-06-01)'."""
    return ", ".join(f"{r['decision']} ({r['date'].isoformat()})" for r in evaluated)


def _measured_text(row: dict) -> str:
    if "time_saved_base" in row:
        saved = row["time_saved_base"] + row["base"] - row["measured"]
        return f"{bc.minutes(saved)} saved (handling time {bc.minutes(row['measured'])})"
    return bc._fmt(row["input"], row["measured"])


def _gate_outcome_section(decision: dict, evaluated: list[dict], case: bc.CaseInputs) -> list[str]:
    lines = []
    if not evaluated:
        due = gate_date(decision)
        return lines + [f"No review gate recorded yet (due on {due.isoformat()})." if due
                        else "No review gate applies."]
    lines += ["Each gate compares the measured values with the stop or rework thresholds of section 5 and "
              "re-runs the business case on the measured values (same 36-month horizon and start date; the "
              "delay caused by a rework is not modelled).", ""]
    for i, r in enumerate(evaluated, start=1):
        lines += [
            f"### Gate {i}: {r['date'].isoformat()}. Decision: **{GATE_OUTCOMES[r['decision']]}**",
            "",
            "| Trigger | Stop or rework if | Measured | Reached? |",
            "|---|---|---|---|",
        ]
        for row in r["rows"]:
            lines.append(f"| {row['label']} | {bc.trigger_text(row)} | {_measured_text(row)} | "
                         f"{'**yes**' if row['hit'] else 'no'} |")
        cost_note = (f", including {bc._eur(r['earlier_cost'])} of earlier rework cost"
                     if r["earlier_cost"] > 0 else "")
        lines += ["", f"- 3-year NPV re-run on the measured values{cost_note}: **{bc._eur(r['npv_measured'])}**."]
        if r["decision"] == "rework":
            plan = ", ".join(f"{case.inputs[k]['label'].lower()} {bc._fmt(k, float(v))}"
                             for k, v in r["rework_plan"].items())
            lines.append(f"- Re-run with the rework plan ({plan}) and its cost of "
                         f"{bc._eur(r['rework_cost_eur'])}: **{bc._eur(r['npv_rework'])}**. Positive, so a rework "
                         "is allowed; otherwise the rule leaves only stop.")
        lines += ["", _cell(r["summary"]), ""]
        if r["decision"] == "rework":
            lines += ["| Rework action | Owner | Due |", "|---|---|---|"]
            lines += [f"| {_cell(a['action'])} | {_cell(a['owner'])} | {a['due']} |" for a in r["actions"]]
            lines += ["", f"Next review gate: **{r['next_gate'].isoformat()}**, same triggers.", ""]
        if r["decision"] == "continue" and r.get("next_review"):
            lines += [f"Next review: **{r['next_review'].isoformat()}** (value review).", ""]
    return lines


# ---------------------------------------------------------------------------
# Review history: value reviews, park reviews and the as-of check
# ---------------------------------------------------------------------------

REVIEW_OUTCOMES = {
    "continue": "Continue",
    "scale": "Scale",
    "fix": "Fix",
    "stop": "Stop",
    "remain_parked": "Remain parked",
    "reopen": "Reopen",
}
CLOSING_OUTCOMES = ("stop", "reopen")


def _load_review_log(raw: dict, path: str, errors: list[str]) -> list[dict]:
    """Validate the optional ``review_log`` list (value reviews and park reviews)."""
    log = raw.get("review_log") or []
    if not isinstance(log, list):
        errors.append(f"{path}: 'review_log' must be a list.")
        return []
    out = []
    for i, entry in enumerate(log, start=1):
        tag = f"{path}: review {i}"
        if not isinstance(entry, dict):
            errors.append(f"{tag} must be a mapping.")
            continue
        entry = dict(entry)
        entry["date"] = _date(entry.get("date"), f"review_log[{i}].date", path, errors)
        if entry.get("outcome") not in REVIEW_OUTCOMES:
            errors.append(f"{tag}: 'outcome' must be one of {', '.join(REVIEW_OUTCOMES)}.")
        for field in ("type", "summary"):
            if not entry.get(field):
                errors.append(f"{tag}: '{field}' is required.")
        if entry.get("outcome") in CLOSING_OUTCOMES:
            if entry.get("next_review"):
                errors.append(f"{tag}: no 'next_review' after '{entry['outcome']}'.")
        elif not entry.get("next_review"):
            errors.append(f"{tag}: 'next_review' is required after '{entry.get('outcome')}'.")
        else:
            entry["next_review"] = _date(entry["next_review"], f"review_log[{i}].next_review", path, errors)
        out.append(entry)
    return out


def review_log_status(decision: dict) -> str:
    return ", ".join(f"{e['type']}: {e['outcome'].replace('_', ' ')} ({e['date'].isoformat()})"
                     for e in decision.get("review_log") or [])


def review_history(decision: dict, evaluated: list[dict], gated: bool) -> dict:
    """Follow the chain of reviews of one decision and return where it stands.

    The first review is due on the gate date (gated decisions) or on
    ``review.date``. Each review sets the next one: a rework sets
    ``next_gate``, a continue at a gate may set ``next_review``, and each
    entry of ``review_log`` sets ``next_review``. A stop (at a gate or a
    review) or a reopen closes the chain. A reject without a review date is
    closed from the start.

    Returns {"next_due": date | None, "closed": bool, "stopped_on": date | None,
    "last_date": date | None}. Raises InputError if a review is held on
    another date than the one due, or after the chain is closed.
    """
    src = decision["source"]
    errors: list[str] = []
    closed, stopped_on, last_date = False, None, None
    if gated:
        due = gate_date(decision)
        if evaluated:
            last = evaluated[-1]
            last_date = last["date"]
            if last["decision"] == "stop":
                closed, stopped_on, due = True, last["date"], None
            elif last["decision"] == "rework":
                due = last["next_gate"]
            else:
                due = last.get("next_review")
    else:
        review_day = (decision.get("review") or {}).get("date")
        due = review_day if isinstance(review_day, dt.date) else None
        closed = decision["decision"] == "reject" and due is None
    log = decision.get("review_log") or []
    if log and gated and (not evaluated or evaluated[-1]["decision"] != "continue"):
        errors.append(f"{src}: review_log entries can only follow a 'continue' at the review gate.")
    for i, entry in enumerate(log, start=1):
        if closed:
            errors.append(f"{src}: review {i} on {entry['date']} comes after the case was closed.")
            break
        if due is None or entry["date"] != due:
            errors.append(f"{src}: review {i} is dated {entry['date']}, but the review due is "
                          f"{due.isoformat() if due else 'not set (add next_review to the previous review)'}.")
        last_date = entry["date"]
        if entry["outcome"] in CLOSING_OUTCOMES:
            closed, due = True, None
            if entry["outcome"] == "stop":
                stopped_on = entry["date"]
        else:
            due = entry["next_review"]
    if errors:
        raise InputError(errors)
    return {"next_due": due, "closed": closed, "stopped_on": stopped_on, "last_date": last_date}


def portfolio_status(decision: dict, history: dict) -> str:
    """'stopped' if a review ended the case, else the decision."""
    return "stopped" if history["stopped_on"] else decision["decision"]


def check_as_of(decisions: list[dict], histories: list[dict], as_of: dt.date) -> None:
    """No gaps in the story: every review due on or before ``as_of`` is recorded.

    ``decisions`` are the records of one use case in date order; all but the
    last are superseded by the next one.
    """
    errors = []
    for i, (decision, history) in enumerate(zip(decisions, histories)):
        src = decision["source"]
        dates = [decision["decision_date"]] + [r["date"] for r in decision.get("gate_reviews") or []] \
            + [e["date"] for e in decision.get("review_log") or []]
        early = [x for x in dates[1:] if x and x <= decision["decision_date"]]
        if early:
            errors.append(f"{src}: review(s) on {', '.join(map(str, early))} not after the decision date "
                          f"{decision['decision_date']}.")
        late = [x for x in dates if x and x > as_of]
        if late:
            errors.append(f"{src}: dated after the as-of date {as_of}: {', '.join(map(str, late))}.")
        successor = decisions[i + 1] if i + 1 < len(decisions) else None
        if successor:
            if history["last_date"] and history["last_date"] > successor["decision_date"]:
                errors.append(f"{src}: review on {history['last_date']} after the record was superseded on "
                              f"{successor['decision_date']}.")
            if history["next_due"] and history["next_due"] < successor["decision_date"]:
                errors.append(f"{src}: review due on {history['next_due']} is missing; the record was only "
                              f"superseded on {successor['decision_date']}.")
            if history["closed"]:
                errors.append(f"{src}: a closed record cannot be superseded; start a new intake instead.")
        elif not history["closed"]:
            if history["next_due"] is None:
                errors.append(f"{src}: no next review is planned (add next_review to the last review).")
            elif history["next_due"] <= as_of:
                errors.append(f"{src}: the review due on {history['next_due']} is not recorded "
                              f"(as of {as_of}).")
    if errors:
        raise InputError(errors)


def _history_section(decision: dict, evaluated: list[dict], case: bc.CaseInputs, gated: bool, history: dict,
                     as_of: dt.date | None, superseded_by: dict | None) -> list[str]:
    lines = ["", "## 9. Review history", ""]
    if gated:
        lines += _gate_outcome_section(decision, evaluated, case)
    log = decision.get("review_log") or []
    if log:
        if gated:
            lines += ["", "### Value and park reviews"]
        lines += ["", "| Date | Review | Outcome | What was found | Next review |", "|---|---|---|---|---|"]
        for e in log:
            nxt = e["next_review"].isoformat() if e.get("next_review") else "none"
            lines.append(f"| {e['date'].isoformat()} | {_cell(e['type'])} | **{REVIEW_OUTCOMES[e['outcome']]}** | "
                         f"{_cell(e['summary'])} | {nxt} |")
    elif not gated:
        lines.append("No review held yet." if history["next_due"] or not history["closed"]
                     else "No review planned.")
    if superseded_by:
        status = f"superseded on {superseded_by['date'].isoformat()} by `{superseded_by['file']}`."
    elif history["stopped_on"]:
        status = f"stopped on {history['stopped_on'].isoformat()}. No further review."
    elif history["closed"]:
        status = ("rejected. No further review." if decision["decision"] == "reject"
                  else "closed. No further review.")
    elif history["next_due"]:
        status = f"next review due on {history['next_due'].isoformat()}."
    else:
        status = "no next review planned."
    prefix = f"**Status as of {as_of.isoformat()}:**" if as_of else "**Status:**"
    lines += ["", f"{prefix} {status}"]
    return lines
