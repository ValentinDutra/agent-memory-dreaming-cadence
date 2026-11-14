"""Does the error rate grow with the life of the agent? Rates per stretch of sessions and per policy, from the cache. Owner: P6b.

  uv run python -m diagnosis.growth estimate monthly/academic_researcher monthly/startup_founder --policies never every-1 every-5 every-20 triggered-phrases-any
  uv run python -m diagnosis.growth exam monthly/academic_researcher --policies never every-1 every-5 every-20 triggered-phrases-any
  uv run python -m diagnosis.growth notes monthly/academic_researcher --policies every-1 every-5 every-20 triggered-phrases-any

estimate projects, without calling anything, what a whole-persona run would pay beyond the sessions already cached.
exam and notes read the runs from the P5 cache with a cap of $0, and stop at the first call that is not cached.
"""

import argparse
import re
from collections import Counter

from answering.client import BudgetedClient
from dreaming import quality
from dreaming.transcripts import load_transcripts
from exam.questions import EXAM_STEP
from exam.unreachable import unreachable
from policies import projection, triggered_run
from policies.engine import PolicyRun, run_policy
from policies.run import policy_named
from truth.changes import persona_changes
from truth.timeline import build_timeline

STRETCH = 210  # sessions per stretch: s1-210 is what P7 runs, then 211-420 and 421 to the end
ERRORS = ("stale", "missing", "invented")


def stretch_of(session_id: int) -> int:
    return (session_id - 1) // STRETCH


def stretch_label(stretch: int, last_session: int) -> str:
    return f"s{stretch * STRETCH + 1}-{min((stretch + 1) * STRETCH, last_session)}"


# --- Cost estimate --------------------------------------------------------------------------------


def estimate(arguments) -> None:
    perfect = projection.Perfect()
    dream_model, exam_model, ratio, _, _ = projection.fit(STRETCH, perfect)
    base, per_kilocharacter, per_session = dream_model
    exam_base, exam_per_kilocharacter = exam_model
    print(f"projected cost after s{arguments.cached_through}, which is cached (policies.projection fit, notes x{ratio:.2f} the perfect ones)\n")
    print("| period/persona | policy | dreams after cache | dream $ | exams after cache | exam $ | total $ |\n| --- | --- | --: | --: | --: | --: | --: |")
    grand_total = 0.0
    for spec in arguments.slices:
        period, persona, _ = triggered_run.slice_of(spec)
        for name in arguments.policies:
            policy = projection.policy_named(name)
            dreams, dream_dollars, exams, exam_dollars, pending, last_dream = 0, 0.0, 0, 0.0, [], 0
            for session in load_transcripts(period, persona):
                pending.append(session)
                if policy.decide("", list(pending), None, "").dream:
                    if session.session_id > arguments.cached_through:
                        notes = ratio * perfect.length(period, persona, last_dream)
                        dream_dollars += base + per_kilocharacter * notes / 1000 + per_session * len(pending)
                        dreams += 1
                    pending, last_dream = [], session.session_id
                if session.session_id % EXAM_STEP == 0 and session.session_id > arguments.cached_through:
                    exam_dollars += exam_base + exam_per_kilocharacter * ratio * perfect.length(period, persona, last_dream) / 1000
                    exams += 1
            grand_total += dream_dollars + exam_dollars
            print(f"| {spec} | {name} | {dreams} | {dream_dollars:.4f} | {exams} | {exam_dollars:.4f} | {dream_dollars + exam_dollars:.4f} |")
    print(f"\ntotal: ${grand_total:.4f}")


# --- Runs from the cache --------------------------------------------------------------------------


def cached_runs(arguments) -> list[PolicyRun]:
    client = BudgetedClient(arguments.budget_name, 0.0)
    runs = []
    for spec in arguments.slices:
        period, persona, through = triggered_run.slice_of(spec)
        for name in arguments.policies:
            runs.append(run_policy(policy_named(name, arguments.budget_name, 0.0), period, persona, client, EXAM_STEP, through, arguments.repetition))
    return runs


# --- Exam: rates per stretch ------------------------------------------------------------------------


def graded(run: PolicyRun, without_marked: bool = False):
    """(stretch, question, outcome) of every answer of the run; without_marked drops the questions of decision (c) (P5 §3.2)."""
    marked = unreachable(run.period, run.persona) if without_marked else {}
    for exam in run.exams:
        for question, question_grade in zip(exam.questions, exam.grades, strict=True):
            if question.question_id not in marked:
                yield stretch_of(exam.session_id), question, question_grade.outcome


