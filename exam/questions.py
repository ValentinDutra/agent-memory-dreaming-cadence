"""Which questions the exam asks, and after which sessions. The exam depends only on (period, persona)."""

import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from functools import cache

from exam.schema import DOMAINS, Question, fact_states
from truth.changes import MEMORA_ROOT, extract_changes, load_sessions, personas
from truth.timeline import FactId, Timeline, build_timeline

EXAM_SEED = 20261112

# Sessions between two exams. 7 shares no factor with the fixed dreaming cadences 5, 20 and 50,
# so the exams fall on every phase of each dreaming cycle instead of always right after a dream.
EXAM_STEP = 7

# Stable facts are asked in two strata of sessions since their last change. From 50 on, every fixed cadence
# has dreamt at least once since then, so the answer is a control: did dreaming keep a good note intact?
# Below 50, cadences 20 and 50 differ in whether the note has caught up yet.
STABLE_CONTROL_AGE = 50

# Questions per domain and exam, at most. "stable" is per stratum.
QUOTA = {"recent_change": 2, "new": 1, "stable": 1, "never_existed": 1, "aggregate": 1}

FIXED_CADENCES = (5, 20, 50)

METADATA = MEMORA_ROOT / "data_generation" / "meta_data"

DOCUMENT_TITLE_FIELD = {
    "project_proposal": "project_title",
    "email_writeup": "email_purpose",
    "meeting_notes": "meeting_title",
    "social_media_post": "main_message",
}

DOCUMENT_KIND = {
    "project_proposal": "project proposal",
    "email_writeup": "email about",
    "meeting_notes": "meeting notes",
    "social_media_post": "social media post about",
}

PREFERENCE_LABEL = {
    ("movies", "genres"): "movie genre",
    ("movies", "actors"): "movie actor",
    ("movies", "directors"): "movie director",
    ("movies", "already_watched_list"): "movie the user has watched",
    ("books", "authors"): "book author",
    ("books", "topics"): "book topic",
    ("books", "already_read_list"): "book the user has read",
    ("music", "genres"): "music genre",
    ("music", "artists"): "music artist",
    ("music", "decades"): "music decade",
    ("music", "already_listened_list"): "music the user has listened to",
    ("travel", "destination_types"): "travel destination type",
    ("travel", "regions"): "travel region",
    ("travel", "climates"): "travel climate",
    ("travel", "already_visited_list"): "place the user has visited",
}

YES_NO = ("yes", "no")
LIKE_DISLIKE = ("like", "dislike")


def exam_sessions(period: str, persona: str) -> list[int]:
    return [session["session_id"] for session in load_sessions(period, persona) if session["session_id"] % EXAM_STEP == 0]


def build_exam(period: str, persona: str) -> list[Question]:
    sessions = load_sessions(period, persona)
    changes = [change for session in sessions for change in extract_changes(session)]
    persona_data = PersonaData(
        period=period,
        persona=persona,
        timeline=build_timeline(changes),
        session_dates={session["session_id"]: session["date"] for session in sessions},
        rescheduled={(change.domain, change.key): change.session_id for change in reversed(changes) if change.domain == "calendar" and change.action == "update"},
        conversation_text=" ".join(turn["message"] for session in sessions for turn in session["conversation"]).casefold(),
    )
    exam_session_ids = [session_id for session_id in persona_data.session_dates if session_id % EXAM_STEP == 0]
    questions = []
    previous_exam = 0
    for session_id in exam_session_ids:
        questions += exam_at(persona_data, previous_exam, session_id)
        previous_exam = session_id
    return questions


class PersonaData:
    def __init__(self, period, persona, timeline: Timeline, session_dates, rescheduled, conversation_text):
        self.period = period
        self.persona = persona
        self.timeline = timeline
        self.session_dates = session_dates
        self.rescheduled = rescheduled  # calendar fact -> session of its first reschedule
        self.conversation_text = conversation_text
        self.starts = defaultdict(list)  # fact -> sessions where one of its values starts holding
        for version in timeline.versions:
            self.starts[version.domain, version.key].append(version.valid_from)
        self.mentions = {}

    def last_change(self, fact: FactId, session_id: int) -> int:
        return max(start for start in self.starts[fact] if start <= session_id)

    def date_is_reliable(self, fact: FactId, session_id: int) -> bool:
        """Memora's stored date of a rescheduled event does not match what the user said (P1 defect 1)."""
        return fact not in self.rescheduled or self.rescheduled[fact] > session_id

    def mentioned(self, name: str) -> bool:
        if name not in self.mentions:
            # Memora's lists say "1980s"; the conversations usually say "80s".
            spoken = re.sub(r"^(?:19|20)(\d0s)$", r"\1", name.casefold())
            self.mentions[name] = spoken in self.conversation_text
        return self.mentions[name]


