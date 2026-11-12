"""Grade synthetic answers on the real exam, without a model, to check that every outcome comes out where it should."""

import sys
from collections import Counter

from exam.grading import OUTCOMES, grade, render, tally, tally_table
from exam.questions import build_exam
from exam.schema import DOMAINS, UNKNOWN, Question
from truth.changes import personas


def previous_state(question: Question) -> dict | None:
    return question.history[-1] if question.history else None


SYNTHETIC_AGENTS = {
    "perfect": lambda question: render(question, question.current),
    "always unknown": lambda question: UNKNOWN,
    "previous state": lambda question: render(question, previous_state(question)),
}


def expected_outcome(agent: str, question: Question) -> str:
    """What each synthetic agent must get, derived from the definitions of the outcomes."""
    answer = SYNTHETIC_AGENTS[agent](question)
    if answer == render(question, question.current):
        return "correct"
    if answer == UNKNOWN:
        return "missing"
    return "stale"


def by_domain(counts: dict[tuple[str, str, str], int]) -> str:
    """A Markdown table with one row per domain and one column per outcome."""
    totals = Counter()
    for (domain, _, outcome), count in counts.items():
        totals[domain, outcome] += count
    lines = ["| domain | " + " | ".join(OUTCOMES) + " |", "| --- |" + " --: |" * len(OUTCOMES)]
    for domain in DOMAINS:
        lines.append(f"| {domain} | " + " | ".join(str(totals[domain, outcome]) for outcome in OUTCOMES) + " |")
    return "\n".join(lines)


def main(periods: list[str]) -> None:
    for period in periods:
        questions = [question for persona in personas(period) for question in build_exam(period, persona)]
        for agent, answer in SYNTHETIC_AGENTS.items():
            grades = [grade(question, answer(question)) for question in questions]
            mismatches = sum(
                question_grade.outcome != expected_outcome(agent, question)
                for question, question_grade in zip(questions, grades)
            )
            counts = tally(questions, grades)
            print(f"== {period}: {agent} ({len(questions)} questions, {mismatches} unexpected outcomes)")
            print(by_domain(counts))
            print()
            print(tally_table(counts))
            print()


if __name__ == "__main__":
    main(sys.argv[1:] or ["weekly"])