def fact_asked(question) -> tuple:
    """The fact behind a question; for a total, its week. Exams ask a stable fact or a week's total again and again."""
    return question.fact or (question.domain, re.findall(r"\d{4}-\d{2}-\d{2}", question.prompt)[0])


def rate(part: int, whole: int) -> str:
    return f"{part / whole:.1%}" if whole else "-"


def exam_report(arguments) -> None:
    runs = cached_runs(arguments)
    for spec in arguments.slices:
        period, persona, _ = triggered_run.slice_of(spec)
        persona_runs = [run for run in runs if (run.period, run.persona) == (period, persona)]
        last_session = persona_runs[0].steps[-1].session_id
        stretches = sorted({stretch for run in persona_runs for stretch, _, _ in graded(run)})
        labels = [stretch_label(stretch, last_session) for stretch in stretches]
        print(f"# {spec}\n")
        overall_table(persona_runs, stretches, labels)
        for without_marked in (False, True):
            print("### " + ("Without the marked questions of decision (c)" if without_marked else "Official count, every question") + "\n")
            ranking_table(persona_runs, stretches, labels, without_marked)
            standardized_table(persona_runs, stretches, labels, without_marked)
            for outcome in ("invented", "error"):
                cell_table(persona_runs, stretches, labels, outcome, without_marked)
        reading_table(persona_runs, stretches, labels)
        aggregate_table(persona_runs)


