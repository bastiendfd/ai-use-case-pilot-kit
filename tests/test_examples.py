"""Tests on the fictional example portfolio (examples/ and outputs/)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scoring import build_examples as be
from scoring import business_case as bc

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"

EXPECTED = {  # id: (AI Act category, first decision), as in the project brief
    "UC-01": ("minimal", "go_with_conditions"),
    "UC-02": ("minimal", "go"),
    "UC-03": ("minimal", "pilot"),
    "UC-04": ("minimal", "park"),
    "UC-05": ("limited", "pilot"),
    "UC-06": ("high", "reject"),
}


@pytest.fixture(scope="module")
def generated():
    return be.generate()


@pytest.fixture(scope="module")
def table(generated):
    return {row["id"]: row for row in generated[1]}


def folder(uc: str) -> Path:
    return next(EXAMPLES.glob(f"{uc}_*"))


def test_six_cases_with_all_files():
    for uc in EXPECTED:
        files = {p.name for p in folder(uc).iterdir()}
        assert set(be.HAND_WRITTEN) | {"triage.md", "business_case.md", "decision_record.md"} <= files, uc


def test_committed_generated_files_are_up_to_date(generated):
    files, rows = generated
    files = dict(files)
    files[ROOT / "outputs" / "decisions.csv"] = be.decisions_csv(rows)
    stale = [str(p.relative_to(ROOT)) for p, text in files.items()
             if not p.is_file() or p.read_text(encoding="utf-8") != text]
    assert not stale, "Run python -m scoring.build_examples; out of date: " + ", ".join(stale)


def test_expected_outcomes(table):
    first = {uc: r["decision_history"].split(" (")[0] for uc, r in table.items()}
    assert {uc: (r["ai_act_category"], first[uc]) for uc, r in table.items()} == EXPECTED
    # Where the story stands on the as-of date (2027-12-31).
    assert {uc: r["status"] for uc, r in table.items()} == {
        "UC-01": "go_with_conditions", "UC-02": "go", "UC-03": "go_with_conditions",
        "UC-04": "park", "UC-05": "stopped", "UC-06": "reject"}
    assert table["UC-01"]["quadrant"] == "quick win" and table["UC-01"]["rank"] == 1


def test_every_example_file_says_it_is_fictional():
    for path in EXAMPLES.rglob("*"):
        if path.suffix in (".md", ".yaml"):
            assert "fictional" in path.read_text(encoding="utf-8").lower(), path
    assert "(fictional)" in (EXAMPLES / "use_cases.csv").read_text(encoding="utf-8")


def test_uc01_inputs_match_the_workbook_template():
    template = bc.load_inputs(ROOT / "templates" / "business_case_inputs.yaml")
    example = bc.load_inputs(folder("UC-01") / "business_case_inputs.yaml")
    assert example.inputs == template.inputs and example.scenarios == template.scenarios


def test_uc01_record_is_go_with_conditions_with_pessimistic_npv():
    case = bc.load_inputs(folder("UC-01") / "business_case_inputs.yaml")
    pess = bc.compute_all(case)["pessimistic"]["npv_3y"]
    record = (folder("UC-01") / "decision_record.md").read_text(encoding="utf-8")
    assert "| Decision | **Go with conditions** |" in record
    assert f"Pessimistic NPV: {bc._eur(pess)}." in record
    assert "review gate on **2027-04-11**, 3 months after go-live" in record
    assert "time saved at or below 3 minutes per transaction" in record
    assert "at or below 60%" in record


def test_downside_rule_applied_wherever_a_scenario_is_negative(table):
    """Every approving decision with a negative scenario has a 3-month gate and shows the pessimistic NPV."""
    gated = []
    for uc, row in table.items():
        record = (folder(uc) / "decision_record.md").read_text(encoding="utf-8")
        assert f"NPV: {bc._eur(row['npv_pessimistic_eur'])}" in record, uc
        if row["negative_scenario"] == "yes" and row["decision"] in ("go", "go_with_conditions", "pilot"):
            gated.append(uc)
            assert row["decision"] != "go", uc
            assert row["review_gate_date"], uc
            assert "| Stop or rework if |" in record, uc
            assert "## 7. Conditions attached\n\n- Review gate on" in record, uc
    assert gated == ["UC-01", "UC-03", "UC-05"]


def test_ranking_outputs_exist_and_match_the_scores(table):
    with open(ROOT / "outputs" / "ranking.csv", encoding="utf-8") as handle:
        ranking = {r["id"]: r for r in csv.DictReader(handle)}
    for uc, row in table.items():
        assert float(ranking[uc]["weighted_score"]) == float(row["weighted_score"])
    for name in ("ranking.md", "value_feasibility_matrix.png", "sensitivity.md", "decisions.csv"):
        assert (ROOT / "outputs" / name).is_file()


def test_check_mode_passes_on_committed_files():
    assert be.main(["--check"]) == 0


def test_uc03_record_shows_the_gate_firing_and_the_rework():
    record = (folder("UC-03") / "decision_record.md").read_text(encoding="utf-8")
    assert "| Review gate outcomes | rework (2027-03-01), continue (2027-06-01); see section 9 |" in record
    assert "### Gate 1: 2027-03-01. Decision: **Rework**" in record
    assert "| at or above 14.0% | 15% | **yes** |" in record
    assert "### Gate 2: 2027-06-01. Decision: **Continue**" in record


def test_gate_outcomes_in_decisions_table(table):
    assert table["UC-03"]["gate_outcomes"] == "rework (2027-03-01), continue (2027-06-01), continue (2027-10-01)"
    assert table["UC-01"]["gate_outcomes"] == "continue (2027-04-11)"
    assert table["UC-05"]["gate_outcomes"] == "stop (2027-04-11)"
    assert all(table[uc]["gate_outcomes"] == "" for uc in ("UC-02", "UC-04", "UC-06"))
