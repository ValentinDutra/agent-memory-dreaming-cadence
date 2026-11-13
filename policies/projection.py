"""What each policy would cost over whole personas, from what the cached dreams and exams paid. Owner: P5. Calls nothing.

1. Fit, on every dream and exam cached under results/raw/p5/ that reads no session past --fit-through:
   dream $ = a + b per 1,000 characters of the notes it read + c per session it read; exam $ = d + e per 1,000
   characters of the notes it read. A dream's notes run about `ratio` times the perfect notes after the same session.
2. Check the fit against the one policy run over a whole monthly persona (every-5, monthly/academic_researcher).
3. Project every policy over every session of every persona of a period. Fixed cadences and the phrase detector
   decide without reading the notes, so their dreams are exact; the notes are the perfect notes times `ratio`.

Run: uv run python -m policies.projection weekly monthly
"""

import argparse
import json
import re
from pathlib import Path
from statistics import mean

from answering.answer import exam_prompt
from answering.client import RESULTS
from answering.notes import render_notes
from dreaming.transcripts import load_transcripts
from exam.questions import EXAM_STEP, build_exam
from policies.fixed import policy_named as fixed_policy
from policies.triggered import PhraseDetector, Triggered
from truth.changes import persona_changes, personas
from truth.timeline import build_timeline

POLICIES = ("never", "every-1", "every-2", "every-3", "every-5", "every-10", "every-20", "every-50", "triggered-phrases-change", "triggered-phrases-any")
CACHE = RESULTS / "raw" / "p5"
NOTES = re.compile(r"<notes>\n(.*?)\n</notes>", flags=re.DOTALL)
SESSION = re.compile(r'<session number="(\d+)"')


def policy_named(name: str):
    if name.startswith("triggered-phrases-"):
        return Triggered(PhraseDetector(), name.removeprefix("triggered-phrases-"))
    return fixed_policy(name)


def cached(kind: str) -> list[tuple[str, str, dict]]:
    """(period, persona, record) of every cached call of this kind: "dream" or "exam"."""
    return [(path.parent.parent.name, path.parent.name, json.loads(path.read_text())) for path in CACHE.glob(f"r*/{kind}/*/*/*.json")]


def least_squares(rows: list[list[float]], targets: list[float]) -> list[float]:
    """Solve the normal equations by Gaussian elimination: a handful of unknowns."""
    size = len(rows[0])
    matrix = [[sum(row[i] * row[j] for row in rows) for j in range(size)] + [sum(row[i] * target for row, target in zip(rows, targets))] for i in range(size)]
    for pivot in range(size):
        for below in range(pivot + 1, size):
            factor = matrix[below][pivot] / matrix[pivot][pivot]
            matrix[below] = [value - factor * pivot_value for value, pivot_value in zip(matrix[below], matrix[pivot])]
    solution = [0.0] * size
    for row in reversed(range(size)):
        solution[row] = (matrix[row][size] - sum(matrix[row][column] * solution[column] for column in range(row + 1, size))) / matrix[row][row]
    return solution


class Perfect:
    """Perfect notes' length after each session, per persona, computed once."""

    def __init__(self):
        self.lengths = {}

    def length(self, period: str, persona: str, session_id: int) -> int:
        if (period, persona) not in self.lengths:
            timeline = build_timeline(persona_changes(period, persona))
            last = load_transcripts(period, persona)[-1].session_id
            self.lengths[period, persona] = [len(render_notes(timeline.state_after(session))) if session else 0 for session in range(last + 1)]
        return self.lengths[period, persona][session_id]


