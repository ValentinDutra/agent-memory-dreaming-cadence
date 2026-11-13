"""Where each invented answer of a policy run comes from: the notes, the reader, or Memora and the exam. Owner: P6a.

  uv run python -m diagnosis.causes monthly/academic_researcher --policies every-5 --check-cache

For each invented answer, `from_notes` is what a reader that follows the notes and the answer rules exactly would
answer. If that is the expected answer, the reader misread right notes. Otherwise the notes are compared entry by
entry with the truth after the exam session, and every difference is explained: an entry logged after the last
dream (the notes lag), an entry the dream read and left out, a line no state ever had, or an expense the user dated
"last night" that Memora dates on the session's day. See docs/p6a-origen-de-las-inventadas.md.
"""

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache

from diagnosis.invented import WrongAnswer, line_origin, wrong_answers
from dreaming.quality import parse_notes, similarity
from dreaming.transcripts import Session, load_transcripts
from exam.grading import negates_removed_preference, normalize
from exam.schema import UNKNOWN
from exam.unreachable import relative_dated_expenses, unreachable
from policies.engine import PolicyRun, Step
from truth.changes import persona_changes
from truth.timeline import Timeline, build_timeline, text_support

# The cause of each invented answer, and the group of the P6a statement it belongs to.
CAUSES = {
    "dream_false_line": "1 dream",          # a note line holds a value no state of the fact ever had
    "dream_omission": "1 dream",            # the dream read the session that logged an entry and left it out of the notes
    "reader_misread": "2 reader",           # the notes give the expected answer; the reader answered something else
    "reader_nothing_for_absent": "2 reader",  # the notes lack the asked expense, step count or event date; the reader answered 0 or no, not unknown
    "memora_relative_date": "3 Memora/exam",  # the notes follow the user's "last night"; Memora dates that expense on the session's day
    "memora_kept_removed": "3 Memora/exam",   # a dream deleted the fact after the user dropped it; Memora still holds it
    "grader_empty_total": "3 Memora/exam",  # the notes have no entry in the total's range yet; 0 is their total, graded invented, not stale
    "unexplained": "4 other",
}

LOGS = ("expense", "steps")
DROPPED = re.compile(r"\b(?:no longer|anymore|cancel\w*|remov\w*|drop\w*)\b", flags=re.IGNORECASE)


@dataclass(frozen=True)
class Entry:
    """One logged expense or step count, from the truth or from a note line."""

    date: str
    kind: str      # expense type; "" for steps
    amount: float
    logged_in: int = 0  # truth: the session that logged it
    line: str = ""      # notes: the line it was read from, as written


@dataclass(frozen=True)
class Difference:
    kind: str  # lag, omitted, relative_date, merged, false_line, dropped_by_user
    detail: str
    about: str = ""  # the expense or fact it is about, the same in every exam it spoils; detail when empty


@dataclass(frozen=True)
class Diagnosis:
    wrong: WrongAnswer
    cause: str
    from_notes: str  # what a faithful reader of the notes answers, in canonical form
    differences: tuple[Difference, ...]
    marked: str | None  # the reason exam.unreachable marks the question, if it does


@dataclass(frozen=True)
class Persona:
    timeline: Timeline
    sessions: dict[int, Session]
    shifted: frozenset[tuple[str, str, float]]  # (date Memora gave, type, amount) of expenses the user dated "last night"
    marked: dict[str, str]


@cache
def persona(period: str, persona_name: str) -> Persona:
    timeline = build_timeline(persona_changes(period, persona_name))
    sessions = {session.session_id: session for session in load_transcripts(period, persona_name)}
    shifted = frozenset(
        (value["date"], value["expense_type"], round(float(value["amount"]), 2))
        for version in timeline.versions
        if ((version.domain, version.key), version.valid_from) in relative_dated_expenses(timeline, sessions)
        for value in [version.value]
    )
    return Persona(timeline, sessions, shifted, unreachable(period, persona_name))


def diagnose_run(run: PolicyRun) -> list[Diagnosis]:
    dreams = [step for step in run.steps if step.dreamt]
    return [diagnose(wrong, dreams, persona(run.period, run.persona)) for wrong in wrong_answers(run)]


