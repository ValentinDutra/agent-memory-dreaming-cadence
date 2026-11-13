from diagnosis.causes import diagnose, persona
from diagnosis.invented import WrongAnswer
from exam.grading import grade
from exam.questions import build_exam
from policies.engine import Step

WEEK_OF_JUNE_8 = """## Food expenses
- 2025-06-08 coffee: $5.33
- 2025-06-08 breakfast: $11.89
- 2025-06-08 dinner: $25.97
- 2025-06-09 coffee: $3.18
- 2025-06-09 coffee: $3.46
- 2025-06-10 coffee: $7.07
- 2025-06-10 lunch: $21.40
- 2025-06-11 breakfast: $9.70
- 2025-06-11 lunch: $11.26
- 2025-06-11 coffee: $4.90
- 2025-06-12 coffee: $3.38
- 2025-06-12 dinner: $46.53"""


def wrong_answer(question_id: str, answer: str, notes: str, last_dream: int) -> WrongAnswer:
    question = next(question for question in build_exam("monthly", "academic_researcher") if question.question_id == question_id)
    return WrongAnswer("every-5", "monthly", "academic_researcher", 0, question, answer, grade(question, answer), notes, last_dream, ())


def dream(session_id: int, notes: str) -> Step:
    return Step(session_id, True, 5, 0.0, 0, 0, 0.0, notes)


def test_invented_answers_of_every_5_on_the_whole_researcher_get_their_cause():
    data = persona("monthly", "academic_researcher")
    # s245: the notes lack the $4.11 coffee of s236 ("grabbing a $4.11 coffee can be a small break"), read by the dream after s240.
    omission = wrong_answer("monthly/academic_researcher/s245/expense/total", "154.07", WEEK_OF_JUNE_8, 245)
    assert diagnose(omission, [dream(240, WEEK_OF_JUNE_8), dream(245, WEEK_OF_JUNE_8)], data).cause == "dream_omission"
    # s441: s429 (2025-06-20) says "a $45.81 dinner last night"; the notes put it on 2025-06-19 next to the $45.45 one.
    both_dinners = "## Food expenses\n- 2025-06-19 dinner: $45.45\n- 2025-06-19 dinner: $45.81"
    relative = wrong_answer("monthly/academic_researcher/s441/expense/402", "91.26", both_dinners, 440)
    assert diagnose(relative, [dream(430, both_dinners), dream(440, both_dinners)], data).cause == "memora_relative_date"
    # s147: the coffee of 2025-06-08 came in s147, after the dream of s145; the notes' total of that day is 0.
    lagging = wrong_answer("monthly/academic_researcher/s147/expense/total", "0", "## Food expenses\n- 2025-06-07 coffee: $4.00", 145)
    assert diagnose(lagging, [dream(145, lagging.notes)], data).cause == "grader_empty_total"
