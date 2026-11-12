"""Compare note and prompt formats with perfect notes on the same exams.

uv run python -m answering.format_compare weekly software_engineer --formats stub+stub,markdown+block --sessions 7,14 --repeats 0,1 [--errors] [--estimate]
"""

import argparse
from collections import Counter

from answering import answer, format_json, format_json_answers, format_line_answers, format_stub, format_totals, format_work_answers, notes
from answering.client import BudgetedClient, worst_case_cost
from exam.grading import OUTCOMES, grade, negates_removed_preference
from exam.questions import build_exam
from exam.schema import DOMAINS
from truth.changes import persona_changes
from truth.timeline import build_timeline

BUDGET_NAME = "p3a"
BUDGET_DOLLARS = 0.80


NOTES = {
    "stub": format_stub.render_notes,
    "markdown": notes.render_markdown,
    "markdown_without_prose": lambda facts: notes.render_markdown(notes.without_prose(facts)),
    "markdown_with_totals": format_totals.render_markdown,
    "markdown_without_prose_with_totals": format_totals.render_markdown_without_prose,
    "notes": notes.render_notes,
    "notes_with_totals": format_totals.render_notes,
    "json": format_json.render_notes,
}

THINKING_OFF = {"type": "disabled"}
THINKING_ADAPTIVE = {"type": "adaptive"}

# name -> (answer_exam, thinking, effort)
ANSWERS = {
    "stub": (format_stub.answer_exam, THINKING_OFF, "low"),
    "lines": (format_line_answers.answer_exam, THINKING_OFF, "low"),
    "json": (format_json_answers.answer_exam, THINKING_OFF, "low"),
    "block": (answer.answer_exam, THINKING_OFF, "low"),
    "work": (format_work_answers.answer_exam, THINKING_OFF, "low"),
    "block_thinking": (answer.answer_exam, THINKING_ADAPTIVE, "low"),
    "block_thinking_medium": (answer.answer_exam, THINKING_ADAPTIVE, "medium"),
}

class RecordingClient:
    """Keeps every Completion so the comparison can report tokens and cost per exam."""

    def __init__(self, client: BudgetedClient):
        self.client = client
        self.thinking = client.thinking
        self.completions = []

    def complete(self, run, system, user, max_tokens, repeat=0):
        completion = self.client.complete(run, system, user, max_tokens, repeat)
        self.completions.append(completion)
        return completion


class EstimatingClient:
    """Adds up the client's worst-case cost of each call without calling the API."""

    def __init__(self, thinking: dict):
        self.thinking = thinking
        self.dollars = 0.0

    def complete(self, run, system, user, max_tokens, repeat=0):
        self.dollars += worst_case_cost(system + user, max_tokens)
        raise LookupError


def compare(period: str, persona: str, format_names: list[str], sessions: list[int] | None, repeats: list[int], show_errors: bool, estimate: bool) -> None:
    timeline = build_timeline(persona_changes(period, persona))
    exam = build_exam(period, persona)
    exam_sessions = sorted({question.session_id for question in exam} & set(sessions)) if sessions else sorted({question.session_id for question in exam})
    print(f"== {period}/{persona}: {len(exam_sessions)} exams, sessions {exam_sessions}")
    for name in format_names:
        notes_name, answers_name = name.split("+")
        render_notes = NOTES[notes_name]
        answer_exam, thinking, effort = ANSWERS[answers_name]
        if estimate:
            estimator = EstimatingClient(thinking)
            for session_id in exam_sessions:
                questions = [question for question in exam if question.session_id == session_id]
                try:
                    answer_exam(render_notes(timeline.state_after(session_id)), questions, estimator, "estimate")
                except LookupError:
                    pass
            print(f"  {name:<24} worst case ${estimator.dollars * len(repeats):.4f}")
            continue
        client = BudgetedClient(BUDGET_NAME, BUDGET_DOLLARS, thinking=thinking, effort=effort)
        for repeat in repeats:
            recorder = RecordingClient(client)
            outcomes = Counter()
            by_domain = Counter()
            by_position = Counter()
            lenient = 0
            questions_seen = []
            for session_id in exam_sessions:
                questions = [question for question in exam if question.session_id == session_id]
                notes_text = render_notes(timeline.state_after(session_id))
                answers = answer_exam(notes_text, questions, recorder, f"p3a/{name}/{period}/{persona}", repeat)
                for position, (question, given) in enumerate(zip(questions, answers, strict=True), start=1):
                    question_grade = grade(question, given)
                    by_position[position == 1, question_grade.outcome == "correct"] += 1
                    outcomes[question_grade.outcome] += 1
                    by_domain[question.domain, question_grade.outcome == "correct"] += 1
                    lenient += question_grade.outcome == "correct" or negates_removed_preference(question, question_grade)
                    questions_seen.append((question, given, question_grade))
            report(f"{name} repeat {repeat}", questions_seen, outcomes, by_domain, by_position, lenient, recorder.completions, show_errors)


