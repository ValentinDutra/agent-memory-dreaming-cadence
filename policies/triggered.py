"""Dream only after a session that brings something the notes do not reflect. Owner: P5b.

A detector reads the session that just ended (and, for one of them, the notes) and says "change", "new" or "none".
The policy dreams on "change", or on "new" too, and after at most max_wait sessions without a dream.
See docs/p5b-sueno-disparado.md.

Anti-cheat rule (docs/p5-interfaz.md): a detector sees only the notes and Session. This module never imports
truth, exam or policies.session_changes.
"""

import re
from dataclasses import dataclass
from typing import Literal

from answering.client import BudgetedClient
from dreaming.dream import render_session
from dreaming.transcripts import Session
from policies.engine import Decision

Verdict = Literal["none", "new", "change"]
VERDICTS = ("none", "new", "change")
Target = Literal["any", "change"]


@dataclass(frozen=True)
class Detection:
    verdict: Verdict
    cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


# Phrases that announce a change, a cancellation or a completion, and cues that the user tells a fact of a kind the
# notes keep. Matched on the user's turns only: the assistant says "update" and "remove" in almost every session.
CHANGE_PHRASES = re.compile(
    r"used to|anymore|no longer|not into|changed my mind|instead|"
    r"finished|completed|already (?:did|done)|done with|took care of|"
    r"cancel|call(?:ed)? off|reschedul|postpon|push(?:ed)? (?:back|it)|moved? (?:it|the)|"
    r"\bupdate|revis|remove|delete|drop|replace|adjust|change (?:the|it|my)|"
    r"new goal|goal (?:to|of)|budget (?:to|of|for)",
    re.IGNORECASE,
)
FACT_CUES = re.compile(
    r"\$\s?\d|\bsteps?\b|\b(?:i|i'm|i've|i'd)\b[^.?!]{0,40}\b(?:like|love|enjoy|adore|fan of|favou?rite|into|hate|dislike|can't stand)\b|"
    r"\bremind|need to|have to|plan(?:ning)? to|schedul|appointment|meeting|deadline|"
    r"\badd\b|email|proposal|post|agenda|attendees|hashtag|"
    r"spent|bought|paid|coffee|lunch|dinner|grocer",
    re.IGNORECASE,
)


class PhraseDetector:
    name = "phrases"

    def detect(self, notes: str, session: Session, run: str) -> Detection:
        user_lines = [turn.message for turn in session.turns if turn.speaker == "user_agent"]
        if any(CHANGE_PHRASES.search(line) for line in user_lines):
            return Detection("change")
        if any(FACT_CUES.search(line) for line in user_lines):
            return Detection("new")
        return Detection("none")


SYSTEM = (
    "A personal assistant keeps notes about its user and updates them between conversations. You read the "
    "conversation that just ended and decide, cheaply, whether the notes need an update now."
)

KEPT = (
    "The notes keep what the user tells about themselves: likes and dislikes, tasks to do, calendar events, the daily "
    "step goal and weekly budgets, the documents they write with the assistant (emails, meeting notes, project "
    "proposals, social media posts) with their lists and budgets, food expenses, and daily step counts. Small talk, "
    "opinions on general topics and questions to the assistant are not kept. The speaker labels are sometimes wrong: "
    "judge by what a line says. Such a fact is often a single passing remark in the middle of small talk (\"I've been "
    "really into X lately\", \"I just spent $7 on a coffee\"): it still counts."
)

QUESTION_WITHOUT_NOTES = """First quote, in a few words each, the user's lines that tell such a fact, or write "nothing". Then end with "Verdict: " and one word:
change: the user changes, cancels, finishes, drops or replaces something of a kind the notes keep (a task done, an event moved or cancelled, a like they lost or swapped, a new step goal or budget, an item edited or removed from a document);
new: the user only tells something new of a kind the notes keep;
none: the user tells nothing of a kind the notes keep."""

QUESTION_WITH_NOTES = """Compare the conversation with the notes. First quote, in a few words each, the user's lines that tell such a fact, or write "nothing". Then end with "Verdict: " and one word:
change: the conversation contradicts, updates or removes something the notes say (a task done, an event moved or cancelled, a like lost or swapped, a different goal or budget, an item edited or removed from a document);
new: the conversation only adds things the notes do not have yet;
none: everything the user tells of a kind the notes keep is already in the notes, or the user tells nothing of that kind."""

# The quotes are short; a reply cut off before its verdict counts as "change".
MAX_TOKENS = 200


class ModelDetector:
    """One short call without thinking. with_notes=False reads only the session, so its prompt is the same for every policy."""

    def __init__(self, client: BudgetedClient, with_notes: bool):
        self.client = client
        self.with_notes = with_notes
        self.name = "model-notes" if with_notes else "model"

    def detect(self, notes: str, session: Session, run: str) -> Detection:
        completion = self.client.complete(run, SYSTEM, self.prompt(notes, session), max_tokens=MAX_TOKENS)
        return Detection(parse_verdict(completion.text), completion.cost, completion.input_tokens, completion.output_tokens)

    def prompt(self, notes: str, session: Session) -> str:
        conversation = f"<conversation>\n{render_session(session)}\n</conversation>"
        if self.with_notes:
            return f"<notes>\n{notes}\n</notes>\n\n{conversation}\n\n{KEPT}\n\n{QUESTION_WITH_NOTES}"
        return f"{conversation}\n\n{KEPT}\n\n{QUESTION_WITHOUT_NOTES}"


def parse_verdict(text: str) -> Verdict:
    """The word after the last "Verdict:". A reply without one counts as "change": dreaming is the safe side."""
    found = re.findall(r"verdict:\W*(change|new|none)\b", text.lower())
    return found[-1] if found else "change"


class Screened:
    """The phrases first: a session they find nothing in is "none" without a call; any other gets the model's verdict."""

    def __init__(self, model: ModelDetector):
        self.phrases = PhraseDetector()
        self.model = model
        self.name = f"screened-{model.name}"

    def detect(self, notes: str, session: Session, run: str) -> Detection:
        if self.phrases.detect(notes, session, run).verdict == "none":
            return Detection("none")
        # Cached under the model's name: the same call the model alone makes.
        return self.model.detect(notes, session, run.replace(f"/{self.name}/", f"/{self.model.name}/"))


class Triggered:
    """Dream after a session the detector flags (target "change": only "change"; "any": "change" or "new"),
    or once max_wait sessions have waited for a dream."""

    def __init__(self, detector, target: Target, max_wait: int | None = None):
        self.detector = detector
        self.target = target
        self.max_wait = max_wait
        self.name = f"triggered-{detector.name}-{target}" + (f"-wait{max_wait}" if max_wait else "")

    def decide(self, notes: str, pending: list[Session], client: BudgetedClient, run: str) -> Decision:
        # The engine names the run after the policy; a detector's verdicts are cached under the detector's name so
        # that policies sharing a detector, and the detector's own measurement, share them.
        detection = self.detector.detect(notes, pending[-1], run.replace(f"/{self.name}/", f"/{self.detector.name}/"))
        flagged = detection.verdict == "change" or (self.target == "any" and detection.verdict == "new")
        waited_enough = self.max_wait is not None and len(pending) >= self.max_wait
        return Decision(flagged or waited_enough, detection.cost, detection.input_tokens, detection.output_tokens)