def overall_table(runs: list[PolicyRun], stretches: list[int], labels: list[str]) -> None:
    print("## Every question, per stretch: correct, and each error as a share of the questions asked\n")
    print("| policy | stretch | exams | questions | correct | stale | missing | invented | marked questions | correct without marked | invented without marked | errors without marked | distinct facts behind them |"
          "\n| --- | --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    for run in runs:
        marked = unreachable(run.period, run.persona)
        for stretch, label in zip(stretches, labels):
            answers = [(question, outcome) for each_stretch, question, outcome in graded(run) if each_stretch == stretch]
            counts = Counter(outcome for _, outcome in answers)
            reachable = [outcome for question, outcome in answers if question.question_id not in marked]
            wrong_facts = {fact_asked(question) for question, outcome in answers if question.question_id not in marked and outcome in ERRORS}
            reachable_errors = sum(outcome in ERRORS for outcome in reachable)
            exams = sum(stretch_of(exam.session_id) == stretch for exam in run.exams)
            cells = [run.policy, label, exams, len(answers), f"{counts['correct']} ({rate(counts['correct'], len(answers))})",
                     *(f"{counts[outcome]} ({rate(counts[outcome], len(answers))})" for outcome in ERRORS),
                     len(answers) - len(reachable), rate(reachable.count("correct"), len(reachable)),
                     f"{reachable.count('invented')} ({rate(reachable.count('invented'), len(reachable))})",
                     f"{reachable_errors} ({rate(reachable_errors, len(reachable))})", len(wrong_facts)]
            print("| " + " | ".join(map(str, cells)) + " |")
    print()


def ranking_table(runs: list[PolicyRun], stretches: list[int], labels: list[str], without_marked: bool) -> None:
    print("## Policies from best to worst in each stretch (correct share)\n")
    print("| stretch | ranking |\n| --- | --- |")
    for stretch, label in zip(stretches, labels):
        shares = []
        for run in runs:
            outcomes = [outcome for each_stretch, _, outcome in graded(run, without_marked) if each_stretch == stretch]
            shares.append((outcomes.count("correct") / len(outcomes), run.policy))
        print(f"| {label} | " + " > ".join(f"{policy} {share:.1%}" for share, policy in sorted(shares, reverse=True)) + " |")
    print()


def cells_of(run: PolicyRun, stretch: int, without_marked: bool) -> dict[tuple[str, str], Counter]:
    """(domain, probe) -> outcome counts, with "asked", for the stretch."""
    cells = {}
    for each_stretch, question, outcome in graded(run, without_marked):
        if each_stretch == stretch:
            cell = cells.setdefault((question.domain, question.probe), Counter())
            cell.update(asked=1, **{outcome: 1})
    return cells


def errors_in(cell: Counter, outcome: str) -> int:
    return sum(cell[each] for each in ERRORS) if outcome == "error" else cell[outcome]


def standardized(first: dict[tuple[str, str], Counter], cells: dict[tuple[str, str], Counter], outcome: str) -> tuple[float, float, float]:
    """Splits "more questions of a risky kind" from "a higher rate on the same kind of question". Returns:

    observed: the stretch's rate. same mix as the first stretch: each (domain, probe) cell keeps its rate in the
    stretch, weighted by its share of the first stretch's questions. first stretch's rates: each cell keeps the
    first stretch's rate, weighted by the stretch's own mix, so it moves only with the mix.
    """
    asked = sum(cell["asked"] for cell in cells.values())
    observed = sum(errors_in(cell, outcome) for cell in cells.values()) / asked
    shared = [key for key in first if key in cells]
    same_mix = sum(first[key]["asked"] * errors_in(cells[key], outcome) / cells[key]["asked"] for key in shared) / sum(first[key]["asked"] for key in shared)
    # A cell the first stretch never asked has no first-stretch rate: it counts at the stretch's own rate.
    first_rates = sum(
        cell["asked"] * (errors_in(first[key], outcome) / first[key]["asked"] if key in first else errors_in(cell, outcome) / cell["asked"])
        for key, cell in cells.items()
    ) / asked
    return observed, same_mix, first_rates


def standardized_table(runs: list[PolicyRun], stretches: list[int], labels: list[str], without_marked: bool) -> None:
    print("## Invented and all errors per stretch: observed, with the first stretch's mix of (domain, probe), and with the first stretch's rates\n")
    print("| policy | stretch | invented observed | invented, same mix as first | invented, first stretch's rates | errors observed | errors, same mix as first | errors, first stretch's rates |\n| --- | --- | --: | --: | --: | --: | --: | --: |")
    for run in runs:
        first = cells_of(run, stretches[0], without_marked)
        for stretch, label in zip(stretches, labels):
            cells = cells_of(run, stretch, without_marked)
            row = [run.policy, label]
            for outcome in ("invented", "error"):
                row += [f"{value:.1%}" for value in standardized(first, cells, outcome)]
            print("| " + " | ".join(row) + " |")
    print()

def cell_table(runs: list[PolicyRun], stretches: list[int], labels: list[str], outcome: str, without_marked: bool) -> None:
    title = "invented" if outcome == "invented" else "errors (stale + missing + invented)"
    print(f"## {title} / questions asked, per (domain, probe) and stretch\n")
    print("| domain/probe | policy | " + " | ".join(labels) + " |\n| --- | --- |" + " --: |" * len(labels))
    per_run = {run.policy: [cells_of(run, stretch, without_marked) for stretch in stretches] for run in runs}
    keys = sorted({key for cells_list in per_run.values() for cells in cells_list for key in cells})
    for key in keys:
        for run in runs:
            cells = [cells.get(key, Counter()) for cells in per_run[run.policy]]
            if not any(errors_in(cell, outcome) for cell in cells):
                continue
            print(f"| {key[0]}/{key[1]} | {run.policy} | " + " | ".join(
                f"{errors_in(cell, outcome)}/{cell['asked']} ({rate(errors_in(cell, outcome), cell['asked'])})" for cell in cells
            ) + " |")
    print()


def reading_table(runs: list[PolicyRun], stretches: list[int], labels: list[str]) -> None:
    """Splits a wrong note from a wrong reading: for each question about a fact that holds, how the notes the exam read
    hold that fact (P4b's compare_notes), and how often the answer is wrong given that. Marked questions are left out."""
    print("## Questions about a fact that holds, without marked: how the notes the exam read hold the fact, and the error rate given that\n")
    print("| policy | stretch | fact correct in notes | error when correct in notes | fact missing in notes | error when missing | fact stale or wrong in notes | error when stale or wrong |"
          "\n| --- | --- | --: | --: | --: | --: | --: | --: |")
    for run in runs:
        timeline = build_timeline(persona_changes(run.period, run.persona))
        steps = {step.session_id: step for step in run.steps}
        marked = unreachable(run.period, run.persona)
        tallies = {stretch: Counter() for stretch in stretches}
        for exam in run.exams:
            comparison = quality.compare_notes(steps[exam.session_id].notes, timeline, exam.session_id)
            for question, question_grade in zip(exam.questions, exam.grades, strict=True):
                if question.question_id in marked or question.fact not in comparison.fact_outcomes:
                    continue
                held = comparison.fact_outcomes[question.fact][0]
                held = "stale or wrong" if held in ("stale", "wrong") else held
                tally = tallies[stretch_of(exam.session_id)]
                tally[held] += 1
                tally[held, "error"] += question_grade.outcome in ERRORS
        for stretch, label in zip(stretches, labels):
            tally = tallies[stretch]
            cells = [run.policy, label]
            for held in ("correct", "missing", "stale or wrong"):
                cells += [tally[held], f"{tally[held, 'error']} ({rate(tally[held, 'error'], tally[held])})"]
            print("| " + " | ".join(map(str, cells)) + " |")
    print()

def aggregate_table(runs: list[PolicyRun]) -> None:
    """Expense totals per calendar week. A monthly persona is one month of about 20 sessions a day, so each week's
    running total is asked at some 20 exams in a row, and one missed expense repeats in all of them.

    complete notes: every expense of the total's range sits in the notes the exam read, with its amount (P4b's
    compare_notes). An invented total on complete notes is a wrong selection or sum, not a wrong note, except in a
    marked week: there the notes date a "last night" expense the day before Memora does, and compare_notes still
    matches "2025-06-21 dinner" to "2025-06-22 dinner" (similarity 0.75), so the notes look complete.
    shortfalls: the distinct amounts (expected - given) of the invented totals; one shortfall repeated is one mistake.
    """
    print("## Expense totals (aggregate) per calendar week: items summed, notes the exam read, and invented answers\n")
    print("| policy | week from | exams | totals | mean items | mean expense lines in the notes | complete notes | invented | invented on complete notes | distinct shortfalls of the invented | marked (relative_date) |"
          "\n| --- | --- | --- | --: | --: | --: | --: | --: | --: | --: | --: |")
    for run in runs:
        timeline = build_timeline(persona_changes(run.period, run.persona))
        steps = {step.session_id: step for step in run.steps}
        marked = unreachable(run.period, run.persona)
        weeks = {}
        for exam in run.exams:
            for question, question_grade in zip(exam.questions, exam.grades, strict=True):
                if (question.domain, question.probe) != ("expense", "aggregate"):
                    continue
                comparison = quality.compare_notes(steps[exam.session_id].notes, timeline, exam.session_id)
                start, end = re.findall(r"\d{4}-\d{2}-\d{2}", question.prompt)[:2]
                state = timeline.state_after(exam.session_id)
                in_range = [fact for fact, value in state.items() if fact[0] == "expense" and start <= value["date"] <= end]
                complete = all(comparison.fact_outcomes.get(fact, ("missing",))[0] == "correct" for fact in in_range)
                expense_lines = sum(number for (domain, outcome), number in comparison.facts.items() if domain == "expense" and outcome != "missing")
                expense_lines += sum(number for (domain, _), number in comparison.lines.items() if domain == "expense")
                shortfall = round(float(question_grade.expected) - float(question_grade.given), 2) if question_grade.outcome == "invented" else None
                weeks.setdefault(start, []).append((exam.session_id, len(question.history), expense_lines, complete, question_grade.outcome, shortfall, question.question_id in marked))
        for start, rows in weeks.items():
            invented = [row for row in rows if row[4] == "invented"]
            cells = [run.policy, start, f"s{rows[0][0]}-s{rows[-1][0]}", len(rows), f"{sum(row[1] for row in rows) / len(rows):.1f}",
                     f"{sum(row[2] for row in rows) / len(rows):.0f}", f"{sum(row[3] for row in rows)}/{len(rows)}", f"{len(invented)}/{len(rows)}",
                     f"{sum(row[3] for row in invented)}/{sum(row[3] for row in rows)}", len({row[5] for row in invented}), sum(row[6] for row in rows)]
            print("| " + " | ".join(map(str, cells)) + " |")
    print()


# --- Notes: size and line-by-line accuracy of every dream ----------------------------------------------

LINE_KINDS = ("stale", "invented", "duplicate", "unmatched_supported", "unmatched_unsupported")


def dream_comparisons(run: PolicyRun) -> list[tuple[int, int, quality.Comparison]]:
    """(session, note characters, comparison against the truth after that session) for every dream of the run."""
    timeline = build_timeline(persona_changes(run.period, run.persona))
    transcript_by_session = {session.session_id: " ".join(turn.message for turn in session.turns) for session in load_transcripts(run.period, run.persona)}
    read_so_far = []
    found = []
    for step in run.steps:
        read_so_far.append(transcript_by_session[step.session_id])
        if step.dreamt:
            found.append((step.session_id, len(step.notes), quality.compare_notes(step.notes, timeline, step.session_id, " ".join(read_so_far))))
            # stems() caches by text: without this, every growing transcript would stay in memory.
            quality.stems.cache_clear()
    return found


def notes_report(arguments) -> None:
    runs = cached_runs(arguments)
    print("## Notes after each dream, mean per dream in each stretch: size, live facts in the truth, how the notes hold them, and lines that state no live fact\n")
    header = ("| period/persona | policy | stretch | dreams | characters | note lines | live facts | correct | stale | wrong | missing | "
              + " | ".join(f"{kind} lines" for kind in LINE_KINDS) + " |")
    print(header + "\n| --- | --- | --- |" + " --: |" * (header.count("|") - 4))
    by_domain = []
    for run in runs:
        comparisons = dream_comparisons(run)
        last_session = run.steps[-1].session_id
        for stretch in sorted({stretch_of(session) for session, _, _ in comparisons}):
            chosen = [(characters, comparison) for session, characters, comparison in comparisons if stretch_of(session) == stretch]
            count = len(chosen)
            live = sum(comparison.fact_total() for _, comparison in chosen)
            lines = Counter()
            for _, comparison in chosen:
                for (_, outcome), number in comparison.lines.items():
                    lines[outcome] += number
            note_lines = sum(comparison.fact_total() - comparison.fact_total("missing") + comparison.line_total() for _, comparison in chosen)
            cells = [f"{run.period}/{run.persona}", run.policy, stretch_label(stretch, last_session), count,
                     f"{sum(characters for characters, _ in chosen) / count:,.0f}", f"{note_lines / count:.0f}", f"{live / count:.0f}",
                     *(rate(sum(comparison.fact_total(outcome) for _, comparison in chosen), live) for outcome in quality.FACT_OUTCOMES),
                     *(f"{lines[kind] / count:.1f}" for kind in LINE_KINDS)]
            print("| " + " | ".join(map(str, cells)) + " |")
            for domain in ("expense", "steps", "preference", "todo", "calendar", "content", "goal"):
                facts = Counter()
                domain_lines = Counter()
                for _, comparison in chosen:
                    for (each_domain, outcome), number in comparison.facts.items():
                        if each_domain == domain:
                            facts[outcome] += number
                    for (each_domain, outcome), number in comparison.lines.items():
                        if each_domain == domain:
                            domain_lines[outcome] += number
                by_domain.append((run, stretch_label(stretch, last_session), domain, count, facts, domain_lines))
    print("\n## The same per domain\n")
    print("| period/persona | policy | stretch | domain | live facts | correct | stale | wrong | missing | " + " | ".join(f"{kind} lines" for kind in LINE_KINDS)
          + " |\n| --- | --- | --- | --- |" + " --: |" * (5 + len(LINE_KINDS)))
    for run, label, domain, count, facts, domain_lines in by_domain:
        live = sum(facts.values())
        cells = [f"{run.period}/{run.persona}", run.policy, label, domain, f"{live / count:.0f}",
                 *(rate(facts[outcome], live) for outcome in quality.FACT_OUTCOMES), *(f"{domain_lines[kind] / count:.1f}" for kind in LINE_KINDS)]
        print("| " + " | ".join(map(str, cells)) + " |")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("estimate", "exam", "notes"))
    parser.add_argument("slices", nargs="+", help='"period/persona[:through]"')
    parser.add_argument("--policies", nargs="+", required=True)
    parser.add_argument("--budget-name", default="p6b")
    parser.add_argument("--repetition", type=int, default=0, help="exam and notes: which repetition of the cache to read")
    parser.add_argument("--cached-through", type=int, default=STRETCH, help="estimate: sessions already paid for every policy")
    arguments = parser.parse_args()
    {"estimate": estimate, "exam": exam_report, "notes": notes_report}[arguments.command](arguments)


if __name__ == "__main__":
    main()
