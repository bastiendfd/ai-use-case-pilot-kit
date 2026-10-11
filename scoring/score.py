"""Score, gate and rank AI use cases.

Usage (from the repository root):

    python -m scoring.score examples/use_cases.csv
    python -m scoring.score examples/use_cases.csv --weights business_value=40,feasibility=10
    python -m scoring.score examples/use_cases.csv --sensitivity

Steps:
1. Load the criteria and weights from scoring/criteria.yaml.
2. Load and validate the use cases (one row per case).
3. Apply the hard gates (reject / park) before scoring.
4. Compute the weighted score out of 100: sum of weight x score / 5.
5. Rank the cases that pass the gates and write outputs/ranking.csv,
   outputs/ranking.md and outputs/value_feasibility_matrix.png.
6. Optionally, vary each weight by +/-10 points and report whether the top 3
   changes (outputs/sensitivity.md).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from scoring.errors import InputError

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CRITERIA = Path(__file__).resolve().parent / "criteria.yaml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs"

AI_ACT_CATEGORIES = ("not_ai_system", "excluded", "minimal", "limited", "high", "prohibited")
YES_NO = ("yes", "no")
MISSING_OWNER_VALUES = {"", "none", "tbd", "n/a", "na", "unknown", "-"}

GATE_FIELDS = (
    "ai_act_category",
    "process_owner",
    "data_owner",
    "restricted_data",
    "approved_environment_available",
)
IDENTITY_FIELDS = ("id", "title")
# Optional column: path to a triage answers file, relative to the CSV file.
# When set, the AI Act category is computed by scoring/triage.py.
TRIAGE_FIELD = "triage_answers"

GATE_PASS = "pass"
GATE_PARK = "park"
GATE_REJECT = "reject"

SENSITIVITY_STEP = 10.0
TOP_N = 3


@dataclass(frozen=True)
class Criteria:
    """Criteria definitions loaded from criteria.yaml."""

    ids: tuple[str, ...]
    names: dict[str, str]
    weights: dict[str, float]
    scale_min: int
    scale_max: int
    value_axis: tuple[str, ...]
    feasibility_axis: tuple[str, ...]
    threshold: float
    quadrants: dict[str, str]


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------


def load_criteria(path: Path = DEFAULT_CRITERIA) -> Criteria:
    """Load criteria.yaml and check that the weights sum to 100."""
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    items = raw["criteria"]
    ids = tuple(item["id"] for item in items)
    weights = {item["id"]: float(item["weight"]) for item in items}
    names = {item["id"]: item["name"] for item in items}
    validate_weights(weights, ids)

    matrix = raw["matrix"]
    return Criteria(
        ids=ids,
        names=names,
        weights=weights,
        scale_min=int(raw["scale"]["min"]),
        scale_max=int(raw["scale"]["max"]),
        value_axis=tuple(matrix["value_axis"]),
        feasibility_axis=tuple(matrix["feasibility_axis"]),
        threshold=float(matrix["threshold"]),
        quadrants=dict(matrix["quadrants"]),
    )


def validate_weights(weights: dict[str, float], ids: tuple[str, ...]) -> None:
    """Check that there is one non-negative weight per criterion, summing to 100."""
    errors = []
    unknown = sorted(set(weights) - set(ids))
    missing = [cid for cid in ids if cid not in weights]
    if unknown:
        errors.append(f"Unknown criteria in weights: {', '.join(unknown)}. Known: {', '.join(ids)}.")
    if missing:
        errors.append(f"Missing weights for: {', '.join(missing)}.")
    negative = [cid for cid, w in weights.items() if w < 0]
    if negative:
        errors.append(f"Weights must not be negative: {', '.join(negative)}.")
    total = sum(weights.values())
    if abs(total - 100.0) > 1e-6:
        errors.append(f"Weights must sum to 100, got {total:g}.")
    if errors:
        raise InputError(errors)


def parse_weights(spec: str, criteria: Criteria) -> dict[str, float]:
    """Parse a --weights option.

    ``spec`` is either a path to a YAML mapping {criterion_id: weight} or a
    comma-separated list such as ``business_value=40,feasibility=10``.
    Criteria that are not mentioned keep their weight from criteria.yaml.
    The final weights must sum to 100.
    """
    path = Path(spec)
    if path.suffix.lower() in {".yaml", ".yml"} and path.is_file():
        with open(path, encoding="utf-8") as handle:
            overrides = yaml.safe_load(handle) or {}
        if not isinstance(overrides, dict):
            raise InputError([f"{spec}: expected a mapping of criterion id to weight."])
    else:
        overrides = {}
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            if "=" not in part:
                raise InputError([f"Invalid --weights item '{part}'. Use criterion=weight, e.g. business_value=40."])
            key, value = part.split("=", 1)
            overrides[key.strip()] = value.strip()

    weights = dict(criteria.weights)
    errors = []
    for key, value in overrides.items():
        if key not in criteria.ids:
            errors.append(f"Unknown criterion '{key}' in --weights. Known: {', '.join(criteria.ids)}.")
            continue
        try:
            weights[key] = float(value)
        except (TypeError, ValueError):
            errors.append(f"Weight for '{key}' must be a number, got '{value}'.")
    if errors:
        raise InputError(errors)
    validate_weights(weights, criteria.ids)
    return weights


def load_use_cases(path: Path, criteria: Criteria) -> pd.DataFrame:
    """Read the use-case CSV and validate it.

    Returns a DataFrame with the criterion columns converted to int and the
    yes/no and category columns normalised to lower case.
    Raises InputError listing every problem found.
    """
    path = Path(path)
    if not path.is_file():
        raise InputError([f"Input file not found: {path}"])
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        raise InputError([f"{path}: the file is empty."]) from None
    df.columns = [str(c).strip() for c in df.columns]
    return validate_use_cases(df, criteria, source=str(path), base_dir=path.parent)


def apply_triage(df: pd.DataFrame, base_dir: Path, source: str) -> pd.DataFrame:
    """Fill or check ai_act_category from the triage answers files.

    For each row with a ``triage_answers`` path, run scoring/triage.py. An
    empty ai_act_category is filled with the result; a non-empty one must
    match it.
    """
    from scoring.triage import load_checklist, triage_file

    df = df.copy()
    if "ai_act_category" not in df.columns:
        df["ai_act_category"] = ""
    checklist = None
    errors = []
    for idx, row in df.iterrows():
        rel = str(row[TRIAGE_FIELD]).strip()
        if not rel:
            continue
        checklist = checklist or load_checklist()
        label = f"{row.get('id') or 'line ' + str(idx + 2)} (line {idx + 2})"
        try:
            result = triage_file(Path(base_dir) / rel, checklist)
        except InputError as exc:
            errors += [f"{label}: {m}" for m in exc.errors]
            continue
        given = str(row["ai_act_category"]).strip().lower()
        if given and given != result.category:
            errors.append(
                f"{label}: ai_act_category is '{given}' but the triage of {rel} "
                f"gives '{result.category}'. Fix the answers or the category."
            )
        df.at[idx, "ai_act_category"] = result.category
    if errors:
        raise InputError(errors)
    return df


def validate_use_cases(df: pd.DataFrame, criteria: Criteria, source: str = "input",
                       base_dir: Path | None = None) -> pd.DataFrame:
    """Validate a raw (all-text) use-case table. See load_use_cases."""
    required = list(IDENTITY_FIELDS) + list(GATE_FIELDS) + list(criteria.ids)
    if TRIAGE_FIELD in df.columns:
        required.remove("ai_act_category")  # filled from the triage answers
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise InputError([f"{source}: missing required column(s): {', '.join(missing_cols)}."])
    if df.empty:
        raise InputError([f"{source}: no use cases found (the file has a header but no rows)."])

    df = df.copy()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    if TRIAGE_FIELD in df.columns:
        df = apply_triage(df, base_dir or Path("."), source)

    errors: list[str] = []
    # Row numbers are reported as in a spreadsheet: header is line 1.
    for idx, row in df.iterrows():
        line = idx + 2
        label = row["id"] or f"line {line}"
        if not row["id"]:
            errors.append(f"Line {line}: 'id' is empty.")
        if not row["title"]:
            errors.append(f"{label} (line {line}): 'title' is empty.")
        for cid in criteria.ids:
            value = row[cid]
            if not re.fullmatch(r"\d+", value) or not (criteria.scale_min <= int(value) <= criteria.scale_max):
                errors.append(
                    f"{label} (line {line}): '{cid}' must be an integer from "
                    f"{criteria.scale_min} to {criteria.scale_max}, got '{value}'."
                )
        category = row["ai_act_category"].lower()
        if category not in AI_ACT_CATEGORIES:
            errors.append(
                f"{label} (line {line}): 'ai_act_category' must be one of "
                f"{', '.join(AI_ACT_CATEGORIES)}, got '{row['ai_act_category']}'."
            )
        for col in ("restricted_data", "approved_environment_available"):
            if row[col].lower() not in YES_NO:
                errors.append(f"{label} (line {line}): '{col}' must be yes or no, got '{row[col]}'.")

    ids = df.loc[df["id"] != "", "id"]
    duplicates = sorted(set(ids[ids.duplicated()]))
    if duplicates:
        errors.append(f"Duplicate use-case id(s): {', '.join(duplicates)}.")

    if errors:
        raise InputError(errors)

    for cid in criteria.ids:
        df[cid] = df[cid].astype(int)
    for col in ("ai_act_category", "restricted_data", "approved_environment_available"):
        df[col] = df[col].str.lower()
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Gates, scores, ranking
# ---------------------------------------------------------------------------


def _owner_missing(value: str) -> bool:
    return value.strip().lower() in MISSING_OWNER_VALUES


def apply_gates(row: pd.Series | dict) -> tuple[str, str]:
    """Return (gate_result, reason) for one use case.

    Gates, in order:
    1. AI Act category "prohibited" -> reject, whatever the score.
    2. No process owner or no data owner -> park until assigned.
    3. Export-controlled or classified data and no approved (non-public-cloud)
       environment -> park until an approved environment exists.
    Several park reasons are combined.
    """
    if str(row["ai_act_category"]).lower() == "prohibited":
        return GATE_REJECT, "Prohibited AI practice under the AI Act screening."

    reasons = []
    if _owner_missing(str(row["process_owner"])):
        reasons.append("no process owner assigned")
    if _owner_missing(str(row["data_owner"])):
        reasons.append("no data owner assigned")
    if (
        str(row["restricted_data"]).lower() == "yes"
        and str(row["approved_environment_available"]).lower() == "no"
    ):
        reasons.append("export-controlled or classified data with no approved environment")
    if reasons:
        text = "; ".join(reasons)
        return GATE_PARK, text[0].upper() + text[1:] + "."
    return GATE_PASS, ""


def weighted_contributions(row: pd.Series | dict, weights: dict[str, float], scale_max: int = 5) -> dict[str, float]:
    """Contribution of each criterion: weight x score / scale_max."""
    return {cid: weights[cid] * int(row[cid]) / scale_max for cid in weights}


def weighted_score(row: pd.Series | dict, weights: dict[str, float], scale_max: int = 5) -> float:
    """Weighted score out of 100."""
    return sum(weighted_contributions(row, weights, scale_max).values())


def quadrant(row: pd.Series | dict, criteria: Criteria) -> str:
    """Position in the value-vs-feasibility matrix."""
    value = sum(int(row[c]) for c in criteria.value_axis) / len(criteria.value_axis)
    feas = sum(int(row[c]) for c in criteria.feasibility_axis) / len(criteria.feasibility_axis)
    v = "high_value" if value >= criteria.threshold else "low_value"
    f = "high_feasibility" if feas >= criteria.threshold else "low_feasibility"
    return criteria.quadrants[f"{v}_{f}"]


def _rationale(row: pd.Series, criteria: Criteria, gate: str, gate_reason: str, quad: str) -> str:
    """One-line explanation built from the scores and the gate."""
    if gate == GATE_REJECT:
        return f"Rejected at the gate: {gate_reason[0].lower() + gate_reason[1:]} Score for information only."
    if gate == GATE_PARK:
        return f"Parked at the gate: {gate_reason[0].lower() + gate_reason[1:]} Score for information only."

    scores = {cid: int(row[cid]) for cid in criteria.ids}
    high, low = max(scores.values()), min(scores.values())
    if high == low:
        return f"{quad.capitalize()}: even profile, all criteria at {high}."
    # List the strongest/weakest criteria in weight order, at most two each.
    order = sorted(criteria.ids, key=lambda c: -criteria.weights[c])
    strong = [f"{criteria.names[c].lower()} ({scores[c]})" for c in order if scores[c] == high][:2]
    weak = [f"{criteria.names[c].lower()} ({scores[c]})" for c in order if scores[c] == low][:2]
    return f"{quad.capitalize()}: strongest on {' and '.join(strong)}; weakest on {' and '.join(weak)}."


def score_use_cases(df: pd.DataFrame, criteria: Criteria, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Gate, score and rank all use cases.

    Only cases that pass the gates get a rank. Ranking order: weighted score
    (descending), then business value score (descending), then id.
    Gated cases follow, unranked, rejected before parked.
    """
    weights = dict(weights or criteria.weights)
    validate_weights(weights, criteria.ids)

    records = []
    for _, row in df.iterrows():
        gate, reason = apply_gates(row)
        contrib = weighted_contributions(row, weights, criteria.scale_max)
        quad = quadrant(row, criteria)
        record = {
            "id": row["id"],
            "title": row["title"],
            "weighted_score": round(sum(contrib.values()), 1),
            "_raw_score": sum(contrib.values()),
            "gate_result": gate,
            "gate_reason": reason,
            "ai_act_category": row["ai_act_category"],
            "quadrant": quad,
        }
        for cid in criteria.ids:
            record[f"score_{cid}"] = int(row[cid])
        for cid in criteria.ids:
            record[f"contrib_{cid}"] = round(contrib[cid], 1)
        record["rationale"] = _rationale(row, criteria, gate, reason, quad)
        records.append(record)

    out = pd.DataFrame.from_records(records)
    gate_order = {GATE_PASS: 0, GATE_REJECT: 1, GATE_PARK: 2}
    out["_gate_order"] = out["gate_result"].map(gate_order)
    out = out.sort_values(
        by=["_gate_order", "_raw_score", "score_business_value", "id"],
        ascending=[True, False, False, True],
        kind="mergesort",
    ).drop(columns=["_gate_order", "_raw_score"])

    passed = out["gate_result"] == GATE_PASS
    out.insert(0, "rank", pd.array([pd.NA] * len(out), dtype="Int64"))
    out.loc[passed, "rank"] = range(1, int(passed.sum()) + 1)
    return out.reset_index(drop=True)