def fit(fit_through: int, perfect: Perfect):
    dream_rows, dream_costs, ratios = [], [], []
    for period, persona, record in cached("dream"):
        read = [int(number) for number in SESSION.findall(record["request"]["user"])]
        if max(read) > fit_through:
            continue
        notes = NOTES.search(record["request"]["user"]).group(1)
        dream_rows.append([1.0, len(notes) / 1000, len(read)])
        dream_costs.append(record["cost"])
        if read[0] > 1 and perfect.length(period, persona, read[0] - 1):
            ratios.append(len(notes) / perfect.length(period, persona, read[0] - 1))
    exam_rows, exam_costs = [], []
    exam_sessions = {}
    for period, persona, record in cached("exam"):
        if (period, persona) not in exam_sessions:
            exam_sessions[period, persona] = questions_to_session(period, persona)
        questions = record["request"]["user"].split("</notes>", 1)[1]
        if exam_sessions[period, persona][questions] > fit_through:
            continue
        exam_rows.append([1.0, len(NOTES.search(record["request"]["user"]).group(1)) / 1000])
        exam_costs.append(record["cost"])
    return least_squares(dream_rows, dream_costs), least_squares(exam_rows, exam_costs), mean(ratios), len(dream_costs), len(exam_costs)


def questions_to_session(period: str, persona: str) -> dict[str, int]:
    """The exam prompt after its notes -> the session of that exam: a cached exam records its prompt, not its session."""
    by_session = {}
    for question in build_exam(period, persona):
        by_session.setdefault(question.session_id, []).append(question)
    return {exam_prompt("", questions).split("</notes>", 1)[1]: session_id for session_id, questions in by_session.items()}


def project(name: str, period: str, persona: str, dream_model, exam_model, ratio: float, perfect: Perfect) -> tuple[int, float, float]:
    """(dreams, dream $, exam $) of the policy over all the persona's sessions, with exams every 7."""
    policy = policy_named(name)
    base, per_kilocharacter, per_session = dream_model
    exam_base, exam_per_kilocharacter = exam_model
    dreams, dream_dollars, exam_dollars, pending, last_dream = 0, 0.0, 0.0, [], 0
    for session in load_transcripts(period, persona):
        pending.append(session)
        if policy.decide("", list(pending), None, "").dream:
            notes = ratio * perfect.length(period, persona, last_dream)
            dream_dollars += base + per_kilocharacter * notes / 1000 + per_session * len(pending)
            dreams, pending, last_dream = dreams + 1, [], session.session_id
        if session.session_id % EXAM_STEP == 0:
            exam_dollars += exam_base + exam_per_kilocharacter * ratio * perfect.length(period, persona, last_dream) / 1000
    return dreams, dream_dollars, exam_dollars


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("periods", nargs="+")
    parser.add_argument("--fit-through", type=int, default=210, help="fit on cached calls that read no session past this one")
    arguments = parser.parse_args()
    perfect = Perfect()
    dream_model, exam_model, ratio, dream_count, exam_count = fit(arguments.fit_through, perfect)
    print(f"dream $ = {dream_model[0]:.6f} + {dream_model[1]:.6f} per 1,000 note characters + {dream_model[2]:.6f} per session read ({dream_count} dreams)")
    print(f"exam $ = {exam_model[0]:.6f} + {exam_model[1]:.6f} per 1,000 note characters ({exam_count} exams)")
    print(f"a dream's notes / perfect notes after the same session: {ratio:.2f}")
    dreams, dream_dollars, exam_dollars = project("every-5", "monthly", "academic_researcher", dream_model, exam_model, ratio, perfect)
    print(f"\ncheck, every-5 over all of monthly/academic_researcher: projected {dreams} dreams ${dream_dollars:.4f} + exams ${exam_dollars:.4f}"
          " (measured: uv run python -m policies.run monthly/academic_researcher --policies every-5 --check-cache)")
    for period in arguments.periods:
        everyone = personas(period)
        print(f"\n{period}: mean per persona over the {len(everyone)} personas, all sessions, exams every {EXAM_STEP}")
        print("| policy | dreams | dream $ | exam $ | total $ | total $, all personas |\n| --- | --: | --: | --: | --: | --: |")
        for name in POLICIES:
            rows = [project(name, period, persona, dream_model, exam_model, ratio, perfect) for persona in everyone]
            dreams, dream_dollars, exam_dollars = (mean(column) for column in zip(*rows))
            total = dream_dollars + exam_dollars
            print(f"| {name} | {dreams:.0f} | {dream_dollars:.4f} | {exam_dollars:.4f} | {total:.4f} | {total * len(everyone):.2f} |")


if __name__ == "__main__":
    main()
