import json

from answering.client import Completion
from dreaming.dream import dream
from dreaming.transcripts import transcript
from truth.changes import MEMORA_DATA

ANSWER_KEY_FIELDS = ("session_type", "operation", "operation_details", "share_memory")


class RecordingClient:
    """Stands in for BudgetedClient: keeps every prompt and never calls the API."""

    thinking = {"type": "adaptive"}
    effort = "medium"

    def __init__(self):
        self.prompts = []

    def complete(self, run, system, user, max_tokens, repeat=0):
        self.prompts.append(system + user)
        return Completion("<notes>\n</notes>", 0, 0, 0.0, True, "", self.thinking, self.effort, "fake")


def memora_session(session_id: int) -> dict:
    path = MEMORA_DATA / "weekly" / "software_engineer" / "conversations" / f"session_{session_id:04d}.json"
    return json.loads(path.read_text())


def with_answer_key_replaced(session: dict) -> dict:
    tampered = {**session, "session_type": "x", "operation": "x", "operation_details": {"item": "x"}}
    tampered["conversation"] = [{**turn, "share_memory": not turn["share_memory"]} for turn in session["conversation"]]
    return tampered


def test_the_dream_never_sees_the_answer_key():
    # s30 deletes Bonobo; its turn 14 shares a fact the answer key does not record (P1 defect 2).
    real = memora_session(30)
    client = RecordingClient()
    dream("", [transcript(real)], client, run="test")
    dream("", [transcript(with_answer_key_replaced(real))], client, run="test")
    assert client.prompts[0] == client.prompts[1]
    assert not any(field in client.prompts[0] for field in ANSWER_KEY_FIELDS)
    assert "Bonobo" in client.prompts[0]
