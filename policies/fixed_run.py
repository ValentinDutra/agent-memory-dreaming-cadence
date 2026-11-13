"""Run the fixed cadences on real personas and print what the P5a report uses. Owner: P5a.

This script measures, so it reads the truth (docs/p5-interfaz.md); the policies in policies.fixed never do.

    uv run python -m policies.fixed_run weekly software_engineer --policies never every-1 every-5 every-10 every-20 every-50 \
        --budget-name p5a --limit 1.50 --dry-run

Every run comes from results/raw/p5/r<repetition>/ when it is cached, so the tables cost nothing to print again.
"""

import argparse
import statistics
from collections import Counter, defaultdict

from answering.answer import RULES, SYSTEM
from answering.client import BudgetedClient
from answering.notes import render_notes
from dreaming.quality import compare_notes
from dreaming.transcripts import load_transcripts
from exam.questions import EXAM_STEP, STABLE_CONTROL_AGE, build_exam
from exam.schema import DOMAINS
from policies.engine import PolicyRun, percent, run_policy, runs_table, score
from policies.fixed import Every, policy_named
from truth.changes import persona_changes, personas
from truth.timeline import FactId, Timeline, build_timeline

# P4a's cost model of one dream, in dollars (docs/p4-sueno.md §4.4).
DREAM_FIXED = 0.00047
DREAM_PER_THOUSAND_NOTE_CHARACTERS = 0.00004
DREAM_PER_SESSION = 0.0001
# An exam reply, thinking included, averaged 687 output tokens weekly and 761 monthly (docs/p3-respuestas.md §4.4).
EXAM_OUTPUT_TOKENS = 800
CHARACTERS_PER_TOKEN = 4
INPUT_PRICE = 0.10 / 1_000_000
OUTPUT_PRICE = 0.50 / 1_000_000

PROBE_COLUMNS = ("recent_change", "new", "stable < 50", "stable >= 50", "never_existed", "aggregate")


def last_change(timeline: Timeline, fact: FactId, session_id: int) -> int:
    """The last session up to session_id where the fact started, changed or stopped holding; 0 if never."""
    domain, key = fact
    sessions = [0]
    for version in timeline.versions:
        if version.domain == domain and version.key == key:
            sessions += [boundary for boundary in (version.valid_from, version.valid_until) if boundary is not None and boundary <= session_id]
    return max(sessions)


def last_dream_before(run: PolicyRun) -> dict[int, int]:
    """Session -> the last session up to it that ended with a dream, 0 if none."""
    last = 0
    by_session = {}
    for step in run.steps:
        if step.dreamt:
            last = step.session_id
        by_session[step.session_id] = last
    return by_session


# --- Dry run -------------------------------------------------------------------------------------


def estimate(policy_names: list[str], period: str, persona: str, through: int | None, exam_every: int) -> list[str]:
    """Dollars if nothing were cached: P4a's model for each dream and the prompt length for each exam, with perfect notes."""
    timeline = build_timeline(persona_changes(period, persona))
    sessions = [session for session in load_transcripts(period, persona) if through is None or session.session_id <= through]
    questions = defaultdict(list)
    for question in build_exam(period, persona):
        if question.session_id % exam_every == 0:
            questions[question.session_id].append(question)
    perfect_characters = {}

    def notes_characters(session_id: int) -> int:
        if session_id not in perfect_characters:
            perfect_characters[session_id] = len(render_notes(timeline.state_after(session_id)))
        return perfect_characters[session_id]

    lines = ["| policy | dreams | dreams $ | exams | exams $ | total $ |", "| --- |" + " --: |" * 5]
    for name in policy_names:
        policy = policy_named(name)
        pending = []
        last_dream = 0
        dream_dollars = exam_dollars = 0.0
        dreams = 0
        for session in sessions:
            pending.append(session)
            if policy.decide("", list(pending), None, "").dream:
                dreams += 1
                dream_dollars += DREAM_FIXED + DREAM_PER_THOUSAND_NOTE_CHARACTERS * notes_characters(last_dream) / 1000 + DREAM_PER_SESSION * len(pending)
                pending = []
                last_dream = session.session_id
            if session.session_id in questions:
                prompt_characters = len(SYSTEM) + len(RULES) + notes_characters(last_dream) if last_dream else len(SYSTEM) + len(RULES)
                prompt_characters += sum(len(question.prompt) + 5 for question in questions[session.session_id])
                exam_dollars += prompt_characters / CHARACTERS_PER_TOKEN * INPUT_PRICE + EXAM_OUTPUT_TOKENS * OUTPUT_PRICE
        exams = sum(1 for session in sessions if session.session_id in questions)
        lines.append(f"| {name} | {dreams} | {dream_dollars:.4f} | {exams} | {exam_dollars:.4f} | {dream_dollars + exam_dollars:.4f} |")
    return lines


