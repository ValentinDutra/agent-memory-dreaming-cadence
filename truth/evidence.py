"""Check extracted changes against the evidence attached to Memora's own evaluation questions.

Memora computes `memory_evidence` and `forgetting_evidence` from its simulator's memory state after the
last session, which is not released. Rebuilding the same evidence from our changes is the best external
check of the extraction. Run: uv run python -m truth.evidence weekly monthly
"""

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date

from truth.changes import MEMORA_DATA, Change, extract_changes, load_sessions, personas


@dataclass
class Replay:
    """The final state after applying every change, plus what it took to get there."""

    state: dict[tuple, dict]
    last_session: dict[tuple, int]
    values_held: dict[tuple, list[dict]]
    sessions_touching: dict[tuple, set[int]]
    precondition_failures: list[Change]


def replay(changes: list[Change]) -> Replay:
    """A minimal fold for validation only; the real timeline is P1b's truth/timeline.py."""
    result = Replay({}, {}, {}, {}, [])
    for change in changes:
        fact = (change.domain, change.key)
        exists = fact in result.state
        previous_matches = change.previous is None or result.state.get(fact) == change.previous
        if (change.action == "add" and exists) or (change.action != "add" and not (exists and previous_matches)):
            result.precondition_failures.append(change)
        if change.action == "remove":
            result.state.pop(fact, None)
        else:
            result.state[fact] = change.value
            result.last_session[fact] = change.session_id
            result.values_held.setdefault(fact, []).append(change.value)
        result.sessions_touching.setdefault(fact, set()).add(change.session_id)
    return result


@dataclass
class QuestionCheck:
    question_id: str
    family: str
    memory_matches: bool
    forgetting_matches: bool | None
    note: str = ""

    @property
    def matches(self) -> bool:
        return self.memory_matches and self.forgetting_matches is not False


def facts(replayed: Replay, domain: str) -> dict[tuple, dict]:
    return {key: value for (fact_domain, key), value in replayed.state.items() if fact_domain == domain}


def memora_expense_session(replayed: Replay) -> dict[tuple, int]:
    """Memora finds an expense's session by (date, type, amount), so identical expenses share the first session."""
    first_session = {}
    for key, value in sorted(facts(replayed, "expense").items(), key=lambda pair: int(pair[0][0])):
        first_session.setdefault((value["date"], value["expense_type"], value["amount"]), int(key[0]))
    return {key: first_session[(value["date"], value["expense_type"], value["amount"])] for key, value in facts(replayed, "expense").items()}


def expense_items(replayed: Replay, expense_type: str | None = None) -> Counter:
    session_of = memora_expense_session(replayed)
    return Counter(
        (session_of[key], value["expense_type"], value["amount"])
        for key, value in facts(replayed, "expense").items()
        if expense_type in (None, value["expense_type"])
    )


def step_items(replayed: Replay) -> Counter:
    return Counter((replayed.last_session[("steps", key)], value["step_count"]) for key, value in facts(replayed, "steps").items())


def stale_names(replayed: Replay, domain: str, matches_key) -> tuple[set, set]:
    """Names that were once a fact matching `matches_key`, and the subset that no longer is one."""
    ever = {key[-1] for fact_domain, key in replayed.values_held if fact_domain == domain and matches_key(key)}
    current = {key[-1] for key in facts(replayed, domain) if matches_key(key)}
    return ever, current


def forgotten_are_stale(forgotten: list, ever: set, current: set) -> tuple[bool, str]:
    wrong = [name for name in forgotten if name not in ever or name in current]
    return not wrong, f"forgotten but not stale: {wrong}" if wrong else ""


