"""Run triggered policies end to end with the engine of P5, next to a fixed cadence as reference. Owner: P5b.

Policies are named on the command line:
  every-<n>                              a dream every n sessions (a minimal reference; P5a owns policies/fixed.py)
  triggered-<detector>-<any|change>[-wait<k>]  detector: phrases, model, model-notes, screened-model

Run:
  uv run python -m policies.triggered_run weekly/software_engineer:161 monthly/academic_researcher:210 \
      --policies triggered-model-any every-5 --dry-run

The dry run calls nothing. Fixed cadences and detectors that read only the session decide the same way whatever the
notes hold, so their dreams are known before running: their cost is estimated with P4's model over the perfect notes'
size. The detector's verdicts come from the cache (a verdict not cached yet counts as a dream). This script reads the
truth to measure and to estimate; the policies never do.
"""

import argparse
from collections import Counter

from answering.client import BudgetedClient, BudgetExceeded
from answering.notes import render_notes
from dreaming.transcripts import load_transcripts
from exam.questions import EXAM_STEP
from exam.schema import DOMAINS
from policies.engine import Decision, PolicyRun, percent, run_policy, runs_table, score
from policies.session_changes import session_change
from policies.triggered import ModelDetector, PhraseDetector, Screened, Triggered
from truth.changes import persona_changes
from truth.timeline import build_timeline

BUDGET_NAME = "p5b"
DETECTOR_THINKING = {"type": "disabled"}
# P4a's cost model of one dream (docs/p4-sueno.md §4.4), and P4's measured exam cost: total minus dreams over the
# exams of the three monthly chains, about $0.0006-0.0007 each.
DREAM_DOLLARS = 0.00047
DREAM_DOLLARS_PER_NOTES_KILOCHARACTER = 0.00004
DREAM_DOLLARS_PER_SESSION = 0.0001
EXAM_DOLLARS = 0.0007
DETECTOR_DOLLARS_PER_SESSION = {"model": 0.00015, "screened-model": 0.00012, "model-notes": 0.00045}


class Every:
    name: str

    def __init__(self, sessions: int):
        self.sessions = sessions
        self.name = f"every-{sessions}"

    def decide(self, notes, pending, client, run) -> Decision:
        return Decision(pending[-1].session_id % self.sessions == 0)


def policy_named(name: str, limit: float, budget_name: str = BUDGET_NAME):
    if name.startswith("every-"):
        return Every(int(name.removeprefix("every-")))
    parts = name.removeprefix("triggered-").split("-")
    max_wait = int(parts.pop().removeprefix("wait")) if parts[-1].startswith("wait") else None
    target = parts.pop()
    detector_name = "-".join(parts)
    if detector_name == "phrases":
        detector = PhraseDetector()
    else:
        client = BudgetedClient(budget_name, limit, thinking=DETECTOR_THINKING, effort="low")
        model = ModelDetector(client, with_notes=detector_name.endswith("model-notes"))
        detector = Screened(model) if detector_name.startswith("screened-") else model
    policy = Triggered(detector, target, max_wait)
    if policy.name != name:
        raise ValueError(f"unknown policy {name!r}")
    return policy


def slice_of(spec: str) -> tuple[str, str, int | None]:
    name, _, through = spec.partition(":")
    period, persona = name.split("/")
    return period, persona, int(through) if through else None


def estimate(policy, period: str, persona: str, through: int | None, repetition: int) -> tuple[int, float, float]:
    """Dreams, dollars of dreams and dollars of detector calls if nothing were cached, without calling the API."""
    timeline = build_timeline(persona_changes(period, persona))
    sessions = [session for session in load_transcripts(period, persona) if through is None or session.session_id <= through]
    if isinstance(policy, Triggered) and isinstance(policy.detector, ModelDetector) and policy.detector.with_notes:
        policy = Triggered(PhraseDetector(), policy.target, policy.max_wait)  # its notes are unknown before the run
    dreams, dream_dollars, detector_dollars, pending = 0, 0.0, 0.0, []
    for session in sessions:
        pending.append(session)
        try:
            dream_now = policy.decide("", list(pending), None, f"p5/r{repetition}/decide/{policy.name}/{period}/{persona}").dream
        except BudgetExceeded:  # not cached yet: the cap of 0 refuses the call
            dream_now = True
            detector_dollars += DETECTOR_DOLLARS_PER_SESSION[policy.detector.name]
        if dream_now:
            notes_characters = len(render_notes(timeline.state_after(session.session_id)))
            dream_dollars += DREAM_DOLLARS + DREAM_DOLLARS_PER_NOTES_KILOCHARACTER * notes_characters / 1000 + DREAM_DOLLARS_PER_SESSION * len(pending)
            dreams += 1
            pending = []
    return dreams, dream_dollars, detector_dollars