def exam_at(data: PersonaData, previous_exam: int, session_id: int) -> list[Question]:
    rng = random.Random(f"{EXAM_SEED}/{data.period}/{data.persona}/{session_id}")
    before = data.timeline.state_after(previous_exam)
    now = data.timeline.state_after(session_id)
    expenses_per_day_and_type = Counter((value["date"], value["expense_type"]) for (domain, _), value in now.items() if domain == "expense")
    questions = []
    for domain in DOMAINS:
        facts = sorted(fact for fact in before.keys() | now.keys() if fact[0] == domain and askable(fact, now, expenses_per_day_and_type))
        recent_change = [fact for fact in facts if fact in before and before[fact] != now.get(fact) and not is_reschedule(data, fact, now, session_id)]
        new = [fact for fact in facts if fact not in before and fact in now]
        stable = [fact for fact in facts if fact in before and before[fact] == now.get(fact)]
        settling = [fact for fact in stable if session_id - data.last_change(fact, session_id) < STABLE_CONTROL_AGE]
        settled = [fact for fact in stable if fact not in settling]
        for probe, candidates in (("recent_change", recent_change), ("new", new), ("stable", settling), ("stable", settled)):
            for fact in rng.sample(candidates, min(QUOTA[probe], len(candidates))):
                questions.append(fact_question(data, session_id, probe, fact))
        questions += never_existed_questions(data, rng, session_id, domain, now)
        if domain in ("expense", "steps"):
            questions += aggregate_questions(data, session_id, domain)
    return questions


def askable(fact: FactId, now: dict, expenses_per_day_and_type: Counter) -> bool:
    domain, key = fact
    if domain == "content":
        # Scalar fields other than the budget are long prose that never changes.
        return len(key) == 3 or key[1] == "budget"
    if domain == "expense":
        # The agent never sees a session_id, so an expense is named by date and type, which must be unique.
        value = now[fact]
        return expenses_per_day_and_type[value["date"], value["expense_type"]] == 1
    return True


def is_reschedule(data: PersonaData, fact: FactId, now: dict, session_id: int) -> bool:
    return fact[0] == "calendar" and fact in now and not data.date_is_reliable(fact, session_id)


def fact_question(data: PersonaData, session_id: int, probe: str, fact: FactId) -> Question:
    history, current = fact_states(data.timeline, fact, session_id)
    field, answer_format, options, prompt = wording(data, fact, history, current, session_id)
    return question(data, session_id, fact[0], probe, fact, field, answer_format, options, prompt, current, history)


def question(data, session_id, domain, probe, fact, field, answer_format, options, prompt, current, history) -> Question:
    key = "|".join(fact[1]) if fact else "total"
    return Question(
        question_id=f"{data.period}/{data.persona}/s{session_id:03d}/{domain}/{key}",
        period=data.period,
        persona=data.persona,
        session_id=session_id,
        domain=domain,
        probe=probe,
        fact=fact,
        field=field,
        answer_format=answer_format,
        options=options,
        prompt=prompt,
        current=current,
        history=history,
    )