def check_preference(question: dict, replayed: Replay) -> QuestionCheck:
    category, scope = question["question_id"].removeprefix("pref_").rsplit("_", 1)[0].split("_", 1)
    evidence = question["memory_evidence"]
    if scope == "general":
        expected_lists = evidence["memory_items"]
    else:
        expected_lists = {scope: evidence["subcategory_data"]}
    expected = {
        (subcategory, entry["item"], list_name.removesuffix("s"))
        for subcategory, lists in expected_lists.items()
        for list_name, entries in lists.items()
        for entry in entries
    }

    def in_scope(key):
        return key[0] == category and (scope == "general" or key[1] == scope)

    mine = {(key[1], key[2], value["preference"]) for key, value in facts(replayed, "preference").items() if in_scope(key)}
    forgetting_matches, note = None, ""
    if "forgetting_evidence" in question:
        forgotten = [entry["value"] for entry in question["forgetting_evidence"]["forgotten_items"]]
        forgetting_matches, note = forgotten_are_stale(forgotten, *stale_names(replayed, "preference", in_scope))
    if expected != mine:
        note = f"memory only Memora: {sorted(expected - mine)} only ours: {sorted(mine - expected)} {note}"
    return QuestionCheck(question["question_id"], f"pref_{scope if scope == 'general' else 'subcategory'}", expected == mine, forgetting_matches, note)


def check_todos(question: dict, replayed: Replay) -> QuestionCheck:
    expected = {entry["value"] for entry in question["memory_evidence"]["remaining_tasks"]}
    mine = {key[0] for key in facts(replayed, "todo")}
    forgotten = [entry["value"] for entry in question["forgetting_evidence"]["forgotten_items"]]
    forgetting_matches, note = forgotten_are_stale(forgotten, *stale_names(replayed, "todo", lambda key: True))
    return QuestionCheck(question["question_id"], "activity_todos", expected == mine, forgetting_matches, note)


def check_calendar(question: dict, replayed: Replay) -> QuestionCheck:
    today = question["question_date"]
    events = facts(replayed, "calendar")
    upcoming = {key[0] for key, value in events.items() if value["event_date"] > today}
    expected = {entry["value"] for entry in question["memory_evidence"]["calendar_events"]}
    past_count = sum(1 for value in events.values() if value["event_date"] <= today)
    forgetting_matches = question["forgetting_evidence"]["total_forgotten_items"] == past_count
    return QuestionCheck(question["question_id"], "activity_calendar", expected == upcoming, forgetting_matches)


def check_food(question: dict, replayed: Replay) -> QuestionCheck:
    evidence = question["memory_evidence"]
    entries = evidence.get("food_expenses") or evidence["expense_items"]
    expected = Counter((entry["session_id"], entry["expense_type"], entry["amount"]) for entry in entries)
    expense_type = None if question["question_id"].startswith("activity_food_total") else evidence["expense_type"]
    family = "activity_food_total" if expense_type is None else "activity_food_type"
    return QuestionCheck(question["question_id"], family, expected == expense_items(replayed, expense_type), None)


def check_steps(question: dict, replayed: Replay) -> QuestionCheck:
    expected = Counter((entry["session_id"], entry["step_count"]) for entry in question["memory_evidence"]["step_data"])
    return QuestionCheck(question["question_id"], "activity_steps_total", expected == step_items(replayed), None)


def check_goal(question: dict, replayed: Replay) -> QuestionCheck:
    evidence = question["memory_evidence"]
    subcategory = evidence["goal_data"]["subcategory"]
    goal_matches = replayed.state.get(("goal", (subcategory,))) == {"value": evidence["goal_value"]}
    if evidence["goal_data"]["category"] == "step_tracker":
        expected = Counter((entry["session_id"], entry["step_count"]) for entry in evidence["activity_sessions"])
        activity_matches = expected == step_items(replayed)
    else:
        expected = Counter((entry["session_id"], entry["expense_type"], entry["amount"]) for entry in evidence["activity_sessions"])
        activity_matches = expected == expense_items(replayed, subcategory)
    return QuestionCheck(question["question_id"], "goal", goal_matches and activity_matches, None)


PERIOD_DAYS = {"week": 7, "month": 30}


def period_of(day: str, start: str, period_days: int) -> int:
    return (date.fromisoformat(day) - date.fromisoformat(start)).days // period_days + 1


