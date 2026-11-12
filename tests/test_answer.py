from answering.answer import parse_answers
from answering.notes import render_notes
from exam.questions import build_exam
from truth.changes import persona_changes
from truth.timeline import build_timeline

# A real reply (weekly/software_engineer, exam of session 49, results/raw/p3a/markdown+work). Read line by line,
# "9.15 + 3.41 ..." and "13.83" in the work would pass for answers 9, 3 and 13.
REPLY_WITH_WORK = (
    "<work>\nQ1: Ann Leckie not in notes → unknown.\n"
    "Q12: grocery 2025-06-01: 28.50 → 28.50.\nQ13: food expenses 2025-06-01 to 06-03:\n"
    "9.15 + 3.41 + 7.35 + 28.50 = 48.41\n3.25 + 3.91 + 9.84 = 16.99\n13.83\n"
    "Total = 48.41 + 16.99 + 13.83 = 79.23\nQ16: 14096 + 7935 + 7640 = 29671.\n</work>\n\n"
    "<answers>\n1: unknown\n2: like\n3: unknown\n4: yes\n5: yes\n6: no\n7: no\n8: 60\n9: yes\n10: no\n"
    "11: 13.83\n12: 28.50\n13: 79.23\n14: 7640\n15: 14096\n16: 29671\n</answers>"
)


def test_answers_come_only_from_the_answers_block_in_question_order():
    answers = parse_answers(REPLY_WITH_WORK, 17)
    assert answers[:3] == ["unknown", "like", "unknown"]
    assert answers[8] == "yes" and answers[12] == "79.23"
    assert answers[16] is None


def test_notes_name_what_the_questions_name_and_write_an_empty_calendar():
    session = 14
    notes = render_notes(build_timeline(persona_changes("weekly", "software_engineer")).state_after(session))
    questions = [question for question in build_exam("weekly", "software_engineer") if question.session_id == session]
    held_items = [question for question in questions if question.domain == "content" and question.field is None and question.current is not None]
    assert "## Calendar\n- (none)" in notes
    assert held_items
    for question in held_items:
        title = question.prompt.split(" of the user's ")[1].split("'")[1].removesuffix(" ...")
        assert title in notes and question.fact[1][2] in notes
    assert "project_proposal_" not in notes and "email_writeup_" not in notes
