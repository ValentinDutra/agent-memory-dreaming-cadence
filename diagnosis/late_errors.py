"""The late errors of a policy that dreams often, about a fact that holds, one by one. Owner: P6.

  PYTHONHASHSEED=0 uv run python -m diagnosis.late_errors monthly/academic_researcher --policies every-1 --after 420
  PYTHONHASHSEED=0 uv run python -m diagnosis.late_errors monthly/marketing_manager:210 --policies every-1 --repetition 1 --budget-name p7a

P6b split those errors by how P4b's compare_notes finds the fact in the notes the exam read (diagnosis.growth,
reading_table). This prints each case of the two groups that grew late, so they can be read:
- correct in the notes, and the answer is wrong anyway: with the note lines about the fact;
- missing from the notes: a line with the fact's name that compare_notes did not tie to it (another document block,
  another item), or else the last dream whose notes had a line about the fact, the dream after it that dropped the
  line, and what Memora recorded for the fact in the sessions that dream read.
Marked questions (exam.unreachable) are left out, as in P6b. Everything comes from the cache.
"""

import argparse
from collections import Counter

from answering.client import BudgetedClient
from diagnosis.invented import related_lines
from dreaming import quality
from exam.questions import EXAM_STEP
from exam.unreachable import unreachable
from policies import triggered_run
from policies.engine import PolicyRun, run_policy
from policies.run import policy_named
from truth.changes import Change, persona_changes
from truth.timeline import build_timeline

ERRORS = ("stale", "missing", "invented", "unparseable")


def dropped_by(run: PolicyRun, question, before: int) -> tuple[int, int] | None:
    """(last dream whose notes had a line about the fact, the next dream, which had none), before session `before`."""
    dreams = [step for step in run.steps if step.dreamt and step.session_id <= before]
    for index in range(len(dreams) - 1, 0, -1):
        if related_lines(dreams[index - 1].notes, question) and not related_lines(dreams[index].notes, question):
            return dreams[index - 1].session_id, dreams[index].session_id
    return None


def changes_read(changes: list[Change], fact, after: int, through: int) -> str:
    found = [f"s{change.session_id} {change.action} {change.value}" for change in changes if (change.domain, change.key) == fact and after < change.session_id <= through]
    return "; ".join(found) or "none"


def kind_of_drop(changes: list[Change], fact, after: int, through: int) -> str:
    actions = [(change.action, change.value) for change in changes if (change.domain, change.key) == fact and after < change.session_id <= through]
    if not actions:
        return "dropped, no change in Memora"
    action, value = actions[-1]
    if action == "update" and value and value.get("preference") == "dislike":
        return "dropped, Memora: like -> dislike"
    return f"dropped, Memora: {action}"


def late_errors(run: PolicyRun, after: int):
    """(exam session, question, answer, grade, held, kind, detail) of every wrong answer after session `after` about a
    fact that holds and that compare_notes finds correct or missing in the notes the exam read. Marked questions are left out."""
    changes = persona_changes(run.period, run.persona)
    timeline = build_timeline(changes)
    marked = unreachable(run.period, run.persona)
    steps = {step.session_id: step for step in run.steps}
    for exam in run.exams:
        if exam.session_id <= after:
            continue
        notes = steps[exam.session_id].notes
        comparison = quality.compare_notes(notes, timeline, exam.session_id)
        for question, answer, question_grade in zip(exam.questions, exam.answers, exam.grades, strict=True):
            held = comparison.fact_outcomes.get(question.fact, ("not asked",))[0]
            if question.question_id in marked or held not in ("correct", "missing") or question_grade.outcome not in ERRORS:
                continue
            if held == "correct":
                yield exam.session_id, question, answer, question_grade, held, "correct in the notes, answer wrong", f"note: {' / '.join(line.strip() for line in related_lines(notes, question))}"
                continue
            nearby = related_lines(notes, question)
            if nearby:
                # compare_notes did not tie the line to this fact: another document block, or another item's name.
                yield exam.session_id, question, answer, question_grade, held, "a line with its name, not tied to it", f"a line with its name is in the notes: {' / '.join(line.strip() for line in nearby)}"
                continue
            drop = dropped_by(run, question, exam.session_id)
            if drop is None:
                yield exam.session_id, question, answer, question_grade, held, "never in the notes", "never in the notes"
                continue
            last_held, dropping = drop
            started = max(version.valid_from for version in timeline.versions if (version.domain, version.key) == question.fact and version.valid_from <= exam.session_id)
            if started > dropping:
                yield exam.session_id, question, answer, question_grade, held, "Memora added it again, no dream wrote it back", f"dropped after s{last_held}, added again by Memora in s{started}, not in the notes since"
                continue
            yield (exam.session_id, question, answer, question_grade, held, kind_of_drop(changes, question.fact, last_held, dropping),
                   f"last in the notes after s{last_held}; the dream after s{dropping} dropped it; Memora in s{last_held + 1}-s{dropping}: {changes_read(changes, question.fact, last_held, dropping)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slices", nargs="+", help='"period/persona[:through]"')
    parser.add_argument("--policies", nargs="+", required=True)
    parser.add_argument("--after", type=int, default=0, help="only exams after this session")
    parser.add_argument("--repetition", type=int, default=0)
    parser.add_argument("--budget-name", default="p6", help="whose cache ledger to read; the cap is always $0")
    arguments = parser.parse_args()
    client = BudgetedClient(arguments.budget_name, 0.0)
    for spec in arguments.slices:
        period, persona, through = triggered_run.slice_of(spec)
        for name in arguments.policies:
            run = run_policy(policy_named(name, arguments.budget_name, 0.0), period, persona, client, EXAM_STEP, through, arguments.repetition)
            kinds = Counter()
            print(f"## {name} on {spec} r{arguments.repetition}, exams after s{arguments.after}\n")
            for session_id, question, answer, question_grade, held, kind, detail in late_errors(run, arguments.after):
                kinds[question.domain, kind] += 1
                print(f"- s{session_id} [{question.domain}/{question.probe}] {question.prompt}\n"
                      f"  answer {answer!r} -> {question_grade.outcome}, expected {question_grade.expected!r}; fact {held} in the notes\n  {detail}")
            print("\n| domain | case | answers |\n| --- | --- | --: |")
            for (domain, kind), count in sorted(kinds.items()):
                print(f"| {domain} | {kind} | {count} |")
            print()


if __name__ == "__main__":
    main()
