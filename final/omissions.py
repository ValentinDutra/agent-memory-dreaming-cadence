"""What the dreams of P7's grid leave out, and how many exam answers each omission costs, from P7a's cache with a cap of $0. Owner: P8a.

  PYTHONHASHSEED=0 uv run python -m final.omissions measure
  PYTHONHASHSEED=0 uv run python -m final.omissions report > results/p8a/report.txt
  PYTHONHASHSEED=0 uv run python -m final.omissions estimate

measure: walks every dream of triggered-phrases-any and every-1, repetitions 0 and 1, 10 personas, s1-210, compares the
notes after it with the truth line by line (dreaming.quality.compare_notes) and writes results/p8a/: encounters.csv,
episodes.csv, answers.csv (every unmarked wrong answer), runs.csv and cases.txt (each omission of a fact the user said,
with the turns that say it and the dream's reply).
report: the tables of docs/p8a-omisiones.md, from those files.
estimate: what P8b costs with final.grid's cost model, calling nothing.

An encounter is a fact the sessions a dream read added, changed or removed. An episode starts at a dream that leaves a
fact wrong in the notes and ends at the first later dream that gets it right, or when Memora changes the fact again:
- omitted: the dream read the fact's addition or change, and the notes after it do not hold the new value;
- lost: the fact was right after the previous dream, nothing changed it, and the notes after this dream do not hold it;
- removal kept: the dream read the fact's removal, and a line about it is still in the notes.
An episode costs the exam answers about its fact that are wrong while it lasts, and for an expense or a step count, a
share of the wrong totals whose range holds its date (a total wrong while two episodes cover it counts half to each).
Marked questions (exam.unreachable) never count.
"""

import argparse
import csv
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, fields
from datetime import date

from answering.client import INPUT_PRICE, RESULTS, BudgetedClient
from dreaming import dream, dream_named, quality
from dreaming.transcripts import load_transcripts
from exam.questions import item_date
from exam.unreachable import relative_dated_expenses, session_text, unreachable
from final.grid import DATA, PERIOD, THROUGH, Estimator
from final.repetitions import BUDGET_NAME, REPETITIONS, note_state
from policies.engine import PolicyRun, run_policy
from policies.run import policy_named
from truth.changes import persona_changes, personas
from truth.timeline import build_timeline, fact_mention, text_support

POLICIES = ("triggered-phrases-any", "every-1")
OUTPUT = RESULTS / "p8a"
# What the conversation says right after a fact, read from the user's turns: "taken back", "said done", "other weekday"
# or "plain". Memora's simulated user sometimes takes back what they just said, and the answer key keeps the fact anyway.
TAKEN_BACK = re.compile(r"not what i meant|general (?:statement|comment)|just making a|just saying|never mind", re.IGNORECASE)
SAID_DONE = re.compile(r"\b(?:went|going) (?:well|great|fine)\b|\balready (?:did|done)\b", re.IGNORECASE)
WEEKDAYS = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE)


@dataclass
class Encounter:
    persona: str
    policy: str
    repetition: int
    dream: int
    sessions_read: int
    notes_characters: int  # of the notes the dream read
    window_facts: int      # facts the sessions it read added, changed or removed
    domain: str
    fact: str
    change_session: int
    encounter: str         # first (the fact did not hold before the window), change, or removal
    # Decided from the truth and the transcript, never from a model: "said" when the session that brought the fact says
    # all its words; "not said" (an item in Memora's words); "like to dislike" ("not into it anymore": the dream's rule
    # deletes the like, Memora records a dislike, P4a §4.2); "relative date" (exam.unreachable's "last night" expenses).
    reason: str
    follow_up: str         # see TAKEN_BACK
    outcome: str           # compare_notes after the dream; for a removal, "deleted" or "kept"
    shared: bool           # triggered-phrases-any only: every-1 made the same request (same window, same notes)


@dataclass
class Episode:
    persona: str
    policy: str
    repetition: int
    kind: str
    encounter: str
    domain: str
    fact: str
    reason: str
    follow_up: str
    dream: int
    sessions_read: int
    notes_characters: int
    window_facts: int
    outcome: str
    change_session: int    # the session whose change the dream read; 0 for a lost fact
    written: str           # omitted: what the notes after the dream hold instead (see written_instead)
    end: str               # "recovered", "changed again" or "open at s210"
    end_session: int       # the dream that recovered it, Memora's next change, or 211
    answers: int           # wrong answers about the fact while the episode lasts
    total_answers: float   # its share of the wrong totals while it lasts
    shared: bool


