"""Every wrong answer of a policy run, with the notes it read and the dream that wrote the lines it rests on. Owner: P6.

  uv run python -m diagnosis.invented monthly/academic_researcher --policies every-5 --check-cache

See docs/p6-interfaz.md. Nothing here calls the API: runs come from the P5 cache through policies.run.
"""

import argparse
import re
from dataclasses import dataclass

from dreaming.quality import fact_name, parse_notes, similarity
from exam.schema import Grade, Question
from policies.engine import PolicyRun, Step


@dataclass(frozen=True)
class LineOrigin:
    line: str
    written_after: int  # session of the dream that wrote this exact line, which then stayed until the exam
    sessions_read: tuple[int, ...]  # the sessions that dream read


@dataclass(frozen=True)
class WrongAnswer:
    policy: str
    period: str
    persona: str
    repetition: int
    question: Question
    answer: str | None       # as the model wrote it
    grade: Grade
    notes: str               # what the exam read
    last_dream: int | None   # session of the dream that left those notes; None if the run had not dreamt yet
    related: tuple[LineOrigin, ...]  # note lines about the question's fact, oldest origin first


def wrong_answers(run: PolicyRun, outcomes: tuple[str, ...] = ("invented",)) -> list[WrongAnswer]:
    """Every answer of the run graded as one of `outcomes`, in exam order."""
    steps = {step.session_id: step for step in run.steps}
    found = []
    for exam in run.exams:
        notes = steps[exam.session_id].notes
        dreams = [step for step in run.steps if step.dreamt and step.session_id <= exam.session_id]
        for question, answer, question_grade in zip(exam.questions, exam.answers, exam.grades, strict=True):
            if question_grade.outcome not in outcomes:
                continue
            related = tuple(sorted(
                (line_origin(dreams, line) for line in related_lines(notes, question)),
                key=lambda origin: origin.written_after,
            ))
            found.append(WrongAnswer(
                run.policy, run.period, run.persona, run.repetition, question, answer, question_grade, notes,
                dreams[-1].session_id if dreams else None, related,
            ))
    return found


def related_lines(notes: str, question: Question) -> list[str]:
    """Note lines about the question's fact: same domain and a similar name, or for a total, every dated line in its range."""
    parsed = parse_notes(notes)
    if question.fact is None:
        start, end = re.findall(r"\d{4}-\d{2}-\d{2}", question.prompt)[:2]
        return [fact.line for fact in parsed.facts if fact.domain == question.domain and start <= fact.name[:10] <= end]
    domain, key = question.fact
    name = asked_name(question)
    looser = domain == "content"
    return [fact.line for fact in parsed.facts if fact.domain == domain and similarity(fact.name, name, looser=looser)]


def asked_name(question: Question) -> str:
    domain, key = question.fact
    if domain == "expense":
        quoted = re.search(r"on (.+?) on (\d{4}-\d{2}-\d{2})", question.prompt)
        return f"{quoted.group(2)} {quoted.group(1)}" if quoted else key[0]
    return fact_name(domain, key, question.current or {})


def line_origin(dreams: list[Step], line: str) -> LineOrigin:
    """The dream after which `line` sits in the notes without a break up to the last of `dreams`."""
    origin_index = len(dreams) - 1
    while origin_index > 0 and line in dreams[origin_index - 1].notes.splitlines():
        origin_index -= 1
    previous = dreams[origin_index - 1].session_id if origin_index > 0 else 0
    origin = dreams[origin_index]
    return LineOrigin(line, origin.session_id, tuple(range(previous + 1, origin.session_id + 1)))


def describe(wrong: WrongAnswer) -> str:
    question = wrong.question
    lines = [
        f"### {wrong.policy} s{question.session_id} {question.question_id} [{question.domain}/{question.probe}]",
        f"- question: {question.prompt}",
        f"- answer: {wrong.answer!r} -> {wrong.grade.outcome} (expected {wrong.grade.expected!r}; history {question.history})",
        f"- last dream: s{wrong.last_dream}" if wrong.last_dream else "- last dream: none (empty notes)",
    ]
    lines += [f"- note line, written by the dream after s{origin.written_after} (read s{origin.sessions_read[0]}-s{origin.sessions_read[-1]}): `{origin.line.strip()}`" for origin in wrong.related]
    if not wrong.related:
        lines.append("- note lines: none about this fact")
    return "\n".join(lines)


def main() -> None:
    from answering.client import BudgetedClient
    from exam.questions import EXAM_STEP
    from policies import triggered_run
    from policies.engine import run_policy
    from policies.run import policy_named

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slices", nargs="+", help='"period/persona[:through]"')
    parser.add_argument("--policies", nargs="+", required=True)
    parser.add_argument("--outcomes", nargs="+", default=["invented"])
    parser.add_argument("--repetition", type=int, default=0)
    parser.add_argument("--budget-name", default="p6")
    parser.add_argument("--limit", type=float, default=0.0)
    parser.add_argument("--check-cache", action="store_true", help="cap $0: stop at the first call not in the cache")
    arguments = parser.parse_args()
    client = BudgetedClient(arguments.budget_name, 0.0 if arguments.check_cache else arguments.limit)
    for spec in arguments.slices:
        period, persona, through = triggered_run.slice_of(spec)
        for name in arguments.policies:
            run = run_policy(policy_named(name, arguments.budget_name, client.limit_dollars), period, persona, client, EXAM_STEP, through, arguments.repetition)
            found = wrong_answers(run, tuple(arguments.outcomes))
            print(f"## {name} on {spec}: {len(found)} answers graded {'/'.join(arguments.outcomes)}\n")
            for wrong in found:
                print(describe(wrong) + "\n")


if __name__ == "__main__":
    main()
