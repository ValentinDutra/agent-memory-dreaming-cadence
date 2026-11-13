"""Project what a policy costs over whole periods, from what the measured runs paid. Owner: P5b. Calls nothing.

1. Measured: the runs of docs/p5b-sueno-disparado.md §4.2, rebuilt from the cache (a client capped at $0 refuses any
   call not cached). Every dream gives (characters of the notes it read, sessions it read, dollars), and a least-squares
   fit gives dollars = a + b per 1,000 characters of notes + c per session read. The model detector's cost per call is
   the mean of what its calls paid.
2. Extrapolated: each policy over every session of every persona of the period. The notes a dream reads are taken as
   long as the perfect notes (P4: a dream's notes are 0.91-1.06 times as long). The phrases and fixed cadences decide
   the same whatever the notes hold, so their dreams are exact; the model detector's dreams are taken where the truth
   has a fact, since it flags those with 97-100% recall and 98% precision (§4.1).

Run: uv run python -m policies.triggered_projection weekly monthly
"""

import sys

from answering.client import BudgetedClient
from answering.notes import render_notes
from dreaming.transcripts import load_transcripts
from policies.engine import PolicyRun, run_policy
from policies.session_changes import session_change
from policies.triggered import PhraseDetector, Triggered
from policies.triggered_run import BUDGET_NAME, Every, policy_named
from truth.changes import persona_changes, personas
from truth.timeline import build_timeline

MEASURED = (
    ("weekly", "software_engineer", 161, 0, ("triggered-phrases-change", "every-3", "triggered-phrases-any", "triggered-model-any", "every-2")),
    ("weekly", "software_engineer", 161, 1, ("triggered-phrases-any", "every-2")),
    ("monthly", "academic_researcher", 210, 0, ("triggered-phrases-change", "every-3", "triggered-phrases-any", "triggered-model-any", "every-2")),
    ("monthly", "startup_founder", 210, 0, ("triggered-phrases-any", "every-2")),
)
PROJECTED = ("every-1", "every-2", "every-3", "every-5", "triggered-phrases-change", "triggered-phrases-any", "triggered-model-any")


def measured_runs() -> list[PolicyRun]:
    client = BudgetedClient(BUDGET_NAME, 0.0)
    return [
        run_policy(policy_named(name, 0.0), period, persona, client, through=through, repetition=repetition)
        for period, persona, through, repetition, names in MEASURED
        for name in names
    ]


def fit(points: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    """Least squares for y = a + b x1 + c x2 over (x1, x2, y), by the normal equations and Cramer's rule."""
    rows = [(1.0, x1, x2) for x1, x2, _ in points]
    targets = [y for _, _, y in points]
    matrix = [[sum(row[i] * row[j] for row in rows) for j in range(3)] for i in range(3)]
    vector = [sum(row[i] * target for row, target in zip(rows, targets)) for i in range(3)]

    def determinant(m):
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))

    whole = determinant(matrix)
    return tuple(determinant([[vector[i] if j == column else matrix[i][j] for j in range(3)] for i in range(3)]) / whole for column in range(3))


def dreams_of(run: PolicyRun) -> list[tuple[float, float, float]]:
    """(thousands of characters of the notes the dream read, sessions read, dollars) for each dream of the run."""
    points, notes_before = [], ""
    for step in run.steps:
        if step.dreamt:
            points.append((len(notes_before) / 1000, step.sessions_read, step.dream_cost))
        notes_before = step.notes
    return points


