"""The exam of a whole persona answered from perfect notes, to separate the reader's invented answers from the notes'. Owner: P6a.

  uv run python -m diagnosis.perfect_notes monthly/academic_researcher --limit 0.30

The notes of exam N are render_notes(timeline.state_after(N)), as P3's ceiling. Answers are cached under
results/raw/p6a/perfect/, so a second run is free. --dry-run prices the calls not cached yet and stops.
"""

import argparse
from collections import Counter

from answering.answer import answer_exam, exam_prompt, max_tokens, THINKING_TOKENS
from answering.client import BudgetedClient, BudgetExceeded, worst_case_cost
from answering.notes import render_notes
from diagnosis.causes import stretch
from dreaming.transcripts import load_transcripts
from exam.grading import OUTCOMES, grade
from exam.questions import build_exam
from policies import triggered_run
from truth.changes import persona_changes
from truth.timeline import build_timeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slice", help='"period/persona[:through]"')
    parser.add_argument("--limit", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    period, persona, through = triggered_run.slice_of(arguments.slice)
    timeline = build_timeline(persona_changes(period, persona))
    last_session = through or len(load_transcripts(period, persona))
    exams: dict[int, list] = {}
    for question in build_exam(period, persona):
        if through is None or question.session_id <= through:
            exams.setdefault(question.session_id, []).append(question)
    client = BudgetedClient("p6a", 0.0 if arguments.dry_run else arguments.limit)
    spent_before = client.spent()
    run = f"p6a/perfect/{period}/{persona}"
    outcomes = Counter()
    invented = []
    worst_case = 0.0
    for session_id, questions in sorted(exams.items()):
        notes = render_notes(timeline.state_after(session_id))
        try:
            answers = answer_exam(notes, questions, client, run)
        except BudgetExceeded:
            if not arguments.dry_run:
                raise
            worst_case += worst_case_cost(exam_prompt(notes, questions), max_tokens(questions) + THINKING_TOKENS)
            continue
        for question, answer in zip(questions, answers, strict=True):
            question_grade = grade(question, answer)
            outcomes[stretch(session_id, last_session), question_grade.outcome] += 1
            if question_grade.outcome == "invented":
                invented.append((question, question_grade))
    if arguments.dry_run:
        print(f"{len(exams)} exams; not cached: worst case ${worst_case:.4f}")
        return
    stretches = sorted({each for each, _ in outcomes})
    print(f"## Perfect notes on {arguments.slice}: {len(exams)} exams\n")
    print("| stretch | " + " | ".join(OUTCOMES) + " |\n| --- |" + " --: |" * len(OUTCOMES))
    for each in stretches:
        print(f"| {each} | " + " | ".join(str(outcomes[each, outcome]) for outcome in OUTCOMES) + " |")
    print()
    for question, question_grade in invented:
        print(f"- s{question.session_id} {question.domain}/{question.probe}: {question.prompt} -> {question_grade.given!r}, expected {question_grade.expected!r}")
    print(f"\np6a spent: ${spent_before:.4f} before, ${client.spent():.4f} after")


if __name__ == "__main__":
    main()
