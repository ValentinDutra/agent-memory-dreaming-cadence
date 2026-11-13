"""One dream: read the current notes and the transcripts since the last dream, return new notes. Owner: P4a.

The model reads the notes and every turn of the new sessions, and replies with edits only: lines to append to a
section, and blocks of lines to replace or delete, in the style of the memory tool's str_replace. Code applies them
and returns the complete notes in P3's format (answering/notes.py). See docs/p4a-entrada-y-salida.md.

The client must think: BudgetedClient's default, adaptive thinking at effort medium. Without thinking the dream writes
edits that do not match the notes and leaves facts out (P4a §3.3).
"""

import re
from dataclasses import dataclass
from datetime import date

from answering.client import BudgetedClient
from dreaming.transcripts import Session

SYSTEM = (
    "You maintain the notes a personal assistant keeps about its user. Between conversations you read the new "
    "conversations and bring the notes up to date. The assistant's next session reads only the notes, so they must "
    "hold everything that is true about the user now, and nothing that stopped being true."
)

SECTIONS = ("Likes and dislikes", "To-do list", "Calendar", "Goals", "Documents", "Food expenses", "Steps")
# Closed lists: written even when empty, so "(none)" reads as an empty list (P3, answering/notes.py).
CLOSED_LISTS = ("To-do list", "Calendar")
EMPTY_LIST = "- (none)"

FORMAT = """Notes format: Markdown, one "## " section per topic, one fact per line, named the way the user names it:
## Likes and dislikes
- <item> (<category> / <subcategory>): like|dislike
## To-do list
- <task> (<task type>)
## Calendar
- <event>: YYYY-MM-DD (<event type>)
## Goals
- Daily step goal: <n> steps
- Weekly budget for <expense type> expenses: $<n>
## Documents
### <Email|Meeting notes|Project proposal|Social media post>: <title>
- budget: $<n>
- <list name>:
  - <item>
## Food expenses
- YYYY-MM-DD <expense type>: $<amount>
## Steps
- YYYY-MM-DD: <n> steps"""

RULES = """What to keep, as the user states it about themselves:
- Likes and dislikes: what the user likes or dislikes (artists, genres, books, films, places...). If the user stops liking something without saying they now dislike it, delete its line. If they move from one item to another, delete the old one and add the new one.
- To-do list: tasks the user plans to do. Delete a task once the user has done it or drops it.
- Calendar: events with their date. Turn relative dates ("tomorrow", "next Tuesday") into YYYY-MM-DD from the date of the conversation. Change the date when an event moves; delete the event when it is cancelled.
- Goals: the user's daily step goal and weekly budgets per expense type. Keep only the current value.
- Documents: each email, meeting notes, project proposal or social media post the user works on with you, under its title (an email's title is its subject or purpose; a post's title is its main message). Keep its budget and every list it has (key points, recipients, attendees, agenda items, decisions, action items, objectives, stakeholders, deliverables, metrics, hashtags...), one item per line, worded as the user words it. Leave out long descriptions. Apply the user's later changes to a document: add or delete items, change the budget.
- Food expenses: every one, with its date (the conversation's date unless the user gives another), its type as the user names it (coffee, lunch, grocery...) and its amount.
- Steps: the step count the user logs, by date.
- Never write totals or sums.
How to read the conversations:
- They are in order; a later statement replaces an earlier one.
- The speaker labels are sometimes wrong: a line labeled User can be the assistant talking. Judge by what the line says.
- The assistant's questions give context to the user's answers: "Have you moved from X to Y?" answered "Yes, I'm really into Y now" means Y replaced X."""

EDIT_FORMAT = f"""Reply with only the changes to the notes, inside <edits> tags. Two kinds of change:
<append section="To-do list">
- Prepare the quarterly report (work tasks)
</append>
adds lines at the end of a section, one of: {", ".join(f'"{section}"' for section in SECTIONS)}. A new document is appended to "Documents" with its ### heading and its fields.
<replace>
<old>
- Mechanic visit: 2025-06-08 (personal appointments)
</old>
<new>
- Mechanic visit: 2025-06-10 (personal appointments)
</new>
</replace>
changes lines: <old> holds whole lines copied exactly from the notes, and <new> the lines that take their place. Leave <new> empty to delete the lines. <old> must appear only once in the notes: to change an item of one document, include enough of its neighbouring lines to make it unique.
Write nothing else inside <edits>. If nothing changes, reply <edits></edits>."""

# Thinking tokens count against max_tokens. The largest dream measured, 50 monthly sessions over 20k characters of notes,
# used 4.1k output tokens.
MAX_TOKENS = 32_000


@dataclass(frozen=True)
class DreamResult:
    notes: str
    input_tokens: int
    output_tokens: int
    cost: float
    from_cache: bool


