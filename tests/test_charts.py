"""Tests for dashboard/charts.py, the value tracking data and the matrix legend. Fictional data."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

from dashboard import charts
from scoring import business_case as bc
from scoring import score
from scoring.errors import InputError

ROOT = Path(__file__).resolve().parent.parent
TRACKING = ROOT / "data" / "value_tracking.csv"
DECISIONS = ROOT / "outputs" / "decisions.csv"


@pytest.fixture(scope="module")
def tracking() -> pd.DataFrame:
    return charts.load_tracking(TRACKING)


def folder(uc: str) -> Path:
    return next((ROOT / "examples").glob(f"{uc}_*"))


# ---------------------------------------------------------------------------
# data/value_tracking.csv
# ---------------------------------------------------------------------------


def test_tracking_has_the_required_columns_and_12_months_per_case(tracking):
    with open(TRACKING, encoding="utf-8") as handle:
        assert tuple(next(csv.reader(handle))) == charts.TRACKING_COLUMNS
    assert tracking.groupby("use_case_id").size().to_dict() == {"UC-01": 12, "UC-02": 12, "UC-03": 12}


@pytest.mark.parametrize("uc", ["UC-01", "UC-02", "UC-03"])
def test_tracking_starts_at_go_live_and_planned_matches_the_business_case(tracking, uc):
    import yaml
    decision = yaml.safe_load((folder(uc) / "decision.yaml").read_text(encoding="utf-8"))
    g = tracking[tracking["use_case_id"] == uc]
    start = pd.Timestamp(decision["start_date"]).replace(day=1)
    assert g["month"].iloc[0] == start
    case = bc.load_inputs(folder(uc) / "business_case_inputs.yaml")
    plan = bc.compute(case.values("base"))["months"]
    assert list(g["planned_benefit_eur"]) == [round(plan[m]["benefit"]) for m in range(1, 13)]


def test_uc03_under_delivers_with_an_explanation(tracking):
    totals = tracking.groupby("use_case_id")[["planned_benefit_eur", "realised_benefit_eur"]].sum()
    share = totals["realised_benefit_eur"] / totals["planned_benefit_eur"]
    assert share["UC-03"] < 0.6
    assert share["UC-01"] > 0.85 and share["UC-02"] > 0.95
    notes = " ".join(tracking.loc[tracking["use_case_id"] == "UC-03", "notes"])
    assert "Review gate 2027-03-01 fired" in notes and "Decision: rework" in notes
    assert "engine-shop" in notes   # the reason for the remaining gap


def test_tracking_validation(tmp_path):
    bad = pd.read_csv(TRACKING, dtype=str, keep_default_na=False)
    bad.loc[0, "adoption_rate"] = "1.4"
    bad.loc[1, "month"] = "2027-02-15"
    bad = pd.concat([bad, bad.iloc[[5]]])
    path = tmp_path / "t.csv"
    bad.to_csv(path, index=False)
    with pytest.raises(InputError) as exc:
        charts.load_tracking(path)
    text = " ".join(exc.value.errors)
    assert "first day of a month" in text and "between 0 and 1" in text and "duplicate" in text


def test_tracking_months_must_be_consecutive(tmp_path):
    df = pd.read_csv(TRACKING, dtype=str, keep_default_na=False)
    df = df.drop(index=3)
    path = tmp_path / "t.csv"
    df.to_csv(path, index=False)
    with pytest.raises(InputError, match="months of UC-01 must be consecutive"):
        charts.load_tracking(path)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def test_gate_events():
    events = charts.gate_events("rework (2027-03-01), continue (2027-06-01)")
    assert events == [(pd.Timestamp("2027-03-01"), "rework"), (pd.Timestamp("2027-06-01"), "continue")]
    assert charts.gate_events("") == []


def test_charts_main_writes_three_pngs(tmp_path):
    (tmp_path / "decisions.csv").write_bytes(DECISIONS.read_bytes())
    assert charts.main(["--output-dir", str(tmp_path)]) == 0
    for name in ("portfolio_overview.png", "cumulative_value.png", "adoption.png"):
        assert (tmp_path / name).stat().st_size > 20_000, name


def test_charts_refuse_tracking_for_unknown_use_cases(tmp_path, capsys):
    df = pd.read_csv(TRACKING, dtype=str, keep_default_na=False)
    df["use_case_id"] = df["use_case_id"].replace("UC-02", "UC-99")
    df.to_csv(tmp_path / "t.csv", index=False)
    assert charts.main(["--tracking", str(tmp_path / "t.csv"), "--decisions", str(DECISIONS),
                        "--output-dir", str(tmp_path)]) == 2
    assert "UC-99" in capsys.readouterr().err


def test_portfolio_overview_lists_every_decision():
    decisions = charts.load_decisions(DECISIONS)
    assert list(decisions["id"]) == ["UC-01", "UC-02", "UC-03", "UC-05", "UC-04", "UC-06"]  # rank order
    assert decisions.set_index("id").loc["UC-03", "gate_outcomes"] == "rework (2027-03-01), continue (2027-06-01)"


# ---------------------------------------------------------------------------
# Matrix legend
# ---------------------------------------------------------------------------


def test_matrix_uses_decisions_when_given(tmp_path):
    csv_path = ROOT / "examples" / "use_cases.csv"
    assert score.main([str(csv_path), "--output-dir", str(tmp_path), "--decisions", str(DECISIONS)]) == 0
    assert score.main([str(csv_path), "--output-dir", str(tmp_path / "plain")]) == 0
    assert (tmp_path / "value_feasibility_matrix.png").stat().st_size > 20_000


def test_matrix_decisions_file_is_validated(tmp_path, capsys):
    bad = tmp_path / "d.csv"
    bad.write_text("id,decision\nUC-01,maybe\n", encoding="utf-8")
    code = score.main([str(ROOT / "examples" / "use_cases.csv"), "--output-dir", str(tmp_path),
                       "--decisions", str(bad)])
    assert code == 2
    assert "unknown decision(s): maybe" in capsys.readouterr().err


def test_readme_opens_with_the_portfolio_figure():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    first_image = next(i for i, line in enumerate(readme) if line.startswith("!["))
    assert first_image <= 3, "the portfolio figure must be at the top of the README"
    assert "(outputs/portfolio_overview.png)" in readme[first_image]
    assert (ROOT / "outputs" / "portfolio_overview.png").is_file()
