"""Two alternative ways to grade the invented answers of P5, measured apart from the official count. Owner: P6a.

  uv run python -m diagnosis.criteria monthly/academic_researcher:210 --policies never every-5 --check-cache

- nothing_logged: "0" to an expense, step count or total, or "no" to an event date, when the fact once did not hold
  (None in its history). The agent believes nothing was logged, which was true before: stale, not invented.
- partial_total: a total equal to the sum of some of the true entries of its range, left out or late: an incomplete
  total, not a sum of values that never were.

Neither changes exam/grading.py: they are a decision for the user (docs/p6a-origen-de-las-inventadas.md §5).
"""

import argparse
from collections import Counter

from diagnosis.causes import asked_range, note_entries, persona, truth_entries
from dreaming.quality import parse_notes, similarity
from exam.grading import as_number, normalize
from exam.schema import UNKNOWN
from exam.schema import Grade, Question

CRITERIA = ("official", "nothing_logged", "partial_total", "both")


def nothing_logged(question: Question, grade: Grade) -> bool:
    if grade.outcome != "invented" or None not in question.history:
        return False
    if question.domain in ("expense", "steps"):
        return grade.given == "0"
    return question.domain == "calendar" and question.field is not None and grade.given == "no"


def partial_total(question: Question, grade: Grade) -> bool:
    if grade.outcome != "invented" or question.probe != "aggregate" or as_number(grade.given) is None:
        return False
    start, end, kind = asked_range(question)
    entries = truth_entries(persona(question.period, question.persona).timeline, question.domain, question.session_id, start, end, kind)
    return round(as_number(grade.given) * 100) in subset_sums(round(entry.amount * 100) for entry in entries)


def subset_sums(amounts) -> set[int]:
    sums = {0}
    for amount in amounts:
        sums |= {total + amount for total in sums}
    return sums


def outcome_under(criterion: str, question: Question, grade: Grade) -> str:
    if criterion in ("nothing_logged", "both") and nothing_logged(question, grade):
        return "stale"
    if criterion in ("partial_total", "both") and partial_total(question, grade):
        return "incomplete"
    return grade.outcome


def absent_answer(question: Question, notes: str, answer: str | None) -> str | None:
    """For an expense, a step count or an event date the notes lack while it holds: unknown, nothing (0 or no) or other."""
    if question.current is None or question.probe == "aggregate":
        return None
    if question.domain in ("expense", "steps"):
        start, end, kind = asked_range(question)
        if note_entries(notes, question.domain, start, end, kind):
            return None
    elif question.domain == "calendar" and question.field is not None:
        if any(fact.domain == "calendar" and similarity(fact.name, question.fact[1][-1]) for fact in parse_notes(notes).facts):
            return None
    else:
        return None
    given = normalize(question, answer)
    return "unknown" if given == UNKNOWN else "nothing" if given in ("0", "no") else "other"


def main() -> None:
    from answering.client import BudgetedClient
    from exam.questions import EXAM_STEP
    from policies import triggered_run
    from policies.engine import run_policy
    from policies.run import policy_named

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slices", nargs="+", help='"period/persona[:through]"')
    parser.add_argument("--policies", nargs="+", required=True)
    parser.add_argument("--check-cache", action="store_true", help="cap $0: stop at the first call not in the cache")
    arguments = parser.parse_args()
    client = BudgetedClient("p6a", 0.0)
    print("| policy | slice | " + " | ".join(f"invented, {criterion}" for criterion in CRITERIA) + " | absent from the notes: unknown / nothing / other |")
    print("| --- | --- |" + " --: |" * (len(CRITERIA) + 1))
    for spec in arguments.slices:
        period, persona_name, through = triggered_run.slice_of(spec)
        for name in arguments.policies:
            run = run_policy(policy_named(name, "p5", 0.0), period, persona_name, client, EXAM_STEP, through)
            notes = {step.session_id: step.notes for step in run.steps}
            counts = Counter()
            for exam in run.exams:
                for question, answer, grade in zip(exam.questions, exam.answers, exam.grades, strict=True):
                    for criterion in CRITERIA:
                        counts[criterion] += outcome_under(criterion, question, grade) == "invented"
                    counts[absent_answer(question, notes[exam.session_id], answer)] += 1
            absent = " / ".join(str(counts[kind]) for kind in ("unknown", "nothing", "other"))
            print(f"| {name} | {spec} | " + " | ".join(str(counts[criterion]) for criterion in CRITERIA) + f" | {absent} |")


if __name__ == "__main__":
    main()
