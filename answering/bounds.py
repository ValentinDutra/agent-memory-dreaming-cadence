"""Ceiling, floor and noise of answering from notes. Owner: P3b.

ceiling: perfect notes, render_notes(timeline.state_after(N)), for the exam of session N.
floor:   empty notes, render_notes({}).
noise:   the ceiling exam repeated NOISE_REPEATS times (repeat 0 is the ceiling run itself).

Every call goes through BudgetedClient, so answers already paid for are read from results/raw/ for free.
Before spending, a dry pass prices the calls that are not cached yet.
"""

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass

from answering.answer import answer_exam
from answering.client import EFFORT, THINKING, BudgetedClient, BudgetExceeded, cost_of
from answering.format_totals import with_totals
from answering.notes import render_notes
from exam.grading import OUTCOMES, grade, negates_removed_preference, tally, tally_table
from exam.questions import build_exam
from exam.schema import DOMAINS, Grade, Question
from truth.changes import persona_changes
from truth.timeline import FactId, build_timeline

MEASURES = ("ceiling", "floor", "noise")
NOISE_REPEATS = 3
# Input estimate for the dry pass: these prompts measured 2.6 bytes per input token. Output is priced at max_tokens.
BYTES_PER_TOKEN = 2.5


CLOSED_WORLD = (
    "These notes are complete and up to date. A to-do, calendar event or document item that is not listed here "
    "is not there: answer no. A preference that is not listed means the user has no current opinion."
)

NOTHING_LOGGED = "Expenses and step counts are listed by date: a date with no entry has nothing logged, so a total covers only the listed entries."
GOAL_LEGEND = "Goals: daily_steps is the user's daily step goal; every other goal is the user's weekly spending budget, in dollars, for that expense type."


def notes_variant(facts: dict[FactId, dict], additions: tuple[str, ...]) -> str:
    """render_notes(facts), optionally with a closed-world header, legends of goals and logs, and P3a's weekly totals, to test format hypotheses."""
    parts = [render_notes(facts)]
    if "goals" in additions:
        parts.insert(0, GOAL_LEGEND)
    if "logs" in additions:
        parts.insert(0, NOTHING_LOGGED)
    if "closed" in additions:
        parts.insert(0, CLOSED_WORLD)
    notes = "\n".join(part for part in parts if part)
    return with_totals(notes, facts) if "totals" in additions else notes


NOTES_ADDITIONS = ("closed", "goals", "logs", "totals")


class CallLog:
    """Keeps every completion answer_exam asks for, and in a dry pass prices each call that is not cached."""

    def __init__(self, client: BudgetedClient, dry_run: bool):
        self.client = client
        self.thinking = client.thinking  # answer_exam sizes max_tokens by it
        self.dry_run = dry_run
        self.completions = []
        self.uncached_estimates = []
        self.truncated = 0  # responses that hit max_tokens, so their last answers are missing

    def complete(self, run: str, system: str, user: str, max_tokens: int, repeat: int = 0):
        try:
            completion = self.client.complete(run, system, user, max_tokens, repeat=repeat)
        except BudgetExceeded:
            if self.dry_run:
                prompt_tokens = round(len((system + user).encode()) / BYTES_PER_TOKEN)
                self.uncached_estimates.append(cost_of({"input_tokens": prompt_tokens, "output_tokens": max_tokens}))
            raise
        self.completions.append(completion)
        self.truncated += completion.output_tokens >= max_tokens
        return completion


@dataclass(frozen=True)
class ExamRun:
    measure: str
    repeat: int
    questions: list[Question]
    grades: list[Grade]
    positions: list[int]  # where each question stood in the prompt, from 1


def exams_by_session(period: str, persona: str, every: int) -> dict[int, list[Question]]:
    """Every k-th exam of the persona, keyed by its session."""
    by_session = defaultdict(list)
    for question in build_exam(period, persona):
        by_session[question.session_id].append(question)
    sessions = sorted(by_session)[::every]
    return {session_id: by_session[session_id] for session_id in sessions}


def planned_runs(measures: list[str]) -> list[tuple[str, bool, int]]:
    """(measure, perfect notes, repeat) for each requested measure. Noise reuses the ceiling as its repeat 0."""
    runs = []
    for measure in measures:
        if measure == "noise":
            runs += [("noise", True, repeat) for repeat in range(NOISE_REPEATS)]
        else:
            runs.append((measure, measure == "ceiling", 0))
    return runs


def answer_in_order(notes: str, questions: list[Question], call_log: CallLog, run: str, repeat: int, reversed_order: bool) -> list[str | None]:
    """Asking the exam backwards tells whether an error follows the question or its position in the prompt."""
    if not reversed_order:
        return answer_exam(notes, questions, call_log, run=run, repeat=repeat)
    return answer_exam(notes, questions[::-1], call_log, run=run, repeat=repeat)[::-1]