def consistency_warnings(df: pd.DataFrame) -> list[str]:
    """Flag inputs that contradict the level descriptions in criteria.yaml."""
    warnings = []
    for _, row in df.iterrows():
        if row["ai_act_category"] == "high" and int(row["risk"]) > 1:
            warnings.append(
                f"{row['id']}: AI Act category is 'high' but the risk score is {row['risk']}; "
                "criteria.yaml defines high-risk as risk level 1."
            )
        if row["ai_act_category"] == "limited" and int(row["risk"]) > 3:
            warnings.append(
                f"{row['id']}: AI Act category is 'limited' (transparency obligations) but the risk "
                f"score is {row['risk']}; criteria.yaml places transparency obligations at level 3 or lower."
            )
    return warnings


# ---------------------------------------------------------------------------
# Sensitivity
# ---------------------------------------------------------------------------


def shifted_weights(weights: dict[str, float], criterion: str, delta: float) -> dict[str, float] | None:
    """Move one weight by ``delta`` points and rescale the others so the total stays 100.

    The other weights keep their relative proportions. Returns None when the
    shift would make the weight negative or above 100.
    """
    new_value = weights[criterion] + delta
    if new_value < 0 or new_value > 100:
        return None
    rest_before = 100.0 - weights[criterion]
    rest_after = 100.0 - new_value
    shifted = {}
    for cid, w in weights.items():
        if cid == criterion:
            shifted[cid] = new_value
        elif rest_before == 0:
            shifted[cid] = 0.0
        else:
            shifted[cid] = w * rest_after / rest_before
    return shifted