def wording(data: PersonaData, fact: FactId, history, current, session_id: int) -> tuple[str | None, str, tuple[str, ...], str]:
    """(field, answer_format, options, prompt) for one fact."""
    domain, key = fact
    if domain == "preference":
        category, subcategory, item = key
        return "preference", "choice", LIKE_DISLIKE, (
            f"Does the user currently like or dislike '{item}' ({PREFERENCE_LABEL[category, subcategory]})? "
            "Answer like, dislike, or unknown if the user has no current opinion."
        )
    if domain == "todo":
        return None, "choice", YES_NO, f"Is the task '{key[0]}' currently on the user's to-do list? Answer yes, no, or unknown."
    if domain == "calendar":
        if current is not None and data.date_is_reliable(fact, session_id):
            return "event_date", "value", (), f"On what date is the user's event '{key[0]}' scheduled? Answer with a date (YYYY-MM-DD) or unknown."
        return None, "choice", YES_NO, f"Is the event '{key[0]}' currently on the user's calendar? Answer yes, no, or unknown."
    if domain == "goal":
        if key[0] == "daily_steps":
            return "value", "number", (), "What is the user's current daily step goal? Answer with a number or unknown."
        return "value", "number", (), f"What is the user's current weekly budget goal for {key[0]} expenses, in dollars? Answer with a number or unknown."
    if domain == "content":
        document = document_label(data, key[0], session_id)
        if len(key) == 2:
            return "value", "number", (), f"What is the current budget of {document}, in dollars? Answer with a number or unknown."
        return None, "choice", YES_NO, (
            f"Is '{key[2]}' currently one of the {key[1].replace('_', ' ')} of {document}? Answer yes, no, or unknown."
        )
    if domain == "expense":
        value = current or history[-1]
        return "amount", "number", (), (
            f"How much did the user spend on {value['expense_type']} on {value['date']}, in dollars? Answer with a number or unknown."
        )
    if domain == "steps":
        return "step_count", "number", (), f"How many steps did the user log for {key[0]}? Answer with a number or unknown."
    raise ValueError(f"no wording for {fact}")


def document_label(data: PersonaData, document_id: str, session_id: int) -> str:
    kind = document_id.rsplit("_", 1)[0]
    title_fact = ("content", (document_id, DOCUMENT_TITLE_FIELD[kind]))
    _, title = fact_states(data.timeline, title_fact, session_id)
    words = title["value"].split()
    title_text = " ".join(words[:12]) + (" ..." if len(words) > 12 else "")
    return f"the user's {DOCUMENT_KIND[kind]} '{title_text}'"


# --- never_existed ------------------------------------------------------------------------------


def never_existed_questions(data: PersonaData, rng: random.Random, session_id: int, domain: str, now: dict) -> list[Question]:
    candidates = sorted(fact for fact in distractors(data, domain, now) if fact not in data.starts and not data.mentioned(fact[1][-1]))
    questions = []
    for fact in rng.sample(candidates, min(QUOTA["never_existed"], len(candidates))):
        field, answer_format, options, prompt = wording(data, fact, (), None, session_id)
        questions.append(question(data, session_id, domain, "never_existed", fact, field, answer_format, options, prompt, None, ()))
    return questions


def distractors(data: PersonaData, domain: str, now: dict) -> list[FactId]:
    """Plausible facts from the lists Memora's simulator drew this persona's facts from."""
    if domain == "preference":
        archetypes = metadata("preference_metadata.json")["preference_personas"]
        archetype_by_category = metadata("persona_traits.json")["persona_profiles"][data.persona]["category_traits"]["preference_memory"]
        return [
            ("preference", (category, subcategory, item))
            for category, archetype in archetype_by_category.items()
            for subcategory, items in archetypes[category][archetype]["preferences"].items()
            for item in items
        ]
    activities = metadata("activity_metadata.json")["activity_personas"][data.persona]["activity_categories"]
    if domain == "todo":
        return [("todo", (task,)) for tasks in activities["todo_list"].values() for task in tasks]
    if domain == "calendar":
        return [("calendar", (event,)) for event_type in activities["calendar_event"].values() for event in event_type["events"]]
    if domain == "content":
        return content_distractors(data, now)
    return []


@cache
def metadata(name: str) -> dict:
    return json.loads((METADATA / name).read_text())


def content_distractors(data: PersonaData, now: dict) -> list[FactId]:
    """List elements that other personas' documents carry in the same field."""
    elements_by_field = other_personas_elements(data.period, data.persona)
    list_fields = {key[:2] for domain, key in now if domain == "content" and len(key) == 3}
    return [("content", (document_id, field, element)) for document_id, field in list_fields for element in elements_by_field.get(field, ())]


@cache
def other_personas_elements(period: str, persona: str) -> dict[str, frozenset[str]]:
    elements_by_field = defaultdict(set)
    with open(METADATA / f"content_meta_data_{period}.jsonl") as lines:
        for line in lines:
            record = json.loads(line)
            if record["persona"] == persona:
                continue
            for document in record["data"]:
                for field, content in document.items():
                    if isinstance(content, list) and all(isinstance(element, str) for element in content):
                        elements_by_field[field].update(content)
    return {field: frozenset(elements) for field, elements in elements_by_field.items()}


