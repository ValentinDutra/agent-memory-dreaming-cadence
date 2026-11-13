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
