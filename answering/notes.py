"""How notes look: the text an agent reads at the start of a session. Owner: P3a.

Markdown, one section per domain, one line per fact, everything named the way the user names it in conversation:
a document by its title, an expense by its date and type. A dream (P4) writes this by reading transcripts.
Documents keep their title, budget and list items; their free-text fields (description, timeline, call to action...)
are left out.
"""

from collections import defaultdict

from exam.questions import DOCUMENT_TITLE_FIELD
from truth.timeline import FactId

DOCUMENT_HEADING = {
    "project_proposal": "Project proposal",
    "email_writeup": "Email",
    "meeting_notes": "Meeting notes",
    "social_media_post": "Social media post",
}


# Closed lists the exam asks "is X on it?" about: written even when empty, so "(none)" reads as an empty list,
# not as a list the notes do not track.
CLOSED_LISTS = ("To-do list", "Calendar")


def render_notes(facts: dict[FactId, dict]) -> str:
    """Notes holding `facts`, as returned by Timeline.state_after, without document prose. Empty facts give empty notes."""
    if not facts:
        return ""
    return render_markdown(without_prose(facts), write_empty_lists=True)


def without_prose(facts: dict[FactId, dict]) -> dict[FactId, dict]:
    """Drop the free-text scalar fields of documents. Titles name the document; budgets and list items can change."""
    def is_prose(domain: str, key: tuple[str, ...]) -> bool:
        if domain != "content" or len(key) != 2:
            return False
        return key[1] not in ("budget", DOCUMENT_TITLE_FIELD[key[0].rsplit("_", 1)[0]])
    return {fact: value for fact, value in facts.items() if not is_prose(*fact)}


def render_markdown(facts: dict[FactId, dict], write_empty_lists: bool = False) -> str:
    """Every fact in `facts`, prose included."""
    by_domain = defaultdict(dict)
    for (domain, key), value in facts.items():
        by_domain[domain][key] = value
    sections = [
        ("Likes and dislikes", preference_lines(by_domain["preference"])),
        ("To-do list", [f"- {description} ({label(value['task_type'])})" for (description,), value in sorted(by_domain["todo"].items())]),
        ("Calendar", [f"- {name}: {value['event_date']} ({label(value['event_type'])})" for (name,), value in sorted(by_domain["calendar"].items(), key=lambda item: (item[1]["event_date"], item[0]))]),
        ("Goals", goal_lines(by_domain["goal"])),
        ("Documents", document_lines(by_domain["content"])),
        ("Food expenses", [f"- {value['date']} {value['expense_type']}: ${value['amount']:.2f}" for value in sorted(by_domain["expense"].values(), key=lambda value: (value["date"], value["expense_type"], value["amount"]))]),
        ("Steps", [f"- {date}: {value['step_count']} steps" for (date,), value in sorted(by_domain["steps"].items())]),
    ]
    return "\n\n".join(
        f"## {title}\n" + "\n".join(lines or ["- (none)"])
        for title, lines in sections
        if lines or (write_empty_lists and title in CLOSED_LISTS)
    )


def label(identifier: str) -> str:
    return identifier.replace("_", " ")


def preference_lines(preferences: dict) -> list[str]:
    return [
        f"- {item} ({category} / {label(subcategory)}): {value['preference']}"
        for (category, subcategory, item), value in sorted(preferences.items())
    ]


def goal_lines(goals: dict) -> list[str]:
    lines = []
    for (subcategory,), value in sorted(goals.items()):
        if subcategory == "daily_steps":
            lines.append(f"- Daily step goal: {value['value']} steps")
        else:
            lines.append(f"- Weekly budget for {subcategory} expenses: ${value['value']}")
    return lines


def document_lines(content: dict) -> list[str]:
    """One block per document, headed by its title. List fields are bullet lists; the rest are one line each."""
    fields_by_document = defaultdict(dict)
    for key, value in sorted(content.items()):
        document_id, field = key[:2]
        if len(key) == 3:
            fields_by_document[document_id].setdefault(field, []).append(value["value"])
        else:
            fields_by_document[document_id][field] = value["value"]
    lines = []
    for document_id, fields in sorted(fields_by_document.items()):
        kind = document_id.rsplit("_", 1)[0]
        title_field = DOCUMENT_TITLE_FIELD[kind]
        lines.append(f"\n### {DOCUMENT_HEADING[kind]}: {fields[title_field]}")
        for field, value in fields.items():
            if field == title_field:
                continue
            if isinstance(value, list):
                lines.append(f"- {label(field)}:")
                lines += [f"  - {element}" for element in value]
            elif field == "budget":
                lines.append(f"- budget: ${value}")
            else:
                lines.append(f"- {label(field)}: {value}")
    return lines
