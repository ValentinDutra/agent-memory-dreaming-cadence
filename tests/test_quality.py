import re

from answering.client import Completion
from answering.notes import render_notes
from dreaming.dream import DreamResult
from dreaming.quality import compare_notes
from dreaming.quality_run import chain, measure, window
from dreaming.transcripts import load_transcripts
from exam.questions import exam_sessions
from truth.changes import persona_changes
from truth.timeline import build_timeline

TIMELINE = build_timeline(persona_changes("weekly", "software_engineer"))

# From the stub's real dream over weekly/software_engineer sessions 1-35 (results/raw/p4b/stub/.../single), cut down.
STUB_NOTES_AFTER_35 = """## Likes and dislikes
- Bonobo music (Music / Electronic): dislike
- Ann Leckie's books (Books / Science fiction): like
- Trail running when traveling (Activities / Running): like

## To-do list
- Refactor legacy code (Coding)
- Finalize new project proposal (Work)

## Documents
### Social media post: Real-time video stream latency optimization
- Platform: LinkedIn
- Hashtags:
  - #EdgeComputing
  - #VideoEngineering
  - #SoftwareEngineering

### Email: Autonomous navigation latency reduction proposal
- Key points:
  - Current navigation pipeline average latency is 340ms, 140ms over target threshold

## Food expenses
- 2025-06-01 groceries: $28.50
- 2025-06-01 coffee: $3.41
- 2025-06-01 coffee: $7.35"""


def test_perfect_notes_read_all_correct_with_nothing_extra():
    for session_id in exam_sessions("weekly", "software_engineer"):
        comparison = compare_notes(render_notes(TIMELINE.state_after(session_id)), TIMELINE, session_id)
        assert comparison.fact_total("correct") == comparison.fact_total() > 0, session_id
        assert comparison.line_total() == comparison.fuzzy_matches == 0, session_id


def test_dream_labels_match_the_truth_and_a_dislike_after_a_removed_like_is_invented():
    transcript_text = " ".join(turn.message for session in load_transcripts("weekly", "software_engineer")[:35] for turn in session.turns)
    comparison = compare_notes(STUB_NOTES_AFTER_35, TIMELINE, 35, transcript_text)
    outcomes = {(outcome, domain) for outcome, domain, _ in comparison.examples}
    # Ann Leckie, trail running, both coffees, groceries for grocery, the post by its hashtags, the email's paraphrased key point.
    assert comparison.facts["preference", "correct"] == 2 and comparison.facts["expense", "correct"] == 3
    assert comparison.facts["content", "correct"] == 4 and comparison.paraphrased["content"] == 1
    assert comparison.lines["preference", "invented"] == comparison.lenient == 1  # Bonobo was removed in s30
    assert ("line unmatched_supported", "todo") in outcomes  # s5: "I'm hoping to finalize a new project proposal"
    assert comparison.lines["content", "prose"] == 1


def test_notes_that_missed_a_change_are_stale():
    bonobo = compare_notes(render_notes(TIMELINE.state_after(29)), TIMELINE, 35)  # still liked; removed in s30
    deep_house = compare_notes(render_notes(TIMELINE.state_after(131)), TIMELINE, 133)  # disliked in s129, liked in s132
    assert ("line stale", "preference", "- Bonobo (music / artists): like") in bonobo.examples
    assert deep_house.facts["preference", "stale"] == 1


class EchoDream:
    """Returns the notes it got plus one line per session read, and remembers what it was given."""

    def __init__(self):
        self.calls = []

    def __call__(self, notes, sessions, client, run):
        self.calls.append((notes, [session.session_id for session in sessions], run))
        added = "".join(f"\n- seen {session.session_id}" for session in sessions)
        return DreamResult(notes + added, 0, 0, 0.001, True)


class UnknownToEverything:
    thinking = {"type": "disabled"}

    def complete(self, run, system, user, max_tokens, repeat=0):
        question_count = len(re.findall(r"^\d+\. ", user, flags=re.MULTILINE))
        text = "<answers>\n" + "\n".join(f"{number}: unknown" for number in range(1, question_count + 1)) + "\n</answers>"
        return Completion(text, len(user), 0, 0.0, True, "default", self.thinking, "low", "fake")


def test_a_chain_starts_empty_and_reads_the_sessions_since_the_last_dream_a_window_starts_from_perfect_notes():
    dream = EchoDream()
    points = measure(dream, "weekly", "software_engineer", [chain(7, 14), window(5, 35)], UnknownToEverything(), "test/quality")

    first, second, third = dream.calls
    assert first[0] == "" and first[1] == list(range(1, 8))
    assert second[0] == "\n- seen 1\n- seen 2\n- seen 3\n- seen 4\n- seen 5\n- seen 6\n- seen 7" and second[1] == list(range(8, 15))
    assert third[0] == render_notes(TIMELINE.state_after(30)) and third[1] == list(range(31, 36))
    assert [(point.label, point.session_id, point.dreams) for point in points] == [("chain-c7", 7, 1), ("chain-c7", 14, 2), ("window-k5-s35", 35, 1)]
    assert points[1].dream_cost == 0.002
