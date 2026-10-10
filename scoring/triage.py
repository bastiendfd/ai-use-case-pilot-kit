"""EU AI Act screening triage for one use case.

Usage (from the repository root):

    python -m scoring.triage examples/UC-05_policy_assistant/triage.yaml
    python -m scoring.triage path/to/triage.yaml --format markdown

The questions, their article references and the treatment of "unknown"
answers are defined in triage/triage_checklist.yaml. This module applies them
in the order of the decision tree in triage/ai_act_triage.md and returns a
screening category that score.py uses for its hard gates.

This is a screening aid, not legal advice. Final classification needs legal
or compliance review.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from scoring.errors import InputError

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHECKLIST = REPO_ROOT / "triage" / "triage_checklist.yaml"

ANSWER_VALUES = ("yes", "no", "unknown")
CATEGORIES = ("not_ai_system", "excluded", "prohibited", "high", "limited", "minimal")

DISCLAIMER = ("Screening aid only, not legal advice. Final classification needs legal "
              "or compliance review.")

# Duties per Article 50 paragraph, keyed by question id.
TRANSPARENCY_DUTIES = {
    "transparency_interacts_with_people":
        "Art. 50(1) (provider): design the system so that people are told they are interacting with AI, "
        "unless obvious; inform them at the latest at the first interaction (Art. 50(5)).",
    "transparency_generates_content":
        "Art. 50(2) (provider): mark synthetic output in a machine-readable, detectable way.",
    "transparency_emotion_or_biometric":
        "Art. 50(3) (deployer): inform the people exposed to the system.",
    "transparency_deep_fake_or_public_text":
        "Art. 50(4) (deployer): disclose deep fakes and AI-generated public-interest text.",
}


@dataclass(frozen=True)
class Question:
    id: str
    group: str
    reference: str
    text: str
    if_unknown: str
    requires: str | None = None
    optional: bool = False


@dataclass(frozen=True)
class Checklist:
    questions: dict[str, Question]
    categories: dict[str, str]

    def group(self, name: str) -> list[Question]:
        return [q for q in self.questions.values() if q.group == name]


@dataclass
class TriageResult:
    use_case_id: str
    category: str
    reasons: list[str] = field(default_factory=list)
    obligations: list[str] = field(default_factory=list)
    unknown_answers: list[str] = field(default_factory=list)
    derogation_used: bool = False
    transparency: list[str] = field(default_factory=list)
    uses_gpai_model: bool = False

    @property
    def legal_review_required(self) -> bool:
        return (self.category not in ("minimal", "not_ai_system")
                or self.derogation_used or bool(self.unknown_answers))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_checklist(path: Path = DEFAULT_CHECKLIST) -> Checklist:
    """Load and check triage_checklist.yaml."""
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    questions: dict[str, Question] = {}
    errors = []
    for item in raw["questions"]:
        qid = item["id"]
        if qid in questions:
            errors.append(f"Duplicate question id in checklist: {qid}.")
        if_unknown = str(item.get("if_unknown", "")).lower()
        if if_unknown not in ("yes", "no"):
            errors.append(f"{qid}: if_unknown must be yes or no.")
        questions[qid] = Question(
            id=qid, group=item["group"], reference=item["reference"],
            text=" ".join(str(item["text"]).split()), if_unknown=if_unknown,
            requires=item.get("requires"), optional=bool(item.get("optional", False)),
        )
    for q in questions.values():
        if q.requires and q.requires not in questions:
            errors.append(f"{q.id}: requires unknown question '{q.requires}'.")
    if errors:
        raise InputError(errors)
    return Checklist(questions=questions, categories=dict(raw["categories"]))


def normalise_answer(value) -> str | None:
    """Map YAML values to yes/no/unknown. Returns None if the value is invalid."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    text = str(value).strip().lower()
    return text if text in ANSWER_VALUES else None


def load_answers(path: Path) -> tuple[str, dict]:
    """Read an answers file. Returns (use_case_id, raw answers mapping)."""
    path = Path(path)
    if not path.is_file():
        raise InputError([f"Triage answers file not found: {path}"])
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict) or not isinstance(raw.get("answers"), dict):
        raise InputError([f"{path}: expected a mapping with an 'answers' section."])
    return str(raw.get("use_case_id", path.parent.name)), raw["answers"]


# ---------------------------------------------------------------------------
# Triage logic
# ---------------------------------------------------------------------------