def report(name, questions_seen, outcomes, by_domain, by_position, lenient, completions, show_errors) -> None:
    total = len(questions_seen)
    exams = len(completions)
    domains = " ".join(
        f"{domain} {by_domain[domain, True]}/{by_domain[domain, True] + by_domain[domain, False]}"
        for domain in DOMAINS
        if by_domain[domain, True] + by_domain[domain, False]
    )
    print(f"  {name}")
    print(f"    correct {outcomes['correct']}/{total} ({outcomes['correct'] / total:.1%}), lenient {lenient}/{total}  " + " ".join(f"{outcome} {outcomes[outcome]}" for outcome in OUTCOMES))
    print(f"    by domain: {domains}")
    single = [question_grade.outcome == "correct" for question, _, question_grade in questions_seen if question.probe != "aggregate"]
    print(f"    without the totals questions: correct {sum(single)}/{len(single)} ({sum(single) / len(single):.1%})")
    print(f"    first question correct {by_position[True, True]}/{by_position[True, True] + by_position[True, False]}, the others {by_position[False, True]}/{by_position[False, True] + by_position[False, False]}")
    print(
        f"    per exam: {sum(completion.input_tokens for completion in completions) / exams:.0f} input tokens, "
        f"{sum(completion.output_tokens for completion in completions) / exams:.0f} output tokens; "
        f"cost ${sum(completion.cost for completion in completions):.4f} ({sum(not completion.from_cache for completion in completions)} paid now)"
    )
    for question, given, question_grade in questions_seen if show_errors else []:
        if question_grade.outcome != "correct":
            print(f"    - {question_grade.outcome:<11} {question.question_id} expected {question_grade.expected!r} given {given!r}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("period")
    parser.add_argument("personas", help="comma-separated")
    parser.add_argument("--formats", required=True, help="comma-separated <notes>+<answers>, e.g. markdown+block; see NOTES and ANSWERS")
    parser.add_argument("--sessions", help="comma-separated exam sessions; all by default")
    parser.add_argument("--repeats", default="0", help="comma-separated repeat numbers; each is a fresh sample of the same exams")
    parser.add_argument("--errors", action="store_true", help="list every answer that is not correct")
    parser.add_argument("--estimate", action="store_true", help="print the worst-case cost without calling the API")
    arguments = parser.parse_args()
    for persona in arguments.personas.split(","):
        compare(
            arguments.period,
            persona,
            arguments.formats.split(","),
            [int(session) for session in arguments.sessions.split(",")] if arguments.sessions else None,
            [int(repeat) for repeat in arguments.repeats.split(",")],
            arguments.errors,
            arguments.estimate,
        )
    print(f"spent so far on {BUDGET_NAME}: ${BudgetedClient(BUDGET_NAME, BUDGET_DOLLARS).spent():.4f}")
