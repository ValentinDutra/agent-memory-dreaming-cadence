"""Fixed cadences: never dream, or dream every k sessions. Owner: P5a.

A policy sees only the notes and the sessions since the last dream (docs/p5-interfaz.md, anti-cheating rule):
this module must not import truth, exam or policies.session_changes. The CLI that measures them is policies.fixed_run.
"""

from answering.client import BudgetedClient
from dreaming.transcripts import Session
from policies.engine import Decision


class Never:
    name = "never"

    def decide(self, notes: str, pending: list[Session], client: BudgetedClient, run: str) -> Decision:
        return Decision(False)


class Every:
    """Dream once `sessions` sessions have gone by since the last dream, so dreams fall after sessions k, 2k, 3k..."""

    def __init__(self, sessions: int):
        self.sessions = sessions
        self.name = f"every-{sessions}"

    def decide(self, notes: str, pending: list[Session], client: BudgetedClient, run: str) -> Decision:
        return Decision(len(pending) >= self.sessions)


def policy_named(name: str) -> Never | Every:
    if name == "never":
        return Never()
    prefix, _, sessions = name.partition("-")
    if prefix != "every" or not sessions.isdigit() or int(sessions) < 1:
        raise ValueError(f"unknown fixed policy {name!r}: use never or every-<k>")
    return Every(int(sessions))
