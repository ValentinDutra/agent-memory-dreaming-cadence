"""Notes plus running weekly totals of food expenses and steps, weeks Sunday to Saturday.

A dream keeps them by adding each new expense or step count to the total of the week its date falls in.
Memora's periods start on Sunday 2025-06-01, so these weeks are the ones the exam asks about.
"""

from collections import defaultdict
from datetime import date, timedelta

from answering import notes
from truth.timeline import FactId


def render_notes(facts: dict[FactId, dict]) -> str:
    """The notes of notes.render_notes (no document prose) plus the weekly totals."""
    return with_totals(notes.render_notes(facts), facts)


def render_markdown(facts: dict[FactId, dict]) -> str:
    """Every fact, prose included, plus the weekly totals: the first variant measured."""
    return with_totals(notes.render_markdown(facts), facts)


def render_markdown_without_prose(facts: dict[FactId, dict]) -> str:
    """The second variant measured: no prose, empty lists left out."""
    return with_totals(notes.render_markdown(notes.without_prose(facts)), facts)


def with_totals(notes_text: str, facts: dict[FactId, dict]) -> str:
    expenses = defaultdict(float)
    steps = defaultdict(int)
    for (domain, key), value in facts.items():
        if domain == "expense":
            expenses[week_start(value["date"])] += value["amount"]
        elif domain == "steps":
            steps[week_start(key[0])] += value["step_count"]
    lines = []
    for start in sorted(expenses.keys() | steps.keys()):
        end = (date.fromisoformat(start) + timedelta(days=6)).isoformat()
        totals = []
        if start in expenses:
            totals.append(f"food expenses ${expenses[start]:.2f}")
        if start in steps:
            totals.append(f"{steps[start]} steps")
        lines.append(f"- Week {start} to {end} (so far): " + ", ".join(totals))
    return notes_text + "\n\n## Weekly totals (Sunday to Saturday)\n" + "\n".join(lines) if lines else notes_text


def week_start(day: str) -> str:
    """The Sunday on or before `day`."""
    parsed = date.fromisoformat(day)
    return (parsed - timedelta(days=(parsed.weekday() + 1) % 7)).isoformat()
