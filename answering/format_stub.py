"""The stub P3 handed over, kept as the baseline of the format comparison: "domain | key | value" notes with
internal keys (session_id, document_id) and a prompt that does not say the notes are complete."""

import re

from answering.client import BudgetedClient
from exam.schema import Question
from truth.timeline import FactId

SYSTEM = "You are a personal assistant. You know about the user only what your notes say."


def render_notes(facts: dict[FactId, dict]) -> str:
    return "\n".join(f"{domain} | {' / '.join(key)} | {value}" for (domain, key), value in sorted(facts.items()))


def answer_exam(notes: str, questions: list[Question], client: BudgetedClient, run: str, repeat: int = 0) -> list[str | None]:
    numbered = "\n".join(f"{number}. {question.prompt}" for number, question in enumerate(questions, start=1))
    user = (
        f"<notes>\n{notes}\n</notes>\n\n"
        f"Answer each question using only the notes. Reply with one line per question, as '<number>: <answer>'.\n\n{numbered}"
    )
    completion = client.complete(run, SYSTEM, user, max_tokens=60 * len(questions) + 200, repeat=repeat)
    answers = {}
    for line in completion.text.splitlines():
        match = re.match(r"\s*(\d+)\s*[:.)]\s*(.*)", line)
        if match:
            answers.setdefault(int(match.group(1)), match.group(2).strip())
    return [answers.get(number) for number in range(1, len(questions) + 1)]
