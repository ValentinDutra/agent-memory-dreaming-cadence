"""Exam questions no dream can get right, because Memora's answer key holds what the user never said. Owner: P5.

Decision (c), docs/p2-examen.md: these questions stay in the exam and in its cache; they are only marked, so
every result is reported with and without them. The rule reads the truth and the transcripts, never a model:

- unsaid_item: "Is X on the list?" while X holds, and the session where X started holding never says all of X's words
  (Memora stores "Ms. Anya Sharma (Data Scientist, Predictive Analytics Unit)"; the user said "Ms. Anya Sharma").
- relative_date: an expense the user dated "last night" or "yesterday", which Memora always dates on the session's
  day. A dream writes the day before, so the question about that day, the question about the same expense type on the
  day before once it is logged (the user spent on two of them that day: "$45.81 dinner last night" in s429 joins
  the 2025-06-19 dinner of s402), and a weekly total whose first day is that day, cannot be answered. Steps are never
  dated that way in weekly or monthly.
- completed_task: "Is X on the to-do list?" while X holds, where Memora added X in a session whose user turn naming X
  says it is done ("I completed a task to coordinate with the research team"). A dream that believes the user keeps X
  off the list.

Paraphrases are not marked: an item the user said in other words ("Coordinate with the research team") can still be
written and recognized, and most are answered right. The report counts them to show how many there are.

Run: uv run python -m exam.unreachable weekly monthly
"""

import re
import sys
from collections import Counter
from datetime import date, timedelta
from functools import cache
from typing import Literal

from dreaming.transcripts import Session, load_transcripts
from exam.questions import build_exam
from exam.schema import DOMAINS, Question
from truth.changes import persona_changes, personas
from truth.timeline import Timeline, build_timeline, text_support, words

Reason = Literal["unsaid_item", "relative_date", "completed_task"]
REASONS = ("unsaid_item", "relative_date", "completed_task")

RELATIVE_DAY = re.compile(r"\b(?:last night|yesterday)\b", flags=re.IGNORECASE)
# "I just had a $9.81 lunch today, mostly leftovers from yesterday" (monthly/creative_designer s132) is today's lunch.
TODAY = re.compile(r"\btoday\b", flags=re.IGNORECASE)
# Past tense only: "I need to complete the report" announces a task.
COMPLETED = re.compile(r"\b(?:completed|finished|done with|wrapped up|took care of|crossed off)\b", flags=re.IGNORECASE)
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


@cache
def unreachable(period: str, persona: str) -> dict[str, Reason]:
    """question_id -> why no dream can answer it, for the questions of build_exam(period, persona) that qualify."""
    timeline = build_timeline(persona_changes(period, persona))
    sessions = {session.session_id: session for session in load_transcripts(period, persona)}
    shifted_dates = relative_dated_expenses(timeline, sessions)
    reasons = {}
    for question in build_exam(period, persona):
        reason = question_reason(question, timeline, sessions, shifted_dates)
        if reason:
            reasons[question.question_id] = reason
    return reasons


def question_reason(question: Question, timeline: Timeline, sessions: dict[int, Session], shifted_dates: set[tuple[str, int]]) -> Reason | None:
    if question.domain in ("todo", "calendar", "content") and question.field is None and question.current is not None:
        started = holding_version(timeline, question.fact, question.session_id).valid_from
        if text_support(question.fact[1][-1], session_text(sessions[started])) != "full":
            return "unsaid_item"
    if question.domain == "todo" and question.current is not None:
        started = holding_version(timeline, question.fact, question.session_id).valid_from
        if any(turn.speaker == "user_agent" and COMPLETED.search(turn.message) and text_support(question.fact[1][0], turn.message) != "absent" for turn in sessions[started].turns):
            return "completed_task"
    if question.domain == "expense" and question.probe != "aggregate":
        started = holding_version(timeline, question.fact, question.session_id).valid_from
        if (question.fact, started) in shifted_dates:
            return "relative_date"
        asked = holding_version(timeline, question.fact, question.session_id).value
        for fact, logged_in in shifted_dates:
            shifted = holding_version(timeline, fact, logged_in).value
            if logged_in <= question.session_id and shifted["expense_type"] == asked["expense_type"] and day_before(shifted["date"]) == asked["date"]:
                return "relative_date"
    if question.domain == "expense" and question.probe == "aggregate":
        first_day = re.search(r"dated from (\d{4}-\d{2}-\d{2})", question.prompt).group(1)
        if any(sessions[started].date == first_day and started <= question.session_id for _, started in shifted_dates):
            return "relative_date"
    return None