@dataclass(frozen=True)
class Append:
    section: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class Replace:
    old: tuple[str, ...]
    new: tuple[str, ...]


def dream(notes: str, sessions: list[Session], client: BudgetedClient, run: str) -> DreamResult:
    result, _ = dream_with_failures(notes, sessions, client, run)
    return result


def dream_with_failures(notes: str, sessions: list[Session], client: BudgetedClient, run: str) -> tuple[DreamResult, list[Append | Replace]]:
    """The dream, and the edits that could not be applied (a <replace> whose <old> is missing or not unique)."""
    completion = client.complete(run, SYSTEM, dream_prompt(notes, sessions), max_tokens=MAX_TOKENS)
    new_notes, failures = apply_edits(notes, parse_edits(completion.text))
    result = DreamResult(new_notes, completion.input_tokens, completion.output_tokens, completion.cost, completion.from_cache)
    return result, failures


def dream_prompt(notes: str, sessions: list[Session], reply_format: str = EDIT_FORMAT) -> str:
    transcripts = "\n\n".join(render_session(session) for session in sessions)
    return (
        f"<notes>\n{notes}\n</notes>\n\n<conversations>\n{transcripts}\n</conversations>\n\n"
        f"{FORMAT}\n\n{RULES}\n\n{reply_format}"
    )


def render_session(session: Session) -> str:
    weekday = date.fromisoformat(session.date).strftime("%A")
    turns = "\n".join(f"{speaker_name(turn.speaker)}: {turn.message}" for turn in session.turns)
    return f'<session number="{session.session_id}" date="{session.date}" weekday="{weekday}">\n{turns}\n</session>'


def speaker_name(speaker: str) -> str:
    return "User" if speaker == "user_agent" else "Assistant"


def parse_edits(text: str) -> list[Append | Replace]:
    """The edits from the last <edits> tag to the end of the reply, in order.

    Not only those inside the block: the model sometimes closes </edits> and keeps writing edits after it.
    """
    start = text.rfind("<edits>")
    if start == -1:
        return []
    edits = []
    pattern = r'<append section="([^"]*)">(.*?)</append>|<replace>\s*<old>(.*?)</old>\s*<new>(.*?)</new>\s*</replace>'
    for match in re.finditer(pattern, text[start:], flags=re.DOTALL):
        section, appended, old, new = match.groups()
        if section is not None:
            edits.append(Append(section.strip(), content_lines(appended)))
        else:
            edits.append(Replace(content_lines(old), content_lines(new)))
    return edits


def content_lines(text: str) -> tuple[str, ...]:
    return tuple(line.rstrip() for line in text.splitlines() if line.strip())


def apply_edits(notes: str, edits: list[Append | Replace]) -> tuple[str, list[Append | Replace]]:
    """Apply the edits in order; return the notes in canonical form and the edits that could not be applied."""
    lines = notes.splitlines()
    failures = []
    for edit in edits:
        if isinstance(edit, Append):
            lines = appended(lines, edit)
            continue
        start = unique_match(lines, edit.old)
        if start is None:
            failures.append(edit)
        else:
            lines = lines[:start] + list(edit.new) + lines[start + len(edit.old):]
    return canonical("\n".join(lines)), failures


def unique_match(lines: list[str], old: tuple[str, ...]) -> int | None:
    """Where `old` starts in `lines` if it appears exactly once, comparing lines without surrounding whitespace."""
    if not old:
        return None
    stripped = [line.strip() for line in lines]
    wanted = [line.strip() for line in old]
    starts = [start for start in range(len(lines) - len(old) + 1) if stripped[start:start + len(old)] == wanted]
    return starts[0] if len(starts) == 1 else None


def appended(lines: list[str], edit: Append) -> list[str]:
    heading = f"## {edit.section}"
    if heading not in lines:
        return lines + ["", heading, *edit.lines]
    end = lines.index(heading) + 1
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    while lines[end - 1].strip() == "":
        end -= 1
    return lines[:end] + list(edit.lines) + lines[end:]


def canonical(notes: str) -> str:
    """Sections in P3's order, blank lines only before a document, "- (none)" exactly when a closed list is empty."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in notes.splitlines():
        if line.startswith("## "):
            current = sections.setdefault(line[3:].strip(), [])
        elif current is not None and line.strip():
            current.append(line.rstrip())
    for title in CLOSED_LISTS:
        sections.setdefault(title, [])
    blocks = []
    for title in sorted(sections, key=lambda title: SECTIONS.index(title) if title in SECTIONS else len(SECTIONS)):
        lines = [line for line in sections[title] if line.strip() != EMPTY_LIST]
        if not lines and title not in CLOSED_LISTS:
            continue
        body = "\n".join(("\n" + line) if line.startswith("### ") else line for line in lines or [EMPTY_LIST])
        blocks.append(f"## {title}\n{body}")
    return "\n\n".join(blocks)
