"""Tests for scoring/score.py. All test data is fictional."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from scoring import score as s

FIXTURE = Path(__file__).parent / "fixtures" / "sample_use_cases.csv"


@pytest.fixture(scope="module")
def criteria() -> s.Criteria:
    return s.load_criteria()


@pytest.fixture()
def raw_rows() -> list[dict]:
    """A small valid table, as text, like a CSV read."""
    return pd.read_csv(FIXTURE, dtype=str, keep_default_na=False).to_dict("records")


def write_csv(tmp_path: Path, rows: list[dict], name: str = "cases.csv") -> Path:
    path = tmp_path / name
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def case(**overrides) -> dict:
    """One valid use case; override any field."""
    row = {
        "id": "X-01", "title": "Fictional case", "ai_act_category": "minimal",
        "process_owner": "Owner", "data_owner": "Data owner",
        "restricted_data": "no", "approved_environment_available": "no",
        "business_value": 3, "feasibility": 3, "data_maturity": 3,
        "ai_maturity": 3, "risk": 3, "strategic_fit": 3,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Criteria and weights
# ---------------------------------------------------------------------------


def test_default_weights_sum_to_100(criteria):
    assert sum(criteria.weights.values()) == pytest.approx(100)


def test_default_weights_match_the_brief(criteria):
    assert criteria.weights == {
        "business_value": 30, "feasibility": 20, "data_maturity": 20,
        "ai_maturity": 10, "risk": 10, "strategic_fit": 10,
    }


def test_every_criterion_describes_all_five_levels():
    raw = yaml.safe_load(s.DEFAULT_CRITERIA.read_text(encoding="utf-8"))
    for item in raw["criteria"]:
        assert sorted(item["levels"]) == [1, 2, 3, 4, 5], item["id"]
        assert all(str(text).strip() for text in item["levels"].values()), item["id"]
        assert item["why_this_weight"].strip(), item["id"]


def test_criteria_file_with_bad_weights_is_rejected(tmp_path):
    raw = yaml.safe_load(s.DEFAULT_CRITERIA.read_text(encoding="utf-8"))
    raw["criteria"][0]["weight"] = 35
    bad = tmp_path / "criteria.yaml"
    bad.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(s.InputError, match="sum to 100, got 105"):
        s.load_criteria(bad)


def test_parse_weights_partial_override(criteria):
    w = s.parse_weights("business_value=40,feasibility=10", criteria)
    assert w["business_value"] == 40 and w["feasibility"] == 10
    assert sum(w.values()) == pytest.approx(100)


def test_parse_weights_from_yaml_file(criteria, tmp_path):
    path = tmp_path / "w.yaml"
    path.write_text("business_value: 20\nstrategic_fit: 20\n", encoding="utf-8")
    w = s.parse_weights(str(path), criteria)
    assert w["business_value"] == 20 and w["strategic_fit"] == 20


@pytest.mark.parametrize("spec, message", [
    ("business_value=50", "sum to 100, got 120"),
    ("value=30", "Unknown criterion 'value'"),
    ("business_value=high", "must be a number"),
    ("business_value", "Use criterion=weight"),
    ("business_value=40,feasibility=-10,data_maturity=40", "must not be negative"),
])
def test_parse_weights_rejects_bad_specs(criteria, spec, message):
    with pytest.raises(s.InputError, match=message):
        s.parse_weights(spec, criteria)


# ---------------------------------------------------------------------------
# Score formula
# ---------------------------------------------------------------------------


def test_weighted_score_hand_calculated(criteria):
    # 30x5/5 + 20x4/5 + 20x3/5 + 10x2/5 + 10x1/5 + 10x5/5 = 30+16+12+4+2+10 = 74
    row = case(business_value=5, feasibility=4, data_maturity=3, ai_maturity=2, risk=1, strategic_fit=5)
    assert s.weighted_score(row, criteria.weights) == pytest.approx(74.0)
    assert s.weighted_contributions(row, criteria.weights) == pytest.approx({
        "business_value": 30, "feasibility": 16, "data_maturity": 12,
        "ai_maturity": 4, "risk": 2, "strategic_fit": 10,
    })


def test_score_bounds(criteria):
    top = case(**{c: 5 for c in criteria.ids})
    bottom = case(**{c: 1 for c in criteria.ids})
    assert s.weighted_score(top, criteria.weights) == pytest.approx(100)
    assert s.weighted_score(bottom, criteria.weights) == pytest.approx(20)


@pytest.mark.parametrize("value, feas, data, expected", [
    (4, 4, 3, "quick win"),       # feasibility axis = mean(4, 3) = 3.5 -> high
    (5, 2, 3, "strategic bet"),
    (3, 5, 5, "fill-in"),
    (2, 2, 2, "avoid"),
])
def test_quadrant(criteria, value, feas, data, expected):
    row = case(business_value=value, feasibility=feas, data_maturity=data)
    assert s.quadrant(row, criteria) == expected


# ---------------------------------------------------------------------------
# Hard gates
# ---------------------------------------------------------------------------


def test_gate_pass():
    assert s.apply_gates(case()) == (s.GATE_PASS, "")


def test_gate_prohibited_is_rejected_whatever_the_score(criteria):
    row = case(ai_act_category="prohibited", **{c: 5 for c in criteria.ids})
    result, reason = s.apply_gates(row)
    assert result == s.GATE_REJECT
    assert "Prohibited" in reason


def test_gate_prohibited_wins_over_park():
    row = case(ai_act_category="prohibited", data_owner="")
    assert s.apply_gates(row)[0] == s.GATE_REJECT


@pytest.mark.parametrize("field", ["process_owner", "data_owner"])
@pytest.mark.parametrize("value", ["", "TBD", "none", "n/a"])
def test_gate_missing_owner_parks(field, value):
    result, reason = s.apply_gates(case(**{field: value}))
    assert result == s.GATE_PARK
    assert field.replace("_", " ") in reason.lower()


def test_gate_restricted_data_without_approved_environment_parks():
    result, reason = s.apply_gates(case(restricted_data="yes", approved_environment_available="no"))
    assert result == s.GATE_PARK
    assert "export-controlled" in reason.lower()


def test_gate_restricted_data_with_approved_environment_passes():
    assert s.apply_gates(case(restricted_data="yes", approved_environment_available="yes"))[0] == s.GATE_PASS


def test_gate_combines_park_reasons():
    result, reason = s.apply_gates(case(process_owner="", restricted_data="yes"))
    assert result == s.GATE_PARK
    assert "process owner" in reason and "export-controlled" in reason


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["0", "6", "3.5", "abc", "", "-1"])
def test_invalid_scores_are_rejected(tmp_path, criteria, bad):
    path = write_csv(tmp_path, [case(feasibility=bad)])
    with pytest.raises(s.InputError) as exc:
        s.load_use_cases(path, criteria)
    message = str(exc.value)
    assert "X-01 (line 2)" in message
    assert "'feasibility' must be an integer from 1 to 5" in message


def test_missing_column_is_reported(tmp_path, criteria):
    row = case()
    del row["data_maturity"]
    path = write_csv(tmp_path, [row])
    with pytest.raises(s.InputError, match="missing required column.*data_maturity"):
        s.load_use_cases(path, criteria)


@pytest.mark.parametrize("field, value, message", [
    ("ai_act_category", "medium", "'ai_act_category' must be one of"),
    ("restricted_data", "maybe", "'restricted_data' must be yes or no"),
    ("approved_environment_available", "", "'approved_environment_available' must be yes or no"),
    ("title", "", "'title' is empty"),
    ("id", "", "'id' is empty"),
])
def test_invalid_fields_are_rejected(tmp_path, criteria, field, value, message):
    path = write_csv(tmp_path, [case(**{field: value})])
    with pytest.raises(s.InputError, match=message):
        s.load_use_cases(path, criteria)


def test_all_errors_are_reported_together(tmp_path, criteria):
    path = write_csv(tmp_path, [case(risk="9", restricted_data="maybe")])
    with pytest.raises(s.InputError) as exc:
        s.load_use_cases(path, criteria)
    assert len(exc.value.errors) == 2


def test_duplicate_ids_are_rejected(tmp_path, criteria):
    path = write_csv(tmp_path, [case(), case()])
    with pytest.raises(s.InputError, match="Duplicate use-case id"):
        s.load_use_cases(path, criteria)


def test_header_only_file_is_rejected(tmp_path, criteria):
    path = tmp_path / "empty.csv"
    path.write_text(",".join(case().keys()) + "\n", encoding="utf-8")
    with pytest.raises(s.InputError, match="no use cases found"):
        s.load_use_cases(path, criteria)


def test_missing_file_is_reported(tmp_path, criteria):
    with pytest.raises(s.InputError, match="not found"):
        s.load_use_cases(tmp_path / "nope.csv", criteria)


def test_values_are_normalised(tmp_path, criteria):
    path = write_csv(tmp_path, [case(ai_act_category=" Minimal ", restricted_data="YES",
                                     approved_environment_available="Yes", risk=" 4 ")])
    df = s.load_use_cases(path, criteria)
    assert df.loc[0, "ai_act_category"] == "minimal"
    assert df.loc[0, "restricted_data"] == "yes"
    assert df.loc[0, "risk"] == 4


def test_cli_returns_error_code_on_invalid_input(tmp_path, capsys):
    path = write_csv(tmp_path, [case(feasibility="7")])
    code = s.main([str(path), "--output-dir", str(tmp_path / "out")])
    assert code == 2
    assert "'feasibility' must be an integer from 1 to 5, got '7'" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_ranking_order_on_fixture(criteria):
    df = s.load_use_cases(FIXTURE, criteria)
    ranked = s.score_use_cases(df, criteria)
    # Hand-calculated: T-01 94.0, T-02 70.0, T-04 66.0, T-03 62.0.
    passed = ranked[ranked["gate_result"] == s.GATE_PASS]
    assert list(passed["id"]) == ["T-01", "T-02", "T-04", "T-03"]
    assert list(passed["weighted_score"]) == [94.0, 70.0, 66.0, 62.0]
    assert list(passed["rank"]) == [1, 2, 3, 4]


def test_gated_cases_are_listed_after_ranked_cases_without_rank(criteria):
    df = s.load_use_cases(FIXTURE, criteria)
    ranked = s.score_use_cases(df, criteria)
    gated = ranked[ranked["gate_result"] != s.GATE_PASS]
    assert list(gated["id"]) == ["T-05", "T-06", "T-07"]  # reject first, then park
    assert gated["rank"].isna().all()
    assert list(gated["gate_result"]) == ["reject", "park", "park"]
    # T-05 has a high score but is rejected at the gate.
    assert ranked.loc[ranked["id"] == "T-05", "weighted_score"].item() > 90


def test_ranking_tie_break_by_business_value_then_id(criteria):
    rows = [
        case(id="B", business_value=3, feasibility=4),  # 18 + 16 + 12 + 6 + 6 + 6 = 64
        case(id="A", business_value=3, feasibility=4),  # same score, same value -> id order
        case(id="C", business_value=4, feasibility=3, data_maturity=3, ai_maturity=2,
             risk=3, strategic_fit=4),  # 24 + 12 + 12 + 4 + 6 + 8 = 66
        case(id="D", business_value=4, feasibility=3, ai_maturity=3, risk=2),  # 24+12+12+6+4+6 = 64
    ]
    df = s.validate_use_cases(pd.DataFrame(rows).astype(str), criteria)
    ranked = s.score_use_cases(df, criteria)
    assert list(ranked["id"]) == ["C", "D", "A", "B"]


def test_ranking_changes_with_custom_weights(criteria):
    df = s.load_use_cases(FIXTURE, criteria)
    weights = s.parse_weights("business_value=10,feasibility=40", criteria)
    ranked = s.score_use_cases(df, criteria, weights)
    passed = ranked[ranked["gate_result"] == s.GATE_PASS]
    assert list(passed["id"])[:2] == ["T-01", "T-04"]


def test_contributions_add_up_to_score(criteria):
    df = s.load_use_cases(FIXTURE, criteria)
    ranked = s.score_use_cases(df, criteria)
    contrib_cols = [f"contrib_{c}" for c in criteria.ids]
    assert (ranked[contrib_cols].sum(axis=1) - ranked["weighted_score"]).abs().max() < 0.2


def test_rationale_names_strengths_and_gate(criteria):
    df = s.load_use_cases(FIXTURE, criteria)
    ranked = s.score_use_cases(df, criteria).set_index("id")
    assert ranked.loc["T-04", "rationale"].startswith("Fill-in: strongest on risk (inverted) (5)")
    assert "weakest on business value (2)" in ranked.loc["T-04", "rationale"]
    assert ranked.loc["T-06", "rationale"].startswith("Parked at the gate: no data owner")


def test_consistency_warning_for_high_risk_with_low_risk_score(criteria):
    df = s.validate_use_cases(pd.DataFrame([case(ai_act_category="high", risk=4)]).astype(str), criteria)
    warnings = s.consistency_warnings(df)
    assert len(warnings) == 1 and "X-01" in warnings[0]


# ---------------------------------------------------------------------------
# Sensitivity
# ---------------------------------------------------------------------------


def test_shifted_weights_keep_total_and_proportions(criteria):
    w = s.shifted_weights(criteria.weights, "business_value", 10)
    assert w["business_value"] == 40
    assert sum(w.values()) == pytest.approx(100)
    # The others keep their 2:2:1:1:1 proportions.
    assert w["feasibility"] == pytest.approx(2 * w["risk"])
    assert w["feasibility"] == pytest.approx(60 * 20 / 70)


def test_shifted_weights_out_of_range_returns_none(criteria):
    weights = dict(criteria.weights, ai_maturity=5, strategic_fit=15)
    assert s.shifted_weights(weights, "ai_maturity", -10) is None


def test_sensitivity_reports_every_variation(criteria):
    df = s.load_use_cases(FIXTURE, criteria)
    result = s.sensitivity(df, criteria)
    assert len(result) == 2 * len(criteria.ids)
    assert result.attrs["base_top"] == ["T-01", "T-02", "T-04"]


def test_sensitivity_detects_top3_change(criteria):
    # With business value at 40, T-03 (value 4) overtakes T-04 (value 2):
    # T-03 = 64.6, T-04 = 62.3 (hand-calculated with the others rescaled by 60/70).
    df = s.load_use_cases(FIXTURE, criteria)
    result = s.sensitivity(df, criteria).set_index(["criterion", "change"])
    assert bool(result.loc[("business_value", "+10"), "set_changed"]) is True
    assert "T-03" in result.loc[("business_value", "+10"), "top"]
    assert bool(result.loc[("strategic_fit", "-10"), "set_changed"]) is False


def test_cli_writes_all_outputs(tmp_path, capsys):
    out = tmp_path / "out"
    code = s.main([str(FIXTURE), "--output-dir", str(out), "--sensitivity"])
    assert code == 0
    for name in ("ranking.csv", "ranking.md", "value_feasibility_matrix.png", "sensitivity.md"):
        assert (out / name).is_file(), name
    assert (out / "value_feasibility_matrix.png").stat().st_size > 10_000
    ranking = pd.read_csv(out / "ranking.csv")
    assert list(ranking["id"].head(4)) == ["T-01", "T-02", "T-04", "T-03"]
    md = (out / "ranking.md").read_text(encoding="utf-8")
    assert "| Rank | ID | Title |" in md
    sens = (out / "sensitivity.md").read_text(encoding="utf-8")
    assert "Base top 3: **T-01, T-02, T-04**" in sens
    printed = capsys.readouterr().out
    assert "Sensitivity: base top 3 = T-01, T-02, T-04" in printed
