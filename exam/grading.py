"""The correct answer to each exam question, and how an agent's answer is classified."""

import re
from collections import Counter
from datetime import date, datetime

from exam.schema import DOMAINS, UNKNOWN, Grade, Question

OUTCOMES = ("correct", "stale", "missing", "invented", "unparseable")

UNKNOWN_SYNONYMS = {
    "unknown", "i don't know", "i do not know", "don't know", "dont know", "not sure", "unsure",
    "no idea", "not known", "unclear", "n/a", "no information",
}
CHOICE_SYNONYMS = {"likes": "like", "dislikes": "dislike", "y": "yes", "n": "no"}
DATE_FORMATS = ("%Y-%m-%d", "%B %d, %Y", "%B %d %Y", "%d %B %Y")


def plain_text(answer: str) -> str:
    text = answer.strip().strip("\"'`").strip().casefold()
    text = re.sub(r"\s+", " ", text)
    return text.rstrip(".!")


def as_number(text: str) -> float | None:
    """"$1,234.50", "1234.5" and "1234.50 dollars" are the same number. Totals are compared to the cent."""
    match = re.fullmatch(r"\$?\s*(-?[\d,]*\.?\d+)\s*(?:usd|dollars|steps)?", text)
    if match is None:
        return None
    return round(float(match.group(1).replace(",", "")), 2)


def number_text(number: float) -> str:
    return f"{number:.2f}".rstrip("0").rstrip(".")


def as_date(text: str) -> date | None:
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    return None


def normalize(question: Question, answer: str | None) -> str | None:
    """The answer in canonical form: UNKNOWN, an option, a number, an ISO date or casefolded text. None if unparseable."""
    if answer is None:
        return UNKNOWN
    text = plain_text(str(answer))
    if text in UNKNOWN_SYNONYMS or text == "":
        return UNKNOWN
    if question.answer_format == "choice":
        text = CHOICE_SYNONYMS.get(text, text).replace("_", " ")
        options = {option.casefold().replace("_", " "): option for option in choice_options(question)}
        return options.get(text)
    number = as_number(text)
    if question.answer_format == "number":
        return None if number is None else number_text(number)
    if number is not None:
        return number_text(number)
    parsed_date = as_date(text)
    return parsed_date.isoformat() if parsed_date else text


def choice_options(question: Question) -> tuple[str, ...]:
    return ("yes", "no") if question.field is None else question.options


def render(question: Question, state: dict | None) -> str:
    """What an agent that believes the fact is `state` would answer, in canonical form."""
    if question.field is None:
        return "no" if state is None else "yes"
    if state is None:
        return UNKNOWN
    return normalize(question, str(state[question.field]))


def expected_answer(question: Question) -> str:
    return render(question, question.current)


def grade(question: Question, answer: str | None) -> Grade:
    given = normalize(question, answer)
    expected = expected_answer(question)
    earlier_answers = {render(question, state) for state in question.history if state != question.current}
    if given is None:
        outcome = "unparseable"
    elif given == expected:
        outcome = "correct"
    elif given == UNKNOWN:
        # Abstaining is correct only where the expected answer is UNKNOWN (no current opinion). An agent that
        # cannot say a removed task is gone, or a value that holds, lacks that knowledge.
        outcome = "missing"
    elif given in earlier_answers:
        outcome = "stale"
    else:
        outcome = "invented"
    return Grade(question.question_id, outcome, expected, given if given is not None else plain_text(str(answer)))


def negates_removed_preference(question: Question, grade: Grade) -> bool:
    """After a removed like, "dislike" is invented under the strict reading and correct under the lenient one."""
    return (
        question.field == "preference"
        and question.current is None
        and bool(question.history)
        and question.history[-1] is not None
        and grade.outcome == "invented"
    )


def tally(questions: list[Question], grades: list[Grade]) -> dict[tuple[str, str, str], int]:
    counts = Counter()
    for question, question_grade in zip(questions, grades, strict=True):
        if question.question_id != question_grade.question_id:
            raise ValueError(f"grade {question_grade.question_id} does not match question {question.question_id}")
        counts[(question.domain, question.probe, question_grade.outcome)] += 1
    return dict(counts)


def tally_table(counts: dict[tuple[str, str, str], int]) -> str:
    """A Markdown table with one row per (domain, probe) and one column per outcome."""
    rows = sorted({(domain, probe) for domain, probe, _ in counts}, key=lambda row: (DOMAINS.index(row[0]), row[1]))
    lines = ["| domain | probe | " + " | ".join(OUTCOMES) + " |", "| --- | --- |" + " --: |" * len(OUTCOMES)]
    for domain, probe in rows:
        cells = [str(counts.get((domain, probe, outcome), 0)) for outcome in OUTCOMES]
        lines.append(f"| {domain} | {probe} | " + " | ".join(cells) + " |")
    return "\n".join(lines)