def day_before(iso_date: str) -> str:
    return (date.fromisoformat(iso_date) - timedelta(days=1)).isoformat()


def holding_version(timeline: Timeline, fact, session_id: int):
    """The version of the fact that holds after session_id, or the last one before it."""
    versions = [version for version in timeline.versions if (version.domain, version.key) == fact and version.valid_from <= session_id]
    return max(versions, key=lambda version: version.valid_from)


def relative_dated_expenses(timeline: Timeline, sessions: dict[int, Session]) -> set[tuple[tuple, int]]:
    """(fact, session it was logged in) for expenses whose amount the user gave in a turn that says "last night" or "yesterday"."""
    shifted = set()
    for version in timeline.versions:
        if version.domain != "expense":
            continue
        session = sessions[version.valid_from]
        amount = round(float(version.value["amount"]), 2)
        turn = next((turn for turn in session.turns if amount in numbers(turn.message)), None)
        if turn and RELATIVE_DAY.search(turn.message) and not TODAY.search(turn.message) and version.value["date"] == session.date:
            shifted.add(((version.domain, version.key), version.valid_from))
    return shifted


def numbers(text: str) -> set[float]:
    return {round(float(match.replace(",", "")), 2) for match in NUMBER.findall(text)}


def session_text(session: Session) -> str:
    return " ".join(turn.message for turn in session.turns)


def said_in_other_words(question: Question, timeline: Timeline, sessions: dict[int, Session]) -> bool:
    """A held list item whose words the session says, but not one after another as the question asks it."""
    if question.domain not in ("todo", "calendar", "content") or question.field is not None or question.current is None:
        return False
    text = session_text(sessions[holding_version(timeline, question.fact, question.session_id).valid_from])
    return " ".join(words(question.fact[1][-1])) not in " ".join(words(text))


def report(period: str) -> None:
    asked = Counter()
    marked = Counter()
    other_words = Counter()
    for persona in personas(period):
        reasons = unreachable(period, persona)
        timeline = build_timeline(persona_changes(period, persona))
        sessions = {session.session_id: session for session in load_transcripts(period, persona)}
        for question in build_exam(period, persona):
            asked[question.domain] += 1
            if question.question_id in reasons:
                marked[question.domain, reasons[question.question_id]] += 1
            elif said_in_other_words(question, timeline, sessions):
                other_words[question.domain] += 1
    print(f"== {period}: questions no dream can get right, by domain")
    print("| domain | questions | " + " | ".join(REASONS) + " | marked | said in other words (not marked) |")
    print("| --- |" + " --: |" * (len(REASONS) + 3))
    for domain in [*DOMAINS, "total"]:
        domains = DOMAINS if domain == "total" else (domain,)
        cells = [sum(marked[each, reason] for each in domains) for reason in REASONS]
        total_asked = sum(asked[each] for each in domains)
        paraphrased = sum(other_words[each] for each in domains)
        print(f"| {domain} | {total_asked} | " + " | ".join(map(str, cells)) + f" | {sum(cells)} ({sum(cells) / total_asked:.1%}) | {paraphrased} |")


if __name__ == "__main__":
    for period in sys.argv[1:]:
        report(period)