# --- aggregate ----------------------------------------------------------------------------------

AMOUNT_FIELD = {"expense": "amount", "steps": "step_count"}


def aggregate_questions(data: PersonaData, session_id: int, domain: str) -> list[Question]:
    """The running total of the current week, as Memora asks "What is my total food spending this week?"."""
    first_date = date.fromisoformat(min(data.session_dates.values()))
    end = date.fromisoformat(data.session_dates[session_id])
    start = first_date + timedelta(days=7 * ((end - first_date).days // 7))
    items = sorted(
        (version.valid_from, version.value[AMOUNT_FIELD[domain]])
        for version in data.timeline.versions
        if version.domain == domain and version.valid_from <= session_id and start.isoformat() <= item_date(version) <= end.isoformat()
    )
    if not items:
        return []
    totals = []
    running = 0
    for _, amount in items:
        running = round(running + amount, 2)
        totals.append(running)
    history = (None, *(dict(value=total) for total in totals[:-1]))
    if domain == "expense":
        prompt = f"What is the total of the user's food expenses dated from {start} to {end}, in dollars? Answer with a number or unknown."
    else:
        prompt = f"How many steps in total did the user log for the dates from {start} to {end}? Answer with a number or unknown."
    return [question(data, session_id, domain, "aggregate", None, "value", "number", (), prompt, {"value": totals[-1]}, history)]


def item_date(version) -> str:
    return version.value["date"] if version.domain == "expense" else version.key[0]


# --- report -------------------------------------------------------------------------------------


def report(period: str) -> None:
    by_domain_and_probe = Counter()
    by_persona = {}
    lags = {cadence: Counter() for cadence in FIXED_CADENCES}
    disappeared = Counter()
    prompt_characters = 0
    exam_count = 0
    print(f"== {period}: exams every {EXAM_STEP} sessions")
    for persona in personas(period):
        questions = build_exam(period, persona)
        sessions = sorted({question.session_id for question in questions})
        exam_count += len(sessions)
        by_persona[persona] = (len(sessions), Counter(question.domain for question in questions))
        by_domain_and_probe.update((question.domain, question.probe) for question in questions)
        disappeared.update(question.domain for question in questions if question.probe == "recent_change" and question.current is None)
        prompt_characters += sum(len(question.prompt) for question in questions)
        for cadence in FIXED_CADENCES:
            lags[cadence].update(session_id % cadence for session_id in sessions)
    probes = ("recent_change", "new", "stable", "never_existed", "aggregate")
    print(f"  {'domain':<12}" + "".join(f"{probe:>15}" for probe in probes) + f"{'total':>8}")
    for domain in DOMAINS:
        counts = [by_domain_and_probe[domain, probe] for probe in probes]
        print(f"  {domain:<12}" + "".join(f"{count:>15}" for count in counts) + f"{sum(counts):>8}")
    print("  recent_change that disappeared (the rest changed value): " + ", ".join(f"{domain} {disappeared[domain]}" for domain in DOMAINS))
    total = sum(by_domain_and_probe.values())
    print(f"  total {total} questions in {exam_count} exams, {total / exam_count:.1f} per exam, {prompt_characters / total:.0f} prompt characters per question")
    print("  by persona: exams, questions by domain")
    for persona, (exams, domains) in by_persona.items():
        print(f"    {persona:<22} {exams:>3}  {sum(domains.values()):>5}  {dict(sorted(domains.items()))}")
    print("  sessions since the last dream at exam time (dream after session N when N % cadence == 0)")
    for cadence, counter in lags.items():
        exams = sum(counter.values())
        mean = sum(lag * count for lag, count in counter.items()) / exams
        histogram = " ".join(f"{lag}:{counter[lag]}" for lag in range(cadence))
        print(f"    cadence {cadence:>2}: mean {mean:5.2f} (uniform {(cadence - 1) / 2:5.2f}), lags hit {len(counter)}/{cadence}  {histogram}")


if __name__ == "__main__":
    for period in sys.argv[1:]:
        report(period)
