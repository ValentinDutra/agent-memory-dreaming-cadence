from exam.unreachable import unreachable


def test_memora_text_the_user_never_said_last_night_expenses_and_done_tasks_added_are_marked():
    researcher = unreachable("monthly", "academic_researcher")
    # The user named "Mr. David Kim" in s44; Memora stores his role and department too.
    assert researcher["monthly/academic_researcher/s049/content/meeting_notes_1|attendees|Mr. David Kim (Systems Integration Lead, Engineering Department)"] == "unsaid_item"
    # s25: "I completed a task to coordinate with the research team." Memora adds the task; s28 asks if it is on the list.
    assert researcher["monthly/academic_researcher/s028/todo/Coordinate with research team"] == "completed_task"
    founder = unreachable("monthly", "startup_founder")
    # s112 (2025-06-06): "I spent $27.04 on dinner last night"; Memora dates it 2025-06-06, the first day of that week's total.
    assert founder["monthly/startup_founder/s112/expense/112"] == "relative_date"
    assert founder["monthly/startup_founder/s112/expense/total"] == "relative_date"
    assert not any("Bonobo" in question_id for question_id in unreachable("weekly", "software_engineer"))


def test_the_day_a_last_night_expense_belongs_to_is_marked_once_it_is_logged():
    researcher = unreachable("monthly", "academic_researcher")
    # Dinner of 2025-06-19 (s402, $45.45). In s429 (2025-06-20) the user adds "a $45.81 dinner last night", which
    # Memora dates 2025-06-20; the notes of every-5 hold both dinners on 2025-06-19 and the reader answers 91.26.
    assert researcher["monthly/academic_researcher/s441/expense/402"] == "relative_date"
    assert "monthly/academic_researcher/s406/expense/402" not in researcher
    # s132 of monthly/creative_designer (2025-06-07): "I just had a $9.81 lunch today, mostly leftovers from yesterday."
    assert "monthly/creative_designer/s133/expense/132" not in unreachable("monthly", "creative_designer")