class _Asker:
    """Reads answers, applies if_unknown, records unknowns and missing answers."""

    def __init__(self, answers: dict, checklist: Checklist, source: str):
        self.checklist = checklist
        self.source = source
        self.answers: dict[str, str] = {}
        self.unknown: list[str] = []
        self.missing: list[str] = []
        errors = []
        for key, value in answers.items():
            key = str(key)
            if key not in checklist.questions:
                errors.append(f"{source}: unknown question id '{key}'.")
                continue
            norm = normalise_answer(value)
            if norm is None:
                errors.append(f"{source}: '{key}' must be yes, no or unknown, got '{value}'.")
                continue
            self.answers[key] = norm
        if errors:
            raise InputError(errors)

    def ask(self, qid: str) -> bool:
        q = self.checklist.questions[qid]
        if qid not in self.answers:
            if not q.optional:
                self.missing.append(qid)
            return q.if_unknown == "yes" and not q.optional
        answer = self.answers[qid]
        if answer == "unknown":
            self.unknown.append(qid)
            answer = q.if_unknown
        return answer == "yes"

    def check_missing(self, step: str) -> None:
        if self.missing:
            raise InputError([
                f"{self.source}: answer needed for {step}: "
                + ", ".join(self.missing) + ". See triage/triage_checklist.yaml."
            ])


def _ref(checklist: Checklist, qid: str) -> str:
    return checklist.questions[qid].reference


def triage(answers: dict, checklist: Checklist | None = None, use_case_id: str = "",
           source: str = "answers") -> TriageResult:
    """Apply the decision tree to one set of answers."""
    checklist = checklist or load_checklist()
    asker = _Asker(answers, checklist, source)
    result = TriageResult(use_case_id=use_case_id, category="minimal")

    def finish(category: str) -> TriageResult:
        result.category = category
        result.unknown_answers = list(asker.unknown)
        result.obligations = _obligations(result, asker, checklist)
        return result

    # Context first: it never changes the category.
    result.uses_gpai_model = asker.ask("uses_gpai_model")

    # Step 1: AI system?
    is_ai = asker.ask("is_ai_system")
    asker.check_missing("step 1 (AI system definition)")
    if not is_ai:
        result.reasons.append(f"Not an AI system: rule-based, does not infer ({_ref(checklist, 'is_ai_system')}).")
        return finish("not_ai_system")

    # Step 2: exclusion.
    excluded = asker.ask("exclusively_military")
    asker.check_missing("step 2 (exclusions)")
    if excluded:
        result.reasons.append(
            f"Used exclusively for military, defence or national security ({_ref(checklist, 'exclusively_military')})."
        )
        return finish("excluded")

    # Step 3: prohibited practices.
    hits = [q.id for q in checklist.group("prohibited") if asker.ask(q.id)]
    asker.check_missing("step 3 (prohibited practices)")
    if hits:
        result.reasons += [f"Prohibited practice: {qid} ({_ref(checklist, qid)})." for qid in hits]
        return finish("prohibited")

    high = False
    # Step 4a: Annex I.
    if asker.ask("annex_i_safety_component"):
        if asker.ask("annex_i_third_party_assessment"):
            high = True
            result.reasons.append(
                "Safety component of an Annex I product that needs third-party conformity assessment "
                "(Art. 6(1)). For Annex I Section B products only a reduced set of provisions applies (Art. 2(2))."
            )
        else:
            result.reasons.append("Annex I product without third-party conformity assessment: not high-risk under Art. 6(1).")
    asker.check_missing("step 4a (Annex I)")

    # Step 4b/4c: Annex III and Article 6(3).
    if not high:
        annex_iii = [q.id for q in checklist.group("annex_iii") if asker.ask(q.id)]
        asker.check_missing("step 4b (Annex III)")
        if annex_iii:
            refs = ", ".join(_ref(checklist, qid) for qid in annex_iii)
            profiling = asker.ask("profiling_of_persons")
            asker.check_missing("step 4c (profiling)")
            if profiling:
                high = True
                result.reasons.append(f"Annex III use case ({refs}) with profiling of natural persons: always high-risk (Art. 6(3), last subparagraph).")
            else:
                no_significant_risk = asker.ask("derogation_no_significant_risk")
                conditions = [q.id for q in checklist.group("derogation")
                              if q.id != "derogation_no_significant_risk" and asker.ask(q.id)]
                asker.check_missing("step 4c (Art. 6(3) exceptions)")
                if no_significant_risk and conditions:
                    result.derogation_used = True
                    result.reasons.append(
                        f"Annex III use case ({refs}) but an Art. 6(3) exception applies: "
                        + ", ".join(f"{c} ({_ref(checklist, c)})" for c in conditions)
                        + ". Not high-risk if the documented assessment holds."
                    )
                else:
                    high = True
                    result.reasons.append(f"Annex III use case ({refs}); no Art. 6(3) exception applies (Art. 6(2)).")

    # Step 5: transparency (also for high-risk systems, Art. 50(6)).
    result.transparency = [q.id for q in checklist.group("transparency") if asker.ask(q.id)]
    asker.check_missing("step 5 (transparency)")
    if result.transparency:
        result.reasons.append("Transparency trigger: " + ", ".join(
            f"{qid} ({_ref(checklist, qid)})" for qid in result.transparency) + ".")

    if high:
        return finish("high")
    if result.transparency:
        return finish("limited")
    result.reasons.append("No prohibited, high-risk or transparency trigger: minimal risk.")
    return finish("minimal")


