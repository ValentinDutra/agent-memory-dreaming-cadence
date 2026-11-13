from answering.client import Completion
from answering.notes import render_notes
from dreaming.dream import Replace, apply_edits, dream
from truth.changes import persona_changes
from truth.timeline import build_timeline


class ReplyingClient:
    """Stands in for BudgetedClient: answers every dream with a fixed reply and never calls the API."""

    thinking = {"type": "adaptive"}
    effort = "medium"

    def __init__(self, reply: str):
        self.reply = reply

    def complete(self, run, system, user, max_tokens, repeat=0):
        return Completion(self.reply, 0, 0, 0.0, True, "", self.thinking, self.effort, "fake")


def notes_after(session_id: int) -> str:
    return render_notes(build_timeline(persona_changes("weekly", "software_engineer")).state_after(session_id))


def test_a_dream_applies_its_edits_to_real_notes():
    # weekly/software_engineer after s29: Bonobo is liked (deleted in s30), "Buy groceries" is a to-do, the calendar is empty.
    reply = """<edits>
<replace>
<old>
- Bonobo (music / artists): like
</old>
<new>
</new>
</replace>
<replace>
<old>
- Buy groceries (personal tasks)
</old>
<new>
- Buy groceries for the week (personal tasks)
</new>
</replace>
<append section="Calendar">
- Mechanic visit: 2025-06-15 (personal appointments)
</append>
</edits>"""
    notes = dream(notes_after(29), [], ReplyingClient(reply), run="test").notes
    assert "Bonobo" not in notes
    assert "- Buy groceries for the week (personal tasks)\n- Refactor legacy code (work tasks)" in notes
    assert "## Calendar\n- Mechanic visit: 2025-06-15 (personal appointments)\n\n## Goals" in notes


def test_an_ambiguous_replace_is_reported_and_changes_nothing():
    # After s35 two social media posts have a "- hashtags:" line: the edit cannot say which one it means.
    notes = notes_after(35)
    edit = Replace(old=("- hashtags:",), new=())
    assert apply_edits(notes, [edit]) == (notes, [edit])


def test_edits_written_after_the_closing_tag_are_applied():
    # The real reply of the monthly/academic_researcher dream over s15-21: it closed </edits> after its first edit.
    reply = """<edits>
<replace>
<old>
- (none)
</old>
<new>
- Mom's birthday: 2025-07-12 (personal events)
</new>
</replace>
</edits>

<append section="Goals">
- Weekly budget for lunch expenses: $115
</append>

<append section="Steps">
- 2025-06-01: 8381 steps
</append>"""
    notes = dream("## To-do list\n- (none)\n\n## Calendar\n- (none)", [], ReplyingClient(reply), run="test").notes
    assert "- Weekly budget for lunch expenses: $115" in notes
    assert "- 2025-06-01: 8381 steps" in notes
