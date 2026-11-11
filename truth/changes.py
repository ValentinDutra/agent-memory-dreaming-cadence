import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from typing import Literal

# A git worktree has no vendor/ of its own; MEMORA_ROOT points it at the main checkout's copy.
MEMORA_ROOT = Path(os.environ.get("MEMORA_ROOT", Path(__file__).resolve().parent.parent / "vendor" / "Memora"))
MEMORA_DATA = MEMORA_ROOT / "data"
PERIODS = ("weekly", "monthly", "quarterly")


@dataclass(frozen=True)
class Change:
    """One edit to the set of facts that are true about the user."""

    session_id: int
    date: str
    action: Literal["add", "update", "remove"]
    domain: str
    key: tuple[str, ...]
    value: dict | None
    previous: dict | None = None
    evidence_turns: tuple[int, ...] = ()


def personas(period: str) -> list[str]:
    return sorted(path.name for path in (MEMORA_DATA / period).iterdir() if path.is_dir())


def load_sessions(period: str, persona: str) -> list[dict]:
    session_paths = sorted((MEMORA_DATA / period / persona / "conversations").glob("session_*.json"))
    return [json.loads(path.read_text()) for path in session_paths]


@cache
def _preference_lists(persona: str) -> dict[str, dict[str, list[str]]]:
    """The item lists the Memora simulator drew this persona's preferences from: category -> subcategory -> items."""
    metadata = MEMORA_ROOT / "data_generation" / "meta_data"
    traits = json.loads((metadata / "persona_traits.json").read_text())["persona_profiles"]
    archetypes = json.loads((metadata / "preference_metadata.json").read_text())["preference_personas"]
    archetype_by_category = traits[persona]["category_traits"]["preference_memory"]
    return {
        category: archetypes[category][archetype]["preferences"]
        for category, archetype in archetype_by_category.items()
    }


def preference_category(persona: str, subcategory: str, item: str) -> str:
    """Memora's preference sessions omit the category; "genres" exists in both movies and music."""
    candidates = [
        category
        for category, subcategories in _preference_lists(persona).items()
        if subcategory in subcategories
    ]
    if len(candidates) > 1:
        candidates = [category for category in candidates if item in _preference_lists(persona)[category][subcategory]]
    if len(candidates) != 1:
        raise ValueError(f"cannot place {subcategory}={item!r} for {persona}: {candidates}")
    return candidates[0]


def calendar_event_date(event: dict) -> str:
    """Memora anchors the relative "+N days" on created_at, even after an update moves the event."""
    days = int(event["date"].split()[0].removeprefix("+"))
    return (date.fromisoformat(event["created_at"]) + timedelta(days=days)).isoformat()


def extract_changes(session: dict) -> list[Change]:
    details = session.get("operation_details") or {}
    operation = session["operation"]
    evidence_turns = tuple(turn["turn"] for turn in session["conversation"] if turn.get("share_memory"))

    def change(action, domain, key, value, previous=None):
        return Change(session["session_id"], session["date"], action, domain, key, value, previous, evidence_turns)

    if session["session_type"] == "preference":
        subcategory = details["subcategory"]
        category = preference_category(session["persona"], subcategory, details["item"])
        liked = {"preference": details["preference"]}
        key = (category, subcategory, details["item"])
        if operation == "add":
            return [change("add", "preference", key, liked)]
        if operation == "delete":
            return [change("remove", "preference", key, None, liked)]
        old_liked = {"preference": details["old_preference"]}
        if details["update_type"] == "value_update":
            return [
                change("remove", "preference", (category, subcategory, details["old_item"]), None, old_liked),
                change("add", "preference", key, liked),
            ]
        return [change("update", "preference", key, liked, old_liked)]

    if session["session_type"] == "goal":
        goal = {"value": details["item"]}
        if details["actual_operation"] == "update":
            return [change("update", "goal", (details["subcategory"],), goal, {"value": details["old_value"]})]
        return [change("add", "goal", (details["subcategory"],), goal)]

    if session["session_type"] != "activity":
        return []

    item = details["item"]
    if isinstance(item, str):
        return _content_changes(item, details, change)

    category = details["category"]
    if category == "todo_list":
        todo = {"task_type": item["task_type"]}
        if operation == "add":
            return [change("add", "todo", (item["description"],), todo)]
        return [change("remove", "todo", (item["description"],), None, todo)]

    if category == "calendar_event":
        event = {"event_type": item["event_type"], "event_date": calendar_event_date(item)}
        key = (item["event_name"],)
        if operation == "add":
            return [change("add", "calendar", key, event)]
        if operation == "update":
            return [change("update", "calendar", key, event)]
        return [change("remove", "calendar", key, None, event)]

    if category == "food_expenses":
        expense = {"date": item["created_at"], "expense_type": item["expense_type"], "amount": item["amount"]}
        return [change("add", "expense", (str(session["session_id"]),), expense)]

    if category == "step_tracker":
        steps = {"activity_type": item["activity_type"], "step_count": item["step_count"]}
        return [change("add", "steps", (item["created_at"],), steps)]

    raise ValueError(f"unknown activity category {category!r} in session {session['session_id']}")


def _content_changes(document_id: str, details: dict, change) -> list[Change]:
    """A document is a set of atomic facts: one per scalar field, one per element of a list field."""
    if "memory_updates" not in details and "memory_deletes" not in details:
        changes = []
        for field, content in details["content_data"].items():
            if isinstance(content, list):
                changes += [change("add", "content", (document_id, field, element), {"value": element}) for element in content]
            else:
                changes.append(change("add", "content", (document_id, field), {"value": content}))
        return changes

    changes = []
    for edit in details.get("memory_updates", []) + details.get("memory_deletes", []):
        if "error" in edit:
            # The simulator records a failed edit this way and leaves the document unchanged.
            continue
        field = edit["field"]
        if edit["action"] == "added":
            element = edit["added_item"]
            changes.append(change("add", "content", (document_id, field, element), {"value": element}))
        elif edit["action"] == "removed_from_memory":
            element = edit["removed_item"]
            changes.append(change("remove", "content", (document_id, field, element), None, {"value": element}))
        elif edit["action"] == "budget_revised":
            changes.append(change("update", "content", (document_id, field), {"value": edit["updated_to"]}, {"value": edit["updated_from"]}))
        elif edit["action"] == "budget_reverted":
            changes.append(change("update", "content", (document_id, field), {"value": edit["reverted_to"]}, {"value": edit["reverted_from"]}))
        else:
            raise ValueError(f"unknown content edit {edit['action']!r} on {document_id}")
    return changes


def persona_changes(period: str, persona: str) -> list[Change]:
    return [change for session in load_sessions(period, persona) for change in extract_changes(session)]