def _obligations(result: TriageResult, asker: _Asker, checklist: Checklist) -> list[str]:
    """Main obligations to carry into the business case and decision record."""
    cat = result.category
    out: list[str] = []
    if cat == "not_ai_system":
        return ["No AI Act obligations. Other law (data protection, product safety) still applies."]
    if cat == "excluded":
        return ["AI Act does not apply (Art. 2(3)). Re-run the triage if the system is ever used for a civil purpose."]
    if cat == "prohibited":
        return ["Do not develop, deploy or use (Art. 5). Gate result: reject."]
    if cat == "high":
        out.append("Deployer duties (Art. 26): use per instructions, competent human oversight, relevant input data, "
                   "monitoring and incident reporting, logs kept at least six months, information to affected people.")
        out.append("If built in-house, provider duties (Art. 16; Chapter III, Section 2: Arts. 9-15, 17, 43, 47-49, 72, 73).")
        if asker.answers.get("annex_iii_employment") in ("yes", "unknown"):
            out.append("Inform workers' representatives and affected workers before use at the workplace (Art. 26(7)).")
        if asker.answers.get("annex_iii_essential_services") in ("yes", "unknown"):
            out.append("Check whether a fundamental rights impact assessment is required (Art. 27).")
        out.append("High-risk obligations apply from 2 December 2027 (Annex III) or 2 August 2028 (Annex I) (Art. 113(c)).")
    if result.derogation_used:
        out.append("Document the Art. 6(3) assessment before putting into service, and register it (Art. 6(4), Art. 49(2)).")
    out += [TRANSPARENCY_DUTIES[qid] for qid in result.transparency]
    out.append("AI literacy measures for staff using the system (Art. 4).")
    if result.uses_gpai_model:
        out.append("Built on a general-purpose AI model: model duties sit with the model provider (Art. 53); "
                   "use its documentation (Art. 53(1)(b)). Using it for an Annex III purpose makes you the provider "
                   "of a high-risk system (Art. 25(1)(c)).")
    return out


def triage_file(path: Path, checklist: Checklist | None = None) -> TriageResult:
    """Load an answers file and triage it."""
    use_case_id, answers = load_answers(path)
    return triage(answers, checklist, use_case_id=use_case_id, source=str(path))


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def to_text(result: TriageResult) -> str:
    lines = [
        f"Use case: {result.use_case_id}",
        f"Screening category: {result.category}",
        f"Legal review required: {'yes' if result.legal_review_required else 'no'}",
        "Reasons:",
        *[f"  - {r}" for r in result.reasons],
        "Obligations to carry forward:",
        *[f"  - {o}" for o in result.obligations],
    ]
    if result.unknown_answers:
        lines.append("Answered 'unknown' (treated conservatively): " + ", ".join(result.unknown_answers))
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def to_markdown(result: TriageResult) -> str:
    lines = [
        f"# AI Act triage result: {result.use_case_id}",
        "",
        f"> {DISCLAIMER}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Screening category | **{result.category}** |",
        f"| Legal review required | {'yes' if result.legal_review_required else 'no'} |",
        f"| Art. 6(3) exception relied on | {'yes' if result.derogation_used else 'no'} |",
        f"| Answers marked unknown | {', '.join(result.unknown_answers) or 'none'} |",
        "",
        "## Reasons",
        "",
        *[f"- {r}" for r in result.reasons],
        "",
        "## Obligations to carry into the business case",
        "",
        *[f"- {o}" for o in result.obligations],
        "",
        "Generated by `scoring/triage.py` from the answers file. Explanations and sources: "
        "`triage/ai_act_triage.md`.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m scoring.triage",
                                     description="EU AI Act screening triage for one use case.")
    parser.add_argument("answers", type=Path, help="YAML answers file (see triage/triage_checklist.yaml).")
    parser.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    parser.add_argument("--format", choices=("text", "markdown"), default="text")
    parser.add_argument("--output", type=Path, default=None, help="Write the result to this file.")
    args = parser.parse_args(argv)
    try:
        result = triage_file(args.answers, load_checklist(args.checklist))
    except InputError as exc:
        print("Input error:", file=sys.stderr)
        for message in exc.errors:
            print(f"  - {message}", file=sys.stderr)
        return 2
    text = to_markdown(result) if args.format == "markdown" else to_text(result)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
