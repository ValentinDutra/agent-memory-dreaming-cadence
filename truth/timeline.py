"""The truth over time: which facts hold after each session, and where Memora contradicts itself."""

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, replace
from typing import Literal

from truth.changes import MEMORA_DATA, Change, extract_changes, load_sessions, personas

FactId = tuple[str, tuple[str, ...]]
InconsistencyKind = Literal["add_existing", "update_missing", "remove_missing", "previous_mismatch"]


@dataclass(frozen=True)
class Version:
    """One value of a fact and the sessions during which it holds: valid_from <= session < valid_until."""

    domain: str
    key: tuple[str, ...]
    value: dict
    valid_from: int
    valid_until: int | None = None

    def holds_after(self, session_id: int) -> bool:
        return self.valid_from <= session_id and (self.valid_until is None or session_id < self.valid_until)


@dataclass(frozen=True)
class Inconsistency:
    """A change whose precondition failed. `found` is the value the truth held right before it."""

    kind: InconsistencyKind
    change: Change
    found: dict | None


@dataclass(frozen=True)
class Timeline:
    versions: tuple[Version, ...]
    inconsistencies: tuple[Inconsistency, ...]

    def state_after(self, session_id: int) -> dict[FactId, dict]:
        return {
            (version.domain, version.key): version.value
            for version in self.versions
            if version.holds_after(session_id)
        }

    def changed_between(self, start_session: int, end_session: int) -> dict[FactId, tuple[dict | None, dict | None]]:
        """Facts whose value after end_session differs from their value after start_session, as (before, after)."""
        before = self.state_after(start_session)
        after = self.state_after(end_session)
        return {
            fact: (before.get(fact), after.get(fact))
            for fact in before.keys() | after.keys()
            if before.get(fact) != after.get(fact)
        }


def precondition_violation(change: Change, current: dict | None) -> InconsistencyKind | None:
    if change.action == "add":
        return "add_existing" if current is not None else None
    if current is None:
        return "update_missing" if change.action == "update" else "remove_missing"
    if change.previous is not None and change.previous != current:
        return "previous_mismatch"
    return None


def build_timeline(changes: list[Change]) -> Timeline:
    """Replay the changes in order. On a failed precondition the newest statement still wins."""
    open_versions: dict[FactId, Version] = {}
    closed_versions: list[Version] = []
    inconsistencies: list[Inconsistency] = []
    for change in changes:
        fact = (change.domain, change.key)
        current = open_versions.get(fact)
        kind = precondition_violation(change, current.value if current else None)
        if kind:
            inconsistencies.append(Inconsistency(kind, change, current.value if current else None))
        if current is not None and change.action != "remove" and change.value == current.value:
            continue
        if current is not None:
            closed_versions.append(replace(current, valid_until=change.session_id))
            del open_versions[fact]
        if change.action != "remove":
            open_versions[fact] = Version(change.domain, change.key, change.value, change.session_id)
    return Timeline(tuple(closed_versions) + tuple(open_versions.values()), tuple(inconsistencies))


def state_after(changes: list[Change], session_id: int) -> dict[FactId, dict]:
    return build_timeline(changes).state_after(session_id)


# --- Validation against the conversation text -------------------------------------------------

STOPWORDS = {"a", "an", "and", "at", "for", "in", "my", "of", "on", "the", "to", "up", "with", "your"}


def words(text: str) -> list[str]:
    # Memora names decades "1980s" in operation_details and "80s" in the conversation.
    text = re.sub(r"\b(?:19|20)(\d0s)\b", r"\1", text.casefold())
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    return [word for word in re.findall(r"[a-z0-9]+", text) if word not in STOPWORDS]


def same_stem(wanted: str, found: str) -> bool:
    prefix_length = min(len(wanted), 4)
    return len(found) >= prefix_length and found[:prefix_length] == wanted[:prefix_length]