def measure_exams(
    period: str, personas: list[str], measures: list[str], every: int, call_log: CallLog,
    notes_additions: tuple[str, ...] = (), reversed_order: bool = False,
) -> list[ExamRun]:
    """Answer and grade every sampled exam. Stops at the first BudgetExceeded outside a dry pass."""
    exam_runs = []
    for persona in personas:
        timeline = build_timeline(persona_changes(period, persona))
        for session_id, questions in exams_by_session(period, persona, every).items():
            graded = {}  # (perfect notes, repeat) -> grades, so noise repeat 0 is the ceiling run
            for measure, perfect_notes, repeat in planned_runs(measures):
                if (perfect_notes, repeat) not in graded:
                    notes = notes_variant(timeline.state_after(session_id) if perfect_notes else {}, notes_additions)
                    try:
                        answers = answer_in_order(notes, questions, call_log, f"bounds/{period}/{persona}", repeat, reversed_order)
                    except BudgetExceeded:
                        if not call_log.dry_run:
                            raise
                        graded[perfect_notes, repeat] = None
                        continue
                    graded[perfect_notes, repeat] = [grade(question, answer) for question, answer in zip(questions, answers, strict=True)]
                if graded[perfect_notes, repeat] is None:
                    continue
                positions = list(range(len(questions), 0, -1)) if reversed_order else list(range(1, len(questions) + 1))
                exam_runs.append(ExamRun(measure, repeat, questions, graded[perfect_notes, repeat], positions))
    return exam_runs


