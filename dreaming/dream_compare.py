"""Compare dream variants with a cheap signal: P2's exam answered from the dream's notes, and the cost of each dream.

chain: dream every `cadence` sessions from empty notes, take the exam after every session N with N % 7 == 0, reading
       the notes of the last dream at or before N.
speakers: the share of transcript characters each speaker writes.
preference-changes: how often a like is removed versus flipped to dislike, in the truth.
scale: one dream over the last k sessions before an exam session, from empty notes or from perfect notes (P3's
       render_notes of the truth), to measure cost against sessions read and notes size, and what one dream loses.

Measurement only: this module reads truth/ and exam/ to grade; the dream itself never sees them.
"""

import argparse
from collections import Counter, defaultdict
from statistics import linear_regression, mean

from answering.answer import answer_exam
from answering.client import RESULTS, BudgetedClient
from answering.notes import render_notes
from dreaming import dream as edits_dream
from dreaming import dream_rewrite
from dreaming.transcripts import load_transcripts, sessions_between
from exam.grading import grade
from exam.questions import build_exam
from exam.schema import DOMAINS
from truth.changes import MEMORA_DATA, persona_changes
from truth.timeline import build_timeline

BUDGET_NAME = "p4a"
VARIANTS = {
    "edits": edits_dream.dream_with_failures,
    "rewrite": lambda notes, sessions, client, run: (dream_rewrite.dream(notes, sessions, client, run), []),
}
# Printed with every exam that asks about them: the control cases of docs/p4-interfaz.md (weekly/software_engineer) and
# P1's defect 4 (weekly/marketing_manager s86: only the assistant names Taylor Swift, replaced by SZA).
WATCHED = ("'Bonobo'", "'deep house'", "'Mechanic visit'", "'Taylor Swift'", "'SZA'")


def clients(limit: float, thinking: str, effort: str) -> tuple[BudgetedClient, BudgetedClient]:
    """The dream's client, with the configuration under test, and the exam's, always P3's official one."""
    dream_client = BudgetedClient(BUDGET_NAME, limit, thinking={"type": thinking}, effort=effort)
    return dream_client, BudgetedClient(BUDGET_NAME, limit)


def exams(period: str, persona: str) -> dict[int, list]:
    by_session = defaultdict(list)
    for question in build_exam(period, persona):
        by_session[question.session_id].append(question)
    return dict(by_session)


def take_exam(notes: str, questions: list, client: BudgetedClient, run: str, errors: bool = False) -> list:
    answers = answer_exam(notes, questions, client, run=run)
    grades = [grade(question, answer) for question, answer in zip(questions, answers, strict=True)]
    for question, question_grade in zip(questions, grades):
        if errors and question_grade.outcome != "correct":
            print(f"    error s{question.session_id} {question.domain} {question.probe}: {question.prompt[:110]} -> {question_grade.given} "
                  f"(expected {question_grade.expected}, {question_grade.outcome})")
        elif any(name in question.prompt for name in WATCHED):
            print(f"    s{question.session_id} {question.probe}: {question.prompt[:70]}... -> {question_grade.given} ({question_grade.outcome})")
    return grades