def diagnose(wrong: WrongAnswer, dreams: list[Step], data: Persona) -> Diagnosis:
    question = wrong.question
    marked = data.marked.get(question.question_id)
    if question.domain not in LOGS:
        from_notes = choice_from_notes(wrong)
        removal = None if from_notes == wrong.grade.expected else removal_by_user(wrong, dreams, data)
        if from_notes == wrong.grade.expected:
            cause = "reader_misread"
        elif removal:
            cause = "memora_kept_removed"
        elif from_notes == wrong.grade.given:
            cause = "dream_false_line"
        elif from_notes == UNKNOWN and wrong.grade.given == "no":
            cause = "reader_nothing_for_absent"
        else:
            cause = "unexplained"
        differences = (removal,) if removal else (absent_fact(wrong, data),) if from_notes == UNKNOWN and question.current else ()
        return Diagnosis(wrong, cause, from_notes, differences, marked)
    start, end, kind = asked_range(question)
    truth = truth_entries(data.timeline, question.domain, question.session_id, start, end, kind)
    notes = note_entries(wrong.notes, question.domain, start, end, kind)
    # The rules: a total covers the entries listed; a number the notes do not contain is unknown.
    from_notes = number_text(sum(entry.amount for entry in notes)) if notes or question.probe == "aggregate" else UNKNOWN
    differences = tuple(compare_entries(truth, notes, wrong, dreams, data))
    kinds = {difference.kind for difference in differences}
    if from_notes == wrong.grade.expected:
        cause = "reader_misread"
    elif "relative_date" in kinds:
        cause = "memora_relative_date"
    elif kinds & {"false_line", "merged"}:
        cause = "dream_false_line"
    elif question.probe != "aggregate" and not notes and wrong.grade.given == "0":
        cause = "reader_nothing_for_absent"
    elif "omitted" in kinds:
        cause = "dream_omission"
    elif question.probe == "aggregate" and not notes and wrong.grade.given == "0":
        cause = "grader_empty_total"
    else:
        cause = "unexplained"
    return Diagnosis(wrong, cause, from_notes, differences, marked)


def asked_range(question) -> tuple[str, str, str]:
    """(first date, last date, expense type or "") the question covers."""
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", question.prompt)
    if question.probe == "aggregate":
        return dates[0], dates[1], ""
    if question.domain == "expense":
        return dates[0], dates[0], question.current["expense_type"]
    return dates[0], dates[0], ""


def truth_entries(timeline: Timeline, domain: str, session_id: int, start: str, end: str, kind: str) -> list[Entry]:
    entries = []
    for version in timeline.versions:
        if version.domain != domain or not version.holds_after(session_id):
            continue
        entry = log_entry(domain, version.key, version.value, version.valid_from)
        if start <= entry.date <= end and kind in ("", entry.kind):
            entries.append(entry)
    return sorted(entries, key=lambda entry: entry.logged_in)


def log_entry(domain: str, key: tuple, value: dict, logged_in: int) -> Entry:
    if domain == "expense":
        return Entry(value["date"], value["expense_type"], round(float(value["amount"]), 2), logged_in)
    return Entry(key[0], "", round(float(value["step_count"]), 2), logged_in)


def note_entries(notes: str, domain: str, start: str, end: str, kind: str) -> list[Entry]:
    entries = []
    for fact in parse_notes(notes).facts:
        if fact.domain != domain:
            continue
        line_date, _, line_kind = fact.name.partition(" ")
        if start <= line_date <= end and (not kind or similarity(line_kind, kind)):
            entries.append(Entry(line_date, line_kind, fact.value, line=fact.line))
    return entries


def compare_entries(truth: list[Entry], notes: list[Entry], wrong: WrongAnswer, dreams: list[Step], data: Persona) -> list[Difference]:
    """Pair truth and note entries by date and amount; explain every entry left on either side."""
    unmatched_truth = list(truth)
    unmatched_notes = []
    for note in notes:
        twin = next((entry for entry in unmatched_truth if (entry.date, entry.amount) == (note.date, note.amount)), None)
        if twin:
            unmatched_truth.remove(twin)
        else:
            unmatched_notes.append(note)
    differences = []
    for note in unmatched_notes:
        difference = explain_note_line(note, unmatched_truth, data)
        origin = line_origin([step for step in dreams if step.session_id <= wrong.question.session_id], note.line)
        differences.append(Difference(difference.kind, f"{difference.detail}; written by the dream after s{origin.written_after}, which read s{origin.sessions_read[0]}-s{origin.sessions_read[-1]}", difference.about or difference.detail))
    for entry in unmatched_truth:
        differences.append(explain_absent_entry(entry, wrong, dreams, data))
    return differences


