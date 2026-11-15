"""The dream P8b tries: P4a's dream (dreaming.dream) with rules that name what it left out in P7. Owner: P8a.

Only RULES changes; the notes format, the edit format, the parsing and the client are P4a's. The three changes come from
P7's omissions (docs/p8a-omisiones.md §3):
- to-do list: a task said in passing ("I really need to...", "I'm trying to...") is a task;
- likes and dislikes: one said without those words ("I've been enjoying X lately", "I don't care about X") counts;
- documents: every list, whatever its name, including items that are whole sentences.
"""

from answering.client import BudgetedClient
from dreaming.dream import EDIT_FORMAT, FORMAT, MAX_TOKENS, SYSTEM, DreamResult, apply_edits, parse_edits, render_session
from dreaming.transcripts import Session

RULES = """What to keep, as the user states it about themselves:
- Likes and dislikes: what the user likes or dislikes (artists, genres, books, films, places...). One said in other words counts: "I've been enjoying X lately" or "I really liked X" is a like; "I don't care about X" is a dislike. If the user stops liking something without saying they now dislike it, delete its line. If they move from one item to another, delete the old one and add the new one.
- To-do list: tasks the user plans to do, also when said in passing while talking about something else and the conversation moves on at once ("I really need to renew my passport soon", "I'm trying to learn to cook"). Having to leave the conversation, or asking you to change a document, is not a task. Delete a task once the user has done it or drops it.
- Calendar: events with their date. Turn relative dates ("tomorrow", "next Tuesday") into YYYY-MM-DD from the date of the conversation. Change the date when an event moves; delete the event when it is cancelled.
- Goals: the user's daily step goal and weekly budgets per expense type. Keep only the current value.
- Documents: each email, meeting notes, project proposal or social media post the user works on with you, under its title (an email's title is its subject or purpose; a post's title is its main message). Keep its budget and every list it has, whatever the list is called (key points, recipients, attendees, agenda items, decisions, action items, objectives, stakeholders, deliverables, metrics, hashtags, risks, competitive analysis, ROI projections, inspiration references...), one item per line, worded as the user words it, even when an item is a whole sentence. Leave out only what the document is about, its description. Apply the user's later changes to a document: add or delete items, change the budget.
- Food expenses: every one, with its date (the conversation's date unless the user gives another), its type as the user names it (coffee, lunch, grocery...) and its amount.
- Steps: the step count the user logs, by date.
- Never write totals or sums.
How to read the conversations:
- They are in order; a later statement replaces an earlier one.
- The speaker labels are sometimes wrong: a line labeled User can be the assistant talking. Judge by what the line says.
- The assistant's questions give context to the user's answers: "Have you moved from X to Y?" answered "Yes, I'm really into Y now" means Y replaced X."""


def dream(notes: str, sessions: list[Session], client: BudgetedClient, run: str) -> DreamResult:
    completion = client.complete(run, SYSTEM, dream_prompt(notes, sessions), max_tokens=MAX_TOKENS)
    new_notes, _ = apply_edits(notes, parse_edits(completion.text))
    return DreamResult(new_notes, completion.input_tokens, completion.output_tokens, completion.cost, completion.from_cache)


def dream_prompt(notes: str, sessions: list[Session]) -> str:
    transcripts = "\n\n".join(render_session(session) for session in sessions)
    return f"<notes>\n{notes}\n</notes>\n\n<conversations>\n{transcripts}\n</conversations>\n\n{FORMAT}\n\n{RULES}\n\n{EDIT_FORMAT}"
