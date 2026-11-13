"""Chain dreams along a persona under a policy, and grade the exams on the notes it leaves. Owner: P5.

After each session the policy decides whether to dream now. A dream reads the notes and every session since the
previous dream (dreaming.dream.dream). After every exam session N, the exam of N is answered from the notes left
after N's dream, if any (P2: the exam of N is the first question of session N+1). See docs/p5-interfaz.md.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from answering.answer import answer_exam
from answering.client import BudgetedClient, Completion
from dreaming.dream import dream
from dreaming.transcripts import Session, load_transcripts
from exam.grading import OUTCOMES, grade, negates_removed_preference
from exam.questions import EXAM_STEP, build_exam
from exam.schema import Grade, Question
from exam.unreachable import unreachable


@dataclass(frozen=True)
class Decision:
    dream: bool
    cost: float = 0.0  # dollars spent deciding, such as a detector call; 0 for a fixed cadence
    input_tokens: int = 0
    output_tokens: int = 0


class Policy(Protocol):
    name: str  # names its cache folder and its rows in reports, e.g. "every-20"

    def decide(self, notes: str, pending: list[Session], client: BudgetedClient, run: str) -> Decision:
        """Whether to dream right after pending[-1]. pending: the sessions since the last dream, oldest first."""


@dataclass(frozen=True)
class Step:
    session_id: int
    dreamt: bool
    sessions_read: int  # by this session's dream; 0 when it did not dream
    dream_cost: float
    dream_input_tokens: int
    dream_output_tokens: int
    decision_cost: float
    notes: str          # after this session, and after its dream if it dreamt


@dataclass(frozen=True)
class ExamResult:
    session_id: int
    questions: tuple[Question, ...]
    answers: tuple[str | None, ...]
    grades: tuple[Grade, ...]
    cost: float


@dataclass(frozen=True)
class PolicyRun:
    policy: str
    period: str
    persona: str
    repetition: int
    steps: tuple[Step, ...]
    exams: tuple[ExamResult, ...]

    def dreams(self) -> int:
        return sum(step.dreamt for step in self.steps)

    def dream_cost(self) -> float:
        return sum(step.dream_cost for step in self.steps)

    def decision_cost(self) -> float:
        return sum(step.decision_cost for step in self.steps)

    def exam_cost(self) -> float:
        return sum(exam.cost for exam in self.exams)


class LastCompletion:
    """Stands between answer_exam and the client to keep the cost of the exam's call."""

    def __init__(self, client: BudgetedClient):
        self.client = client
        self.thinking = client.thinking
        self.cost = 0.0

    def complete(self, run: str, system: str, user: str, max_tokens: int, repeat: int = 0) -> Completion:
        completion = self.client.complete(run, system, user, max_tokens, repeat=repeat)
        self.cost = completion.cost
        return completion


def run_policy(policy: Policy, period: str, persona: str, client: BudgetedClient, exam_every: int = EXAM_STEP, through: int | None = None, repetition: int = 0) -> PolicyRun:
    """The policy over sessions 1..through (all by default), with the exams of sessions that are multiples of exam_every.

    Dreams and exams are cached by request under results/raw/p5/r<repetition>/, shared by every policy: two policies
    that hold the same notes get the same dream and the same answers. Another repetition draws them again.
    """
    if exam_every % EXAM_STEP:
        raise ValueError(f"exam_every must be a multiple of {EXAM_STEP}, the exam's own step")
    sessions = [session for session in load_transcripts(period, persona) if through is None or session.session_id <= through]
    exams: dict[int, list[Question]] = {}
    for question in build_exam(period, persona):
        if question.session_id % exam_every == 0:
            exams.setdefault(question.session_id, []).append(question)
    cache = f"p5/r{repetition}"
    recorder = LastCompletion(client)
    notes = ""
    pending: list[Session] = []
    steps = []
    results = []
    for session in sessions:
        pending.append(session)
        decision = policy.decide(notes, list(pending), client, f"{cache}/decide/{policy.name}/{period}/{persona}")
        dreamt = None
        if decision.dream:
            dreamt = dream(notes, pending, client, f"{cache}/dream/{period}/{persona}")
            notes = dreamt.notes
        steps.append(Step(
            session_id=session.session_id,
            dreamt=dreamt is not None,
            sessions_read=len(pending) if dreamt else 0,
            dream_cost=dreamt.cost if dreamt else 0.0,
            dream_input_tokens=dreamt.input_tokens if dreamt else 0,
            dream_output_tokens=dreamt.output_tokens if dreamt else 0,
            decision_cost=decision.cost,
            notes=notes,
        ))
        if dreamt:
            pending = []
        if session.session_id in exams:
            questions = exams[session.session_id]
            answers = answer_exam(notes, questions, recorder, f"{cache}/exam/{period}/{persona}")
            grades = [grade(question, answer) for question, answer in zip(questions, answers, strict=True)]
            results.append(ExamResult(session.session_id, tuple(questions), tuple(answers), tuple(grades), recorder.cost))
    return PolicyRun(policy.name, period, persona, repetition, tuple(steps), tuple(results))


# --- Counting ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Score:
    """Correct answers four ways: official (strict) and lenient, each with and without the questions no dream can get right."""

    asked: int
    correct: int
    lenient: int
    reachable_asked: int
    reachable_correct: int
    reachable_lenient: int
    outcomes: Counter  # outcome -> count, official, every question

    def row(self) -> list[str]:
        return [
            percent(self.correct, self.asked), percent(self.lenient, self.asked),
            percent(self.reachable_correct, self.reachable_asked), percent(self.reachable_lenient, self.reachable_asked),
        ]


def score(run: PolicyRun, domains: tuple[str, ...] | None = None) -> Score:
    marked = unreachable(run.period, run.persona)
    counts = Counter()
    outcomes = Counter()
    for exam in run.exams:
        for question, question_grade in zip(exam.questions, exam.grades, strict=True):
            if domains and question.domain not in domains:
                continue
            correct = question_grade.outcome == "correct"
            # Decision (P2): "dislike" after a removed like is correct under the lenient count.
            lenient = correct or negates_removed_preference(question, question_grade)
            reachable = question.question_id not in marked
            counts.update(asked=1, correct=correct, lenient=lenient, reachable_asked=reachable, reachable_correct=reachable and correct, reachable_lenient=reachable and lenient)
            outcomes[question_grade.outcome] += 1
    return Score(counts["asked"], counts["correct"], counts["lenient"], counts["reachable_asked"], counts["reachable_correct"], counts["reachable_lenient"], outcomes)


def percent(part: int, whole: int) -> str:
    return f"{part}/{whole} ({part / whole:.1%})" if whole else "-"


def runs_table(runs: list[PolicyRun]) -> str:
    """One row per run: dreams, what they cost, and the exam counted four ways, with the official outcomes."""
    header = (
        "| policy | period/persona | rep | sessions | dreams | dream $ | decision $ | exam $ | exams "
        "| official | lenient | official without marked | lenient without marked | " + " | ".join(OUTCOMES) + " |"
    )
    lines = [header, "| --- | --- |" + " --: |" * (header.count("|") - 3)]
    for run in runs:
        run_score = score(run)
        cells = [
            run.policy, f"{run.period}/{run.persona}", run.repetition, len(run.steps), run.dreams(),
            f"{run.dream_cost():.4f}", f"{run.decision_cost():.4f}", f"{run.exam_cost():.4f}", len(run.exams),
            *run_score.row(), *(run_score.outcomes[outcome] for outcome in OUTCOMES),
        ]
        lines.append("| " + " | ".join(map(str, cells)) + " |")
    return "\n".join(lines)
