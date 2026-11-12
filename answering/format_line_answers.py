"""The first prompt P3a tried: rules, then "<number>: <answer>" lines with nothing before them. A variant of the format comparison."""

import re

from answering.client import BudgetedClient
from exam.schema import Question

SYSTEM = (
    "You are the user's personal assistant, starting a new session. Everything you know about the user is in your notes. "
    "The notes are complete and up to date: they were rewritten from all your past conversations with the user."
)

RULES = """Answer each question using only the notes.
- To-do list, calendar, and documents are complete lists: if a task, event, or document item is not in the notes, it is not there, so answer "no", not "unknown".
- Likes and dislikes: answer like or dislike only as the notes record it; if the notes record no opinion about it, answer "unknown".
- A number or date the notes do not contain: answer "unknown".
- Dates as YYYY-MM-DD. Numbers in digits only, without currency signs, units, or words (for example 1234.5).
- A total: add up every matching entry in the notes.

Reply with exactly one line per question, "<number>: <answer>", and nothing else."""

OUTPUT_TOKENS_PER_QUESTION = 15


def answer_exam(notes: str, questions: list[Question], client: BudgetedClient, run: str, repeat: int = 0) -> list[str | None]:
    """One call for the whole exam. One answer per question, in order; None where the model gave none."""
    completion = client.complete(run, SYSTEM, exam_prompt(notes, questions), max_tokens=max_tokens(questions), repeat=repeat)
    return parse_answers(completion.text, len(questions))


def exam_prompt(notes: str, questions: list[Question]) -> str:
    numbered = "\n".join(f"{number}. {question.prompt}" for number, question in enumerate(questions, start=1))
    return f"<notes>\n{notes}\n</notes>\n\n{RULES}\n\n<questions>\n{numbered}\n</questions>"


def max_tokens(questions: list[Question]) -> int:
    return OUTPUT_TOKENS_PER_QUESTION * len(questions) + 200


def parse_answers(text: str, question_count: int) -> list[str | None]:
    """The first "<number>: <answer>" line for each question number; None for numbers the reply skips."""
    answers = {}
    for line in text.splitlines():
        match = re.match(r"\s*(\d+)\s*[:.)]\s*(.*)", line)
        if match:
            answers.setdefault(int(match.group(1)), match.group(2).strip())
    return [answers.get(number) for number in range(1, question_count + 1)]