def check_comparative_max(question: dict, replayed: Replay, start: str) -> QuestionCheck:
    measure, period_name = re.fullmatch(r"comparative_(.+)_max_(week|month)_\d+", question["question_id"]).groups()
    period_days = PERIOD_DAYS[period_name]
    session_of = memora_expense_session(replayed)
    expected, mine = Counter(), Counter()
    for period, breakdown in question["memory_evidence"]["period_breakdown"].items():
        for entry in breakdown["items"]:
            expected[(int(period), entry["session_id"], entry.get("expense_type"), entry.get("amount", entry.get("step_count")))] += 1
    if measure == "steps":
        for key, value in facts(replayed, "steps").items():
            mine[(period_of(key[0], start, period_days), replayed.last_session[("steps", key)], None, value["step_count"])] += 1
    else:
        for key, value in facts(replayed, "expense").items():
            if value["expense_type"] == measure:
                mine[(period_of(value["date"], start, period_days), session_of[key], measure, value["amount"])] += 1
    mine = Counter({item: count for item, count in mine.items() if str(item[0]) in question["memory_evidence"]["period_breakdown"]})
    return QuestionCheck(question["question_id"], f"comparative_max_{period_name}", expected == mine, None)


def check_comparative_goal(question: dict, changes: list[Change], start: str, end: str) -> QuestionCheck:
    outcome, subcategory, period_name = re.fullmatch(r"comparative_goal_(met|exceeded)_(.+)_(week|month)_\d+", question["question_id"]).groups()
    # Memora drops changes made after day (end - start), which excludes the last day of the timeline.
    last_day = (date.fromisoformat(end) - date.fromisoformat(start)).days
    timeline, current = {}, None
    for change in changes:
        day = (date.fromisoformat(change.date) - date.fromisoformat(start)).days + 1
        if change.domain == "goal" and change.key == (subcategory,) and change.value["value"] != current and day <= last_day:
            current = change.value["value"]
            timeline[str(day)] = current
    expected = question["memory_evidence"]["budget_timeline"]
    return QuestionCheck(question["question_id"], f"comparative_goal_{outcome}_{period_name}", expected == timeline, None, f"Memora {expected} ours {timeline}")


def document(replayed: Replay, document_id: str) -> dict:
    content = {}
    for key, value in facts(replayed, "content").items():
        if key[0] != document_id:
            continue
        if len(key) == 2:
            content[key[1]] = value["value"]
        else:
            content.setdefault(key[1], []).append(value["value"])
    return {field: sorted(entries) if isinstance(entries, list) else entries for field, entries in content.items()}


def check_content(question: dict, replayed: Replay) -> QuestionCheck:
    document_id = re.fullmatch(r"content_[a-z_]+?_\d+_(.+)", question["question_id"]).group(1)
    evidence = question["memory_evidence"]
    expected = {field: sorted(entries) if isinstance(entries, list) else entries for field, entries in evidence["content_data"].items()}
    touching = set().union(*(sessions for (domain, key), sessions in replayed.sessions_touching.items() if domain == "content" and key[0] == document_id))
    memory_matches = expected == document(replayed, document_id) and set(evidence["session_history"]) == touching
    wrong = []
    for entry in question["forgetting_evidence"]["forgotten_items"]:
        list_fact = ("content", (document_id, entry["field"], entry["value"]))
        scalar_fact = ("content", (document_id, entry["field"]))
        was_list_element = list_fact in replayed.values_held and list_fact not in replayed.state
        was_scalar_value = {"value": entry["value"]} in replayed.values_held.get(scalar_fact, []) and replayed.state.get(scalar_fact) != {"value": entry["value"]}
        if not (was_list_element or was_scalar_value):
            wrong.append((entry["field"], entry["value"]))
    note = f"forgotten but not stale: {wrong}" if wrong else ""
    return QuestionCheck(question["question_id"], "content", memory_matches, not wrong, note)