def explain_note_line(note: Entry, unmatched_truth: list[Entry], data: Persona) -> Difference:
    """A note line no truth entry of the range matches: the user's own date of a "last night" expense, two entries in one line, or false."""
    user_dated = {(day_before(memora_date), amount) for memora_date, _, amount in data.shifted}
    if (note.date, note.amount) in user_dated:
        return Difference("relative_date", f"`{note.line.strip()}` is the day the user meant; Memora dates it a day later", f"last night {note.amount}")
    same_day = [("truth", entry.amount) for entry in unmatched_truth if entry.date == note.date]
    same_day += [("last night", amount) for user_date, amount in user_dated if user_date == note.date]
    for first_index, (_, first) in enumerate(same_day):
        for source, second in same_day[first_index + 1:]:
            if round(first + second, 2) == note.amount:
                kind = "relative_date" if source == "last night" else "merged"
                return Difference(kind, f"`{note.line.strip()}` adds {first} and {second} ({source}) in one line", f"last night {second}" if kind == "relative_date" else "")
    return Difference("false_line", f"`{note.line.strip()}`: no entry of the truth has that date and amount")


def explain_absent_entry(entry: Entry, wrong: WrongAnswer, dreams: list[Step], data: Persona) -> Difference:
    """A truth entry the notes lack: logged after the last dream, dated by Memora a day late, or left out by a dream that read it."""
    described = f"{entry.date} {entry.kind or 'steps'} {entry.amount} (logged in s{entry.logged_in})"
    if (entry.date, entry.kind, entry.amount) in data.shifted:
        return Difference("relative_date", f"{described}: the user said last night; the notes date it {day_before(entry.date)}", f"last night {entry.amount}")
    if wrong.last_dream is None:
        return Difference("lag", f"{described}: no dream yet")
    if entry.logged_in > wrong.last_dream:
        return Difference("lag", f"{described}: after the last dream (s{wrong.last_dream})")
    reader = next(step for step in dreams if step.session_id >= entry.logged_in)
    return Difference("omitted", f"{described}: the dream after s{reader.session_id} read it and left it out")


def absent_fact(wrong: WrongAnswer, data: Persona) -> Difference:
    """Why the notes lack a fact that holds: no dream yet, it started after the last dream, or a dream read it and left it out."""
    question = wrong.question
    started = min(version.valid_from for version in data.timeline.versions if (version.domain, version.key) == question.fact and version.holds_after(question.session_id))
    if wrong.last_dream is None:
        return Difference("lag", f"holds since s{started}; no dream yet")
    if started > wrong.last_dream:
        return Difference("lag", f"holds since s{started}, after the last dream (s{wrong.last_dream})")
    return Difference("omitted", f"holds since s{started}; the dreams up to s{wrong.last_dream} read it and the notes lack it")


def removal_by_user(wrong: WrongAnswer, dreams: list[Step], data: Persona) -> Difference | None:
    """A fact Memora still holds whose line a dream deleted after reading a user turn that names it and drops it."""
    question = wrong.question
    if question.current is None or question.fact is None:
        return None
    name = question.fact[1][-1]

    def names_fact(notes: str) -> bool:
        return any(fact.domain == question.domain and similarity(fact.name, name) for fact in parse_notes(notes).facts)

    earlier = [step for step in dreams if step.session_id <= question.session_id]
    if not earlier or names_fact(earlier[-1].notes):
        return None
    for before, after in reversed(list(zip(earlier, earlier[1:]))):
        if names_fact(before.notes) and not names_fact(after.notes):
            for session_id in range(before.session_id + 1, after.session_id + 1):
                for turn in data.sessions[session_id].turns:
                    if turn.speaker == "user_agent" and DROPPED.search(turn.message) and text_support(name, turn.message) != "absent":
                        return Difference("dropped_by_user", f"the dream after s{after.session_id} deleted it; s{session_id}: \"{turn.message}\"")
            return None
    return None


def day_before(iso_date: str) -> str:
    return (date.fromisoformat(iso_date) - timedelta(days=1)).isoformat()


def number_text(number: float) -> str:
    return f"{round(number, 2):.2f}".rstrip("0").rstrip(".")


def choice_from_notes(wrong: WrongAnswer) -> str:
    """For preference and calendar questions: the line's value, or the answer the rules give when no line names the fact."""
    question = wrong.question
    lines = [fact for fact in parse_notes(wrong.notes).facts if fact.domain == question.domain and fact.line in {origin.line for origin in wrong.related}]
    if question.domain == "preference":
        exact = [fact for fact in lines if fact.name.casefold() == question.fact[1][-1].casefold()]
        return normalize(question, exact[0].value) if exact else UNKNOWN
    if question.domain == "calendar" and question.field is not None:
        return normalize(question, lines[0].value) if lines and lines[0].value else UNKNOWN
    return normalize(question, "yes" if lines else "no")


