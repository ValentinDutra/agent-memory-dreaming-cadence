"""Measure a dream: chains of dreams, single dreams and windows from perfect notes, each graded by the exam and line by line. Owner: P4b.

The dream is any function with the signature of dreaming.dream.dream, named "module:function" with --dream, so the
same commands measure P4a's dream after integration. Examples:

    uv run python -m dreaming.quality_run weekly software_engineer chain --cadence 7 --through 56 --dry-run
    uv run python -m dreaming.quality_run weekly software_engineer single --at 35 56
    uv run python -m dreaming.quality_run weekly software_engineer window --sizes 1 5 20 50 --at 56 133

chain:  dreams after sessions c, 2c, ... up to --through, starting from empty notes; each reads the sessions since the last.
single: one dream from empty notes over sessions 1..N.
window: one dream over the k sessions before N, starting from perfect notes after session N-k, so its errors are its own.

Every examined session N is a multiple of 7 (an exam session). There the notes get the exam of session N, and so do the
perfect notes and empty notes of N, as ceiling and floor; the notes' token count is the exam's input tokens minus the
empty-notes exam's.
"""

import argparse
import importlib
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass

from answering.answer import answer_exam, exam_prompt
from answering.client import BudgetedClient, Completion
from answering.notes import render_notes
from dreaming.quality import FACT_OUTCOMES, LINE_OUTCOMES, Comparison, compare_notes
from dreaming.transcripts import load_transcripts, sessions_between
from exam.grading import OUTCOMES, grade
from exam.questions import EXAM_STEP, build_exam
from exam.schema import DOMAINS, Grade, Question
from truth.changes import persona_changes
from truth.timeline import build_timeline

# Dry-run estimate, calibrated on the stub's dream over weekly/software_engineer 1-35: 66,914 prompt characters gave
# 22,038 input tokens, and 2,872 output tokens for notes of about 3,000 characters, so about 2,000 of thinking.
CHARACTERS_PER_TOKEN = 3.0
THINKING_TOKENS = 2_000
EXAM_OUTPUT_TOKENS = 1_500


@dataclass(frozen=True)
class Sequence:
    """Dreams run one after another: from perfect notes after session `start` (empty notes when 0), one dream after each of `points`."""

    label: str
    run: str  # where its dreams are cached, under results/raw/<run-prefix>/<period>/<persona>/
    start: int
    points: tuple[int, ...]


@dataclass
class Point:
    label: str
    session_id: int
    sessions_read: int    # by the dream that wrote these notes
    dreams: int           # in the sequence so far
    dream_cost: float     # of the sequence so far
    notes: str
    comparison: Comparison
    questions: list[Question]
    grades: list[Grade]
    notes_tokens: int
    ceiling: int          # exam answers correct with the perfect notes of session_id
    floor: int            # and with empty notes
    perfect_lines: int    # size of the perfect notes of session_id
    perfect_characters: int


class InputTokens:
    """Stands between answer_exam and the client to keep the input tokens of the last call."""

    def __init__(self, client: BudgetedClient):
        self.client = client
        self.thinking = client.thinking
        self.last = 0

    def complete(self, run: str, system: str, user: str, max_tokens: int, repeat: int = 0) -> Completion:
        completion = self.client.complete(run, system, user, max_tokens, repeat=repeat)
        self.last = completion.input_tokens
        return completion


def chain(cadence: int, through: int) -> Sequence:
    return Sequence(f"chain-c{cadence}", f"chain-c{cadence}", 0, tuple(range(cadence, through + 1, cadence)))


def single(session_id: int) -> Sequence:
    return Sequence(f"single-s{session_id}", "single", 0, (session_id,))


def window(size: int, session_id: int) -> Sequence:
    return Sequence(f"window-k{size}-s{session_id}", f"window-k{size}", session_id - size, (session_id,))


def load_dream(name: str):
    module, function = name.split(":")
    return getattr(importlib.import_module(module), function)