# --- measure ------------------------------------------------------------------------------------------------------


class DreamRecorder:
    """Stands between run_policy and a client with a cap of $0, and keeps the text of every dream in order."""

    def __init__(self):
        self.client = BudgetedClient(BUDGET_NAME, 0.0)
        self.thinking, self.effort = self.client.thinking, self.client.effort
        self.dreams = []

    def complete(self, run: str, system: str, user: str, max_tokens: int, repeat: int = 0):
        completion = self.client.complete(run, system, user, max_tokens, repeat=repeat)
        if "/dream/" in run:
            self.dreams.append(completion.text)
        return completion


def cached_run(persona: str, policy: str, repetition: int, dream_function=dream.dream, cache_prefix: str = "p5") -> tuple[PolicyRun, dict[int, str]]:
    """A grid run from the cache, and the reply of the dream after each session that dreamt. Raises BudgetExceeded if a call is missing."""
    recorder = DreamRecorder()
    run = run_policy(policy_named(policy, BUDGET_NAME, 0.0), PERIOD, persona, recorder, through=THROUGH, repetition=repetition,
                     dream_function=dream_function, cache_prefix=cache_prefix)
    dream_sessions = [step.session_id for step in run.steps if step.dreamt]
    return run, dict(zip(dream_sessions, recorder.dreams, strict=True))


def fact_label(fact) -> str:
    domain, key = fact
    return f"{domain}: " + " | ".join(key)


def reason_of(fact, before: dict, after: dict, change, session, shifted: set) -> str:
    if fact[0] == "preference" and before.get(fact) == {"preference": "like"} and after.get(fact) == {"preference": "dislike"}:
        return "like to dislike"
    if fact[0] == "expense" and (fact, change.session_id) in shifted:
        return "relative date"
    return "said" if text_support(fact_mention(change), session_text(session)) == "full" else "not said"


def names_fact(parsed: quality.ParsedNotes, fact, value: dict) -> list[str]:
    """Note lines in the fact's domain whose name is like the fact's, as compare_notes matches them."""
    domain, key = fact
    name = quality.fact_name(domain, key, value)
    return [line.line for line in parsed.facts if line.domain == domain and quality.similarity(line.name, name, looser=domain == "content")]


def written_instead(parsed: quality.ParsedNotes, fact, value: dict) -> str:
    """What the notes hold in place of a fact compare_notes does not find right, as "<how> | <line>"."""
    domain, key = fact
    if domain in ("expense", "steps"):
        # Two expenses of one day share three of their four name stems, so an expense is found by its amount.
        amount = quality.projected_value(domain, value)
        same_amount = [line.line for line in parsed.facts if line.domain == domain and line.value == amount]
        return f"same amount, other date | {same_amount[0].strip()}" if same_amount else "nothing"
    same_name = names_fact(parsed, fact, value)
    if same_name:
        return f"same name | {same_name[0].strip()}"
    name_stems = quality.stems(quality.fact_name(domain, key, value))
    shares = [(len(name_stems & quality.stems(line.name)) / len(name_stems), line.line) for line in parsed.facts if line.domain == domain and name_stems]
    share, line = max(shares, default=(0.0, ""))
    return f"other words | {line.strip()}" if share >= 0.5 else "nothing"


def follow_up(session, mention: str) -> str:
    """How the session goes on after the user's first turn that names the fact: "taken back", "said done", "other weekday" or "plain"."""
    turns = list(session.turns)
    first = next((index for index, turn in enumerate(turns) if turn.speaker == "user_agent" and text_support(mention, turn.message) != "absent"), None)
    if first is None:
        return "plain"
    later_user_turns = [turn.message for turn in turns[first + 1:first + 3] if turn.speaker == "user_agent"]
    if any(TAKEN_BACK.search(message) for message in later_user_turns):
        return "taken back"
    if any(SAID_DONE.search(message) for message in later_user_turns):
        return "said done"
    weekday = date.fromisoformat(session.date).strftime("%A").casefold()
    if any(named.casefold() != weekday for named in WEEKDAYS.findall(turns[first].message)):
        return "other weekday"
    return "plain"


