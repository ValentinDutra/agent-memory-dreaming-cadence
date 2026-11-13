"""What a dream may read: the conversation text, its speakers and the session's number and date. Owner: P4.

Memora's session files also carry the simulator's answer key (session_type, operation, operation_details, and
share_memory on every turn). Sessions are built field by field from an allow-list, so none of it can reach a dream.
"""

import json
from dataclasses import dataclass

from truth.changes import MEMORA_DATA


@dataclass(frozen=True)
class Turn:
    speaker: str  # "user_agent" or "ai_agent", as Memora labels them
    message: str


@dataclass(frozen=True)
class Session:
    session_id: int
    date: str
    turns: tuple[Turn, ...]


def load_transcripts(period: str, persona: str) -> list[Session]:
    """Every session of the persona, ordered by session_id."""
    paths = (MEMORA_DATA / period / persona / "conversations").glob("session_*.json")
    sessions = [transcript(json.loads(path.read_text())) for path in paths]
    return sorted(sessions, key=lambda session: session.session_id)


def transcript(memora_session: dict) -> Session:
    return Session(
        session_id=memora_session["session_id"],
        date=memora_session["date"],
        turns=tuple(Turn(turn["speaker"], turn["message"]) for turn in memora_session["conversation"]),
    )


def sessions_between(sessions: list[Session], after: int, through: int) -> list[Session]:
    """The sessions a dream run after session `through` reads when the previous dream ran after session `after`."""
    return [session for session in sessions if after < session.session_id <= through]