def check_question(question: dict, replayed: Replay, changes: list[Change], start: str, end: str) -> QuestionCheck:
    question_id = question["question_id"]
    if question_id.startswith("pref_"):
        return check_preference(question, replayed)
    if question_id.startswith("activity_todos"):
        return check_todos(question, replayed)
    if question_id.startswith("activity_calendar"):
        return check_calendar(question, replayed)
    if question_id.startswith("activity_food"):
        return check_food(question, replayed)
    if question_id.startswith("activity_steps"):
        return check_steps(question, replayed)
    if question_id.startswith("goal_"):
        return check_goal(question, replayed)
    if question_id.startswith("comparative_goal_"):
        return check_comparative_goal(question, changes, start, end)
    if question_id.startswith("comparative_"):
        return check_comparative_max(question, replayed, start)
    if question_id.startswith("content_"):
        return check_content(question, replayed)
    raise ValueError(f"unknown question family {question_id}")


def evaluation_questions(period: str, persona: str) -> list[dict]:
    path = MEMORA_DATA / period / persona / f"evaluation_questions_{persona}.json"
    return [question for questions in json.loads(path.read_text())["questions"].values() for question in questions]


def content_snapshot_mismatches(sessions: list[dict]) -> list[int]:
    """Sessions whose `content_data` (Memora's full post-session document) differs from the replayed facts."""
    changes, mismatches = [], []
    for session in sessions:
        changes += extract_changes(session)
        item = (session.get("operation_details") or {}).get("item")
        if session["session_type"] == "activity" and isinstance(item, str):
            content_data = session["operation_details"]["content_data"]
            expected = {field: sorted(entries) if isinstance(entries, list) else entries for field, entries in content_data.items()}
            if expected != document(replay(changes), item):
                mismatches.append(session["session_id"])
    return mismatches


def persona_report(period: str, persona: str) -> dict:
    sessions = load_sessions(period, persona)
    changes = [change for session in sessions for change in extract_changes(session)]
    replayed = replay(changes)
    start, end = sessions[0]["date"], sessions[-1]["date"]
    checks = [check_question(question, replayed, changes, start, end) for question in evaluation_questions(period, persona)]
    return {
        "sessions": len(sessions),
        "changes": Counter((change.domain, change.action) for change in changes),
        "distinct_facts": len({(change.domain, change.key) for change in changes}),
        "final_facts": len(replayed.state),
        "precondition_failures": replayed.precondition_failures,
        "checks": checks,
    }


DOMAINS = ("preference", "todo", "calendar", "expense", "steps", "goal", "content")


def main(periods: list[str]) -> None:
    for period in periods:
        print(f"\n## {period}\n")
        print("Changes per domain as add/update/remove.\n")
        print(f"| persona | sessions | {' | '.join(DOMAINS)} | distinct facts | final facts | precondition failures | questions matching |")
        print("|---" * (len(DOMAINS) + 6) + "|")
        by_domain, by_family, failures = Counter(), Counter(), []
        for persona in personas(period):
            report = persona_report(period, persona)
            by_domain.update(report["changes"])
            cells = [f"{report['changes'][(domain, 'add')]}/{report['changes'][(domain, 'update')]}/{report['changes'][(domain, 'remove')]}" for domain in DOMAINS]
            for check in report["checks"]:
                by_family[(check.family, check.matches)] += 1
                if not check.matches:
                    failures.append((persona, check))
            matching = sum(check.matches for check in report["checks"])
            print(
                f"| {persona} | {report['sessions']} | {' | '.join(cells)} | {report['distinct_facts']} | {report['final_facts']} "
                f"| {len(report['precondition_failures'])} | {matching}/{len(report['checks'])} |"
            )
        totals = [f"{by_domain[(domain, 'add')]}/{by_domain[(domain, 'update')]}/{by_domain[(domain, 'remove')]}" for domain in DOMAINS]
        print(f"| **total** | | {' | '.join(totals)} | | | | |")
        print("\n| question family | match | no match |\n|---|---|---|")
        for family in sorted({family for family, _ in by_family}):
            print(f"| {family} | {by_family[(family, True)]} | {by_family[(family, False)]} |")
        for persona, check in failures:
            print(f"- {persona} {check.question_id}: memory={check.memory_matches} forgetting={check.forgetting_matches} {check.note}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["weekly", "monthly"])