def context(session, mention: str) -> list[str]:
    """The turns of the session that name the fact, each with the two turns after it."""
    turns = list(session.turns)
    shown = []
    for index, turn in enumerate(turns):
        if turn.speaker == "user_agent" and text_support(mention, turn.message) != "absent":
            shown += [f"{'User' if each.speaker == 'user_agent' else 'Assistant'}: {each.message}" for each in turns[index:index + 3]]
    return list(dict.fromkeys(shown))


def walk(run: PolicyRun, dream_replies: dict[int, str], every_one_requests: set) -> tuple[list[Encounter], list[Episode], list[dict], list[str]]:
    """The encounters, episodes, unmarked wrong answers and printed cases of one run.
    every_one_requests: (previous dream, dream, notes read) of every-1's dreams."""
    changes = persona_changes(run.period, run.persona)
    timeline = build_timeline(changes)
    sessions = {session.session_id: session for session in load_transcripts(run.period, run.persona)}
    shifted = relative_dated_expenses(timeline, sessions)
    changes_by_fact = defaultdict(list)
    for change in changes:
        changes_by_fact[change.domain, change.key].append(change)
    last_dream, notes_read, previous_outcomes = 0, "", {}
    encounters, episodes, open_episodes, cases = [], [], {}, []
    removed_values = {}  # fact -> the value a removal took away, to find the lines still about it
    for step in run.steps:
        if not step.dreamt:
            continue
        comparison = quality.compare_notes(step.notes, timeline, step.session_id)
        parsed = quality.parse_notes(step.notes)
        before, after = timeline.state_after(last_dream), timeline.state_after(step.session_id)
        changed = {fact for fact in before.keys() | after.keys() if before.get(fact) != after.get(fact) and not quality.is_title_or_prose(*fact)}
        shared = run.policy != "every-1" and (last_dream, step.session_id, notes_read) in every_one_requests
        for fact, episode in list(open_episodes.items()):
            if fact in changed:
                episode.end = "changed again"
                episode.end_session = next(change.session_id for change in changes_by_fact[fact] if change.session_id > episode.dream)
            elif (comparison.fact_outcomes.get(fact, ("",))[0] == "correct") if fact in after else not names_fact(parsed, fact, removed_values[fact]):
                episode.end, episode.end_session = "recovered", step.session_id
            else:
                continue
            del open_episodes[fact]

        def start(kind: str, fact, change_session: int, encounter: str, reason: str, follow: str, outcome: str, written: str) -> Episode:
            episode = Episode(run.persona, run.policy, run.repetition, kind, encounter, fact[0], fact_label(fact), reason, follow, step.session_id,
                              step.sessions_read, len(notes_read), len(changed), outcome, change_session, written, "open at s210", 211, 0, 0.0, shared)
            episodes.append(episode)
            open_episodes[fact] = episode
            return episode

        for fact in sorted(changed):
            change = [change for change in changes_by_fact[fact] if last_dream < change.session_id <= step.session_id][-1]
            follow = follow_up(sessions[change.session_id], fact_mention(change))
            if fact in after:
                encounter = "first" if fact not in before else "change"
                reason = reason_of(fact, before, after, change, sessions[change.session_id], shifted)
                outcome = comparison.fact_outcomes[fact][0]
                if outcome != "correct":
                    episode = start("omitted", fact, change.session_id, encounter, reason, follow, outcome, written_instead(parsed, fact, after[fact]))
                    if reason == "said":
                        cases.append((episode, context(sessions[change.session_id], fact_mention(change)), dream_replies[step.session_id]))
            else:
                encounter, reason = "removal", "said" if text_support(fact_mention(change), session_text(sessions[change.session_id])) == "full" else "not said"
                outcome = "kept" if names_fact(parsed, fact, before[fact]) else "deleted"
                if outcome == "kept":
                    removed_values[fact] = before[fact]
                    start("removal kept", fact, change.session_id, encounter, reason, follow, outcome, "")
            encounters.append(Encounter(run.persona, run.policy, run.repetition, step.session_id, step.sessions_read, len(notes_read), len(changed),
                                        fact[0], fact_label(fact), change.session_id, encounter, reason, follow, outcome, shared))
        for fact, (outcome, _) in comparison.fact_outcomes.items():
            if fact not in changed and fact not in open_episodes and previous_outcomes.get(fact) == "correct" and outcome != "correct":
                start("lost", fact, 0, "-", "-", "-", outcome, written_instead(parsed, fact, after[fact]))
        last_dream, notes_read = step.session_id, step.notes
        previous_outcomes = {fact: outcome for fact, (outcome, _) in comparison.fact_outcomes.items()}
    answers = charge(run, episodes, timeline)
    printed = [describe(episode, turns, reply) for episode, turns, reply in cases]
    return encounters, episodes, answers, printed


