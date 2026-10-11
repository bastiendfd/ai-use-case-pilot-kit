"""Static portfolio charts (PNG), no Power BI needed.

Usage (from the repository root):

    python dashboard/charts.py
    python dashboard/charts.py --tracking data/value_tracking.csv --decisions outputs/decisions.csv

Inputs:
- data/value_tracking.csv: one row per use case and month (planned and
  realised benefit, adoption, incidents, notes);
- outputs/decisions.csv: one row per use case (rank, score, decision, AI Act
  category, NPV range, review-gate outcomes), written by
  ``python -m scoring.build_examples``.

Outputs in outputs/:
- portfolio_overview.png: ranking and decision per use case (the README figure);
- cumulative_value.png: cumulative planned vs. realised value, with review gates;
- adoption.png: realised adoption per use case against the business case plan.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:  # allow "python dashboard/charts.py"
    sys.path.insert(0, str(REPO_ROOT))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from scoring import business_case as bc  # noqa: E402
from scoring.decision import DECISION_COLOURS, GATE_OUTCOMES, REVIEW_OUTCOMES, STATUS_LABELS  # noqa: E402
from scoring.errors import InputError  # noqa: E402

DEFAULT_TRACKING = REPO_ROOT / "data" / "value_tracking.csv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs"
EXAMPLES_DIR = REPO_ROOT / "examples"

TRACKING_COLUMNS = ("use_case_id", "month", "planned_benefit_eur", "realised_benefit_eur",
                    "adoption_rate", "incidents", "notes")
DECISION_COLUMNS = ("id", "short_title", "decision", "status", "decision_history", "ai_act_category", "rank",
                    "weighted_score", "npv_pessimistic_eur", "npv_base_eur", "npv_optimistic_eur", "gate_outcomes",
                    "other_reviews", "as_of")
SHORT_DECISIONS = {"go": "go", "go_with_conditions": "go w/ cond.", "pilot": "pilot", "park": "park",
                   "reject": "reject"}
EVENT_RE = re.compile(r"(?:([a-z ]+): )?([a-z_ ]+?) \((\d{4}-\d{2}-\d{2})\)")
AI_ACT_LABELS = {"not_ai_system": "Not AI", "excluded": "Excluded", "prohibited": "Prohibited",
                 "high": "High-risk", "limited": "Limited (Art. 50)", "minimal": "Minimal"}
GATE_RE = re.compile(r"(continue|rework|stop) \((\d{4}-\d{2}-\d{2})\)")
FICTION = "Fictional data: \"Northwind Aero Services\"."
# Adoption lines are told apart by use case, not by decision (two cases can share a decision).
CASE_STYLES = [("#0072B2", "o"), ("#009E73", "s"), ("#CC79A7", "^"), ("#4D4D4D", "D"), ("#E69F00", "v")]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_tracking(path: Path) -> pd.DataFrame:
    """Read and validate value_tracking.csv."""
    path = Path(path)
    if not path.is_file():
        raise InputError([f"Value tracking file not found: {path}"])
    df = pd.read_csv(path, dtype={"use_case_id": str, "notes": str}, keep_default_na=False)
    missing = [c for c in TRACKING_COLUMNS if c not in df.columns]
    if missing:
        raise InputError([f"{path}: missing column(s): {', '.join(missing)}."])
    errors = []
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m-%d", errors="coerce")
    if df["month"].isna().any() or (df["month"].dt.day != 1).any():
        errors.append(f"{path}: 'month' must be the first day of a month (YYYY-MM-01).")
    for col in ("planned_benefit_eur", "realised_benefit_eur", "adoption_rate", "incidents"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any() or (df[col] < 0).any():
            errors.append(f"{path}: '{col}' must be a number of at least 0 in every row.")
    if ((df["adoption_rate"] > 1).any()):
        errors.append(f"{path}: 'adoption_rate' must be between 0 and 1.")
    if df.duplicated(["use_case_id", "month"]).any():
        errors.append(f"{path}: duplicate (use_case_id, month) rows.")
    if not errors:
        for uc, g in df.groupby("use_case_id"):
            months = g["month"].sort_values()
            gaps = (months.dt.year * 12 + months.dt.month).diff().dropna()
            if (gaps != 1).any():
                errors.append(f"{path}: months of {uc} must be consecutive.")
    if errors:
        raise InputError(errors)
    return df.sort_values(["use_case_id", "month"]).reset_index(drop=True)


def load_decisions(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.is_file():
        raise InputError([f"Decisions file not found: {path}. Run: python -m scoring.build_examples"])
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in DECISION_COLUMNS if c not in df.columns]
    if missing:
        raise InputError([f"{path}: missing column(s): {', '.join(missing)}."])
    for col in ("weighted_score", "npv_pessimistic_eur", "npv_base_eur", "npv_optimistic_eur"):
        df[col] = pd.to_numeric(df[col])
    df["rank_num"] = pd.to_numeric(df["rank"], errors="coerce")
    return df.sort_values(["rank_num", "id"], na_position="last").reset_index(drop=True)


def gate_events(gate_outcomes: str) -> list[tuple[pd.Timestamp, str]]:
    """'rework (2027-03-01), continue (2027-06-01)' -> [(date, 'rework'), (date, 'continue')]."""
    return [(pd.Timestamp(d), kind) for kind, d in GATE_RE.findall(gate_outcomes or "")]


def story_events(row) -> list[tuple[pd.Timestamp, str, str]]:
    """Everything that happened to a case after its first decision, in date order.

    Returns (date, kind, label) with kind 'gate', 'review' or 'decision'; for
    example (2027-06-10, 'decision', 'go w/ cond.').
    """
    events = []
    for kind, d in GATE_RE.findall(row.get("gate_outcomes", "") or ""):
        events.append((pd.Timestamp(d), "gate", GATE_OUTCOMES[kind].lower()))
    for item in (row.get("other_reviews", "") or "").split(", "):
        m = EVENT_RE.fullmatch(item.strip())
        if m:
            events.append((pd.Timestamp(m.group(3)), "review", REVIEW_OUTCOMES[m.group(2).replace(" ", "_")].lower()))
    for item in (row.get("decision_history", "") or "").split(" -> ")[1:]:
        m = EVENT_RE.fullmatch(item.strip())
        if m:
            events.append((pd.Timestamp(m.group(3)), "decision", SHORT_DECISIONS[m.group(2)]))
    order = {"gate": 0, "review": 0, "decision": 1}
    return sorted(events, key=lambda e: (e[0], order[e[1]]))


def _event_text(kind: str, label: str) -> str:
    return {"gate": f"gate: {label}", "review": f"review: {label}", "decision": f"decision: {label}"}[kind]


def planned_adoption(use_case_id: str, months: int) -> list[float] | None:
    """Adoption curve of the base business case, months 1..n, if the inputs file exists."""
    folder = next(EXAMPLES_DIR.glob(f"{use_case_id}_*"), None)
    if folder is None or not (folder / "business_case_inputs.yaml").is_file():
        return None
    case = bc.load_inputs(folder / "business_case_inputs.yaml")
    rows = bc.compute(case.values("base"))["months"]
    return [rows[m]["adoption"] for m in range(1, months + 1)]


def _k(x: float) -> str:
    sign = "−" if x < 0 else ""
    return f"{sign}€{abs(x) / 1000:,.0f}k"


# ---------------------------------------------------------------------------
# Portfolio overview (README figure)
# ---------------------------------------------------------------------------


def portfolio_overview(decisions: pd.DataFrame, path: Path) -> Path:
    """One figure: rank, score, decision, AI Act category, NPV range and gate outcomes per case."""
    n = len(decisions)
    fig_h = 1.7 + 0.78 * n
    fig, ax = plt.subplots(figsize=(13.5, fig_h), dpi=150)
    ax.set_xlim(0, 100)
    ax.set_ylim(n + 0.2, -1.3)
    ax.axis("off")

    cols = {"rank": 0.6, "case": 3.2, "score": 26.5, "decision": 40.5, "ai": 73.0,
            "npv": (85.5, 92.5, 99.3)}
    head = dict(fontsize=9, color="0.35", fontweight="bold", va="center")
    ax.text(cols["rank"], -0.55, "#", **head)
    ax.text(cols["case"], -0.55, "Use case", **head)
    ax.text(cols["score"], -0.55, "Score /100", **head)
    ax.text(cols["decision"], -0.55, "Status", **head)
    ax.text(cols["ai"], -0.55, "AI Act", **head)
    ax.text(cols["npv"][1], -0.95, "3-year NPV", ha="center", **dict(head, fontsize=8.5))
    for x, label in zip(cols["npv"], ("Pessimistic", "Base", "Optimistic")):
        ax.text(x, -0.5, label, ha="right", **dict(head, fontsize=8.5))
    ax.plot([0, 100], [-0.15, -0.15], color="0.75", linewidth=0.8)

    bar_w = 10.0
    for i, r in decisions.iterrows():
        y = i + 0.35
        colour = DECISION_COLOURS.get(r["status"], "0.5")
        if i % 2 == 0:
            ax.add_patch(plt.Rectangle((0, y - 0.48), 100, 0.96, color="0.96", zorder=0, linewidth=0))
        ax.text(cols["rank"], y, r["rank"] or "–", fontsize=11, fontweight="bold", va="center")
        ax.text(cols["case"], y - 0.2, r["id"], fontsize=10, fontweight="bold", va="center")
        ax.text(cols["case"], y + 0.12, r["short_title"], fontsize=9.5, va="center", color="0.15")
        y_main, y = y, y - 0.1
        ax.add_patch(plt.Rectangle((cols["score"], y - 0.18), bar_w, 0.36, color="0.88", linewidth=0))
        ax.add_patch(plt.Rectangle((cols["score"], y - 0.18), bar_w * r["weighted_score"] / 100, 0.36,
                                   color=colour, linewidth=0))
        ax.text(cols["score"] + bar_w + 0.8, y, f"{r['weighted_score']:.0f}", fontsize=10, va="center")
        ax.add_patch(FancyBboxPatch((cols["decision"], y - 0.2), 14.0, 0.4,
                                    boxstyle="round,pad=0.02,rounding_size=0.15", color=colour, linewidth=0))
        ax.text(cols["decision"] + 7.0, y, STATUS_LABELS[r["status"]], fontsize=9.5, color="white",
                fontweight="bold", ha="center", va="center")
        first = (r["decision_history"].split(" -> ")[0].split(" (")[0])
        trail = " → ".join([f"decided: {SHORT_DECISIONS.get(first, first)}"]
                           + [f"{_event_text(k, label)} ({d:%b %y})" for d, k, label in story_events(r)])
        ax.text(cols["score"], y_main + 0.3, f"History: {trail}", fontsize=7.5, color="0.3", va="center")
        ax.text(cols["ai"], y, AI_ACT_LABELS.get(r["ai_act_category"], r["ai_act_category"]), fontsize=9.5,
                va="center", color="#B00020" if r["ai_act_category"] in ("high", "prohibited") else "0.15")
        npv = [r["npv_pessimistic_eur"], r["npv_base_eur"], r["npv_optimistic_eur"]]
        for j, (x, value) in enumerate(zip(cols["npv"], npv)):
            ax.text(x, y, _k(value), fontsize=9.5, va="center", ha="right",
                    color="#B00020" if value < 0 else "0.15", fontweight="bold" if j == 1 else "normal")

    counts = decisions["status"].value_counts()
    summary = " · ".join(f"{STATUS_LABELS[k]}: {counts[k]}" for k in STATUS_LABELS if k in counts)
    as_of = pd.Timestamp(decisions["as_of"].iloc[0]) if len(decisions) else None
    when = f", as of {as_of:%d %B %Y}" if as_of is not None else ""
    fig.suptitle(f"AI use-case portfolio: ranking and decisions{when}", x=0.012, y=0.985, ha="left",
                 fontsize=14, fontweight="bold")
    fig.text(0.012, 0.985 - 0.36 / fig_h, f"{len(decisions)} use cases · {summary} · {FICTION}",
             ha="left", va="top", fontsize=9.5, color="0.3")
    fig.text(0.012, 0.012, "Score: weighted criteria in scoring/criteria.yaml. AI Act: screening category, not "
             "legal advice. NPV: business case at decision time, 36 months at 8%; red = negative.\n"
             "A negative scenario means approval only with a review gate 3 months after start. "
             "Stopped = ended at a review gate. Review dates and outcomes: each case's decision record.",
             fontsize=7.5, color="0.4", ha="left", va="bottom")
    fig.subplots_adjust(left=0.01, right=0.99, top=1 - 0.75 / fig_h, bottom=0.45 / fig_h)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Value tracking charts
# ---------------------------------------------------------------------------


def cumulative_value(tracking: pd.DataFrame, decisions: pd.DataFrame, path: Path) -> Path:
    """Cumulative planned vs. realised value, one panel per tracked use case, with review gates."""
    ids = list(dict.fromkeys(tracking["use_case_id"]))
    info = decisions.set_index("id")
    fig, axes = plt.subplots(1, len(ids), figsize=(4.4 * len(ids), 4.6), dpi=150, sharey=True, sharex=True)
    axes = [axes] if len(ids) == 1 else list(axes)
    for ax, uc in zip(axes, ids):
        g = tracking[tracking["use_case_id"] == uc]
        plan = g["planned_benefit_eur"].cumsum() / 1000
        real = g["realised_benefit_eur"].cumsum() / 1000
        colour = DECISION_COLOURS.get(info.loc[uc, "status"], "0.3") if uc in info.index else "0.3"
        ax.plot(g["month"], real, color=colour, linewidth=2.4, label="Realised")
        ax.plot(g["month"], plan, color="0.35", linestyle="--", linewidth=1.5, label="Planned (base case)",
                zorder=3)
        ax.fill_between(g["month"], real, plan, where=real < plan, color="#D55E00", alpha=0.12,
                        label="Gap to plan")
        share = real.iloc[-1] / plan.iloc[-1] if plan.iloc[-1] else 0
        title = info.loc[uc, "short_title"] if uc in info.index else ""
        stopped = uc in info.index and info.loc[uc, "status"] == "stopped"
        ax.set_title(f"{uc}: {title}\nrealised {share:.0%} of plan over {len(g)} months"
                     + (" (stopped)" if stopped else ""), fontsize=10)
        events = story_events(info.loc[uc]) if uc in info.index else []
        by_month: dict[pd.Timestamp, list] = {}
        for day, kind, label in events:
            by_month.setdefault(day.to_period("M").to_timestamp(), []).append((day, kind, label))
        for j, (month, items) in enumerate(sorted(by_month.items())):
            day = items[0][0]
            ax.axvline(day, color="0.25", linewidth=1, linestyle=":")
            text = "\n".join(_event_text(k, label) for _, k, label in items)
            alert = any(label in ("rework", "stop") for _, _, label in items)
            late = day >= tracking["month"].max() - pd.DateOffset(months=3)
            pad = "" if late else " "
            ax.text(day, 0.97 - 0.13 * (j % 2), pad + text.replace("\n", "\n" + pad) + (" " if late else ""),
                    transform=ax.get_xaxis_transform(), fontsize=7, va="top", ha="right" if late else "left",
                    multialignment="right" if late else "left", color="#D55E00" if alert else "0.25")
        ax.grid(axis="y", color="0.9")
        ax.tick_params(axis="x", labelrotation=45, labelsize=8)
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %y"))
    axes[0].set_ylabel("Cumulative benefit (€k)")
    axes[0].legend(fontsize=8, loc="lower right")
    as_of = pd.Timestamp(decisions["as_of"].iloc[0]) if len(decisions) else None
    when = f" As of {as_of:%d %B %Y}." if as_of is not None else ""
    fig.suptitle(f"Cumulative planned vs. realised value.{when} {FICTION}", fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def adoption_chart(tracking: pd.DataFrame, decisions: pd.DataFrame, path: Path) -> Path:
    """Realised adoption per use case (solid) against the business case plan (dotted)."""
    info = decisions.set_index("id")
    fig, ax = plt.subplots(figsize=(8.5, 4.4), dpi=150)
    for i, uc in enumerate(dict.fromkeys(tracking["use_case_id"])):
        g = tracking[tracking["use_case_id"] == uc]
        colour, marker = CASE_STYLES[i % len(CASE_STYLES)]
        months_since = range(1, len(g) + 1)
        stopped = uc in info.index and info.loc[uc, "status"] == "stopped"
        ax.plot(months_since, g["adoption_rate"], color=colour, linewidth=2.2, marker=marker, markersize=4,
                label=f"{uc} realised" + (" (stopped)" if stopped else ""))
        plan = planned_adoption(uc, len(g))
        if plan:
            ax.plot(months_since, plan, color=colour, linewidth=1.4, linestyle=":", label=f"{uc} plan")
    ax.set_xlabel("Months since go-live or pilot start")
    ax.set_ylabel("Share of volume processed with the AI solution")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_xticks(range(1, int(tracking.groupby("use_case_id").size().max()) + 1))
    ax.grid(color="0.92")
    ax.legend(fontsize=8, ncol=4, loc="lower right")
    ax.set_title(f"Adoption: realised (solid) vs. plan (dotted). {FICTION}", fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python dashboard/charts.py", description="Draw the portfolio charts.")
    parser.add_argument("--tracking", type=Path, default=DEFAULT_TRACKING)
    parser.add_argument("--decisions", type=Path, default=None,
                        help="Decisions CSV (default: decisions.csv in the output directory).")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    try:
        tracking = load_tracking(args.tracking)
        decisions = load_decisions(args.decisions or args.output_dir / "decisions.csv")
        unknown = sorted(set(tracking["use_case_id"]) - set(decisions["id"]))
        if unknown:
            raise InputError([f"{args.tracking}: use cases not in the decisions file: {', '.join(unknown)}."])
    except InputError as exc:
        print("Input error:", file=sys.stderr)
        for message in exc.errors:
            print(f"  - {message}", file=sys.stderr)
        return 2
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    written = [
        portfolio_overview(decisions, out / "portfolio_overview.png"),
        cumulative_value(tracking, decisions, out / "cumulative_value.png"),
        adoption_chart(tracking, decisions, out / "adoption.png"),
    ]
    for p in written:
        print(f"Wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