def top_ids(ranked: pd.DataFrame, n: int = TOP_N) -> list[str]:
    """IDs of the top ``n`` ranked (gate-passing) cases, in rank order."""
    passed = ranked[ranked["gate_result"] == GATE_PASS]
    return list(passed["id"].head(n))


def sensitivity(df: pd.DataFrame, criteria: Criteria, weights: dict[str, float] | None = None,
                step: float = SENSITIVITY_STEP, n: int = TOP_N) -> pd.DataFrame:
    """Vary each weight by +/- ``step`` points and compare the top ``n``.

    Returns one row per variation with the new weights, the new top n, and
    whether the top-n set and the top-n order changed.
    """
    weights = dict(weights or criteria.weights)
    base_top = top_ids(score_use_cases(df, criteria, weights), n)
    rows = []
    for cid in criteria.ids:
        for delta in (+step, -step):
            new_weights = shifted_weights(weights, cid, delta)
            if new_weights is None:
                rows.append({
                    "criterion": cid, "change": f"{delta:+g}", "weights": "not possible (weight out of range)",
                    "top": "", "set_changed": False, "order_changed": False,
                })
                continue
            top = top_ids(score_use_cases(df, criteria, new_weights), n)
            rows.append({
                "criterion": cid,
                "change": f"{delta:+g}",
                "weights": ", ".join(f"{k}={v:.1f}" for k, v in new_weights.items()),
                "top": ", ".join(top),
                "set_changed": set(top) != set(base_top),
                "order_changed": top != base_top,
            })
    result = pd.DataFrame(rows)
    result.attrs["base_top"] = base_top
    return result


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