def describe(episode: Episode, turns: list[str], reply: str) -> str:
    lines = [f"### {episode.persona} {episode.policy} r{episode.repetition}, dream after s{episode.dream} (read {episode.sessions_read}): {episode.fact}",
             f"- {episode.encounter}, said in s{episode.change_session} ({episode.follow_up}); after the dream: {episode.outcome}; notes hold: {episode.written}; "
             f"{episode.end} s{episode.end_session}; answers lost {cost(episode):.1f}"]
    lines += [f"  > {turn}" for turn in turns]
    lines.append("- the dream's reply: " + " ".join(reply.split())[:500])
    return "\n".join(lines)


def charge(run: PolicyRun, episodes: list[Episode], timeline) -> list[dict]:
    """Give each episode the unmarked wrong answers it explains; return every unmarked wrong answer with what explains it
    and how the notes the exam read hold what it asks (final.repetitions.note_state)."""
    marked = unreachable(run.period, run.persona)
    steps = {step.session_id: step for step in run.steps}
    dated = {}
    for version in timeline.versions:
        if version.domain in ("expense", "steps"):
            dated[fact_label((version.domain, version.key))] = item_date(version)
    answers = []
    for exam in run.exams:
        active = [episode for episode in episodes if episode.dream <= exam.session_id < episode.end_session]
        notes = steps[exam.session_id].notes
        comparison, state = None, None
        for question, grade in zip(exam.questions, exam.grades, strict=True):
            if grade.outcome == "correct" or question.question_id in marked:
                continue
            if question.fact is not None:
                explaining = [episode for episode in active if episode.fact == fact_label(question.fact)]
                for episode in explaining:
                    episode.answers += 1
            else:
                start, end = re.findall(r"\d{4}-\d{2}-\d{2}", question.prompt)[:2]
                explaining = [episode for episode in active if episode.domain == question.domain and episode.kind != "removal kept"
                              and start <= dated.get(episode.fact, "") <= end]
                for episode in explaining:
                    episode.total_answers += 1 / len(explaining)
            if comparison is None:
                comparison, state = quality.compare_notes(notes, timeline, exam.session_id), timeline.state_after(exam.session_id)
            answers.append({
                "persona": run.persona, "policy": run.policy, "repetition": run.repetition, "session": exam.session_id,
                "question": question.question_id, "domain": question.domain, "probe": question.probe, "outcome": grade.outcome,
                "explained": explaining[0].kind if explaining else "", "notes": note_state(question, notes, comparison, state),
            })
    return answers


def measure() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    encounters, episodes, answers, runs, cases = [], [], [], [], []
    for persona in personas(PERIOD):
        for repetition in REPETITIONS:
            every_one_requests = set()
            for policy in reversed(POLICIES):
                run, dream_replies = cached_run(persona, policy, repetition)
                if policy == "every-1":
                    notes_read = ""
                    for step in run.steps:
                        every_one_requests.add((step.session_id - 1, step.session_id, notes_read))
                        notes_read = step.notes
                run_encounters, run_episodes, run_answers, run_cases = walk(run, dream_replies, every_one_requests)
                encounters += run_encounters
                episodes += run_episodes
                answers += run_answers
                cases += run_cases
                asked = sum(question.question_id not in unreachable(PERIOD, persona) for exam in run.exams for question in exam.questions)
                runs.append({"persona": persona, "policy": policy, "repetition": repetition, "asked": asked, "wrong": len(run_answers)})
                print(f"{persona} {policy} r{repetition}: {len(run_encounters)} encounters, {len(run_episodes)} episodes, {len(run_answers)} unmarked wrong answers", flush=True)
    write(OUTPUT / "encounters.csv", [asdict(encounter) for encounter in encounters])
    write(OUTPUT / "episodes.csv", [asdict(episode) for episode in episodes])
    write(OUTPUT / "answers.csv", answers)
    write(OUTPUT / "runs.csv", runs)
    (OUTPUT / "cases.txt").write_text("\n\n".join(cases) + "\n")


def write(path, rows: list[dict]) -> None:
    columns = list(dict.fromkeys(column for row in rows for column in row))
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, restval=0)
        writer.writeheader()
        writer.writerows(rows)


# --- report -------------------------------------------------------------------------------------------------------