def text_support(mention: str, text: str) -> Literal["full", "partial", "absent"]:
    """How many words of `mention` appear in `text`, matching by a 4-letter stem (buy ~ buying, symphony ~ symphonies)."""
    wanted = words(mention)
    found = words(text)
    covered = sum(any(same_stem(word, candidate) for candidate in found) for word in wanted)
    if covered == len(wanted):
        return "full"
    return "partial" if covered * 2 >= len(wanted) else "absent"


# Facts keyed by a session, a date or a document field are named in the conversation by their value.
VALUE_NAMED_DOMAINS = {"expense": "amount", "steps": "step_count", "goal": "value"}


def fact_mention(change: Change) -> str:
    value = change.value or change.previous
    if change.domain in VALUE_NAMED_DOMAINS:
        return str(value[VALUE_NAMED_DOMAINS[change.domain]]).removesuffix(".0")
    if change.domain == "content" and len(change.key) == 2:
        return str(value["value"])
    return str(change.key[-1])


def change_text_support(session: dict, change: Change) -> Literal["full", "partial", "absent", "no_share_turns"]:
    """Whether the turns flagged share_memory=True mention the fact."""
    shared_text = " ".join(turn["message"] for turn in session["conversation"] if turn.get("share_memory"))
    if not shared_text:
        return "no_share_turns"
    return text_support(fact_mention(change), shared_text)


def session_defects(session: dict, changes: list[Change]) -> list[tuple[str, int | None]]:
    """Structural defects of one session, as (kind, turn)."""
    defects = []
    conversation = session["conversation"]
    share_turns = [turn for turn in conversation if turn.get("share_memory")]
    for turn in share_turns:
        if turn["speaker"] != "user_agent":
            defects.append(("share_memory_on_assistant_turn", turn["turn"]))
    # Two assistant turns in a row read as a follow-up; two user turns in a row are where mislabeled
    # assistant text shows up (weekly/software_engineer session 30, turn 15).
    for previous_turn, turn in zip(conversation, conversation[1:]):
        if turn["speaker"] == previous_turn["speaker"] == "user_agent":
            defects.append(("user_turn_after_user_turn", turn["turn"]))
    if session["session_type"] == "no_memory" and share_turns:
        defects.append(("share_memory_in_no_memory_session", share_turns[0]["turn"]))
    if changes and not share_turns:
        defects.append(("changes_without_share_turns", None))
    if changes:
        mentions = [fact_mention(change) for change in changes]
        for turn in share_turns:
            if all(text_support(mention, turn["message"]) == "absent" for mention in mentions):
                defects.append(("share_turn_mentions_no_changed_fact", turn["turn"]))
    return defects


# --- Validation against Memora's own evaluation evidence --------------------------------------

def question_session(question_id: str) -> int:
    """The session the question is asked after: activity_todos_163 and content_meeting_notes_163_meeting_notes_2 -> 163."""
    return int(re.search(r"_(\d+)(?:_|$)", question_id).group(1))


def evidence_items(evidence, inside_content: bool = False) -> list[tuple[str, int | None]]:
    """Facts named in Memora's evidence as (text, session_id): `value`/`item` strings and content_data leaves."""
    if isinstance(evidence, str):
        return [(evidence, None)] if inside_content else []
    if isinstance(evidence, list):
        return [item for child in evidence for item in evidence_items(child, inside_content)]
    if isinstance(evidence, dict):
        found = []
        for name, child in evidence.items():
            if isinstance(child, str) and name in ("value", "item"):
                found.append((child, evidence.get("session_id")))
            else:
                found.extend(evidence_items(child, inside_content or name == "content_data"))
        return found
    return []


def string_leaves(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, (list, tuple)):
        return [leaf for child in value for leaf in string_leaves(child)]
    return []


def names(version: Version, text: str) -> bool:
    return text.casefold() in {leaf.casefold() for leaf in string_leaves([version.key, version.value])}


