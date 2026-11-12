"""The same prompt as answer.py, but the reply is a JSON object {"<number>": "<answer>"}. A variant of the format comparison."""

import json

from answering.format_line_answers import RULES, SYSTEM, exam_prompt, max_tokens
from answering.client import BudgetedClient
from exam.schema import Question

JSON_RULES = RULES.replace(
    'Reply with exactly one line per question, "<number>: <answer>", and nothing else.',
    'Reply with only a JSON object mapping each question number to its answer as a string, for example {"1": "yes", "2": "2025-06-04"}.',
)


def answer_exam(notes: str, questions: list[Question], client: BudgetedClient, run: str, repeat: int = 0) -> list[str | None]:
    prompt = exam_prompt(notes, questions).replace(RULES, JSON_RULES)
    completion = client.complete(run, SYSTEM, prompt, max_tokens=max_tokens(questions), repeat=repeat)
    text = completion.text
    try:
        answers = json.loads(text[text.index("{"): text.rindex("}") + 1])
    except ValueError:
        return [None] * len(questions)
    return [None if answers.get(str(number)) is None else str(answers[str(number)]) for number in range(1, len(questions) + 1)]
