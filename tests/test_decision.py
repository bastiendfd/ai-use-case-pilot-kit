"""Tests for scoring/decision.py: decision rules tied to the computed results. Fictional data."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
import yaml

from scoring import business_case as bc
from scoring import decision as dec
from scoring.errors import InputError

ROOT = Path(__file__).resolve().parent.parent
UC01 = ROOT / "examples" / "UC-01_delivery_note_ocr"
PASS = {"gate_result": "pass"}


@pytest.fixture()
def raw() -> dict:
    return yaml.safe_load((UC01 / "decision.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def case() -> bc.CaseInputs:
    return bc.load_inputs(UC01 / "business_case_inputs.yaml")


def load(tmp_path: Path, raw: dict) -> dict:
    path = tmp_path / "decision.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return dec.load_decision(path)


def test_add_months():
    assert dec.add_months(dt.date(2027, 1, 11), 3) == dt.date(2027, 4, 11)
    assert dec.add_months(dt.date(2026, 11, 30), 3) == dt.date(2027, 2, 28)
    assert dec.add_months(dt.date(2026, 12, 1), 3) == dt.date(2027, 3, 1)


def test_plain_go_is_refused_when_a_scenario_is_negative(tmp_path, raw, case):
    raw["decision"] = "go"
    with pytest.raises(InputError, match="plain 'go' is not allowed"):
        dec.check_decision(load(tmp_path, raw), PASS, bc.downside(case))


def test_go_with_conditions_needs_gate_metrics_and_start_date(tmp_path, raw, case):
    del raw["gate_metrics"]["adoption_steady"]
    del raw["start_date"]
    with pytest.raises(InputError) as exc:
        dec.check_decision(load(tmp_path, raw), PASS, bc.downside(case))
    text = " ".join(exc.value.errors)
    assert "start_date" in text and "adoption_steady" in text


def test_gate_date_is_three_months_after_start(tmp_path, raw):
    d = load(tmp_path, raw)
    assert dec.gate_date(d) == dec.add_months(d["start_date"], bc.REVIEW_GATE_MONTHS)


def test_negative_base_case_cannot_go_live(tmp_path, raw, case):
    downside = dict(bc.downside(case), negative_scenarios=["pessimistic", "base"])
    with pytest.raises(InputError, match="base case NPV is negative"):
        dec.check_decision(load(tmp_path, raw), PASS, downside)


def test_hard_gate_overrides_the_decision(tmp_path, raw, case):
    with pytest.raises(InputError, match="must be 'reject'"):
        dec.check_decision(load(tmp_path, raw), {"gate_result": "reject"}, bc.downside(case))
    with pytest.raises(InputError, match="must be 'park' or 'reject'"):
        dec.check_decision(load(tmp_path, raw), {"gate_result": "park"}, bc.downside(case))


@pytest.mark.parametrize("field, value, message", [
    ("decision", "maybe", "must be one of"),
    ("decision_date", "next week", "must be a date"),
    ("summary", "", "'summary' is required"),
])
def test_invalid_decision_file(tmp_path, raw, field, value, message):
    raw[field] = value
    with pytest.raises(InputError, match=message):
        load(tmp_path, raw)


def test_park_needs_a_reopening_trigger(tmp_path, raw):
    raw["decision"] = "park"
    with pytest.raises(InputError, match="reopening_trigger"):
        load(tmp_path, raw)


def test_no_gate_without_negative_scenario(tmp_path, raw, case):
    downside = dict(bc.downside(case), negative_scenarios=[])
    raw["decision"] = "go"
    d = load(tmp_path, raw)
    dec.check_decision(d, PASS, downside)          # allowed
    assert not dec.gate_applies(d, downside)


# ---------------------------------------------------------------------------
# Review gate outcomes (UC-03, fictional)
# ---------------------------------------------------------------------------

UC03 = ROOT / "examples" / "UC-03_work_order_classification"


@pytest.fixture()
def raw03() -> dict:
    return yaml.safe_load((UC03 / "decision.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def case03() -> bc.CaseInputs:
    return bc.load_inputs(UC03 / "business_case_inputs.yaml")


def evaluate(tmp_path, raw, case):
    return dec.evaluate_gate_reviews(load(tmp_path, raw), case, bc.downside(case))


def test_uc03_first_gate_fires_and_rework_is_allowed(tmp_path, raw03, case03):
    first, second = evaluate(tmp_path, raw03, case03)
    hits = {r["input"]: r["hit"] for r in first["rows"]}
    assert hits == {"error_rate_after": True, "minutes_after": False, "adoption_steady": True}
    assert first["decision"] == "rework"
    assert first["npv_measured"] < 0 < first["npv_rework"]
    # Hand check: measured values with the base inputs otherwise.
    values = dict(case03.values("base"), error_rate_after=0.15, minutes_after=0.8, adoption_steady=0.45)
    assert first["npv_measured"] == pytest.approx(bc.compute(values)["npv_3y"])
    assert not any(r["hit"] for r in second["rows"])
    assert second["earlier_cost"] == 18_000          # rework cost carried into the next re-run
    assert dec.gate_status(load(tmp_path, raw03), [first, second]) == \
        "rework (2027-03-01), continue (2027-06-01)"


def test_continue_is_refused_when_a_trigger_is_reached(tmp_path, raw03, case03):
    raw03["gate_reviews"] = raw03["gate_reviews"][:1]
    raw03["gate_reviews"][0]["decision"] = "continue"
    with pytest.raises(InputError, match="must be rework or stop"):
        evaluate(tmp_path, raw03, case03)


def test_rework_is_refused_when_the_rework_plan_does_not_pay_back(tmp_path, raw03, case03):
    raw03["gate_reviews"] = raw03["gate_reviews"][:1]
    raw03["gate_reviews"][0]["rework_cost_eur"] = 400_000
    with pytest.raises(InputError, match="rule leaves only stop"):
        evaluate(tmp_path, raw03, case03)


def test_rework_is_refused_when_no_trigger_is_reached(tmp_path, raw03, case03):
    raw03["gate_reviews"] = raw03["gate_reviews"][:1]
    raw03["gate_reviews"][0]["measured"] = {"error_rate_after": 0.08, "minutes_after": 0.5,
                                            "adoption_steady": 0.8}
    with pytest.raises(InputError, match="must be continue or stop"):
        evaluate(tmp_path, raw03, case03)


def test_stop_is_always_allowed_and_closes_the_sequence(tmp_path, raw03, case03):
    raw03["gate_reviews"][0]["decision"] = "stop"
    with pytest.raises(InputError, match="closes the gate sequence"):
        evaluate(tmp_path, raw03, case03)
    raw03["gate_reviews"] = raw03["gate_reviews"][:1]
    assert evaluate(tmp_path, raw03, case03)[0]["decision"] == "stop"


@pytest.mark.parametrize("index, date, message", [
    (0, "2027-02-15", "expected 2027-03-01"),
    (1, "2027-07-01", "expected 2027-06-01"),
])
def test_gate_dates_follow_the_gate_and_next_gate(tmp_path, raw03, case03, index, date, message):
    raw03["gate_reviews"][index]["date"] = date
    with pytest.raises(InputError, match=message):
        evaluate(tmp_path, raw03, case03)


def test_each_trigger_needs_a_measured_value(tmp_path, raw03, case03):
    del raw03["gate_reviews"][0]["measured"]["adoption_steady"]
    with pytest.raises(InputError, match="measured value missing for trigger"):
        evaluate(tmp_path, raw03, case03)


def test_rework_needs_actions_and_next_gate(tmp_path, raw03):
    del raw03["gate_reviews"][0]["actions"]
    del raw03["gate_reviews"][0]["next_gate"]
    with pytest.raises(InputError) as exc:
        load(tmp_path, raw03)
    text = " ".join(exc.value.errors)
    assert "needs 'actions'" in text and "needs 'next_gate'" in text


def test_gate_reviews_need_a_gated_decision(tmp_path, raw03, case03):
    downside = dict(bc.downside(case03), negative_scenarios=[])
    with pytest.raises(InputError, match="only allowed when the decision carries a review gate"):
        dec.evaluate_gate_reviews(load(tmp_path, raw03), case03, downside)