# --- Tables --------------------------------------------------------------------------------------


def probe_column(question, timeline: Timeline) -> str:
    if question.probe != "stable":
        return question.probe
    age = question.session_id - last_change(timeline, question.fact, question.session_id)
    return "stable >= 50" if age >= STABLE_CONTROL_AGE else "stable < 50"


def probe_table(runs: list[PolicyRun], timelines: dict) -> list[str]:
    """Official correct answers by probe, stable split as the exam draws it (P2a): under 50 sessions since the last change, or more."""
    lines = ["| policy | period/persona | " + " | ".join(PROBE_COLUMNS) + " |", "| --- | --- |" + " --: |" * len(PROBE_COLUMNS)]
    for run in runs:
        counts = Counter()
        for exam in run.exams:
            for question, question_grade in zip(exam.questions, exam.grades, strict=True):
                column = probe_column(question, timelines[run.period, run.persona])
                counts[column, "asked"] += 1
                counts[column, "correct"] += question_grade.outcome == "correct"
        cells = [percent(counts[column, "correct"], counts[column, "asked"]) for column in PROBE_COLUMNS]
        lines.append(f"| {run.policy} | {run.period}/{run.persona} | " + " | ".join(cells) + " |")
    return lines


def domain_table(runs: list[PolicyRun]) -> list[str]:
    lines = ["| policy | period/persona | " + " | ".join(DOMAINS) + " |", "| --- | --- |" + " --: |" * len(DOMAINS)]
    for run in runs:
        cells = [score(run, (domain,)).row()[0] for domain in DOMAINS]
        lines.append(f"| {run.policy} | {run.period}/{run.persona} | " + " | ".join(cells) + " |")
    return lines


def delay_table(runs: list[PolicyRun], timelines: dict) -> list[str]:
    """Separates waiting from losing. A fact question is "read" when a dream has read its last change, "waiting" when
    the change came after the last dream; never_existed and aggregate questions have no single fact to wait for.
    The same split over the notes, line by line against the truth (P4b's compare_notes), on the notes of every exam."""
    lines = [
        "| policy | period/persona | exam: read | exam: waiting | exam: no single fact | facts read by a dream: correct (the rest were lost) | facts waiting: correct | stale lines |",
        "| --- | --- |" + " --: |" * 6,
    ]
    for run in runs:
        timeline = timelines[run.period, run.persona]
        last_dream = last_dream_before(run)
        notes_by_session = {step.session_id: step.notes for step in run.steps}
        counts = Counter()
        for exam in run.exams:
            for question, question_grade in zip(exam.questions, exam.grades, strict=True):
                if question.probe in ("never_existed", "aggregate"):
                    kind = "no single fact"
                else:
                    kind = "waiting" if last_change(timeline, question.fact, exam.session_id) > last_dream[exam.session_id] else "read"
                counts[kind, "asked"] += 1
                counts[kind, "correct"] += question_grade.outcome == "correct"
            comparison = compare_notes(notes_by_session[exam.session_id], timeline, exam.session_id)
            for fact, (outcome, _) in comparison.fact_outcomes.items():
                kind = "waiting" if last_change(timeline, fact, exam.session_id) > last_dream[exam.session_id] else "read"
                counts["facts", kind] += 1
                counts["facts correct", kind] += outcome == "correct"
            counts["stale lines"] += sum(count for (_, outcome), count in comparison.lines.items() if outcome == "stale")
        cells = [
            percent(counts["read", "correct"], counts["read", "asked"]),
            percent(counts["waiting", "correct"], counts["waiting", "asked"]),
            percent(counts["no single fact", "correct"], counts["no single fact", "asked"]),
            percent(counts["facts correct", "read"], counts["facts", "read"]),
            percent(counts["facts correct", "waiting"], counts["facts", "waiting"]),
            counts["stale lines"],
        ]
        lines.append(f"| {run.policy} | {run.period}/{run.persona} | " + " | ".join(map(str, cells)) + " |")
    return lines


