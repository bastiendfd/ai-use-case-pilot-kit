"""Tests of the story rules: as-of date, successive decision records, review history.

FICTIONAL EXAMPLE DATA ("Northwind Aero Services").
"""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path

import pytest
import yaml

from scoring import build_examples as be
from scoring.errors import InputError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
TRACKING = ROOT / "data" / "value_tracking.csv"


@pytest.fixture()
def copy(tmp_path):
    """A writable copy of examples/ and the tracking file."""
    shutil.copytree(EXAMPLES, tmp_path / "examples")
    shutil.copy(TRACKING, tmp_path / "value_tracking.csv")
    return tmp_path


def run(tmp: Path):
    return be.generate(tmp / "examples" / "use_cases.csv", tmp / "examples" / "portfolio.yaml",
                       tmp / "value_tracking.csv")


def edit_yaml(path: Path, change) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def errors_of(tmp: Path) -> str:
    with pytest.raises(InputError) as exc:
        run(tmp)
    return "\n".join(exc.value.errors)


def uc(tmp: Path, prefix: str) -> Path:
    return next((tmp / "examples").glob(f"{prefix}_*"))


# ---------------------------------------------------------------------------
# As-of date
# ---------------------------------------------------------------------------


def test_as_of_date_is_set_and_stated_in_the_readme():
    assert be.load_portfolio()["as_of"] == dt.date(2027, 12, 31)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "31 December 2027" in readme


def test_the_committed_story_has_no_gaps(copy):
    files, table = run(copy)
    assert {r["as_of"] for r in table} == {"2027-12-31"}
    assert all(r["next_review"] > "2027-12-31" for r in table if r["status"] not in ("stopped", "reject"))


def test_a_missing_review_is_an_error(copy):
    edit_yaml(uc(copy, "UC-05") / "decision.yaml", lambda d: d.pop("gate_reviews"))
    assert "review due on 2027-04-11 is not recorded (as of 2027-12-31)" in errors_of(copy)


def test_an_earlier_as_of_date_rejects_later_reviews(copy):
    (copy / "examples" / "portfolio.yaml").write_text("as_of_date: 2027-05-31\n", encoding="utf-8")
    assert "dated after the as-of date 2027-05-31" in errors_of(copy)


def test_a_review_held_on_the_wrong_date_is_an_error(copy):
    def move(d):
        d["review_log"][0]["date"] = "2027-08-01"
    edit_yaml(uc(copy, "UC-04") / "decision.yaml", move)
    assert "review 1 is dated 2027-08-01, but the review due is 2027-09-01" in errors_of(copy)


def test_a_review_after_a_stop_is_an_error(copy):
    def add(d):
        d["review_log"] = [{"date": "2027-07-11", "type": "value review", "outcome": "continue",
                            "summary": "x", "next_review": "2028-01-11"}]
    edit_yaml(uc(copy, "UC-05") / "decision.yaml", add)
    assert "review_log entries can only follow a 'continue' at the review gate" in errors_of(copy)


def test_review_log_needs_a_next_review_unless_it_closes_the_case(copy):
    edit_yaml(uc(copy, "UC-04") / "decision.yaml", lambda d: d["review_log"][0].pop("next_review"))
    assert "'next_review' is required after 'remain_parked'" in errors_of(copy)


def test_tracking_must_run_to_the_as_of_month(copy):
    lines = (copy / "value_tracking.csv").read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not line.startswith("UC-01,2027-12-01")]
    (copy / "value_tracking.csv").write_text("\n".join(kept) + "\n", encoding="utf-8")
    assert "UC-01 must have one row per month from 2027-01-01 to 2027-12-01" in errors_of(copy)


def test_a_stopped_case_has_no_tracking_after_its_stop_month(copy):
    with open(copy / "value_tracking.csv", "a", encoding="utf-8") as handle:
        handle.write("UC-05,2027-05-01,1000,0,0,0,\n")
    assert "UC-05 must have one row per month from 2027-01-01 to 2027-04-01 (start to stop month)" \
        in errors_of(copy)


# ---------------------------------------------------------------------------
# Successive decision records (UC-03: pilot -> go with conditions)
# ---------------------------------------------------------------------------


def test_uc03_has_a_second_decision_record_after_the_second_review():
    folder = next(EXAMPLES.glob("UC-03_*"))
    first = (folder / "decision_record.md").read_text(encoding="utf-8")
    second = (folder / "decision_record_2.md").read_text(encoding="utf-8")
    assert "> **Superseded** on 2027-06-10 by [`decision_record_2.md`]" in first
    assert "**Status as of 2027-12-31:** superseded on 2027-06-10" in first
    assert "> **Follows** [`decision_record.md`](decision_record.md) (Pilot, 2026-10-20)." in second
    assert "| Decision | **Go with conditions** |" in second
    assert "| Decision date | 2027-06-10 |" in second
    assert "including €18,000 of earlier rework cost" in second
    assert "### Gate 1: 2027-10-01. Decision: **Continue**" in second
    assert "**Status as of 2027-12-31:** next review due on 2028-01-01." in second


def test_decision_files_must_be_numbered_without_gaps(copy):
    folder = uc(copy, "UC-03")
    (folder / "decision_2.yaml").rename(folder / "decision_3.yaml")
    assert "decision files must be numbered" in errors_of(copy)


def test_a_review_due_before_the_next_decision_must_be_recorded(copy):
    edit_yaml(uc(copy, "UC-03") / "decision.yaml",
              lambda d: d["gate_reviews"][1].update(next_review="2027-09-01"))
    edit_yaml(uc(copy, "UC-03") / "decision_2.yaml", lambda d: d.update(decision_date="2027-11-01"))
    text = errors_of(copy)
    assert "review due on 2027-09-01 is missing; the record was only superseded on 2027-11-01" in text
    assert "review(s) on 2027-10-01 not after the decision date 2027-11-01" in text


def test_successive_decisions_must_have_increasing_dates(copy):
    edit_yaml(uc(copy, "UC-03") / "decision_2.yaml", lambda d: d.update(decision_date="2026-10-01"))
    assert "increasing decision dates" in errors_of(copy)


# ---------------------------------------------------------------------------
# UC-05 stopped at its review gate
# ---------------------------------------------------------------------------


def test_uc05_gate_stops_the_pilot():
    folder = next(EXAMPLES.glob("UC-05_*"))
    record = (folder / "decision_record.md").read_text(encoding="utf-8")
    assert "### Gate 1: 2027-04-11. Decision: **Stop**" in record
    assert "| at or below 35% | 30% | **yes** |" in record
    assert "**Status as of 2027-12-31:** stopped on 2027-04-11. No further review." in record


def test_other_reviews_are_rendered():
    uc02 = (next(EXAMPLES.glob("UC-02_*")) / "decision_record.md").read_text(encoding="utf-8")
    assert "| 2027-12-01 | value review | **Scale** |" in uc02
    uc04 = (next(EXAMPLES.glob("UC-04_*")) / "decision_record.md").read_text(encoding="utf-8")
    assert "| 2027-09-01 | park review | **Remain parked** |" in uc04
    uc06 = (next(EXAMPLES.glob("UC-06_*")) / "decision_record.md").read_text(encoding="utf-8")
    assert "**Status as of 2027-12-31:** rejected. No further review." in uc06


def test_readme_links_to_the_value_measurement_section():
    method = (ROOT / "METHOD.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "\n## Measuring realised value in practice\n" in method
    assert "(METHOD.md#measuring-realised-value-in-practice)" in readme
    for topic in ("baseline before go-live", "Sample time", "comparison group", "Attribute gains"):
        assert topic in method
