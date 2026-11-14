"""The final grid of P7: what it would cost, running it, and the two CSVs P7b reads. Owner: P7a.

  PYTHONHASHSEED=0 uv run python -m final.grid estimate
  PYTHONHASHSEED=0 uv run python -m final.grid run monthly/<persona>:210 --repetition 0 --limit 13.00
  PYTHONHASHSEED=0 uv run python -m final.grid table
  uv run python -m final.grid compare

The grid, its order and the schema of data/p7-runs.csv and data/p7-probes.csv are in docs/p7-interfaz.md.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

from answering.client import RESULTS, BudgetedClient, BudgetExceeded
from diagnosis.criteria import nothing_logged, partial_total
from dreaming.transcripts import load_transcripts
from exam.grading import OUTCOMES, negates_removed_preference
from exam.questions import EXAM_STEP, build_exam
from exam.unreachable import unreachable
from policies.engine import PolicyRun, percent, run_policy, runs_table, score
from policies.projection import Perfect
from policies.run import policy_named
from policies.triggered_run import slice_of
from truth.changes import personas

PERIOD = "monthly"
POLICIES = ("never", "every-1", "every-5", "every-10", "every-20", "every-50", "triggered-phrases-any")
STRETCHES = (("s1-210", 1, 210), ("s211-420", 211, 420), ("s421-end", 421, None))
THROUGH = 210
REPETITIONS = (0, 1)
WHOLE_PERSONAS = ("startup_founder", "academic_researcher")
WHOLE_POLICIES = ("every-1", "every-5")
BUDGET_NAME = "p7a"
DATA = Path(__file__).resolve().parent.parent / "data"

COUNTS = ("asked", "official", "lenient", "reachable_asked", "reachable_official", "reachable_lenient")
RUN_COLUMNS = (
    "period", "persona", "policy", "repetition", "scope", "stretch", "sessions", "dreams", "sessions_read",
    "dream_cost", "decision_cost", "maintenance_cost", "exam_cost", "exams", *COUNTS, *OUTCOMES,
    "nothing_logged", "partial_total", "reachable_invented", "reachable_nothing_logged",
)
PROBE_COLUMNS = ("period", "persona", "policy", "repetition", "scope", "stretch", "domain", "probe", *COUNTS)
DOLLAR_COLUMNS = ("dream_cost", "decision_cost", "maintenance_cost", "exam_cost")
# P5's cost model as fitted on 2,666 dreams and 1,012 exams (docs/p5-politicas.md §4.3). The cache it was fitted on
# was lost, so it is fixed here: (dream base, per 1,000 note characters, per session read), (exam base, per 1,000
# note characters), and a dream's notes / perfect notes.
DREAM_MODEL = (0.000204, 0.000039, 0.000133)
EXAM_MODEL = (0.000454, 0.000065)
NOTES_RATIO = 1.00
# The whole runs P6 had paid, apart from the one the user's option (b) added (docs/p6-inventadas.md).
REPAID_WHOLE_RUNS = (("startup_founder", "every-5"), ("academic_researcher", "every-1"), ("academic_researcher", "every-5"))
# The validation against the numbers before the cache was lost (docs/p7-interfaz.md § Validación). Fixed cadences and
# the phrase detector decide without reading the notes, so these columns must not move. Accuracy may move by the noise
# of a policy repeated whole (P5a §4.4), reported past it and stopping past twice it.
BEFORE_LOSS = DATA / "p7-runs-before-loss.csv"
EXACT_COLUMNS = ("sessions", "dreams", "sessions_read", "exams", "asked")
NOISE_POINTS = 2.8
FIXED_ORDER = ("every-1", "every-5", "every-10", "every-20", "every-50", "never")


def in_stretch(session_id: int, first: int, last: int | None) -> bool:
    return first <= session_id and (last is None or session_id <= last)


def question_counts(graded, marked: dict) -> Counter:
    """graded: (question, grade) pairs. The four counts, the five official outcomes and the two criteria of P6."""
    counts = Counter({column: 0 for column in (*COUNTS, *OUTCOMES, "nothing_logged", "partial_total", "reachable_invented", "reachable_nothing_logged")})
    for question, grade in graded:
        official = grade.outcome == "correct"
        lenient = official or negates_removed_preference(question, grade)
        reachable = question.question_id not in marked
        logged_nothing = nothing_logged(question, grade)
        counts.update(
            asked=1, official=official, lenient=lenient,
            reachable_asked=reachable, reachable_official=reachable and official, reachable_lenient=reachable and lenient,
            nothing_logged=logged_nothing, partial_total=partial_total(question, grade),
            reachable_invented=reachable and grade.outcome == "invented", reachable_nothing_logged=reachable and logged_nothing,
        )
        counts[grade.outcome] += 1
    return counts


def run_keys(run: PolicyRun, scope: str) -> dict:
    return {"period": run.period, "persona": run.persona, "policy": run.policy, "repetition": run.repetition, "scope": scope}


def stretch_rows(run: PolicyRun, scope: str) -> list[dict]:
    """One row of data/p7-runs.csv per stretch with sessions."""
    marked = unreachable(run.period, run.persona)
    rows = []
    for stretch, first, last in STRETCHES:
        steps = [step for step in run.steps if in_stretch(step.session_id, first, last)]
        if not steps:
            continue
        exams = [exam for exam in run.exams if in_stretch(exam.session_id, first, last)]
        dream_cost = sum(step.dream_cost for step in steps)
        decision_cost = sum(step.decision_cost for step in steps)
        counts = question_counts(((question, grade) for exam in exams for question, grade in zip(exam.questions, exam.grades, strict=True)), marked)
        rows.append(run_keys(run, scope) | {
            "stretch": stretch,
            "sessions": len(steps),
            "dreams": sum(step.dreamt for step in steps),
            "sessions_read": sum(step.sessions_read for step in steps),
            "dream_cost": dream_cost,
            "decision_cost": decision_cost,
            "maintenance_cost": dream_cost + decision_cost,
            "exam_cost": sum(exam.cost for exam in exams),
            "exams": len(exams),
        } | {column: counts[column] for column in RUN_COLUMNS[RUN_COLUMNS.index("asked"):]})
    return rows


def probe_rows(run: PolicyRun, scope: str) -> list[dict]:
    """Rows of data/p7-probes.csv: one per stretch, domain and probe with at least one question."""
    marked = unreachable(run.period, run.persona)
    groups = {}
    for exam in run.exams:
        stretch = next(name for name, first, last in STRETCHES if in_stretch(exam.session_id, first, last))
        for question, grade in zip(exam.questions, exam.grades, strict=True):
            groups.setdefault((stretch, question.domain, question.probe), []).append((question, grade))
    rows = []
    for (stretch, domain, probe), graded in sorted(groups.items(), key=lambda item: ([name for name, *_ in STRETCHES].index(item[0][0]), item[0][1], item[0][2])):
        counts = question_counts(graded, marked)
        rows.append(run_keys(run, scope) | {"stretch": stretch, "domain": domain, "probe": probe} | {column: counts[column] for column in COUNTS})
    return rows


def check(run: PolicyRun, rows: list[dict], probes: list[dict]) -> None:
    """The invariants of docs/p7-interfaz.md: a run's stretches add up to the run, and its probes to its stretches."""
    problems = []
    for row in rows:
        if row["correct"] != row["official"]:
            problems.append(f"{row['stretch']}: correct {row['correct']} != official {row['official']}")
        if sum(row[outcome] for outcome in OUTCOMES) != row["asked"]:
            problems.append(f"{row['stretch']}: the five outcomes do not add up to asked")
        probe_totals = Counter()
        for probe in probes:
            if probe["stretch"] == row["stretch"]:
                probe_totals.update({column: probe[column] for column in COUNTS})
        if any(probe_totals[column] != row[column] for column in COUNTS):
            problems.append(f"{row['stretch']}: the probes do not add up to the stretch")
    run_score = score(run)
    whole = {
        "sessions": len(run.steps), "dreams": run.dreams(), "exams": len(run.exams), "asked": run_score.asked,
        "official": run_score.correct, "lenient": run_score.lenient, "reachable_asked": run_score.reachable_asked,
        "reachable_official": run_score.reachable_correct, "reachable_lenient": run_score.reachable_lenient,
    }
    for column, value in whole.items():
        if sum(row[column] for row in rows) != value:
            problems.append(f"{column}: the stretches add up to {sum(row[column] for row in rows)}, the run has {value}")
    for column, value in (("dream_cost", run.dream_cost()), ("decision_cost", run.decision_cost()), ("exam_cost", run.exam_cost())):
        if abs(sum(row[column] for row in rows) - value) > 1e-9:
            problems.append(f"{column}: the stretches do not add up to the run's ${value:.6f}")
    if problems:
        raise ValueError(f"{run.policy} on {run.period}/{run.persona} r{run.repetition}: " + "; ".join(problems))