def evidence_check(period: str, persona: str, timeline: Timeline) -> Counter:
    """Per question family, whether the truth at the question's session reproduces Memora's evidence."""
    path = MEMORA_DATA / period / persona / f"evaluation_questions_{persona}.json"
    questions = json.loads(path.read_text())["questions"]
    counts = Counter()
    for question in (question for task in questions.values() for question in task):
        family = "_".join(question["question_id"].split("_")[:2])
        session_id = question_session(question["question_id"])
        alive = [version for version in timeline.versions if version.holds_after(session_id)]
        for text, evidence_session in evidence_items(question.get("memory_evidence") or {}):
            matches = [version for version in alive if names(version, text)]
            facts = {(version.domain, version.key) for version in matches}
            if not matches:
                outcome = "missing"
            elif evidence_session is None or any(version.valid_from == evidence_session for version in matches):
                outcome = "in_truth"
            elif any((version.domain, version.key) in facts and version.valid_from == evidence_session for version in timeline.versions):
                # Memora keeps the session where the fact first appeared; valid_from restarts on every change of value.
                outcome = "in_truth_since_earlier_version"
            else:
                outcome = "in_truth_other_session"
            counts[(family, "remembered", outcome)] += 1
        forgotten = (question.get("forgetting_evidence") or {}).get("forgotten_items", [])
        for text, _ in evidence_items(forgotten):
            if any(names(version, text) for version in alive):
                outcome = "still_in_truth"
            elif any(names(version, text) for version in timeline.versions if version.valid_from <= session_id):
                outcome = "removed"
            else:
                outcome = "never_in_truth"
            counts[(family, "forgotten", outcome)] += 1
    return counts


# --- Report -----------------------------------------------------------------------------------

def report(period: str) -> None:
    alive_by_persona = {}
    inconsistency_counts = Counter()
    support_counts = Counter()
    defect_counts = Counter()
    evidence_counts = Counter()
    examples = {}
    for persona in personas(period):
        sessions = load_sessions(period, persona)
        changes_by_session = {session["session_id"]: extract_changes(session) for session in sessions}
        timeline = build_timeline([change for changes in changes_by_session.values() for change in changes])
        last_session = sessions[-1]["session_id"]
        alive_by_persona[persona] = Counter(domain for domain, _ in timeline.state_after(last_session))
        for inconsistency in timeline.inconsistencies:
            inconsistency_counts[inconsistency.kind] += 1
            examples.setdefault(inconsistency.kind, (persona, inconsistency.change.session_id, inconsistency.change.key))
        for session in sessions:
            changes = changes_by_session[session["session_id"]]
            for change in changes:
                support = change_text_support(session, change)
                support_counts[(change.domain, change.action, support)] += 1
                examples.setdefault((change.domain, support), (persona, session["session_id"], change.key))
            for kind, turn in session_defects(session, changes):
                defect_counts[kind] += 1
                examples.setdefault(kind, (persona, session["session_id"], turn))
        evidence_counts += evidence_check(period, persona, timeline)

    print(f"== {period}: facts alive after the last session, by persona")
    for persona, counts in alive_by_persona.items():
        print(f"  {persona:24} {sum(counts.values()):4}  {dict(sorted(counts.items()))}")
    print(f"== {period}: inconsistencies {dict(inconsistency_counts) or 'none'}")
    print(f"== {period}: does a share_memory turn mention the changed fact?")
    for key, count in sorted(support_counts.items()):
        print(f"  {key} {count}")
    print(f"== {period}: session defects")
    for kind, count in defect_counts.most_common():
        print(f"  {kind:40} {count:5}  e.g. {examples[kind]}")
    print(f"== {period}: Memora evaluation evidence reproduced by the truth")
    for key, count in sorted(evidence_counts.items()):
        print(f"  {key} {count}")
    print(f"== {period}: first example of each finding")
    for key, example in examples.items():
        print(f"  {key}: {example}")


if __name__ == "__main__":
    for period in sys.argv[1:] or ["weekly"]:
        report(period)
