"""The prompt of answer.py, plus room to add up totals in <work> tags before the <answers> block. A variant of the format comparison."""

from answering.answer import RULES, SYSTEM, exam_prompt, max_tokens, parse_answers
from answering.client import BudgetedClient
from exam.schema import Question

WORK_RULES = RULES.replace(
    "Reply with the answers inside <answers> tags",
    "First, inside <work> tags, write out the entries and the additions for every question that asks for a total. Then reply with the answers inside <answers> tags",
)
WORK_OUTPUT_TOKENS = 1500


def answer_exam(notes: str, questions: list[Question], client: BudgetedClient, run: str, repeat: int = 0) -> list[str | None]:
    completion = client.complete(run, SYSTEM, exam_prompt(notes, questions, WORK_RULES), max_tokens=max_tokens(questions) + WORK_OUTPUT_TOKENS, repeat=repeat)
    return parse_answers(completion.text, len(questions))
