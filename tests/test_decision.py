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