def chain(args) -> None:
    dream_client, exam_client = clients(args.limit, args.thinking, args.effort)
    label = f"{args.variant}-{args.thinking}-{args.effort}/{args.period}/{args.persona}/c{args.cadence}"
    if args.repeat:
        # A new run directory misses the response cache, so the same dreams are asked again: that measures noise.
        label += f"/repeat{args.repeat}"
    sessions = load_transcripts(args.period, args.persona)
    last = min(args.through or sessions[-1].session_id, sessions[-1].session_id)
    questions_by_session = exams(args.period, args.persona)
    timeline = build_timeline(persona_changes(args.period, args.persona))
    spent_before = dream_client.spent()
    notes, last_dream = "", 0
    dream_totals = Counter()
    by_domain = defaultdict(Counter)
    notes_dir = RESULTS / "p4a" / "notes" / label
    notes_dir.mkdir(parents=True, exist_ok=True)
    for session_id in range(1, last + 1):
        if session_id % args.cadence == 0:
            read = sessions_between(sessions, last_dream, session_id)
            result, failures = VARIANTS[args.variant](notes, read, dream_client, f"p4a/{label}")
            dream_totals["lines dropped"] += len(fact_lines(notes) - fact_lines(result.notes))
            dream_totals["facts changed"] += sum(before is not None for before, _ in timeline.changed_between(last_dream, session_id).values())
            notes, last_dream = result.notes, session_id
            (notes_dir / f"s{session_id:04d}.md").write_text(notes)
            dream_totals.update(dreams=1, sessions=len(read), input=result.input_tokens, output=result.output_tokens, failed=len(failures))
            dream_totals["cost"] += result.cost
            print(f"dream s{session_id}: {len(read)} sessions, {result.input_tokens} in, {result.output_tokens} out, ${result.cost:.4f}, {len(failures)} failed edits, {len(notes)} chars")
            for failure in failures:
                print(f"    failed: {failure}")
        if session_id in questions_by_session:
            grades = take_exam(notes, questions_by_session[session_id], exam_client, f"p4a/exam/{label}", args.errors)
            for question, question_grade in zip(questions_by_session[session_id], grades):
                by_domain[question.domain][question_grade.outcome] += 1
    report(by_domain)
    print(
        f"dreams: {dream_totals['dreams']}, {dream_totals['input']} input and {dream_totals['output']} output tokens, "
        f"${dream_totals['cost']:.4f}, {dream_totals['failed']} failed edits. p4a spent ${spent_before:.4f} -> ${dream_client.spent():.4f}"
    )
    print(
        f"drift: {dream_totals['lines dropped']} note lines dropped or reworded from one dream to the next; "
        f"{dream_totals['facts changed']} facts changed or went away in the truth over the same spans"
    )


def fact_lines(notes: str) -> set[str]:
    return {line.strip() for line in notes.splitlines() if line.strip().startswith("- ")}


def report(by_domain: dict[str, Counter]) -> None:
    outcomes = ("correct", "stale", "missing", "invented", "unparseable")
    print("| domain | n | " + " | ".join(outcomes) + " |")
    print("| --- | --: |" + " --: |" * len(outcomes))
    total = Counter()
    for domain in DOMAINS:
        counts = by_domain.get(domain, Counter())
        total.update(counts)
        print(f"| {domain} | {sum(counts.values())} | " + " | ".join(str(counts[outcome]) for outcome in outcomes) + " |")
    n = sum(total.values())
    print(f"| **total** | {n} | " + " | ".join(str(total[outcome]) for outcome in outcomes) + f" |  correct {total['correct'] / max(n, 1):.1%}")


def scale(args) -> None:
    dream_client, exam_client = clients(args.limit, args.thinking, args.effort)
    sessions = load_transcripts(args.period, args.persona)
    timeline = build_timeline(persona_changes(args.period, args.persona))
    questions = exams(args.period, args.persona)[args.at]
    print("| variant | notes | sessions | notes chars | input | output | cost | failed edits | exam correct |")
    print("| --- | --- | --: | --: | --: | --: | --: | --: | --: |")
    rows = defaultdict(dict)  # (variant, notes kind) -> {sessions: (notes chars, input tokens, output tokens)}
    for variant in args.variants:
        for notes_kind in args.notes:
            for size in args.sizes:
                notes = render_notes(timeline.state_after(args.at - size)) if notes_kind == "perfect" else ""
                label = f"{variant}-{args.thinking}-{args.effort}/{args.period}/{args.persona}/scale"
                read = sessions_between(sessions, args.at - size, args.at)
                result, failures = VARIANTS[variant](notes, read, dream_client, f"p4a/{label}")
                correct = "—"
                if notes_kind == "perfect":
                    grades = take_exam(result.notes, questions, exam_client, f"p4a/exam/{label}")
                    correct = f"{sum(question_grade.outcome == 'correct' for question_grade in grades)}/{len(grades)}"
                print(f"| {variant} | {notes_kind} | {len(read)} | {len(notes)} | {result.input_tokens} | {result.output_tokens} | ${result.cost:.4f} | {len(failures)} | {correct} |")
                rows[variant, notes_kind][len(read)] = (len(notes), result.input_tokens, result.output_tokens)
    print_cost_model(rows)
    print(f"p4a spent ${dream_client.spent():.4f}")


