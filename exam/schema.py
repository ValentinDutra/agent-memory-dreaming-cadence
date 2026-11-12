"""What P2a (which questions, when) hands to P2b (how to grade). Owner: P2. Change only through P2."""

from dataclasses import dataclass
from typing import Literal

from truth.timeline import FactId, Timeline

DOMAINS = ("preference", "todo", "calendar", "goal", "content", "expense", "steps")

# Why a question is in the exam. P2a owns this list.
Probe = Literal[
    "recent_change",  # the fact changed value or disappeared since the previous exam
    "new",            # the fact did not exist at the previous exam and exists now
    "stable",         # the fact holds now with the same value it had at the previous exam (control)
    "never_existed",  # a plausible fact that never held for this persona (catches invention)
    "aggregate",      # a value derived from several facts, such as a total of expenses
]

AnswerFormat = Literal[
    "choice",  # one of Question.options, or UNKNOWN
    "value",   # a free string compared after normalization, or UNKNOWN
    "number",  # a number, or UNKNOWN
]

UNKNOWN = "unknown"

Outcome = Literal[
    "correct",
    "stale",     # an answer that was correct for an earlier state of the fact
    "missing",   # UNKNOWN, or no answer, while the fact holds
    "invented",  # an answer that no state of the fact ever supported
    "unparseable",  # not one of the options or UNKNOWN (choice), or not a number (number): a format failure, not a memory error
]


@dataclass(frozen=True)
class Question:
    question_id: str                  # stable across runs: same exam, same id, for every policy
    period: str
    persona: str
    session_id: int                   # asked right after this session: the truth is timeline.state_after(session_id)
    domain: str                       # one of DOMAINS
    probe: Probe
    fact: FactId | None               # None only for "aggregate"; may be absent from the timeline for "never_existed"
    field: str | None                 # key of the value dict being asked, e.g. "preference"; None asks whether the fact exists
    answer_format: AnswerFormat
    options: tuple[str, ...]          # for "choice"; () otherwise
    prompt: str                       # English text shown to the agent
    current: dict | None              # the fact's value after session_id; None if it does not hold
    history: tuple[dict | None, ...]  # earlier states up to session_id, oldest first, without repeats; None = did not hold


@dataclass(frozen=True)
class Grade:
    question_id: str
    outcome: Outcome
    expected: str  # canonical correct answer
    given: str     # the answer after normalization


def fact_states(timeline: Timeline, fact: FactId, session_id: int) -> tuple[tuple[dict | None, ...], dict | None]:
    """(history, current) of one fact after session_id. Every fact starts as not holding."""
    domain, key = fact
    versions = sorted(
        (version for version in timeline.versions if version.domain == domain and version.key == key and version.valid_from <= session_id),
        key=lambda version: version.valid_from,
    )
    states: list[dict | None] = [None]
    for version in versions:
        if version.value != states[-1]:
            states.append(version.value)
        if version.valid_until is not None and version.valid_until <= session_id:
            next_starts_then = any(other.valid_from == version.valid_until for other in versions)
            if not next_starts_then:
                states.append(None)
    return tuple(states[:-1]), states[-1]