# --- The grid ---------------------------------------------------------------------------------------------------


def grid() -> list[tuple[str, str, str, int, int | None]]:
    """(scope, persona, policy, repetition, through) of every run in the grid."""
    runs = [("s1-210", persona, policy, repetition, THROUGH) for repetition in REPETITIONS for persona in personas(PERIOD) for policy in POLICIES]
    return runs + [("whole", persona, policy, 0, None) for persona in WHOLE_PERSONAS for policy in WHOLE_POLICIES]


def table() -> None:
    """Rewrite both CSVs from the cache, with a cap of $0. A run not fully cached is left out and listed."""
    client = BudgetedClient(BUDGET_NAME, 0.0)
    runs, probes, missing = [], [], []
    for scope, persona, policy, repetition, through in grid():
        try:
            run = run_policy(policy_named(policy, BUDGET_NAME, 0.0), PERIOD, persona, client, through=through, repetition=repetition)
        except BudgetExceeded:
            missing.append(f"{policy} {PERIOD}/{persona} r{repetition} {scope}")
            continue
        rows, run_probes = stretch_rows(run, scope), probe_rows(run, scope)
        check(run, rows, run_probes)
        runs += rows
        probes += run_probes
    DATA.mkdir(exist_ok=True)
    write_csv(DATA / "p7-runs.csv", RUN_COLUMNS, runs)
    write_csv(DATA / "p7-probes.csv", PROBE_COLUMNS, probes)
    print(f"data/p7-runs.csv: {len(runs)} rows; data/p7-probes.csv: {len(probes)} rows")
    print_summary(runs)
    print(f"\nnot fully cached, left out ({len(missing)}):" + "".join(f"\n- {name}" for name in missing))


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: f"{row[column]:.6f}" if column in DOLLAR_COLUMNS else row[column] for column in columns})