def shared_exams_table(runs: list[PolicyRun]) -> list[str]:
    """Pairs of runs that held the same notes at an exam, and whether they got the same answers (the shared cache)."""
    lines = ["| policies | period/persona | exams with the same notes | of those, same answers |", "| --- | --- | --: | --: |"]
    for index, first in enumerate(runs):
        for second in runs[index + 1:]:
            if (first.period, first.persona, first.repetition) != (second.period, second.persona, second.repetition):
                continue
            first_notes = {step.session_id: step.notes for step in first.steps}
            second_notes = {step.session_id: step.notes for step in second.steps}
            same = [(one, other) for one, other in zip(first.exams, second.exams, strict=True) if first_notes[one.session_id] == second_notes[other.session_id]]
            if same:
                lines.append(f"| {first.policy} and {second.policy} | {first.period}/{first.persona} | {len(same)} | {sum(one.answers == other.answers for one, other in same)} |")
    return lines


def end_table(period: str, runs: list[PolicyRun]) -> list[str]:
    """How the engine's end plays out: sessions after a persona's last exam, which no exam reads, and what each run
    had left undreamt at its last exam."""
    lines = ["| persona | sessions | last exam | sessions after the last exam |", "| --- | --: | --: | --: |"]
    for persona in personas(period):
        last_session = len(load_transcripts(period, persona))
        lines.append(f"| {persona} | {last_session} | {last_session // EXAM_STEP * EXAM_STEP} | {last_session % EXAM_STEP} |")
    lines += ["", "| policy | period/persona | sessions run | last exam | sessions waiting at the last exam | most sessions waiting at any exam |", "| --- | --- |" + " --: |" * 4]
    for run in runs:
        last_dream = last_dream_before(run)
        waiting = [exam.session_id - last_dream[exam.session_id] for exam in run.exams]
        lines.append(f"| {run.policy} | {run.period}/{run.persona} | {len(run.steps)} | {run.exams[-1].session_id} | {waiting[-1]} | {max(waiting)} |")
    return lines


def exam_step_table(runs: list[PolicyRun], steps: tuple[int, ...] = (7, 21)) -> list[str]:
    """The same runs graded only on the exams of sessions that are multiples of a larger step: a cheaper exam for P7.
    Each step's exams are a subset of the step-7 exams, so this costs nothing."""
    lines = [
        "| policy | period/persona | " + " | ".join(f"every {step}: exams | every {step}: official | every {step}: mean sessions waiting" for step in steps) + " |",
        "| --- | --- |" + " --: |" * (3 * len(steps)),
    ]
    for run in runs:
        last_dream = last_dream_before(run)
        cells = []
        for step in steps:
            exams = [exam for exam in run.exams if exam.session_id % step == 0]
            correct = sum(question_grade.outcome == "correct" for exam in exams for question_grade in exam.grades)
            asked = sum(len(exam.grades) for exam in exams)
            cells += [len(exams), percent(correct, asked), f"{statistics.mean(exam.session_id - last_dream[exam.session_id] for exam in exams):.1f}"]
        lines.append(f"| {run.policy} | {run.period}/{run.persona} | " + " | ".join(map(str, cells)) + " |")
    return lines