def _is_bundled_example(path: Path) -> bool:
    try:
        Path(path).resolve().relative_to(REPO_ROOT / "examples")
        return True
    except ValueError:
        return False


def _md_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub Markdown table (no extra dependency)."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        cells = ["" if pd.isna(v) else str(v).replace("|", "\\|") for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_ranking(ranked: pd.DataFrame, criteria: Criteria, weights: dict[str, float],
                  output_dir: Path, source: Path, warnings: list[str]) -> tuple[Path, Path]:
    """Write ranking.csv and ranking.md."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "ranking.csv"
    md_path = output_dir / "ranking.md"
    ranked.to_csv(csv_path, index=False, encoding="utf-8", lineterminator="\n")

    display = ranked.copy()
    display["rank"] = display["rank"].astype(object).where(display["rank"].notna(), "–")
    summary = display[["rank", "id", "title", "weighted_score", "gate_result", "quadrant", "rationale"]]
    summary.columns = ["Rank", "ID", "Title", "Score /100", "Gate", "Quadrant", "Rationale"]

    contrib = display[["id"] + [f"contrib_{c}" for c in criteria.ids] + ["weighted_score"]]
    contrib.columns = ["ID"] + [f"{criteria.names[c]} ({weights[c]:g})" for c in criteria.ids] + ["Total"]

    lines = ["# Use-case ranking", ""]
    if _is_bundled_example(source):
        lines += ["> **Fictional data.** Generated from the fictional example portfolio of "
                  "\"Northwind Aero Services\".", ""]
    lines += [
        f"Generated by `scoring/score.py` from `{_display_path(source)}`. Do not edit by hand.",
        "",
        "Weighted score = sum of weight × score / 5 (out of 100). Only cases that pass the "
        "hard gates are ranked. Read close scores as a tie and check the sensitivity output.",
        "",
        "## Ranking",
        "",
        _md_table(summary),
        "",
        "## Contribution of each criterion (points out of 100)",
        "",
        "Column headers show the weight used.",
        "",
        _md_table(contrib),
        "",
    ]
    if warnings:
        lines += ["## Input warnings", ""] + [f"- {w}" for w in warnings] + [""]
    md_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return csv_path, md_path


def _display_path(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return Path(path).name


def load_decisions(path: Path) -> dict[str, str]:
    """Read {use-case id: status} from a CSV with 'id' and 'status' (or 'decision') columns.

    The status is the decision of the latest record, or 'stopped' when a review
    ended the case (outputs/decisions.csv has both columns).
    """
    from scoring.decision import STATUS_LABELS

    path = Path(path)
    if not path.is_file():
        raise InputError([f"Decisions file not found: {path}"])
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    column = "status" if "status" in df.columns else "decision"
    missing = [c for c in ("id", column) if c not in df.columns]
    if missing:
        raise InputError([f"{path}: missing column(s): {', '.join(missing)}."])
    bad = sorted(set(df[column]) - set(STATUS_LABELS))
    if bad:
        raise InputError([f"{path}: unknown decision(s): {', '.join(bad)}. Use: {', '.join(STATUS_LABELS)}."])
    return dict(zip(df["id"], df[column]))


def write_matrix(ranked: pd.DataFrame, criteria: Criteria, output_dir: Path, fictional: bool,
                 decisions: dict[str, str] | None = None) -> Path:
    """Draw the 2x2 value-vs-feasibility matrix as a PNG.

    Marker fill shows the hard-gate result: filled = passed the gates, hollow =
    stopped at a hard gate. When ``decisions`` ({id: decision}) is given, the
    marker colour shows the decision taken after the business case, and the
    legend says so; without it, all markers are grey and the legend says that
    no decision is shown.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    from scoring.decision import DECISION_COLOURS, STATUS_LABELS

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "value_feasibility_matrix.png"

    x = ranked[[f"score_{c}" for c in criteria.feasibility_axis]].mean(axis=1)
    y = ranked[[f"score_{c}" for c in criteria.value_axis]].mean(axis=1)

    fig, ax = plt.subplots(figsize=(7.5, 6.5), dpi=150)
    lo, hi = criteria.scale_min - 0.5, criteria.scale_max + 0.5
    t = criteria.threshold
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.axvline(t, color="0.6", linewidth=1)
    ax.axhline(t, color="0.6", linewidth=1)

    q = criteria.quadrants
    label_style = dict(fontsize=11, color="0.45", fontweight="bold")
    quadrant_texts = [
        ax.text(hi - 0.1, hi - 0.1, q["high_value_high_feasibility"].upper(), ha="right", va="top", **label_style),
        ax.text(lo + 0.1, hi - 0.1, q["high_value_low_feasibility"].upper(), ha="left", va="top", **label_style),
        ax.text(hi - 0.1, lo + 0.1, q["low_value_high_feasibility"].upper(), ha="right", va="bottom", **label_style),
        ax.text(lo + 0.1, lo + 0.1, q["low_value_low_feasibility"].upper(), ha="left", va="bottom", **label_style),
    ]

    # Spread points that share the same position, draw all points first, then
    # place each label at the first candidate position that overlaps nothing.
    seen: dict[tuple[float, float], int] = {}
    points = []
    for i, row in ranked.iterrows():
        key = (float(x[i]), float(y[i]))
        k = seen.get(key, 0)
        seen[key] = k + 1
        px, py = key[0] + 0.15 * k, key[1] - 0.15 * k
        passed = row["gate_result"] == GATE_PASS
        colour = DECISION_COLOURS.get((decisions or {}).get(row["id"]), "0.45")
        ax.scatter(px, py, s=110, zorder=3,
                   facecolor=colour if passed else "white",
                   edgecolor=colour, linewidth=2)
        label = row["id"] if passed else f"{row['id']} (gate: {row['gate_result']})"
        points.append((px, py, label, passed))

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    marker_boxes = []
    for px, py, _, _ in points:
        cx, cy = ax.transData.transform((px, py))
        marker_boxes.append((cx - 7, cy - 7, cx + 7, cy + 7))
    taken = list(marker_boxes)
    axes_box = ax.get_window_extent(renderer)
    for qt in quadrant_texts:
        e = qt.get_window_extent(renderer)
        taken.append((e.x0, e.y0, e.x1, e.y1))
    candidates = [((8, 4), "left", "bottom"), ((8, -4), "left", "top"),
                  ((-8, 4), "right", "bottom"), ((-8, -4), "right", "top"),
                  ((0, 9), "center", "bottom"), ((0, -9), "center", "top")]

    def _overlaps(a, b):
        return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

    for px, py, label, passed in points:
        for offset, ha, va in candidates:
            text = ax.annotate(label, (px, py), xytext=offset, textcoords="offset points",
                               ha=ha, va=va, fontsize=9, color="black" if passed else "0.4")
            ext = text.get_window_extent(renderer)
            box = (ext.x0, ext.y0, ext.x1, ext.y1)
            inside = (axes_box.x0 <= box[0] and box[2] <= axes_box.x1
                      and axes_box.y0 <= box[1] and box[3] <= axes_box.y1)
            if inside and not any(_overlaps(box, other) for other in taken):
                break
            text.remove()
        else:  # every position overlaps: keep the first one
            text = ax.annotate(label, (px, py), xytext=candidates[0][0], textcoords="offset points",
                               fontsize=9, color="black" if passed else "0.4")
            ext = text.get_window_extent(renderer)
            box = (ext.x0, ext.y0, ext.x1, ext.y1)
        taken.append(box)

    feas_names = " and ".join(criteria.names[c].lower() for c in criteria.feasibility_axis)
    ax.set_xlabel(f"Feasibility axis: mean of {feas_names} scores (1–5)")
    ax.set_ylabel(f"{' + '.join(criteria.names[c] for c in criteria.value_axis)} (1–5)")
    title = "Value vs. feasibility"
    if fictional:
        title += " (fictional examples)"
    ax.set_title(title)
    handles = []
    if decisions:
        shown = [k for k in STATUS_LABELS if k in set(decisions.get(i) for i in ranked["id"])]
        handles += [Line2D([], [], marker="o", linestyle="", markersize=9, markerfacecolor=DECISION_COLOURS[k],
                           markeredgecolor=DECISION_COLOURS[k], label=STATUS_LABELS[k])
                    for k in shown]
    else:
        handles.append(Line2D([], [], marker="o", linestyle="", markersize=9, markerfacecolor="0.45",
                              markeredgecolor="0.45", label="Passed the hard gates (no decision shown)"))
    handles.append(Line2D([], [], marker="o", linestyle="", markersize=9, markerfacecolor="white",
                          markeredgecolor="0.45", markeredgewidth=2, label="Hollow: blocked by a hard gate"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=3, fontsize=8,
              frameon=False)
    ax.text(1.0, 1.01, f"Quadrant lines at {t:g}", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="0.4")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def write_sensitivity(result: pd.DataFrame, output_dir: Path, step: float = SENSITIVITY_STEP) -> Path:
    """Write sensitivity.md."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "sensitivity.md"
    base_top = result.attrs.get("base_top", [])
    valid = result[result["top"] != ""]
    stable = int((~valid["set_changed"]).sum())
    table = result.copy()
    table["set_changed"] = table["set_changed"].map({True: "**yes**", False: "no"})
    table["order_changed"] = table["order_changed"].map({True: "yes", False: "no"})
    table.columns = ["Criterion", "Change (points)", "Weights after change", "Top 3",
                     "Top-3 set changed", "Top-3 order changed"]
    lines = [
        "# Sensitivity of the top 3 to the weights",
        "",
        f"Each weight is moved by ±{step:g} points; the other weights are rescaled "
        "proportionally so the total stays 100.",
        "",
        f"Base top 3: **{', '.join(base_top)}**.",
        "",
        f"The top-3 set is unchanged in **{stable} of {len(valid)}** variations.",
        "",
        _md_table(table),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scoring.score",
        description="Gate, score and rank AI use cases.",
    )
    parser.add_argument("input", type=Path, help="CSV file with one row per use case.")
    parser.add_argument("--criteria", type=Path, default=DEFAULT_CRITERIA,
                        help="Criteria file (default: scoring/criteria.yaml).")
    parser.add_argument("--weights", default=None,
                        help="Override weights: 'business_value=40,feasibility=10' or a YAML file. "
                             "The final weights must sum to 100.")
    parser.add_argument("--sensitivity", action="store_true",
                        help="Vary each weight by +/-10 points and report whether the top 3 changes.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="Where to write the outputs (default: outputs/).")
    parser.add_argument("--decisions", type=Path, default=None,
                        help="Optional CSV with 'id' and 'status' (or 'decision') columns to colour the matrix "
                             "by decision. Default for the bundled example: decisions.csv in the output "
                             "directory, if present.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        criteria = load_criteria(args.criteria)
        weights = parse_weights(args.weights, criteria) if args.weights else dict(criteria.weights)
        df = load_use_cases(args.input, criteria)
        decisions_path = args.decisions
        if decisions_path is None and _is_bundled_example(args.input) \
                and (args.output_dir / "decisions.csv").is_file():
            decisions_path = args.output_dir / "decisions.csv"   # keep the example matrix coloured
        decisions = load_decisions(decisions_path) if decisions_path else None
    except InputError as exc:
        print("Input error:", file=sys.stderr)
        for message in exc.errors:
            print(f"  - {message}", file=sys.stderr)
        return 2

    ranked = score_use_cases(df, criteria, weights)
    warnings = consistency_warnings(df)
    csv_path, md_path = write_ranking(ranked, criteria, weights, args.output_dir, args.input, warnings)
    png_path = write_matrix(ranked, criteria, args.output_dir, fictional=_is_bundled_example(args.input),
                            decisions=decisions)

    print("Weights:", ", ".join(f"{k}={v:g}" for k, v in weights.items()))
    cols = ["rank", "id", "weighted_score", "gate_result", "quadrant"]
    print(ranked[cols].to_string(index=False))
    for w in warnings:
        print(f"Warning: {w}")
    print(f"Wrote {_display_path(csv_path)}, {_display_path(md_path)}, {_display_path(png_path)}")

    if args.sensitivity:
        result = sensitivity(df, criteria, weights)
        sens_path = write_sensitivity(result, args.output_dir)
        valid = result[result["top"] != ""]
        changed = valid[valid["set_changed"]]
        print(f"Sensitivity: base top {TOP_N} = {', '.join(result.attrs['base_top'])}; "
              f"set unchanged in {len(valid) - len(changed)} of {len(valid)} variations.")
        for _, row in changed.iterrows():
            print(f"  {row['criterion']} {row['change']}: top {TOP_N} becomes {row['top']}")
        print(f"Wrote {_display_path(sens_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