def print_summary(rows: list[dict]) -> None:
    print("\n## s1-210, per persona\n")
    print("| persona | policy | rep | dreams | maintenance $ | exam $ | official | lenient | official without marked | lenient without marked | invented | nothing_logged | partial_total |")
    print("| --- | --- | --: |" + " --: |" * 10)
    for row in rows:
        if row["scope"] == "s1-210":
            print(summary_line(row, row["persona"], row["policy"], row["repetition"]))
    print("\n## Whole personas, per stretch (repetition 0)\n")
    print("| persona | policy | stretch | dreams | maintenance $ | exam $ | official | lenient | official without marked | lenient without marked | invented | nothing_logged | partial_total |")
    print("| --- | --- | --- |" + " --: |" * 10)
    for row in rows:
        if row["scope"] == "whole":
            print(summary_line(row, row["persona"], row["policy"], row["stretch"]))


def summary_line(row: dict, *keys) -> str:
    cells = [
        *keys, row["dreams"], f"{row['maintenance_cost']:.4f}", f"{row['exam_cost']:.4f}",
        percent(row["official"], row["asked"]), percent(row["lenient"], row["asked"]),
        percent(row["reachable_official"], row["reachable_asked"]), percent(row["reachable_lenient"], row["reachable_asked"]),
        row["invented"], row["nothing_logged"], row["partial_total"],
    ]
    return "| " + " | ".join(map(str, cells)) + " |"


# --- Cost before paying -----------------------------------------------------------------------------------------