def waiting_at_exams(run: PolicyRun) -> tuple[float, float]:
    """At each exam, the sessions not dreamt yet, and how many of them changed the truth (P1). Averages over the exams."""
    timeline = build_timeline(persona_changes(run.period, run.persona))
    exam_sessions = {exam.session_id for exam in run.exams}
    waiting, with_facts, exams = 0, 0, 0
    undreamt = []
    for step in run.steps:
        undreamt = [] if step.dreamt else undreamt + [step.session_id]
        if step.session_id in exam_sessions:
            exams += 1
            waiting += len(undreamt)
            with_facts += sum(session_change(timeline, session_id) != "none" for session_id in undreamt)
    return waiting / exams, with_facts / exams


def report(runs: list[PolicyRun]) -> None:
    print(runs_table(runs))
    print("\n| policy | period/persona | rep | total $ | sessions per dream | waiting at an exam | of them with facts |\n| --- | --- | --: | --: | --: | --: | --: |")
    for run in runs:
        waiting, with_facts = waiting_at_exams(run)
        total = run.dream_cost() + run.decision_cost() + run.exam_cost()
        print(f"| {run.policy} | {run.period}/{run.persona} | {run.repetition} | {total:.4f} | {len(run.steps) / max(run.dreams(), 1):.2f} | {waiting:.2f} | {with_facts:.2f} |")
    print("\nofficial correct by domain\n\n| policy | period/persona | rep | " + " | ".join(DOMAINS) + " |\n| --- | --- | --: |" + " --: |" * len(DOMAINS))
    for run in runs:
        cells = [percent(score(run, (domain,)).correct, score(run, (domain,)).asked) for domain in DOMAINS]
        print(f"| {run.policy} | {run.period}/{run.persona} | {run.repetition} | " + " | ".join(cells) + " |")
    print("\nofficial correct by probe\n")
    probes = ("recent_change", "new", "stable", "never_existed", "aggregate")
    print("| policy | period/persona | rep | " + " | ".join(probes) + " |\n| --- | --- | --: |" + " --: |" * len(probes))
    for run in runs:
        asked, correct = Counter(), Counter()
        for exam in run.exams:
            for question, question_grade in zip(exam.questions, exam.grades, strict=True):
                asked[question.probe] += 1
                correct[question.probe] += question_grade.outcome == "correct"
        print(f"| {run.policy} | {run.period}/{run.persona} | {run.repetition} | " + " | ".join(percent(correct[probe], asked[probe]) for probe in probes) + " |")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slices", nargs="+", help='"period/persona[:through]"')
    parser.add_argument("--policies", nargs="+", required=True)
    parser.add_argument("--repetition", type=int, default=0)
    parser.add_argument("--exam-every", type=int, default=EXAM_STEP)
    parser.add_argument("--limit", type=float, default=1.50, help="dollar cap of the p5b budget")
    parser.add_argument("--dry-run", action="store_true", help="estimate what is not cached and call nothing")
    arguments = parser.parse_args()
    client = BudgetedClient(BUDGET_NAME, 0.0 if arguments.dry_run else arguments.limit)
    spent_before = client.spent()
    runs = []
    for spec in arguments.slices:
        period, persona, through = slice_of(spec)
        for name in arguments.policies:
            policy = policy_named(name, 0.0 if arguments.dry_run else arguments.limit)
            if arguments.dry_run:
                dreams, dream_dollars, detector_dollars = estimate(policy, period, persona, through, arguments.repetition)
                last_session = through or load_transcripts(period, persona)[-1].session_id
                exams = last_session // arguments.exam_every
                print(
                    f"{name} on {spec}: {dreams} dreams ~${dream_dollars:.4f}, detector not cached ~${detector_dollars:.4f}, "
                    f"exams ~${exams * EXAM_DOLLARS:.4f} (at most {exams}; cached ones are free)"
                )
                continue
            runs.append(run_policy(policy, period, persona, client, arguments.exam_every, through, arguments.repetition))
    if runs:
        report(runs)
    print(f"\np5b spent: ${spent_before:.4f} before, ${client.spent():.4f} after")


if __name__ == "__main__":
    main()