def read(name: str, record) -> list:
    types = {field.name: field.type for field in fields(record)} if record else {}
    def typed(column: str, value: str):
        kind = types.get(column, int if value.lstrip("-").isdigit() else str)
        return value == "True" if kind is bool else kind(value)
    with (OUTPUT / name).open(newline="") as file:
        rows = [{column: typed(column, value) for column, value in row.items()} for row in csv.DictReader(file)]
    return [record(**row) for row in rows] if record else rows


def cost(episode: Episode) -> float:
    return episode.answers + episode.total_answers


def table(header: list[str], rows: list[list]) -> None:
    print("| " + " | ".join(header) + " |\n| --- |" + " --: |" * (len(header) - 1))
    for row in rows:
        print("| " + " | ".join(f"{cell:.1f}" if isinstance(cell, float) else str(cell) for cell in row) + " |")
    print()


def cause(episode: Episode) -> str:
    """Who an episode belongs to: the dream, Memora's answer key, or the dream's rule for a like that ends."""
    if episode.kind != "omitted":
        return episode.kind
    if episode.reason in ("not said", "relative date", "like to dislike"):
        return f"omitted, {episode.reason}"
    return "omitted, said, plain" if episode.follow_up == "plain" else "omitted, said, Memora takes it back"


CAUSES = ("omitted, said, plain", "omitted, said, Memora takes it back", "omitted, like to dislike", "omitted, relative date", "omitted, not said", "removal kept", "lost")
# Lists the dream's rules name ("key points, recipients, attendees..."), by the words of Memora's field names.
NAMED_LISTS = ("key_points", "recipient", "attendee", "agenda", "decision", "action", "objective", "stakeholder", "deliverable", "metric", "hashtag")
LEAVING = re.compile(r"(?:need|have) to (?:go|run|get going|head out|step|get back|leave|sign off|wrap up)\b", re.IGNORECASE)
DOCUMENT_EDIT = re.compile(r"(?:need|have) to (?:update|remove|add|delete|change|revise|include|adjust|modify)\b", re.IGNORECASE)
TASK_PHRASES = re.compile(r"\bi(?:'m| am)?(?: really| actually| also| still| just)* (?:need to|have to|'ve been meaning to|been meaning to|trying to)\b", re.IGNORECASE)


def list_kind(fact: str) -> str:
    parts = fact.split(" | ")
    if len(parts) == 2:
        return "budget"
    return "named in the rules" if any(word in parts[1] for word in NAMED_LISTS) else "not named"


def aimed_at(episode: Episode) -> bool:
    return episode.domain in ("todo", "preference") or (episode.domain == "content" and list_kind(episode.fact) == "not named")


def rate_rows(encounters: list[Encounter], key) -> list[list]:
    groups = defaultdict(list)
    for encounter in encounters:
        groups[encounter.policy, key(encounter)].append(encounter)
    rows = []
    for (policy, value), group in sorted(groups.items(), key=lambda item: (item[0][0], sort_key(item[0][1]))):
        left_out = sum(encounter.outcome != "correct" for encounter in group)
        rows.append([policy, value, len(group), left_out, f"{left_out / len(group):.2%}"])
    return rows