class CacheProbe:
    """A client with a cap of $0 that counts the dreams and the exams it answered from the cache before the first it could not."""

    def __init__(self):
        self.client = BudgetedClient(BUDGET_NAME, 0.0)
        self.thinking = self.client.thinking
        self.effort = self.client.effort
        self.served = Counter()

    def complete(self, run: str, system: str, user: str, max_tokens: int, repeat: int = 0):
        completion = self.client.complete(run, system, user, max_tokens, repeat=repeat)
        self.served["dream" if "/dream/" in run else "exam"] += 1
        return completion


class Estimator:
    """Projects each request a run would make with P5's cost model (DREAM_MODEL, EXAM_MODEL), and prices only the ones
    neither the cache nor an earlier run of the same repetition holds.

    Fixed cadences and the phrase detector decide without reading the notes, so a run's requests are known before
    running it. Two runs that dreamt after the same sessions hold the same notes, so a request is identified by the
    sessions it dreamt after so far and the session it is made at: never and every-50 share their exams up to s49.
    """

    def __init__(self):
        self.perfect = Perfect()
        self.dream_model, self.exam_model, self.ratio = DREAM_MODEL, EXAM_MODEL, NOTES_RATIO
        self.known = set()
        self.exam_sessions = {}

    def requests(self, persona: str, policy_name: str, repetition: int, through: int | None) -> list[tuple[tuple, float]]:
        """(request, projected $) in the order the engine makes them."""
        if persona not in self.exam_sessions:
            self.exam_sessions[persona] = {question.session_id for question in build_exam(PERIOD, persona) if question.session_id % EXAM_STEP == 0}
        policy = policy_named(policy_name, BUDGET_NAME, 0.0)
        dream_base, dream_per_kilocharacter, dream_per_session = self.dream_model
        exam_base, exam_per_kilocharacter = self.exam_model
        dreamt_after, pending, requests = (), [], []
        for session in load_transcripts(PERIOD, persona):
            if through is not None and session.session_id > through:
                break
            pending.append(session)
            if policy.decide("", list(pending), None, "").dream:
                notes = self.ratio * self.perfect.length(PERIOD, persona, dreamt_after[-1] if dreamt_after else 0)
                cost = dream_base + dream_per_kilocharacter * notes / 1000 + dream_per_session * len(pending)
                requests.append((("dream", persona, repetition, dreamt_after, session.session_id), cost))
                dreamt_after, pending = dreamt_after + (session.session_id,), []
            if session.session_id in self.exam_sessions[persona]:
                notes = self.ratio * self.perfect.length(PERIOD, persona, dreamt_after[-1] if dreamt_after else 0)
                requests.append((("exam", persona, repetition, dreamt_after, session.session_id), exam_base + exam_per_kilocharacter * notes / 1000))
        return requests

    def cached(self, persona: str, policy_name: str, repetition: int, through: int | None, requests: list[tuple[tuple, float]]) -> set[tuple]:
        """The requests of the run the cache answers: the ones before its first missing call."""
        if not any((RESULTS / "raw" / "p5" / f"r{repetition}").glob(f"*/{PERIOD}/{persona}")):
            return set()
        probe = CacheProbe()
        try:
            run_policy(policy_named(policy_name, BUDGET_NAME, 0.0), PERIOD, persona, probe, through=through, repetition=repetition)
        except BudgetExceeded:
            pass
        dreams = [request for request, _ in requests if request[0] == "dream"][:probe.served["dream"]]
        exams = [request for request, _ in requests if request[0] == "exam"][:probe.served["exam"]]
        return set(dreams + exams)

    def cost(self, persona: str, policy_name: str, repetition: int, through: int | None) -> tuple[int, int, float]:
        """(dreams, exams, $) still to pay for this run, after the cache and the runs estimated before it."""
        requests = self.requests(persona, policy_name, repetition, through)
        self.known |= self.cached(persona, policy_name, repetition, through, requests)
        to_pay = [(request, cost) for request, cost in requests if request not in self.known]
        self.known |= {request for request, _ in to_pay}
        return (
            sum(request[0] == "dream" for request, _ in to_pay),
            sum(request[0] == "exam" for request, _ in to_pay),
            sum(cost for _, cost in to_pay),
        )

    def runs_cost(self, persona: str, policies: tuple[str, ...], repetition: int, through: int | None) -> tuple[int, int, float]:
        costs = [self.cost(persona, policy, repetition, through) for policy in policies]
        return tuple(sum(column) for column in zip(*costs))