def phase_table(period: str, cadences: list[int], steps: tuple[int, ...] = (7, 14, 21, 28)) -> list[str]:
    """Mean sessions waiting at an exam under cadence k, over every persona's whole length, against the uniform (k - 1) / 2."""
    lengths = [len(load_transcripts(period, persona)) for persona in personas(period)]
    lines = ["| exam step | " + " | ".join(f"every-{cadence}" for cadence in cadences) + " |", "| --: |" + " --: |" * len(cadences)]
    lines.append("| uniform | " + " | ".join(f"{(cadence - 1) / 2:.2f}" for cadence in cadences) + " |")
    for step in steps:
        cells = []
        for cadence in cadences:
            waiting = [exam % cadence for length in lengths for exam in range(step, length + 1, step)]
            cells.append(f"{statistics.mean(waiting):.2f} ({len(set(waiting))}/{cadence} phases)")
        lines.append(f"| {step} | " + " | ".join(cells) + " |")
    return lines


def watch_table(runs: list[PolicyRun], text: str) -> list[str]:
    """Every exam question whose prompt contains `text`, with each run's answer, its outcome and the run's last dream."""
    lines = ["| exam | probe | question | " + " | ".join(run.policy for run in runs) + " |", "| --: | --- | --- |" + " --- |" * len(runs)]
    last_dreams = [last_dream_before(run) for run in runs]
    for exam_index, exam in enumerate(runs[0].exams):
        for question_index, question in enumerate(exam.questions):
            if text.casefold() not in question.prompt.casefold():
                continue
            cells = [
                f"{run.exams[exam_index].answers[question_index]} ({run.exams[exam_index].grades[question_index].outcome}, dream s{last_dream[exam.session_id]})"
                for run, last_dream in zip(runs, last_dreams)
            ]
            lines.append(f"| {exam.session_id} | {question.probe} | {question.prompt.split('?')[0]}? | " + " | ".join(cells) + " |")
    return lines


def dreams_of(run: PolicyRun) -> list[tuple[int, int, int, float]]:
    """(session, characters of the notes the dream read, sessions it read, dollars) for every dream of the run."""
    dreams = []
    notes_before = ""
    for step in run.steps:
        if step.dreamt:
            dreams.append((step.session_id, len(notes_before), step.sessions_read, step.dream_cost))
        notes_before = step.notes
    return dreams


def p4_model(note_characters: int, sessions_read: int) -> float:
    return DREAM_FIXED + DREAM_PER_THOUSAND_NOTE_CHARACTERS * note_characters / 1000 + DREAM_PER_SESSION * sessions_read


def dream_cost_table(runs: list[PolicyRun]) -> list[str]:
    lines = [
        "| policy | period/persona | dreams | sessions read per dream | notes read per dream (characters) | $ per dream | P4a model $ per dream | input tokens per dream | output tokens per dream | dream $ per session |",
        "| --- | --- |" + " --: |" * 8,
    ]
    for run in runs:
        dreams = dreams_of(run)
        if not dreams:
            continue
        dreamt_steps = [step for step in run.steps if step.dreamt]
        cells = [
            len(dreams),
            f"{statistics.mean(dream[2] for dream in dreams):.1f}",
            f"{statistics.mean(dream[1] for dream in dreams):,.0f}",
            f"{run.dream_cost() / len(dreams):.5f}",
            f"{statistics.mean(p4_model(dream[1], dream[2]) for dream in dreams):.5f}",
            f"{statistics.mean(step.dream_input_tokens for step in dreamt_steps):,.0f}",
            f"{statistics.mean(step.dream_output_tokens for step in dreamt_steps):,.0f}",
            f"{run.dream_cost() / len(run.steps):.6f}",
        ]
        lines.append(f"| {run.policy} | {run.period}/{run.persona} | " + " | ".join(map(str, cells)) + " |")
    return lines


