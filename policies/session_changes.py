"""What each session did to the truth: nothing, only new facts, or a change or removal of a fact that held. Owner: P5.

The label a triggered dream's detector is measured against (P5b). It reads the truth of P1, so no policy may import it.

Run: uv run python -m policies.session_changes weekly monthly
"""

import sys
from collections import Counter
from typing import Literal

from truth.changes import load_sessions, persona_changes, personas
from truth.timeline import Timeline, build_timeline

SessionChange = Literal["none", "add", "change"]
SESSION_CHANGES = ("none", "add", "change")


def session_change(timeline: Timeline, session_id: int) -> SessionChange:
    """"change" when a fact that held before the session changed value or stopped holding; "add" when facts only started holding."""
    changed = timeline.changed_between(session_id - 1, session_id)
    if not changed:
        return "none"
    return "add" if all(before is None for before, _ in changed.values()) else "change"


def report(period: str) -> None:
    counts = Counter()
    for persona in personas(period):
        timeline = build_timeline(persona_changes(period, persona))
        counts.update(session_change(timeline, session["session_id"]) for session in load_sessions(period, persona))
    total = sum(counts.values())
    print(f"{period}: {total} sessions | " + " | ".join(f"{label} {counts[label]} ({counts[label] / total:.0%})" for label in SESSION_CHANGES))


if __name__ == "__main__":
    for period in sys.argv[1:]:
        report(period)
