"""Tests for scoring/triage.py and its link to score.py. All data is fictional."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from scoring import score as s
from scoring import triage as t
from scoring.errors import InputError


@pytest.fixture(scope="module")
def checklist() -> t.Checklist:
    return t.load_checklist()


def minimal_answers(checklist: t.Checklist, **overrides) -> dict:
    """Answers that lead to 'minimal risk'; override any question."""
    answers = {"is_ai_system": "yes", "exclusively_military": "no", "annex_i_safety_component": "no"}
    for group in ("prohibited", "annex_iii", "transparency"):
        answers.update({q.id: "no" for q in checklist.group(group)})
    answers.update(overrides)
    return answers


def run(checklist, **overrides) -> t.TriageResult:
    return t.triage(minimal_answers(checklist, **overrides), checklist, use_case_id="X-01")


# ---------------------------------------------------------------------------
# Checklist file
# ---------------------------------------------------------------------------


def test_checklist_questions_have_references_and_valid_groups(checklist):
    groups = {"ai_definition", "exclusion", "prohibited", "annex_i", "annex_iii",
              "profiling", "derogation", "transparency", "context"}
    for q in checklist.questions.values():
        assert q.group in groups, q.id
        assert q.reference.strip() and q.text.strip(), q.id
        assert q.if_unknown in ("yes", "no"), q.id


def test_checklist_covers_all_article_5_points(checklist):
    refs = {q.reference.split(",")[0] for q in checklist.group("prohibited")}
    expected = {f"Art. 5(1)({p})" for p in ("a", "b", "ba", "bb", "c", "d", "e", "f", "g", "h")}
    assert refs == expected


def test_checklist_covers_all_eight_annex_iii_areas(checklist):
    assert len(checklist.group("annex_iii")) == 8


def test_checklist_categories_match_score_categories(checklist):
    assert set(checklist.categories) == set(t.CATEGORIES) == set(s.AI_ACT_CATEGORIES)


def test_duplicate_question_ids_are_rejected(tmp_path):
    raw = yaml.safe_load(t.DEFAULT_CHECKLIST.read_text(encoding="utf-8"))
    raw["questions"].append(dict(raw["questions"][0]))
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(InputError, match="Duplicate question id"):
        t.load_checklist(path)


# ---------------------------------------------------------------------------
# Decision tree paths
# ---------------------------------------------------------------------------


def test_minimal_risk(checklist):
    result = run(checklist)
    assert result.category == "minimal"
    assert not result.legal_review_required
    assert any("Art. 4" in o for o in result.obligations)


def test_not_an_ai_system_stops_early(checklist):
    result = t.triage({"is_ai_system": "no"}, checklist)
    assert result.category == "not_ai_system"
    assert not result.legal_review_required


def test_exclusively_military_is_excluded(checklist):
    result = t.triage({"is_ai_system": "yes", "exclusively_military": "yes"}, checklist)
    assert result.category == "excluded"
    assert result.legal_review_required


@pytest.mark.parametrize("qid", [
    "prohibited_manipulation", "prohibited_workplace_emotion", "prohibited_social_scoring",
    "prohibited_intimate_imagery", "prohibited_realtime_rbi",
])
def test_each_prohibited_practice_gives_prohibited(checklist, qid):
    result = run(checklist, **{qid: "yes"})
    assert result.category == "prohibited"
    assert any(qid in r for r in result.reasons)


def test_annex_i_safety_component_with_third_party_assessment_is_high(checklist):
    result = run(checklist, annex_i_safety_component="yes", annex_i_third_party_assessment="yes")
    assert result.category == "high"
    assert any("Art. 6(1)" in r for r in result.reasons)


def test_annex_i_without_third_party_assessment_is_not_high(checklist):
    result = run(checklist, annex_i_safety_component="yes", annex_i_third_party_assessment="no")
    assert result.category == "minimal"


def test_annex_i_safety_component_requires_follow_up_answer(checklist):
    answers = minimal_answers(checklist, annex_i_safety_component="yes")
    with pytest.raises(InputError, match="annex_i_third_party_assessment"):
        t.triage(answers, checklist)


def test_cv_screening_with_profiling_is_high(checklist):
    result = run(checklist, annex_iii_employment="yes", profiling_of_persons="yes")
    assert result.category == "high"
    assert any("profiling" in r for r in result.reasons)
    assert any("Art. 26(7)" in o for o in result.obligations)
    assert any("2 December 2027" in o for o in result.obligations)


def test_annex_iii_without_exception_is_high(checklist):
    result = run(checklist, annex_iii_employment="yes", profiling_of_persons="no",
                 derogation_no_significant_risk="no", derogation_narrow_procedural_task="no",
                 derogation_improves_human_result="no", derogation_pattern_detection="no",
                 derogation_preparatory_task="no")
    assert result.category == "high"


def test_annex_iii_with_article_6_3_exception_is_not_high(checklist):
    result = run(checklist, annex_iii_employment="yes", profiling_of_persons="no",
                 derogation_no_significant_risk="yes", derogation_narrow_procedural_task="yes",
                 derogation_improves_human_result="no", derogation_pattern_detection="no",
                 derogation_preparatory_task="no")
    assert result.category == "minimal"
    assert result.derogation_used
    assert result.legal_review_required
    assert any("Art. 6(4)" in o for o in result.obligations)


def test_exception_needs_both_no_significant_risk_and_a_condition(checklist):
    result = run(checklist, annex_iii_employment="yes", profiling_of_persons="no",
                 derogation_no_significant_risk="no", derogation_narrow_procedural_task="yes",
                 derogation_improves_human_result="no", derogation_pattern_detection="no",
                 derogation_preparatory_task="no")
    assert result.category == "high"


def test_chatbot_is_limited_risk(checklist):
    result = run(checklist, transparency_interacts_with_people="yes", uses_gpai_model="yes")
    assert result.category == "limited"
    assert any("Art. 50(1)" in o for o in result.obligations)
    assert any("Art. 53" in o for o in result.obligations)
    assert result.legal_review_required


def test_high_risk_system_also_gets_transparency_duties(checklist):
    result = run(checklist, annex_iii_employment="yes", profiling_of_persons="yes",
                 transparency_interacts_with_people="yes")
    assert result.category == "high"
    assert any("Art. 50(1)" in o for o in result.obligations)


# ---------------------------------------------------------------------------
# Unknown answers and invalid input
# ---------------------------------------------------------------------------


def test_unknown_is_treated_conservatively(checklist):
    result = run(checklist, transparency_generates_content="unknown")
    assert result.category == "limited"
    assert result.unknown_answers == ["transparency_generates_content"]
    assert result.legal_review_required


def test_unknown_exception_answer_does_not_open_the_exception(checklist):
    result = run(checklist, annex_iii_employment="yes", profiling_of_persons="no",
                 derogation_no_significant_risk="unknown", derogation_narrow_procedural_task="yes",
                 derogation_improves_human_result="no", derogation_pattern_detection="no",
                 derogation_preparatory_task="no")
    assert result.category == "high"


def test_unknown_military_answer_keeps_the_system_in_scope(checklist):
    result = run(checklist, exclusively_military="unknown")
    assert result.category == "minimal"
    assert result.legal_review_required


def test_yaml_booleans_are_accepted(checklist):
    answers = minimal_answers(checklist)
    answers = {k: (v == "yes") for k, v in answers.items()}
    assert t.triage(answers, checklist).category == "minimal"


def test_invalid_answer_value_is_rejected(checklist):
    with pytest.raises(InputError, match="must be yes, no or unknown, got 'maybe'"):
        t.triage(minimal_answers(checklist, is_ai_system="maybe"), checklist)


def test_unknown_question_id_is_rejected(checklist):
    with pytest.raises(InputError, match="unknown question id 'is_ai'"):
        t.triage({"is_ai": "yes"}, checklist)


def test_missing_answers_are_listed(checklist):
    with pytest.raises(InputError) as exc:
        t.triage({"is_ai_system": "yes", "exclusively_military": "no"}, checklist)
    assert "step 3" in str(exc.value)
    assert "prohibited_manipulation" in str(exc.value)


# ---------------------------------------------------------------------------
# Files, CLI and the link to score.py
# ---------------------------------------------------------------------------


def write_answers(path: Path, use_case_id: str, answers: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"use_case_id": use_case_id, "answers": answers}), encoding="utf-8")
    return path


def test_cli_prints_result_and_writes_markdown(tmp_path, checklist, capsys):
    path = write_answers(tmp_path / "triage.yaml", "X-09",
                         minimal_answers(checklist, transparency_interacts_with_people="yes"))
    assert t.main([str(path)]) == 0
    assert "Screening category: limited" in capsys.readouterr().out
    out = tmp_path / "triage_result.md"
    assert t.main([str(path), "--format", "markdown", "--output", str(out)]) == 0
    md = out.read_text(encoding="utf-8")
    assert "# AI Act triage result: X-09" in md and "not legal advice" in md


def test_cli_returns_error_code_on_missing_file(tmp_path, capsys):
    assert t.main([str(tmp_path / "nope.yaml")]) == 2
    assert "not found" in capsys.readouterr().err


def score_row(**overrides) -> dict:
    row = {
        "id": "X-01", "title": "Fictional case", "ai_act_category": "",
        "process_owner": "Owner", "data_owner": "Data owner",
        "restricted_data": "no", "approved_environment_available": "no",
        "business_value": 4, "feasibility": 4, "data_maturity": 4,
        "ai_maturity": 4, "risk": 4, "strategic_fit": 4, "triage_answers": "",
    }
    row.update(overrides)
    return row


def test_score_fills_category_from_triage(tmp_path, checklist):
    write_answers(tmp_path / "X-01" / "triage.yaml", "X-01",
                  minimal_answers(checklist, transparency_interacts_with_people="yes"))
    csv = tmp_path / "cases.csv"
    pd.DataFrame([score_row(triage_answers="X-01/triage.yaml")]).to_csv(csv, index=False)
    df = s.load_use_cases(csv, s.load_criteria())
    assert df.loc[0, "ai_act_category"] == "limited"


def test_triage_prohibited_result_feeds_the_reject_gate(tmp_path, checklist):
    write_answers(tmp_path / "X-01" / "triage.yaml", "X-01",
                  minimal_answers(checklist, prohibited_workplace_emotion="yes"))
    csv = tmp_path / "cases.csv"
    pd.DataFrame([score_row(triage_answers="X-01/triage.yaml")]).to_csv(csv, index=False)
    criteria = s.load_criteria()
    ranked = s.score_use_cases(s.load_use_cases(csv, criteria), criteria)
    assert ranked.loc[0, "gate_result"] == "reject"


def test_category_that_contradicts_triage_is_rejected(tmp_path, checklist):
    write_answers(tmp_path / "X-01" / "triage.yaml", "X-01", minimal_answers(checklist))
    csv = tmp_path / "cases.csv"
    pd.DataFrame([score_row(ai_act_category="high", triage_answers="X-01/triage.yaml")]).to_csv(csv, index=False)
    with pytest.raises(InputError, match="ai_act_category is 'high' but the triage .* gives 'minimal'"):
        s.load_use_cases(csv, s.load_criteria())


def test_rows_without_triage_file_keep_their_category(tmp_path):
    csv = tmp_path / "cases.csv"
    pd.DataFrame([score_row(ai_act_category="minimal")]).to_csv(csv, index=False)
    df = s.load_use_cases(csv, s.load_criteria())
    assert df.loc[0, "ai_act_category"] == "minimal"


def test_missing_triage_file_is_reported(tmp_path):
    csv = tmp_path / "cases.csv"
    pd.DataFrame([score_row(triage_answers="X-01/missing.yaml")]).to_csv(csv, index=False)
    with pytest.raises(InputError, match="X-01 \\(line 2\\).*not found"):
        s.load_use_cases(csv, s.load_criteria())