def stretch(session_id: int, last_session: int, width: int = 210) -> str:
    start = (session_id - 1) // width * width + 1
    return f"s{start}-{min(start + width - 1, last_session)}"


def root(diagnosis: Diagnosis) -> tuple:
    """What the answer goes wrong on: its differences other than lag, or else the question itself (a lag spoils one exam)."""
    lasting = tuple(sorted({difference.about or difference.detail for difference in diagnosis.differences if difference.kind != "lag"}))
    return lasting or (diagnosis.wrong.question.question_id,)


def describe(diagnosis: Diagnosis) -> str:
    wrong = diagnosis.wrong
    question = wrong.question
    lines = [
        f"### {wrong.policy} s{question.session_id} {question.domain}/{question.probe}: {diagnosis.cause}" + (f" (marked {diagnosis.marked})" if diagnosis.marked else ""),
        f"- question: {question.prompt}",
        f"- answer {wrong.grade.given!r}, expected {wrong.grade.expected!r}, the notes give {diagnosis.from_notes!r}; " + (f"last dream s{wrong.last_dream}" if wrong.last_dream else "no dream yet"),
    ]
    lines += [f"- {difference.kind}: {difference.detail}" for difference in diagnosis.differences]
    if negates_removed_preference(question, wrong.grade):
        lines.append("- lenient count (P2 decision): \"dislike\" after a removed like counts as correct")
    return "\n".join(lines)


def table(rows: dict[str, Counter], columns: list[str]) -> str:
    lines = ["| cause | group | " + " | ".join(columns) + " |", "| --- | --- |" + " --: |" * len(columns)]
    for cause, group in CAUSES.items():
        lines.append(f"| {cause} | {group} | " + " | ".join(str(rows[column][cause]) for column in columns) + " |")
    lines.append("| **total** | | " + " | ".join(f"**{sum(rows[column].values())}**" for column in columns) + " |")
    return "\n".join(lines)


def main() -> None:
    from answering.client import BudgetedClient
    from exam.questions import EXAM_STEP
    from policies import triggered_run
    from policies.engine import run_policy
    from policies.run import policy_named

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slices", nargs="+", help='"period/persona[:through]"')
    parser.add_argument("--policies", nargs="+", required=True)
    parser.add_argument("--stretches", action="store_true", help="also count by stretch of 210 sessions")
    parser.add_argument("--quiet", action="store_true", help="tables only, without one block per answer")
    parser.add_argument("--check-cache", action="store_true", help="cap $0: stop at the first call not in the cache")
    arguments = parser.parse_args()
    client = BudgetedClient("p6a", 0.0)
    by_policy: dict[str, Counter] = {}
    by_stretch: dict[str, Counter] = {}
    marked: dict[str, Counter] = {}
    roots: dict[str, Counter] = {}
    for spec in arguments.slices:
        period, persona_name, through = triggered_run.slice_of(spec)
        for name in arguments.policies:
            run = run_policy(policy_named(name, "p5", 0.0), period, persona_name, client, EXAM_STEP, through)
            diagnoses = diagnose_run(run)
            by_policy[name] = Counter(diagnosis.cause for diagnosis in diagnoses)
            roots[name] = Counter(cause for cause, _ in {(diagnosis.cause, root(diagnosis)) for diagnosis in diagnoses})
            marked[name] = Counter(diagnosis.cause for diagnosis in diagnoses if diagnosis.marked)
            for diagnosis in diagnoses:
                by_stretch.setdefault(f"{name} {stretch(diagnosis.wrong.question.session_id, len(run.steps))}", Counter())[diagnosis.cause] += 1
            if not arguments.quiet:
                print(f"## {name} on {spec}: {len(diagnoses)} invented\n")
                for diagnosis in diagnoses:
                    print(describe(diagnosis) + "\n")
    print("## Invented answers by cause and policy\n")
    print(table(by_policy, list(by_policy)) + "\n")
    print("## Distinct roots: one entry or fact of the notes or the truth, however many exams it spoils\n")
    print(table(roots, list(roots)) + "\n")
    print("## Of those, marked by exam.unreachable\n")
    print(table(marked, list(marked)) + "\n")
    if arguments.stretches:
        print("## By stretch of sessions\n")
        print(table(by_stretch, sorted(by_stretch)) + "\n")


if __name__ == "__main__":
    main()
