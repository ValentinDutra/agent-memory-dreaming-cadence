import pytest

from exam.grading import grade, render
from exam.questions import build_exam
from exam.schema import fact_states
from truth.changes import persona_changes
from truth.timeline import build_timeline

LIKE = {"preference": "like"}
DISLIKE = {"preference": "dislike"}


@pytest.fixture(scope="module")
def exam():
    return build_exam("weekly", "software_engineer")


def by_id(exam):
    return {question.question_id: question for question in exam}


def test_the_exam_is_deterministic_and_every_question_matches_the_truth(exam):
    timeline = build_timeline(persona_changes("weekly", "software_engineer"))

    assert build_exam("weekly", "software_engineer") == exam
    for question in exam:
        if question.probe not in ("never_existed", "aggregate"):
            assert (question.history, question.current) == fact_states(timeline, question.fact, question.session_id)
        assert grade(question, render(question, question.current)).outcome == "correct", question.question_id


def test_changed_preferences_are_asked_with_their_current_and_earlier_values(exam):
    questions = by_id(exam)
    # Bonobo: liked from session 17, deleted in session 30.
    bonobo = questions["weekly/software_engineer/s035/preference/music|artists|Bonobo"]
    # deep house: added as a dislike in session 129, turned into a like in session 132.
    deep_house = questions["weekly/software_engineer/s133/preference/music|genres|deep house"]

    assert (bonobo.probe, bonobo.history, bonobo.current) == ("recent_change", (None, LIKE), None)
    assert (deep_house.probe, deep_house.history, deep_house.current) == ("new", (None, DISLIKE), LIKE)


def test_a_rescheduled_event_is_never_asked_by_date(exam):
    # Mechanic visit: added in session 82, rescheduled in 87 and 105, where Memora's stored date disagrees with the user.
    mechanic = [question for question in exam if question.fact == ("calendar", ("Mechanic visit",))]

    assert {(question.session_id < 87, question.field) for question in mechanic} == {(True, "event_date"), (False, None)}
