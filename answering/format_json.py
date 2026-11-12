"""Notes as one JSON document, the same facts and names as the Markdown notes. A variant of the format comparison."""

import json
from collections import defaultdict

from exam.questions import DOCUMENT_TITLE_FIELD
from answering.notes import DOCUMENT_HEADING, label
from truth.timeline import FactId


def render_notes(facts: dict[FactId, dict]) -> str:
    if not facts:
        return ""
    notes = defaultdict(dict)
    documents = defaultdict(dict)
    for (domain, key), value in sorted(facts.items()):
        if domain == "preference":
            category, subcategory, item = key
            notes["likes_and_dislikes"].setdefault(category, {}).setdefault(label(subcategory), {})[item] = value["preference"]
        elif domain == "todo":
            notes["todo_list"][key[0]] = label(value["task_type"])
        elif domain == "calendar":
            notes["calendar"][key[0]] = {"date": value["event_date"], "type": label(value["event_type"])}
        elif domain == "goal":
            name = "daily step goal" if key[0] == "daily_steps" else f"weekly budget for {key[0]} expenses"
            notes["goals"][name] = value["value"]
        elif domain == "content":
            document_id, field = key[:2]
            if len(key) == 3:
                documents[document_id].setdefault(label(field), []).append(value["value"])
            else:
                documents[document_id][label(field)] = value["value"]
        elif domain == "expense":
            notes["food_expenses"].setdefault(value["date"], []).append({"type": value["expense_type"], "amount": value["amount"]})
        elif domain == "steps":
            notes["steps"][key[0]] = value["step_count"]
    if "food_expenses" in notes:
        notes["food_expenses"] = dict(sorted(notes["food_expenses"].items()))
    for document_id, fields in sorted(documents.items()):
        kind = document_id.rsplit("_", 1)[0]
        title = fields.pop(label(DOCUMENT_TITLE_FIELD[kind]))
        notes.setdefault("documents", []).append({"kind": DOCUMENT_HEADING[kind], "title": title, **fields})
    return json.dumps(notes, ensure_ascii=False)