def print_cost_model(rows: dict) -> None:
    """Least-squares lines of tokens against sessions read, and the input tokens each character of notes adds."""
    for (variant, notes_kind), by_size in sorted(rows.items()):
        sizes = sorted(by_size)
        if len(sizes) < 2:
            continue
        input_line = linear_regression(sizes, [by_size[size][1] for size in sizes])
        output_line = linear_regression(sizes, [by_size[size][2] for size in sizes])
        print(f"{variant}, {notes_kind} notes: input = {input_line.intercept:.0f} + {input_line.slope:.0f}*sessions, "
              f"output = {output_line.intercept:.0f} + {output_line.slope:.0f}*sessions")
        empty = rows.get((variant, "empty"), {})
        shared = [size for size in sizes if size in empty and by_size[size][0]]
        if notes_kind == "perfect" and shared:
            per_char = mean((by_size[size][1] - empty[size][1]) / by_size[size][0] for size in shared)
            print(f"{variant}: each character of notes adds {per_char:.3f} input tokens")


def speakers(args) -> None:
    """How much of the transcripts each speaker writes: what reading only the user's turns would save."""
    for persona in args.personas:
        sessions = load_transcripts(args.period, persona)
        characters = Counter()
        for session in sessions:
            for turn in session.turns:
                characters[turn.speaker] += len(turn.message)
        total = sum(characters.values())
        print(f"{args.period}/{persona}: {len(sessions)} sessions, {total} characters, user_agent {characters['user_agent'] / total:.1%}, ai_agent {characters['ai_agent'] / total:.1%}")


def preference_changes(args) -> None:
    """How often a like goes away versus flips to dislike: which way the dream should read "not into it anymore"."""
    counts = Counter()
    for persona in sorted(path.name for path in (MEMORA_DATA / args.period).iterdir() if path.is_dir()):
        for change in persona_changes(args.period, persona):
            if change.domain == "preference" and change.previous and change.previous["preference"] == "like":
                counts["like removed" if change.action == "remove" else f"like -> {change.value['preference']}"] += 1
    print(f"{args.period}: {dict(counts)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=float, default=1.00)
    parser.add_argument("--thinking", choices=("adaptive", "disabled"), default="adaptive")
    parser.add_argument("--effort", choices=("low", "medium", "high"), default="medium")
    commands = parser.add_subparsers(dest="command", required=True)
    chain_parser = commands.add_parser("chain")
    chain_parser.add_argument("variant", choices=VARIANTS)
    chain_parser.add_argument("period")
    chain_parser.add_argument("persona")
    chain_parser.add_argument("--cadence", type=int, default=7)
    chain_parser.add_argument("--through", type=int)
    chain_parser.add_argument("--repeat", type=int, default=0)
    chain_parser.add_argument("--errors", action="store_true", help="print every answer that is not correct")
    scale_parser = commands.add_parser("scale")
    scale_parser.add_argument("period")
    scale_parser.add_argument("persona")
    scale_parser.add_argument("--at", type=int, required=True, help="exam session the dreams end at")
    scale_parser.add_argument("--variants", nargs="+", choices=VARIANTS, default=list(VARIANTS))
    scale_parser.add_argument("--notes", nargs="+", choices=("empty", "perfect"), default=["empty", "perfect"])
    scale_parser.add_argument("--sizes", nargs="+", type=int, default=[1, 5, 20, 50])
    preference_parser = commands.add_parser("preference-changes")
    preference_parser.add_argument("period")
    speakers_parser = commands.add_parser("speakers")
    speakers_parser.add_argument("period")
    speakers_parser.add_argument("personas", nargs="+")
    args = parser.parse_args()
    {"chain": chain, "scale": scale, "speakers": speakers, "preference-changes": preference_changes}[args.command](args)


if __name__ == "__main__":
    main()