def estimate() -> None:
    """What the rest of the grid costs, in the order of docs/p7-interfaz.md, without calling anything."""
    estimator = Estimator()
    dream_base, dream_per_kilocharacter, dream_per_session = estimator.dream_model
    exam_base, exam_per_kilocharacter = estimator.exam_model
    print(f"dream $ = {dream_base:.6f} + {dream_per_kilocharacter:.6f} per 1,000 note characters + {dream_per_session:.6f} per session read")
    print(f"exam $ = {exam_base:.6f} + {exam_per_kilocharacter:.6f} per 1,000 note characters; notes = {estimator.ratio:.2f} x perfect notes")
    first = {persona: estimator.runs_cost(persona, POLICIES, 0, THROUGH) for persona in personas(PERIOD)}
    order = sorted(first, key=lambda persona: first[persona][2])
    whole_runs = [(persona, policy) for persona in WHOLE_PERSONAS for policy in WHOLE_POLICIES if (persona, policy) not in REPAID_WHOLE_RUNS]
    whole_runs += list(REPAID_WHOLE_RUNS)
    whole = {(persona, policy): estimator.cost(persona, policy, 0, None) for persona, policy in whole_runs}
    second = {persona: estimator.runs_cost(persona, POLICIES, 1, THROUGH) for persona in order}
    print("\nStill to pay, in the order of the run (a run pays only what the cache and the runs above it do not hold)\n")
    print("| step | run | dreams | exams | $ |\n| --- | --- | --: | --: | --: |")
    for persona in order:
        print(estimate_line("1. s1-210 r0", persona, first[persona]))
    for persona, policy in whole_runs:
        step = "2b. whole r0, paid before by P5/P6" if (persona, policy) in REPAID_WHOLE_RUNS else "2a. whole r0"
        print(estimate_line(step, f"{persona} {policy}", whole[persona, policy]))
    for persona in order:
        print(estimate_line("3. s1-210 r1", persona, second[persona]))
    totals = {
        "s1-210 r0": sum(costs[2] for costs in first.values()),
        "whole r0, new": sum(whole[run][2] for run in whole_runs if run not in REPAID_WHOLE_RUNS),
        "whole r0, paid before": sum(whole[run][2] for run in REPAID_WHOLE_RUNS),
        "s1-210 r1": sum(costs[2] for costs in second.values()),
    }
    print("\ntotal: " + " + ".join(f"{name} ${dollars:.4f}" for name, dollars in totals.items()) + f" = ${sum(totals.values()):.4f}")


def estimate_line(step: str, name: str, costs: tuple[int, int, float]) -> str:
    dreams, exams, dollars = costs
    return f"| {step} | {name} | {dreams} | {exams} | {dollars:.4f} |"


# --- Validation against the numbers before the cache was lost -----------------------------------------------------


def read_runs(path: Path) -> dict[tuple, dict]:
    """The repetition 0 rows of a p7-runs.csv, by (persona, policy, scope, stretch)."""
    with path.open(newline="") as file:
        return {(row["persona"], row["policy"], row["scope"], row["stretch"]): row for row in csv.DictReader(file) if row["repetition"] == "0"}


def accuracy(row: dict) -> float:
    return 100 * int(row["official"]) / int(row["asked"])


def compare_runs(before: dict[tuple, dict], after: dict[tuple, dict]) -> list[dict]:
    """One line per row in both: the exact columns that moved, the official accuracy before and after, and a verdict."""
    lines = []
    for key in (key for key in before if key in after):
        moved = [column for column in EXACT_COLUMNS if before[key][column] != after[key][column]]
        difference = accuracy(after[key]) - accuracy(before[key])
        verdict = "stop" if moved or abs(difference) > 2 * NOISE_POINTS else "report" if abs(difference) > NOISE_POINTS else "ok"
        lines.append({"key": key, "moved": moved, "before": accuracy(before[key]), "after": accuracy(after[key]), "difference": difference, "verdict": verdict})
    return lines