def project(name: str, period: str, persona: str, model: tuple[float, float, float]) -> tuple[int, int, float]:
    """Sessions, dreams and dream dollars of the policy over every session of the persona."""
    timeline = build_timeline(persona_changes(period, persona))
    sessions = load_transcripts(period, persona)
    if name == "triggered-model-any":
        policy = None
    elif name.startswith("every-"):
        policy = Every(int(name.removeprefix("every-")))
    else:
        policy = Triggered(PhraseDetector(), name.removeprefix("triggered-phrases-"))
    dreams, dollars, pending = 0, 0.0, 0
    for session in sessions:
        pending += 1
        if policy is None:
            dream_now = session_change(timeline, session.session_id) != "none"
        else:
            dream_now = policy.decide("", [session], None, "").dream
        if dream_now:
            notes_kilocharacters = len(render_notes(timeline.state_after(session.session_id - pending))) / 1000
            dollars += model[0] + model[1] * notes_kilocharacters + model[2] * pending
            dreams += 1
            pending = 0
    return len(sessions), dreams, dollars


def sizes_of(period: str) -> None:
    """What the model detector and a dream read further into the period: session length and perfect notes length."""
    early, late, notes_at_210, notes_at_end = [], [], [], []
    for persona in personas(period):
        timeline = build_timeline(persona_changes(period, persona))
        sessions = load_transcripts(period, persona)
        for session in sessions:
            (early if session.session_id <= 210 else late).append(sum(len(turn.message) for turn in session.turns))
        notes_at_210.append(len(render_notes(timeline.state_after(min(210, sessions[-1].session_id)))))
        notes_at_end.append(len(render_notes(timeline.state_after(sessions[-1].session_id))))
    late_mean = f"{sum(late) / len(late):.0f}" if late else "-"
    print(f"\n{period}: characters per session, s1-210 {sum(early) / len(early):.0f}, after s210 {late_mean}; "
          f"perfect notes, mean (max) over personas: at s210 {sum(notes_at_210) / len(notes_at_210):.0f} ({max(notes_at_210)}), "
          f"at the last session {sum(notes_at_end) / len(notes_at_end):.0f} ({max(notes_at_end)})")


def main() -> None:
    runs = measured_runs()
    points = [point for run in runs for point in dreams_of(run)]
    model = fit(points)
    error = sum(abs(model[0] + model[1] * x1 + model[2] * x2 - y) for x1, x2, y in points) / len(points)
    print(f"dream $ = {model[0]:.6f} + {model[1]:.6f} per 1,000 characters of notes + {model[2]:.6f} per session read "
          f"({len(points)} measured dreams, mean absolute error ${error:.6f})")
    detector_calls = [step.decision_cost for run in runs if run.policy == "triggered-model-any" for step in run.steps]
    per_call = sum(detector_calls) / len(detector_calls)
    print(f"model detector: ${per_call:.6f} per call ({len(detector_calls)} measured calls)")

    print("\nmeasured (s1-161 weekly, s1-210 monthly; the fit applied to the same dreams in brackets)\n")
    print("| policy | period/persona | rep | dreams | dream $ (fit) | detector $ |\n| --- | --- | --: | --: | --: | --: |")
    for run in runs:
        fitted = sum(model[0] + model[1] * x1 + model[2] * x2 for x1, x2, _ in dreams_of(run))
        print(f"| {run.policy} | {run.period}/{run.persona} | {run.repetition} | {run.dreams()} | {run.dream_cost():.4f} ({fitted:.4f}) | {run.decision_cost():.4f} |")

    for period in sys.argv[1:]:
        sizes_of(period)
        print(f"\nextrapolated: {period}, every session of each of its {len(personas(period))} personas, mean per persona\n")
        print("| policy | sessions | dreams | dream $ | detector $ | total $ |\n| --- | --: | --: | --: | --: | --: |")
        for name in PROJECTED:
            projections = [project(name, period, persona, model) for persona in personas(period)]
            sessions = sum(each[0] for each in projections) / len(projections)
            dreams = sum(each[1] for each in projections) / len(projections)
            dream_dollars = sum(each[2] for each in projections) / len(projections)
            detector_dollars = sessions * per_call if "model" in name else 0.0
            print(f"| {name} | {sessions:.0f} | {dreams:.0f} | {dream_dollars:.4f} | {detector_dollars:.4f} | {dream_dollars + detector_dollars:.4f} |")


if __name__ == "__main__":
    main()