def measure(dream, period: str, persona: str, sequences: list[Sequence], client: BudgetedClient, run_prefix: str) -> list[Point]:
    timeline = build_timeline(persona_changes(period, persona))
    sessions = load_transcripts(period, persona)
    exams = defaultdict(list)
    for question in build_exam(period, persona):
        exams[question.session_id].append(question)
    recorder = InputTokens(client)
    references = {}  # session -> (empty notes exam input tokens, ceiling correct, floor correct)
    points = []
    for sequence in sequences:
        notes = render_notes(timeline.state_after(sequence.start)) if sequence.start else ""
        previous = sequence.start
        cost = 0.0
        for count, session_id in enumerate(sequence.points, start=1):
            read = sessions_between(sessions, previous, session_id)
            result = dream(notes, read, client, f"{run_prefix}/{period}/{persona}/{sequence.run}")
            notes, previous, cost = result.notes, session_id, cost + result.cost
            if session_id not in exams:
                continue  # not an exam session, or past the persona's last session
            questions = exams[session_id]
            if session_id not in references:
                reference_run = f"{run_prefix.split('/')[0]}/reference/{period}/{persona}"
                floor = answer_exam("", questions, recorder, reference_run)
                empty_notes_tokens = recorder.last
                ceiling = answer_exam(render_notes(timeline.state_after(session_id)), questions, recorder, reference_run)
                references[session_id] = (empty_notes_tokens, correct_count(questions, ceiling), correct_count(questions, floor))
            answers = answer_exam(notes, questions, recorder, f"{run_prefix}/exam/{period}/{persona}")
            perfect_notes = render_notes(timeline.state_after(session_id))
            transcript_text = " ".join(turn.message for session in sessions if session.session_id <= session_id for turn in session.turns)
            points.append(Point(
                label=sequence.label,
                session_id=session_id,
                sessions_read=len(read),
                dreams=count,
                dream_cost=cost,
                notes=notes,
                comparison=compare_notes(notes, timeline, session_id, transcript_text),
                questions=questions,
                grades=[grade(question, answer) for question, answer in zip(questions, answers, strict=True)],
                notes_tokens=recorder.last - references[session_id][0],
                ceiling=references[session_id][1],
                floor=references[session_id][2],
                perfect_lines=non_empty_lines(perfect_notes),
                perfect_characters=len(perfect_notes),
            ))
    return points


def non_empty_lines(notes: str) -> int:
    return len([line for line in notes.splitlines() if line.strip()])


def correct_count(questions: list[Question], answers: list[str | None]) -> int:
    return sum(grade(question, answer).outcome == "correct" for question, answer in zip(questions, answers, strict=True))


def estimate(period: str, persona: str, sequences: list[Sequence]) -> tuple[int, int, float]:
    """(dreams, exams, dollars) if nothing were cached, with perfect notes standing in for the dream's."""
    timeline = build_timeline(persona_changes(period, persona))
    sessions = load_transcripts(period, persona)
    exams = defaultdict(list)
    for question in build_exam(period, persona):
        exams[question.session_id].append(question)
    dreams = exam_count = 0
    dollars = 0.0
    examined = set()
    for sequence in sequences:
        previous = sequence.start
        for session_id in sequence.points:
            read = sessions_between(sessions, previous, session_id)
            transcript_characters = sum(len(turn.speaker) + len(turn.message) + 2 for session in read for turn in session.turns)
            notes_before = len(render_notes(timeline.state_after(previous))) if previous else 0
            notes_after = len(render_notes(timeline.state_after(session_id)))
            dollars += token_cost((notes_before + transcript_characters) / CHARACTERS_PER_TOKEN, notes_after / CHARACTERS_PER_TOKEN + THINKING_TOKENS)
            dreams += 1
            previous = session_id
            if session_id % EXAM_STEP == 0:
                prompt = exam_prompt(render_notes(timeline.state_after(session_id)), exams[session_id])
                runs = 1 if session_id in examined else 3
                examined.add(session_id)
                exam_count += runs
                dollars += runs * token_cost(len(prompt) / CHARACTERS_PER_TOKEN, EXAM_OUTPUT_TOKENS)
    return dreams, exam_count, dollars


def token_cost(input_tokens: float, output_tokens: float) -> float:
    return (input_tokens * 0.10 + output_tokens * 0.50) / 1_000_000


# --- Report -------------------------------------------------------------------------------------