def report() -> None:
    episodes, encounters, runs, answers = read("episodes.csv", Episode), read("encounters.csv", Encounter), read("runs.csv", None), read("answers.csv", None)
    print("## 1. Unmarked wrong answers per policy and repetition, and what explains them\n")
    rows = []
    for policy in POLICIES:
        for repetition in REPETITIONS:
            run_rows = [row for row in runs if row["policy"] == policy and row["repetition"] == repetition]
            wrong = sum(row["wrong"] for row in run_rows)
            explained = [sum(cost(episode) for episode in episodes if episode.policy == policy and episode.repetition == repetition and cause(episode) == name) for name in CAUSES]
            rows.append([policy, repetition, sum(row["asked"] for row in run_rows), wrong, *explained, wrong - sum(explained)])
    rows.append(["all", "both", *(sum(row[column] for row in rows) for column in range(2, 4 + len(CAUSES) + 1))])
    table(["policy", "rep", "unmarked asked", "wrong", *CAUSES, "no episode"], rows)
    unexplained = Counter(answer["notes"] for answer in answers if not answer["explained"])
    print("Wrong answers with no episode, by how the notes the exam read hold what the question asks: "
          + ", ".join(f"{state} {count}" for state, count in unexplained.most_common()) + "\n")

    print("## 2. Episodes by cause (both policies, both repetitions)\n")
    groups = defaultdict(list)
    for episode in episodes:
        groups[cause(episode), episode.domain].append(episode)
    table(["cause", "domain", "episodes", "costing anything", "answers about the fact", "share of totals", "answers lost"],
          [[*key, len(group), sum(cost(episode) > 0 for episode in group), sum(episode.answers for episode in group), sum(episode.total_answers for episode in group),
            sum(cost(episode) for episode in group)] for key, group in sorted(groups.items(), key=lambda item: (CAUSES.index(item[0][0]), -sum(cost(episode) for episode in item[1])))])

    said_encounters = [encounter for encounter in encounters if encounter.reason == "said" and encounter.encounter != "removal"]
    print("## 3. Facts the session said: share left out, by what the conversation says right after (both policies, both repetitions)\n")
    groups = defaultdict(list)
    for encounter in said_encounters:
        groups[encounter.domain, encounter.follow_up].append(encounter)
    said = [episode for episode in episodes if episode.kind == "omitted" and episode.reason == "said"]
    table(["domain", "after the fact", "encounters", "left out", "rate", "answers lost"],
          [[domain, follow, len(group), sum(encounter.outcome != "correct" for encounter in group), f"{sum(encounter.outcome != 'correct' for encounter in group) / len(group):.1%}",
            sum(cost(episode) for episode in said if episode.domain == domain and episode.follow_up == follow)]
           for (domain, follow), group in sorted(groups.items())])

    taken_back = defaultdict(float)
    for episode in said:
        if episode.follow_up != "plain":
            taken_back[episode.persona, episode.fact, episode.follow_up] += cost(episode)
    print("Facts the conversation takes back right after (answers lost in the 4 runs): " + "; ".join(
        f"{persona} {fact} ({follow}) {lost:.1f}" for (persona, fact, follow), lost in sorted(taken_back.items(), key=lambda item: -item[1])) + "\n")

    plain_encounters = [encounter for encounter in said_encounters if encounter.follow_up == "plain"]
    plain = [episode for episode in said if episode.follow_up == "plain"]
    print("## 4. Plain omissions (said, not taken back): share left out per encounter\n")
    for title, key, chosen in (
        ("domain", lambda encounter: encounter.domain, plain_encounters),
        ("encounter", lambda encounter: encounter.encounter, plain_encounters),
        ("sessions read", lambda encounter: bucket(encounter.sessions_read, (1, 3, 6)), plain_encounters),
        ("facts in the window", lambda encounter: bucket(encounter.window_facts, (1, 5, 10, 20)), plain_encounters),
        ("notes characters read", lambda encounter: bucket(encounter.notes_characters, (0, 2000, 5000, 8000)), plain_encounters),
        ("document list", lambda encounter: list_kind(encounter.fact), [encounter for encounter in plain_encounters if encounter.domain == "content"]),
    ):
        print(f"### by {title}\n")
        table(["policy", title, "encounters", "left out", "rate"], rate_rows(chosen, key))
    wide = [encounter for encounter in plain_encounters if encounter.window_facts > 10]
    print("Plain encounters in windows of more than 10 facts, by domain: " + ", ".join(f"{domain} {count}" for domain, count in Counter(encounter.domain for encounter in wide).most_common())
          + "; left out: " + ", ".join(f"{domain} {count}" for domain, count in Counter(encounter.domain for encounter in wide if encounter.outcome != "correct").most_common()))
    print("Plain omissions of document items, answers lost by list: " + ", ".join(
        f"{kind} {sum(cost(episode) for episode in plain if episode.domain == 'content' and list_kind(episode.fact) == kind):.1f}"
        for kind in ("named in the rules", "not named", "budget")))
    print("Plain omissions by what the notes hold instead: " + ", ".join(
        f"{how} {count} ({sum(cost(episode) for episode in plain if episode.written.split(' | ')[0] == how):.1f} answers)"
        for how, count in Counter(episode.written.split(" | ")[0] for episode in plain).most_common()) + "\n")

    print("Answers lost by the plain omissions the named dream's rules aim at (to-dos, likes and dislikes, document lists the rules do not name), per run:")
    for policy in POLICIES:
        for repetition in REPETITIONS:
            aimed = [episode for episode in plain if episode.policy == policy and episode.repetition == repetition and aimed_at(episode)]
            print(f"- {policy} r{repetition}: {sum(cost(episode) for episode in aimed):.1f} answers, {len(aimed)} episodes")
    print()

    print("## 5. Plain omissions: random or systematic\n")
    left_out = {(encounter.persona, encounter.policy, encounter.fact, encounter.change_session, encounter.repetition)
                for encounter in plain_encounters if encounter.outcome != "correct"}
    for policy in POLICIES:
        first = [key for key in left_out if key[1] == policy and key[4] == 0]
        again = sum((*key[:4], 1) in left_out for key in first)
        second = [key for key in left_out if key[1] == policy and key[4] == 1]
        new_in_second = sum((*key[:4], 0) not in left_out for key in second)
        print(f"- {policy}: of the {len(first)} plain omissions of r0, r1 leaves out the same fact in the same dream {again} times ({again / len(first):.0%}); "
              f"r1 leaves out {new_in_second} facts r0 wrote")
    by_fact = defaultdict(set)
    for key in left_out:
        by_fact[key[0], key[2], key[3]].add(key[4])
    both = sum(cost(episode) for episode in plain if len(by_fact[episode.persona, episode.fact, episode.change_session]) == 2)
    print(f"- answers lost by plain omissions of a fact left out in both repetitions (by either policy): {both:.1f} of {sum(cost(episode) for episode in plain):.1f}")
    for domain in ("todo", "content", "preference", "expense"):
        group = [episode for episode in plain if episode.domain == domain]
        in_both = sum(cost(episode) for episode in group if len(by_fact[episode.persona, episode.fact, episode.change_session]) == 2)
        print(f"  - {domain}: {in_both:.1f} of {sum(cost(episode) for episode in group):.1f}")
    print()

    print("## 6. Omissions of facts the session said: how long they last\n")
    for end in ("recovered", "changed again", "open at s210"):
        group = [episode for episode in said if episode.end == end]
        lengths = [episode.end_session - episode.dream for episode in group]
        print(f"- {end}: {len(group)} episodes, {sum(cost(episode) for episode in group):.1f} answers lost; sessions until the end, median "
              f"{statistics.median(lengths) if lengths else 0:.0f}, max {max(lengths, default=0)}")
    ranked = sorted((cost(episode) for episode in said), reverse=True)
    total = sum(ranked)
    print(f"- concentration: the 10 costliest of {len(ranked)} episodes lose {sum(ranked[:10]):.1f} of {total:.1f} answers ({sum(ranked[:10]) / total:.0%}); "
          f"the 30 costliest {sum(ranked[:30]):.1f} ({sum(ranked[:30]) / total:.0%}); episodes costing nothing: {sum(value == 0 for value in ranked)}")
    print(f"- triggered-phrases-any omissions in a dream every-1 made too (same request): {sum(episode.shared for episode in said if episode.policy != 'every-1')} of "
          f"{sum(episode.policy != 'every-1' for episode in said)}\n")

    print("## 7. The costliest omissions of facts the session said\n")
    table(["persona", "policy", "rep", "dream", "read", "notes chars", "fact", "after the fact", "notes hold", "end", "answers lost"],
          [[episode.persona, episode.policy, episode.repetition, f"s{episode.dream}", episode.sessions_read, episode.notes_characters, episode.fact[:60],
            episode.follow_up, episode.written.replace(" | ", ": ")[:60], f"{episode.end} s{episode.end_session}", cost(episode)]
           for episode in sorted(said, key=cost, reverse=True)[:16]])

    print("## 8. User turns s1-210 that say \"I need to / have to / am trying to / have been meaning to\"\n")
    counts, sessions_with_one, caught = Counter(), 0, 0
    plain_tasks = {(episode.persona, episode.change_session, episode.fact.split(": ", 1)[1]) for episode in plain if episode.domain == "todo"}
    for persona in personas(PERIOD):
        transcripts = {session.session_id: session for session in load_transcripts(PERIOD, persona)}
        caught += sum(any(turn.speaker == "user_agent" and TASK_PHRASES.search(turn.message) and text_support(name, turn.message) != "absent" for turn in transcripts[session_id].turns)
                      for each, session_id, name in plain_tasks if each == persona)
        sessions_with_one += sum(any(turn.speaker == "user_agent" and TASK_PHRASES.search(turn.message) for turn in session.turns)
                                 for session_id, session in transcripts.items() if session_id <= THROUGH)
        task_names = defaultdict(list)
        for change in persona_changes(PERIOD, persona):
            if change.domain == "todo" and change.action == "add":
                task_names[change.session_id].append(change.key[0])
        for session in load_transcripts(PERIOD, persona):
            for turn in session.turns:
                if session.session_id > THROUGH or turn.speaker != "user_agent" or not TASK_PHRASES.search(turn.message):
                    continue
                if any(text_support(name, turn.message) != "absent" for name in task_names[session.session_id]):
                    counts["names a task Memora adds in that session"] += 1
                elif LEAVING.search(turn.message):
                    counts["leaving the conversation"] += 1
                elif DOCUMENT_EDIT.search(turn.message):
                    counts["asking to change a document"] += 1
                else:
                    counts["anything else"] += 1
    print(f"- {sum(counts.values())} user turns in the 10 personas: " + ", ".join(f"{name} {count}" for name, count in counts.most_common()))
    print(f"- sessions with at least one: {sessions_with_one} of {THROUGH * len(personas(PERIOD))}")
    print(f"- plain to-do omissions (distinct persona, session and task) whose turn says it that way: {caught} of {len(plain_tasks)}")