def fixed_order(rows: dict[tuple, dict], persona: str) -> str:
    """Whether every-1 > every-5 > ... > never on official accuracy over s1-210."""
    keys = [(persona, policy, "s1-210", "s1-210") for policy in FIXED_ORDER]
    if any(key not in rows for key in keys):
        return "incomplete"
    accuracies = [accuracy(rows[key]) for key in keys]
    return "holds" if all(higher > lower for higher, lower in zip(accuracies, accuracies[1:])) else "broken"


def compare() -> None:
    """data/p7-runs.csv against data/p7-runs-before-loss.csv. Exits with 1 if a run must stop."""
    before, after = read_runs(BEFORE_LOSS), read_runs(DATA / "p7-runs.csv")
    lines = compare_runs(before, after)
    print("| persona | policy | scope | stretch | exact columns that moved | official before | official after | difference (points) | verdict |")
    print("| --- | --- | --- | --- | --- | --: | --: | --: | --- |")
    for line in lines:
        moved = ", ".join(f"{column} {before[line['key']][column]} -> {after[line['key']][column]}" for column in line["moved"]) or "none"
        print("| " + " | ".join(line["key"]) + f" | {moved} | {line['before']:.1f} % | {line['after']:.1f} % | {line['difference']:+.1f} | {line['verdict']} |")
    print("\norder every-1 > 5 > 10 > 20 > 50 > never, s1-210 official:")
    for persona in dict.fromkeys(key[0] for key in before):
        print(f"- {persona}: before {fixed_order(before, persona)}, after {fixed_order(after, persona)}")
    not_run = [key for key in before if key not in after]
    print(f"\nnot in data/p7-runs.csv yet ({len(not_run)}):" + "".join("\n- " + " ".join(key) for key in not_run))
    verdicts = Counter(line["verdict"] for line in lines)
    print(f"\nverdicts: {verdicts['ok']} ok, {verdicts['report']} report (over {NOISE_POINTS} points), {verdicts['stop']} stop (a count moved or over {2 * NOISE_POINTS:.1f} points)")
    if verdicts["stop"]:
        raise SystemExit(1)


def run(spec: str, repetition: int, limit: float, policies: tuple[str, ...]) -> None:
    """Pay what is missing of these runs, up to the p7a cap. No retry: a failed call stops here, and the cache keeps what was paid."""
    period, persona, through = slice_of(spec)
    if period != PERIOD:
        raise ValueError(f"the grid is {PERIOD} only")
    dreams, exams, dollars = Estimator().runs_cost(persona, policies, repetition, through)
    print(f"estimate for {spec} r{repetition}: {dreams} dreams and {exams} exams to pay, ${dollars:.4f}", flush=True)
    client = BudgetedClient(BUDGET_NAME, limit)
    spent_before = client.spent()
    runs = []
    try:
        for name in policies:
            runs.append(run_policy(policy_named(name, BUDGET_NAME, limit), period, persona, client, through=through, repetition=repetition))
            print(f"{name}: done, ${client.spent() - spent_before:.4f} paid so far", flush=True)
    finally:
        if runs:
            print(runs_table(runs))
        print(f"\n{BUDGET_NAME} spent: ${spent_before:.4f} before, ${client.spent():.4f} after (this run: ${client.spent() - spent_before:.4f})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("estimate", help="$ still to pay per persona, calling nothing")
    paying = commands.add_parser("run", help="pay what is missing, up to the p7a cap")
    paying.add_argument("slice", help='"monthly/persona[:through]"')
    paying.add_argument("--repetition", type=int, required=True)
    paying.add_argument("--limit", type=float, required=True)
    paying.add_argument("--policies", nargs="+", default=POLICIES)
    commands.add_parser("table", help="rewrite data/p7-runs.csv and data/p7-probes.csv from the cache, cap $0")
    commands.add_parser("compare", help="data/p7-runs.csv against the numbers before the cache was lost")
    arguments = parser.parse_args()
    if arguments.command == "estimate":
        estimate()
    elif arguments.command == "compare":
        compare()
    elif arguments.command == "run":
        run(arguments.slice, arguments.repetition, arguments.limit, tuple(arguments.policies))
    else:
        table()


if __name__ == "__main__":
    main()