def points_table(points: list[Point]) -> str:
    header = (
        "| sequence | N | read | dreams | dream $ | lines | chars | tokens | perfect lines | perfect chars | live facts | "
        + " | ".join(FACT_OUTCOMES) + " | " + " | ".join(f"+{outcome}" for outcome in LINE_OUTCOMES)
        + " | lenient | paraphrased | exam | ceiling | floor |"
    )
    lines = [header, "| --- |" + " --: |" * (header.count("|") - 2)]
    for point in points:
        comparison = point.comparison
        total = len(point.grades)
        correct = sum(question_grade.outcome == "correct" for question_grade in point.grades)
        cells = [
            point.label, point.session_id, point.sessions_read, point.dreams, f"{point.dream_cost:.4f}",
            non_empty_lines(point.notes), len(point.notes), point.notes_tokens, point.perfect_lines, point.perfect_characters,
            comparison.fact_total(),
            *(comparison.fact_total(outcome) for outcome in FACT_OUTCOMES),
            *(comparison.line_total(outcome) for outcome in LINE_OUTCOMES),
            comparison.lenient, sum(comparison.paraphrased.values()),
            f"{correct}/{total}", f"{point.ceiling}/{total}", f"{point.floor}/{total}",
        ]
        lines.append("| " + " | ".join(map(str, cells)) + " |")
    return "\n".join(lines)


def summary_table(points: list[Point]) -> str:
    """One row per sequence (or per sequence label without its session, for windows and single dreams), over its examined points."""
    groups = defaultdict(list)
    for point in points:
        groups[point.label.rsplit("-s", 1)[0] if point.label.startswith(("window", "single")) else point.label].append(point)
    header = "| sequence | points | dream $ | facts correct | missing | stale+wrong | +stale | +invented (lenient) | +unmatched | +prose | lost after correct | chars / perfect | exam | exam without expense totals | ceiling | floor |"
    lines = [header, "| --- |" + " --: |" * (header.count("|") - 2)]
    for label, group in groups.items():
        live = sum(point.comparison.fact_total() for point in group)
        cost = sum(point.dream_cost for point in group) if label.startswith(("window", "single")) else max(point.dream_cost for point in group)
        asked = sum(len(point.grades) for point in group)
        correct = sum(question_grade.outcome == "correct" for point in group for question_grade in point.grades)
        # The answerer's one-cent errors in expense totals are a known, measured limit (docs/p3-respuestas.md).
        without_totals = [
            question_grade.outcome == "correct"
            for point in group
            for question, question_grade in zip(point.questions, point.grades, strict=True)
            if not (question.domain == "expense" and question.probe == "aggregate")
        ]
        def total(name: str, outcome: str) -> int:
            return sum(getattr(point.comparison, name)(outcome) for point in group)
        cells = [
            label, len(group), f"{cost:.4f}",
            f"{total('fact_total', 'correct')}/{live} ({total('fact_total', 'correct') / live:.1%})",
            total("fact_total", "missing"), total("fact_total", "stale") + total("fact_total", "wrong"),
            total("line_total", "stale"), f"{total('line_total', 'invented')} ({sum(point.comparison.lenient for point in group)})",
            total("line_total", "unmatched_supported") + total("line_total", "unmatched_unsupported"), total("line_total", "prose"),
            lost_after_correct(group) if label.startswith("chain") else "-",
            f"{sum(len(point.notes) for point in group) / sum(point.perfect_characters for point in group):.2f}",
            f"{correct}/{asked} ({correct / asked:.1%})",
            f"{sum(without_totals)}/{len(without_totals)} ({sum(without_totals) / len(without_totals):.1%})",
            f"{sum(point.ceiling for point in group) / asked:.1%}", f"{sum(point.floor for point in group) / asked:.1%}",
        ]
        lines.append("| " + " | ".join(map(str, cells)) + " |")
    return "\n".join(lines)


def lost_after_correct(chain_points: list[Point]) -> int:
    """Facts a chain had right at one examined point and not at a later one, while the truth kept the same value."""
    lost = set()
    last_correct = {}  # fact -> value it had when the notes last had it right
    for point in chain_points:
        for fact, (outcome, value) in point.comparison.fact_outcomes.items():
            if outcome == "correct":
                last_correct[fact] = value
            elif last_correct.get(fact) == value:
                lost.add(fact)
    return len(lost)


def domain_table(points: list[Point]) -> str:
    """Facts and exam answers by domain, over every examined point."""
    facts = Counter()
    paraphrased = Counter()
    extra = Counter()
    exam = Counter()
    for point in points:
        facts.update(point.comparison.facts)
        paraphrased.update(point.comparison.paraphrased)
        extra.update(point.comparison.lines)
        for question, question_grade in zip(point.questions, point.grades, strict=True):
            exam[question.domain, question_grade.outcome] += 1
    header = "| domain | " + " | ".join(f"fact {outcome}" for outcome in FACT_OUTCOMES) + " | of them paraphrased | " + " | ".join(f"+{outcome}" for outcome in LINE_OUTCOMES) + " | " + " | ".join(f"exam {outcome}" for outcome in OUTCOMES) + " |"
    lines = [header, "| --- |" + " --: |" * (header.count("|") - 2)]
    for domain in [*DOMAINS, "unknown"]:
        row = [facts[domain, outcome] for outcome in FACT_OUTCOMES] + [paraphrased[domain]] + [extra[domain, outcome] for outcome in LINE_OUTCOMES] + [exam[domain, outcome] for outcome in OUTCOMES]
        if any(row):
            lines.append(f"| {domain} | " + " | ".join(map(str, row)) + " |")
    return "\n".join(lines)