def domain_table(questions: list[Question], grades: list[Grade]) -> str:
    """Outcomes by domain, the lenient count of "dislike" after a removed like, and both accuracies."""
    counts = Counter()
    lenient = Counter()
    for question, question_grade in zip(questions, grades, strict=True):
        counts[question.domain, question_grade.outcome] += 1
        lenient[question.domain] += negates_removed_preference(question, question_grade)
    header = "| domain | n | " + " | ".join(OUTCOMES) + " | lenient | accuracy | lenient accuracy |"
    lines = [header, "| --- |" + " --: |" * (len(OUTCOMES) + 4)]
    for domain in [*DOMAINS, "all"]:
        domains = DOMAINS if domain == "all" else (domain,)
        row = [sum(counts[each, outcome] for each in domains) for outcome in OUTCOMES]
        lenient_count = sum(lenient[each] for each in domains)
        total = sum(row)
        if total == 0:
            continue
        correct = row[0]
        cells = [str(total), *map(str, row), str(lenient_count), f"{correct / total:.1%}", f"{(correct + lenient_count) / total:.1%}"]
        lines.append(f"| {domain} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def noise_report(noise_runs: list[ExamRun]) -> str:
    """How many answers change across repeats of the same exam, and the range of accuracy by domain."""
    answers = defaultdict(dict)
    outcomes = defaultdict(dict)
    correct = Counter()
    asked = Counter()
    domain_of = {}
    for exam_run in noise_runs:
        for question, question_grade in zip(exam_run.questions, exam_run.grades, strict=True):
            answers[question.question_id][exam_run.repeat] = question_grade.given
            outcomes[question.question_id][exam_run.repeat] = question_grade.outcome
            domain_of[question.question_id] = question.domain
            asked[question.domain, exam_run.repeat] += 1
            correct[question.domain, exam_run.repeat] += question_grade.outcome == "correct"
    complete = [question_id for question_id in answers if len(answers[question_id]) == NOISE_REPEATS]
    answer_changed = Counter(domain_of[question_id] for question_id in complete if len(set(answers[question_id].values())) > 1)
    outcome_changed = Counter(domain_of[question_id] for question_id in complete if len(set(outcomes[question_id].values())) > 1)
    questions_per_domain = Counter(domain_of[question_id] for question_id in complete)
    lines = [
        "| domain | questions | answer changed | outcome changed | " + " | ".join(f"accuracy r{repeat}" for repeat in range(NOISE_REPEATS)) + " | range (pp) |",
        "| --- |" + " --: |" * (NOISE_REPEATS + 4),
    ]
    for domain in [*DOMAINS, "all"]:
        domains = DOMAINS if domain == "all" else (domain,)
        total = sum(questions_per_domain[each] for each in domains)
        if total == 0:
            continue
        accuracies = [
            sum(correct[each, repeat] for each in domains) / sum(asked[each, repeat] for each in domains)
            for repeat in range(NOISE_REPEATS)
        ]
        cells = [
            str(total),
            str(sum(answer_changed[each] for each in domains)),
            str(sum(outcome_changed[each] for each in domains)),
            *(f"{accuracy:.1%}" for accuracy in accuracies),
            f"{100 * (max(accuracies) - min(accuracies)):.1f}",
        ]
        lines.append(f"| {domain} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def position_report(exam_runs: list[ExamRun]) -> str:
    """Accuracy of the first question in the prompt against the others, over questions whose answer is not "unknown"."""
    asked = Counter()
    correct = Counter()
    for exam_run in exam_runs:
        for position, question, question_grade in zip(exam_run.positions, exam_run.questions, exam_run.grades, strict=True):
            if question_grade.expected == "unknown":
                continue
            slot = "first" if position == 1 else "other"
            asked[question.domain, slot] += 1
            correct[question.domain, slot] += question_grade.outcome == "correct"
    lines = ["| domain | first: correct / n | other: correct / n |", "| --- | --: | --: |"]
    for domain in DOMAINS:
        if asked[domain, "first"] or asked[domain, "other"]:
            cells = [f"{correct[domain, slot]} / {asked[domain, slot]}" for slot in ("first", "other")]
            lines.append(f"| {domain} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def errors_report(exam_runs: list[ExamRun]) -> str:
    lines = []
    for exam_run in exam_runs:
        for question, question_grade in zip(exam_run.questions, exam_run.grades, strict=True):
            if question_grade.outcome != "correct":
                lines.append(
                    f"- {question_grade.outcome} | {question.question_id} | {question.probe} | "
                    f"expected {question_grade.expected!r} | given {question_grade.given!r}"
                )
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("period", choices=("weekly", "monthly", "quarterly"))
    parser.add_argument("personas", nargs="+")
    parser.add_argument("--measure", nargs="+", choices=MEASURES, default=list(MEASURES))
    parser.add_argument("--every", type=int, default=1, help="answer every k-th exam of each persona")
    parser.add_argument("--budget-name", default="p3b")
    parser.add_argument("--limit", type=float, default=1.20, help="dollar cap of the budget")
    parser.add_argument("--notes-add", nargs="*", choices=NOTES_ADDITIONS, default=[], help="format hypotheses added to render_notes")
    parser.add_argument("--thinking", choices=("disabled", "adaptive"), default=THINKING["type"])
    parser.add_argument("--effort", default=EFFORT)
    parser.add_argument("--reversed", action="store_true", help="ask the questions in reverse order")
    parser.add_argument("--dry-run", action="store_true", help="price the calls that are not cached, and stop")
    parser.add_argument("--errors", action="store_true", help="list every answer that is not correct")
    arguments = parser.parse_args(argv)
    thinking = {"type": arguments.thinking}
    measures = [measure for measure in MEASURES if measure in arguments.measure]

    dry_client = BudgetedClient(arguments.budget_name, 0.0, thinking=thinking, effort=arguments.effort)
    dry_log = CallLog(dry_client, dry_run=True)
    measure_exams(arguments.period, arguments.personas, measures, arguments.every, dry_log, tuple(arguments.notes_add), arguments.reversed)
    print(
        f"== bounds {arguments.period} {' '.join(arguments.personas)} | measures {' '.join(measures)} | every {arguments.every} | "
        f"notes render_notes{''.join(' + ' + addition for addition in arguments.notes_add)} | thinking {arguments.thinking} | effort {arguments.effort} | order {'reversed' if arguments.reversed else 'exam'}"
    )
    print(
        f"estimate: {len(dry_log.completions)} calls cached, {len(dry_log.uncached_estimates)} to pay, "
        f"up to ${sum(dry_log.uncached_estimates):.4f} (output priced at max_tokens). "
        f"Budget {arguments.budget_name}: spent ${dry_client.spent():.4f} of ${arguments.limit:.2f}"
    )
    if arguments.dry_run:
        return

    client = BudgetedClient(arguments.budget_name, arguments.limit, thinking=thinking, effort=arguments.effort)
    call_log = CallLog(client, dry_run=False)
    try:
        exam_runs = measure_exams(arguments.period, arguments.personas, measures, arguments.every, call_log, tuple(arguments.notes_add), arguments.reversed)
    finally:
        paid = [completion for completion in call_log.completions if not completion.from_cache]
        print(
            f"cost: ${sum(completion.cost for completion in paid):.4f} paid now in {len(paid)} calls; "
            f"${sum(completion.cost for completion in call_log.completions):.4f} for all {len(call_log.completions)} calls of this measurement; "
            f"{sum(completion.input_tokens for completion in call_log.completions)} input and "
            f"{sum(completion.output_tokens for completion in call_log.completions)} output tokens; "
            f"{call_log.truncated} responses cut at max_tokens. "
            f"Budget {arguments.budget_name}: spent ${client.spent():.4f} of ${arguments.limit:.2f}"
        )

    for measure in measures:
        runs = [exam_run for exam_run in exam_runs if exam_run.measure == measure]
        if measure == "noise":
            print(f"\n### noise: {NOISE_REPEATS} repeats of {len(runs) // NOISE_REPEATS} exams with perfect notes\n")
            print(noise_report(runs))
            continue
        questions = [question for exam_run in runs for question in exam_run.questions]
        grades = [question_grade for exam_run in runs for question_grade in exam_run.grades]
        print(f"\n### {measure}: {len(runs)} exams, {len(questions)} questions\n")
        print(domain_table(questions, grades))
        print()
        print(tally_table(tally(questions, grades)))
        if measure == "ceiling":
            print(f"\n#### {measure}: by position in the prompt (questions whose answer is not unknown)\n")
            print(position_report(runs))
        if arguments.errors and measure == "ceiling":
            print(f"\n#### {measure}: answers that are not correct\n")
            print(errors_report(runs))


if __name__ == "__main__":
    main(sys.argv[1:])
