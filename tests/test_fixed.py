import ast
import re
from pathlib import Path

from answering.client import Completion
from policies.engine import run_policy
from policies.fixed import Every, Never


class FakeClient:
    """Never calls the API: a dream notes the sessions it read, an exam is answered "unknown"."""

    thinking = {"type": "adaptive"}
    effort = "medium"

    def __init__(self):
        self.dreams_read = []

    def complete(self, run, system, user, max_tokens, repeat=0):
        if "/dream/" in run:
            read = [int(number) for number in re.findall(r'<session number="(\d+)"', user)]
            self.dreams_read.append(read)
            return Completion(f'<edits><append section="To-do list">\n- Read up to session {read[-1]} (work)\n</append></edits>', 0, 0, 0.001, True, "", self.thinking, self.effort, "fake")
        return Completion("<answers></answers>", 0, 0, 0.0001, True, "", self.thinking, self.effort, "fake")


def test_every_k_chains_dreams_k_sessions_apart_and_never_leaves_the_notes_empty():
    client = FakeClient()
    run = run_policy(Every(5), "weekly", "software_engineer", client, through=14)
    assert client.dreams_read == [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]
    # The exam of s14 waits on sessions 11-14: the notes stop at the dream of s10.
    assert "- Read up to session 10 (work)" in run.steps[13].notes and "session 14" not in run.steps[13].notes
    never = run_policy(Never(), "weekly", "software_engineer", FakeClient(), through=14)
    assert never.dreams() == 0 and {step.notes for step in never.steps} == {""}


def test_fixed_policies_never_import_the_answer_key():
    imported = set()
    for node in ast.walk(ast.parse(Path("policies/fixed.py").read_text())):
        if isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0] if node.module != "policies.session_changes" else node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
    assert not imported & {"truth", "exam", "policies.session_changes"}