def watched_lines(points: list[Point], watched: list[str]) -> str:
    lines = []
    for point in points:
        for word in watched:
            found = [line.strip() for line in point.notes.splitlines() if word.casefold() in line.casefold()]
            lines.append(f"- {point.label} N={point.session_id} '{word}': {found or 'absent'}")
    return "\n".join(lines)


def errors(points: list[Point]) -> str:
    lines = []
    for point in points:
        for outcome, domain, text in point.comparison.examples:
            lines.append(f"- {point.label} N={point.session_id} | {outcome} | {domain} | {text}")
        for question, question_grade in zip(point.questions, point.grades, strict=True):
            if question_grade.outcome != "correct":
                lines.append(f"- {point.label} N={point.session_id} | exam {question_grade.outcome} | {question.question_id} | {question.probe} | expected {question_grade.expected!r} | given {question_grade.given!r}")
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("period", choices=("weekly", "monthly", "quarterly"))
    parser.add_argument("persona")
    parser.add_argument("experiment", choices=("chain", "single", "window"))
    parser.add_argument("--cadence", type=int, nargs="+", default=[7], help="chain: sessions between dreams")
    parser.add_argument("--through", type=int, default=56, help="chain: last session")
    parser.add_argument("--at", type=int, nargs="+", default=[35], help="single, window: the sessions the dreams end at")
    parser.add_argument("--sizes", type=int, nargs="+", default=[1, 5, 20, 50], help="window: sessions each dream reads")
    parser.add_argument("--dream", default="dreaming.dream:dream", help="module:function with the signature of dreaming.dream.dream")
    parser.add_argument("--budget-name", default="p4b")
    parser.add_argument("--limit", type=float, default=1.20)
    parser.add_argument("--run-prefix", default="p4b/stub", help="dreams and exams are cached under results/raw/<run-prefix>/")
    parser.add_argument("--watch", nargs="*", default=[], help="print the note lines that contain these words at each point")
    parser.add_argument("--errors", action="store_true", help="list every line and exam answer that is not correct")
    parser.add_argument("--dry-run", action="store_true", help="estimate the cost if nothing were cached, and stop")
    arguments = parser.parse_args(argv)

    if arguments.experiment == "chain":
        sequences = [chain(cadence, arguments.through) for cadence in arguments.cadence]
    elif arguments.experiment == "single":
        sequences = [single(session_id) for session_id in arguments.at]
    else:
        sequences = [window(size, session_id) for session_id in arguments.at for size in arguments.sizes]
    client = BudgetedClient(arguments.budget_name, arguments.limit)
    dreams, exam_count, dollars = estimate(arguments.period, arguments.persona, sequences)
    print(f"== {arguments.experiment} {arguments.period}/{arguments.persona} | dream {arguments.dream} | runs {arguments.run_prefix}")
    print(f"estimate if nothing were cached: {dreams} dreams, {exam_count} exams, about ${dollars:.4f}. Budget {arguments.budget_name}: spent ${client.spent():.4f} of ${arguments.limit:.2f}")
    if arguments.dry_run:
        return
    spent_before = client.spent()
    try:
        points = measure(load_dream(arguments.dream), arguments.period, arguments.persona, sequences, client, arguments.run_prefix)
    finally:
        print(f"cost: ${client.spent() - spent_before:.4f} paid now. Budget {arguments.budget_name}: spent ${client.spent():.4f} of ${arguments.limit:.2f}")
    print(f"dream cost of the sequences up to their last examined point: ${sum(max(point.dream_cost for point in points if point.label == label) for label in {point.label for point in points}):.4f}\n")
    print(summary_table(points))
    print()
    print(points_table(points))
    print()
    print(domain_table(points))
    if arguments.watch:
        print()
        print(watched_lines(points, arguments.watch))
    if arguments.errors:
        print()
        print(errors(points))


if __name__ == "__main__":
    main(sys.argv[1:])
