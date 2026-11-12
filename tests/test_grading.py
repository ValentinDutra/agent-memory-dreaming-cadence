from functools import cache

from exam.grading import grade, negates_removed_preference, render
from exam.questions import build_exam
from exam.schema import UNKNOWN, Question, fact_states
from exam.smoke import SYNTHETIC_AGENTS, expected_outcome
from truth.changes import persona_changes
from truth.timeline import Timeline, build_timeline

BONOBO = ("preference", ("music", "artists", "Bonobo"))
DEEP_HOUSE = ("preference", ("music", "genres", "deep house"))
MECHANIC_VISIT = ("calendar", ("Mechanic visit",))


@cache
def timeline(period: str, persona: str) -> Timeline:
    return build_timeline(persona_changes(period, persona))


@cache
def weekly_exam(persona: str) -> list[Question]:
    return build_exam("weekly", persona)


def fact_question(fact, session_id, field, answer_format, options=(), probe="recent_change") -> Question:
    history, current = fact_states(timeline("weekly", "software_engineer"), fact, session_id)
    domain, key = fact
    return Question(
        question_id=f"weekly/software_engineer/s{session_id:03d}/{domain}/{'|'.join(key)}/{field}",
        period="weekly", persona="software_engineer", session_id=session_id, domain=domain, probe=probe,
        fact=fact, field=field, answer_format=answer_format, options=options, prompt="",
        current=current, history=history,
    )


def outcome(question: Question, answer: str | None) -> str:
    return grade(question, answer).outcome


def test_bonobo_after_its_deletion_unknown_is_correct_and_like_is_stale():
    # weekly/software_engineer s30 t12: "I used to really like Bonobo, but I'm just not into his music anymore."
    question = fact_question(BONOBO, 40, "preference", "choice", ("like", "dislike"))

    assert render(question, question.history[-1]) == "like"
    assert [outcome(question, answer) for answer in ["Unknown", "I don't know", None, "Like.", "dislike", "maybe"]] == [
        "correct", "correct", "correct", "stale", "invented", "unparseable",
    ]
    assert negates_removed_preference(question, grade(question, "dislike"))


def test_deep_house_flip_from_dislike_to_like():
    before_flip = fact_question(DEEP_HOUSE, 131, "preference", "choice", ("like", "dislike"))
    after_flip = fact_question(DEEP_HOUSE, 150, "preference", "choice", ("like", "dislike"))

    assert [outcome(before_flip, answer) for answer in ["dislike", "like", UNKNOWN]] == ["correct", "invented", "missing"]
    assert [outcome(after_flip, answer) for answer in ["likes", "dislike", UNKNOWN]] == ["correct", "stale", "missing"]


def test_a_removed_task_must_be_known_as_gone():
    # weekly/software_engineer: "Buy groceries" is on the to-do list from session 9 to 33.
    question = fact_question(("todo", ("Buy groceries",)), 35, None, "choice")

    assert [outcome(question, answer) for answer in ["no", "yes", "not sure"]] == ["correct", "stale", "missing"]


def test_yes_on_a_task_that_never_existed_is_invented():
    question = fact_question(("todo", ("Renew passport",)), 150, None, "choice", probe="never_existed")

    assert question.history == ()
    assert [outcome(question, answer) for answer in ["no", "yes", "not sure"]] == ["correct", "invented", "missing"]


def test_expense_total_is_compared_to_the_cent_and_an_earlier_total_is_stale():
    question = next(
        question for question in weekly_exam("software_engineer")
        if question.question_id == "weekly/software_engineer/s161/expense/total"
    )

    assert question.current == {"value": 258.23}
    assert [outcome(question, answer) for answer in ["$258.23", "258.24", "247.93", "a lot"]] == [
        "correct", "invented", "stale", "unparseable",
    ]


def test_event_date_accepts_written_dates():
    question = fact_question(MECHANIC_VISIT, 104, "event_date", "value")

    assert [outcome(question, answer) for answer in ["2025-06-11", "June 11, 2025", "2025-06-15", "2025-06-12"]] == [
        "correct", "correct", "stale", "invented",
    ]


def test_synthetic_agents_get_their_expected_outcome_on_the_real_exam():
    questions = weekly_exam("software_engineer")

    for agent, answer in SYNTHETIC_AGENTS.items():
        assert [outcome(question, answer(question)) for question in questions] == [
            expected_outcome(agent, question) for question in questions
        ], agent