def bucket(value: int, edges: tuple[int, ...]) -> str:
    """"1", "2-3", "4-6", "7+" for edges (1, 3, 6); a value at most the first edge gets the first label."""
    low = None
    for edge in edges:
        if value <= edge:
            return str(edge) if low is None or low == edge else f"{low}-{edge}"
        low = edge + 1
    return f"{low}+"


def sort_key(value) -> tuple:
    text = str(value)
    digits = text.split("-")[0].rstrip("+")
    return (0, int(digits)) if digits.isdigit() else (1, text)


# --- estimate -----------------------------------------------------------------------------------------------------

# P4a fitted 0.40 input tokens per character of notes (docs/p4a-entrada-y-salida.md §4.4); the rules are English prose too.
TOKENS_PER_CHARACTER = 0.40
INPUT_DOLLARS_PER_TOKEN = INPUT_PRICE["short"] / 1_000_000


def estimate() -> None:
    """What P8b costs: the named dream with triggered-phrases-any over s1-210 of the 10 personas, one and two repetitions."""
    extra_tokens = TOKENS_PER_CHARACTER * (len(dream_named.RULES) - len(dream.RULES))
    print(f"the named dream's rules are {len(dream_named.RULES) - len(dream.RULES)} characters longer: about {extra_tokens:.0f} input tokens, "
          f"${extra_tokens * INPUT_DOLLARS_PER_TOKEN:.6f} more per dream\n")
    estimator = Estimator()
    print("| repetition | dreams | exams | grid model: dreams $ | exams $ | rules $ | total $ | P7a paid for the same runs with P4a's dream: dreams $ | exams $ | plus rules $ |")
    print("| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    with (DATA / "p7-runs.csv").open(newline="") as file:
        paid = [row for row in csv.DictReader(file) if row["scope"] == "s1-210" and row["policy"] == "triggered-phrases-any"]
    totals = []
    for repetition in REPETITIONS:
        requests = [request for persona in personas(PERIOD) for request in estimator.requests(persona, "triggered-phrases-any", repetition, THROUGH)]
        dreams = [cost for request, cost in requests if request[0] == "dream"]
        exams = [cost for request, cost in requests if request[0] == "exam"]
        rules = len(dreams) * extra_tokens * INPUT_DOLLARS_PER_TOKEN
        rows = [row for row in paid if int(row["repetition"]) == repetition]
        paid_dreams, paid_exams = sum(float(row["dream_cost"]) for row in rows), sum(float(row["exam_cost"]) for row in rows)
        totals.append((sum(dreams) + sum(exams) + rules, paid_dreams + paid_exams + rules))
        print(f"| {repetition} | {len(dreams)} | {len(exams)} | {sum(dreams):.4f} | {sum(exams):.4f} | {rules:.4f} | {totals[-1][0]:.4f} | "
              f"{paid_dreams:.4f} | {paid_exams:.4f} | {totals[-1][1]:.4f} |")
    print(f"\none repetition: grid model ${totals[0][0]:.4f}, from what P7a paid ${totals[0][1]:.4f}; "
          f"two: ${totals[0][0] + totals[1][0]:.4f} and ${totals[0][1] + totals[1][1]:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("measure", "report", "estimate"))
    arguments = parser.parse_args()
    {"measure": measure, "report": report, "estimate": estimate}[arguments.command]()


if __name__ == "__main__":
    main()