def least_squares(rows: list[tuple[float, ...]], targets: list[float]) -> list[float]:
    """Coefficients minimizing the squared error of rows · coefficients against targets (normal equations)."""
    size = len(rows[0])
    matrix = [[sum(row[i] * row[j] for row in rows) for j in range(size)] + [sum(row[i] * target for row, target in zip(rows, targets))] for i in range(size)]
    for pivot in range(size):
        best = max(range(pivot, size), key=lambda row: abs(matrix[row][pivot]))
        matrix[pivot], matrix[best] = matrix[best], matrix[pivot]
        for row in range(size):
            if row != pivot:
                factor = matrix[row][pivot] / matrix[pivot][pivot]
                matrix[row] = [value - factor * pivot_value for value, pivot_value in zip(matrix[row], matrix[pivot])]
    return [matrix[row][size] / matrix[row][row] for row in range(size)]


def projection(runs: list[PolicyRun], timelines: dict) -> list[str]:
    """Measured: a dream cost model fitted on every dream of these runs, an exam cost model fitted on every exam, and the
    ratio of the notes to the perfect notes. Extrapolated: the dreams and exams of each cadence over the whole persona,
    with the notes growing as the perfect notes do."""
    dreams = [(characters, sessions, dollars) for run in runs for _, characters, sessions, dollars in dreams_of(run)]
    if len(dreams) < 3:
        return []
    fixed, per_character, per_session = least_squares([(1.0, characters, sessions) for characters, sessions, _ in dreams], [dollars for *_, dollars in dreams])
    exams = []
    ratios = []
    for run in runs:
        timeline = timelines[run.period, run.persona]
        last_dream = last_dream_before(run)
        notes_by_session = {step.session_id: step.notes for step in run.steps}
        for exam in run.exams:
            exams.append((len(notes_by_session[exam.session_id]), exam.cost))
            perfect = len(render_notes(timeline.state_after(last_dream[exam.session_id])))
            if perfect and last_dream[exam.session_id]:
                ratios.append(len(notes_by_session[exam.session_id]) / perfect)
    exam_fit = statistics.linear_regression([characters for characters, _ in exams], [dollars for _, dollars in exams])
    ratio = statistics.mean(ratios)
    lines = [
        f"dream $ = {fixed:.6f} + {per_character * 1000:.6f} per 1,000 note characters + {per_session:.6f} per session read (fitted on {len(dreams)} dreams; P4a: 0.00047 + 0.00004 + 0.0001)",
        f"exam $ = {exam_fit.intercept:.6f} + {exam_fit.slope * 1000:.6f} per 1,000 note characters (fitted on {len(exams)} exams)",
        f"notes / perfect notes at the same dream: {ratio:.2f} (mean of {len(ratios)} exams)",
        "",
    ]
    cadences = sorted({int(run.policy.split("-")[1]) for run in runs if run.policy.startswith("every-")})
    for period, persona in sorted(timelines):
        timeline = timelines[period, persona]
        last_session = len(load_transcripts(period, persona))
        perfect_characters = {session_id: len(render_notes(timeline.state_after(session_id))) for session_id in range(last_session + 1)}
        measured = {(run.policy, run.persona): run for run in runs}
        lines += [
            f"{period}/{persona}, all {last_session} sessions, {last_session // EXAM_STEP} exams:",
            "| policy | dreams | dream $ (extrapolated) | dream $ per session | exam $ (extrapolated) | dream $ measured over the run's sessions | extrapolated over the same sessions |",
            "| --- |" + " --: |" * 6,
        ]
        for cadence in [0, *cadences]:
            dream_sessions = list(range(cadence, last_session + 1, cadence)) if cadence else []
            dream_dollars = []
            previous = 0
            for session_id in dream_sessions:
                dream_dollars.append((session_id, fixed + per_character * ratio * perfect_characters[previous] + per_session * (session_id - previous)))
                previous = session_id
            exam_dollars = 0.0
            for exam_session in range(EXAM_STEP, last_session + 1, EXAM_STEP):
                read = max((session_id for session_id in dream_sessions if session_id <= exam_session), default=0)
                exam_dollars += exam_fit.intercept + exam_fit.slope * (ratio * perfect_characters[read] if read else 0)
            name = f"every-{cadence}" if cadence else "never"
            run = measured.get((name, persona))
            through = len(run.steps) if run else 0
            measured_cells = [f"{run.dream_cost():.4f}", f"{sum(dollars for session_id, dollars in dream_dollars if session_id <= through):.4f}"] if run else ["-", "-"]
            total = sum(dollars for _, dollars in dream_dollars)
            lines.append(f"| {name} | {len(dream_sessions)} | {total:.4f} | {total / last_session:.6f} | {exam_dollars:.4f} | " + " | ".join(measured_cells) + " |")
        lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("period")
    parser.add_argument("personas", nargs="+")
    parser.add_argument("--policies", nargs="+", default=["never", "every-1", "every-5", "every-10", "every-20", "every-50"])
    parser.add_argument("--through", type=int)
    parser.add_argument("--exam-every", type=int, default=EXAM_STEP)
    parser.add_argument("--repetition", type=int, default=0)
    parser.add_argument("--budget-name", default="p5a")
    parser.add_argument("--limit", type=float, default=1.50)
    parser.add_argument("--dry-run", action="store_true", help="estimate the cost if nothing were cached, and stop")
    parser.add_argument("--project", action="store_true", help="also fit the cost models and extrapolate them to whole personas")
    parser.add_argument("--watch", nargs="+", default=[], help="print every exam question containing this text, per policy (one persona)")
    arguments = parser.parse_args()

    client = BudgetedClient(arguments.budget_name, arguments.limit)
    if arguments.dry_run:
        for persona in arguments.personas:
            print(f"\n{arguments.period}/{persona} through {arguments.through or 'the end'}, if nothing were cached:")
            print("\n".join(estimate(arguments.policies, arguments.period, persona, arguments.through, arguments.exam_every)))
        print(f"\nBudget {arguments.budget_name}: spent ${client.spent():.4f} of ${arguments.limit:.2f}")
        return

    spent_before = client.spent()
    runs = []
    timelines = {}
    for persona in arguments.personas:
        timelines[arguments.period, persona] = build_timeline(persona_changes(arguments.period, persona))
        for name in arguments.policies:
            runs.append(run_policy(policy_named(name), arguments.period, persona, client, arguments.exam_every, arguments.through, arguments.repetition))
            print(f"{name} {arguments.period}/{persona}: done, budget {arguments.budget_name} spent ${client.spent():.4f}", flush=True)
    sections = [
        ("Runs, counted four ways", runs_table(runs).splitlines()),
        ("Official correct answers by probe", probe_table(runs, timelines)),
        ("Official correct answers by domain", domain_table(runs)),
        ("Waiting or lost", delay_table(runs, timelines)),
        ("What a dream costs", dream_cost_table(runs)),
        ("Exams shared through the cache", shared_exams_table(runs)),
        ("The end", end_table(arguments.period, runs)),
        ("A cheaper exam: the same runs on fewer exams", exam_step_table(runs)),
        ("Exam phase over whole personas", phase_table(arguments.period, sorted({policy.sessions for policy in map(policy_named, arguments.policies) if isinstance(policy, Every)}))),
    ]
    for text in arguments.watch:
        sections.append((f"Questions about {text!r}", watch_table(runs, text)))
    if arguments.project:
        sections.append(("Cost models and extrapolation to whole personas", projection(runs, timelines)))
    for title, lines in sections:
        print(f"\n## {title}\n")
        print("\n".join(lines))
    print(f"\nPaid now: ${client.spent() - spent_before:.4f}. Budget {arguments.budget_name}: spent ${client.spent():.4f} of ${arguments.limit:.2f}")


if __name__ == "__main__":
    main()
