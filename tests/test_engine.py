import re

from answering.client import Completion
from policies.engine import Decision, run_policy, score


class RecordingClient:
    """Stands in for BudgetedClient and never calls the API. A dream notes the sessions it read; an exam is answered "unknown"."""

    thinking = {"type": "adaptive"}
    effort = "medium"

    def __init__(self):
        self.dream_prompts = []
        self.exam_prompts = []

    def complete(self, run, system, user, max_tokens, repeat=0):
        if "/dream/" in run:
            self.dream_prompts.append(user)
            read = re.findall(r'<session number="(\d+)"', user)
            reply = f'<edits><append section="To-do list">\n- Read sessions {read[0]} to {read[-1]} (work)\n</append></edits>'
            return Completion(reply, 0, 0, 0.001, True, "", self.thinking, self.effort, "fake")
        self.exam_prompts.append(user)
        return Completion("<answers></answers>", 0, 0, 0.0001, True, "", self.thinking, self.effort, "fake")


class DreamAt:
    name = "dream-at"

    def __init__(self, *session_ids):
        self.session_ids = session_ids

    def decide(self, notes, pending, client, run):
        return Decision(pending[-1].session_id in self.session_ids)


def test_each_dream_reads_the_sessions_since_the_last_and_the_exam_sees_its_notes():
    client = RecordingClient()
    run = run_policy(DreamAt(3, 7, 12), "weekly", "software_engineer", client, through=14)
    assert [re.findall(r'<session number="(\d+)"', prompt) for prompt in client.dream_prompts] == [
        ["1", "2", "3"], ["4", "5", "6", "7"], ["8", "9", "10", "11", "12"],
    ]
    # The exam of s7 comes after s7's dream; the exam of s14 sees the dream of s12, not sessions 13-14.
    assert [exam.session_id for exam in run.exams] == [7, 14]
    assert "- Read sessions 4 to 7 (work)" in client.exam_prompts[0] and "8 to 12" not in client.exam_prompts[0]
    assert "- Read sessions 8 to 12 (work)" in client.exam_prompts[1]
    assert [step.sessions_read for step in run.steps if step.dreamt] == [3, 4, 5]
    assert round(run.dream_cost(), 4) == 0.003
    assert score(run).correct < score(run).asked
