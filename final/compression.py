"""Every wrong answer of the whole runs of P7a, per stretch and cause, and how much of every-1 − every-5 each cause
accounts for. From P7a's cache with a cap of $0. Owner: P7c.

  PYTHONHASHSEED=0 uv run python -m final.compression

Questions marked by decision (c) are left out, as in "official without marked". An answer about a single fact that
holds and that the notes hold correct or not at all gets the case of diagnosis.late_errors, and the cases are grouped
into the causes P6 found by reading them (docs/p6-inventadas.md §3.3). Every other wrong answer is counted by what
it asked or by how the notes held its fact.
"""

from collections import Counter

from answering.client import BudgetedClient
from diagnosis.growth import fact_asked
from diagnosis.late_errors import late_errors
from dreaming import quality
from exam.unreachable import unreachable
from final.grid import PERIOD, STRETCHES, WHOLE_PERSONAS, WHOLE_POLICIES, in_stretch
from policies.engine import PolicyRun, run_policy
from policies.run import policy_named
from truth.changes import persona_changes
from truth.timeline import build_timeline

BUDGET_NAME = "p7a"
# (domain, case of diagnosis.late_errors) -> cause of docs/p6-inventadas.md §3.3.
P6_CAUSES = {
    ("preference", "dropped, Memora: like -> dislike"): "no longer liked: the dream drops it, Memora records dislike",
    ("content", "a line with its name, not tied to it"): "post or email under a generic title: the line is there, in a block not read as that document",
    ("content", "correct in the notes, answer wrong"): "post or email under a generic title: the line is there, in a block not read as that document",
    ("calendar", "dropped, no change in Memora"): "cancelled event that Memora keeps",
    ("todo", "Memora added it again, no dream wrote it back"): "implicit to-do that Memora adds again and no dream writes",
    ("preference", "correct in the notes, answer wrong"): "item under another name in the notes",
}
CAUSES = (*dict.fromkeys(P6_CAUSES.values()), "other single fact the notes hold correct or not at all", "fact stale or wrong in the notes",
          "total of expenses or steps", "decoy (never existed)", "other")
ERRORS = ("stale", "missing", "invented", "unparseable")


def whole_run(persona: str, policy: str) -> PolicyRun:
    return run_policy(policy_named(policy, BUDGET_NAME, 0.0), PERIOD, persona, BudgetedClient(BUDGET_NAME, 0.0), repetition=0)


def causes_by_stretch(run: PolicyRun) -> tuple[dict[str, Counter], Counter, dict[str, Counter], dict[str, dict[str, set]]]:
    """stretch -> cause -> wrong answers without marked; stretch -> questions asked without marked; stretch ->
    (domain, case of diagnosis.late_errors) -> wrong answers, for the ones outside P6's causes; and stretch -> cause ->
    the distinct facts behind the wrong answers (one fact is asked again at every exam)."""
    late = {(session_id, question.question_id): (question.domain, kind) for session_id, question, _, _, _, kind, _ in late_errors(run, 0)}
    cases = {key: P6_CAUSES.get(case, "other single fact the notes hold correct or not at all") for key, case in late.items()}
    other_cases = {name: Counter() for name, _, _ in STRETCHES}
    timeline = build_timeline(persona_changes(run.period, run.persona))
    steps = {step.session_id: step for step in run.steps}
    marked = unreachable(run.period, run.persona)
    found = {name: Counter() for name, _, _ in STRETCHES}
    facts = {name: {} for name, _, _ in STRETCHES}
    asked = Counter()
    for exam in run.exams:
        stretch = next(name for name, first, last in STRETCHES if in_stretch(exam.session_id, first, last))
        comparison = quality.compare_notes(steps[exam.session_id].notes, timeline, exam.session_id)
        for question, question_grade in zip(exam.questions, exam.grades, strict=True):
            if question.question_id in marked:
                continue
            asked[stretch] += 1
            if question_grade.outcome not in ERRORS:
                continue
            held = comparison.fact_outcomes.get(question.fact, ("not live",))[0]
            if (exam.session_id, question.question_id) in cases:
                cause = cases[exam.session_id, question.question_id]
                if late[exam.session_id, question.question_id] not in P6_CAUSES:
                    other_cases[stretch][late[exam.session_id, question.question_id]] += 1
            elif question.fact is None:
                cause = "total of expenses or steps"
            elif question.probe == "never_existed":
                cause = "decoy (never existed)"
            elif held in ("stale", "wrong"):
                cause = "fact stale or wrong in the notes"
            else:
                cause = "other"
            found[stretch][cause] += 1
            facts[stretch].setdefault(cause, set()).add(fact_asked(question))
    return found, asked, other_cases, facts


def dislikes_by_stretch(persona: str) -> Counter:
    """Memora's changes of a like into a dislike, per stretch: the facts behind "no longer liked"."""
    return Counter(next(name for name, first, last in STRETCHES if in_stretch(change.session_id, first, last))
                   for change in persona_changes(PERIOD, persona)
                   if change.domain == "preference" and change.action == "update" and change.value and change.value.get("preference") == "dislike")


def main() -> None:
    stretches = [name for name, _, _ in STRETCHES]
    for persona in WHOLE_PERSONAS:
        results = {policy: causes_by_stretch(whole_run(persona, policy)) for policy in WHOLE_POLICIES}
        first, second = WHOLE_POLICIES
        asked = results[first][1]
        if asked != results[second][1]:
            raise ValueError(f"{persona}: the two policies were asked different questions")
        print(f"## {PERIOD}/{persona}, repetition 0, without marked questions\n")
        print("Wrong answers per cause, and what each cause adds to the gap: (errors of every-5 − errors of every-1) / asked, in points.\n")
        print("| cause | " + " | ".join(f"{policy} {stretch}" for stretch in stretches for policy in WHOLE_POLICIES)
              + " | " + " | ".join(f"gap points {stretch}" for stretch in stretches) + f" | gap change {stretches[0]} -> {stretches[-1]} |")
        print("| --- |" + " --: |" * (3 * len(stretches) + 1))
        for cause in CAUSES:
            counts = [results[policy][0][stretch][cause] for stretch in stretches for policy in WHOLE_POLICIES]
            if not any(counts):
                continue
            gaps = [100 * (results[second][0][stretch][cause] - results[first][0][stretch][cause]) / asked[stretch] for stretch in stretches]
            print(f"| {cause} | " + " | ".join(map(str, counts)) + " | " + " | ".join(f"{gap:+.1f}" for gap in gaps) + f" | {gaps[-1] - gaps[0]:+.1f} |")
        totals = [sum(results[policy][0][stretch].values()) for stretch in stretches for policy in WHOLE_POLICIES]
        gaps = [100 * (sum(results[second][0][stretch].values()) - sum(results[first][0][stretch].values())) / asked[stretch] for stretch in stretches]
        print("| **all wrong answers** | " + " | ".join(map(str, totals)) + " | " + " | ".join(f"**{gap:+.1f}**" for gap in gaps) + f" | **{gaps[-1] - gaps[0]:+.1f}** |")
        print("\nquestions asked without marked: " + ", ".join(f"{stretch} {asked[stretch]}" for stretch in stretches))
        dislikes = dislikes_by_stretch(persona)
        print("Memora's like -> dislike changes: " + ", ".join(f"{stretch} {dislikes[stretch]}" for stretch in stretches))
        last = stretches[-1]
        print(f"\ndistinct facts behind the wrong answers of {last}:\n\n| cause | " + " | ".join(WHOLE_POLICIES) + " |\n| --- |" + " --: |" * len(WHOLE_POLICIES))
        for cause in CAUSES:
            counts = [len(results[policy][3][last].get(cause, ())) for policy in WHOLE_POLICIES]
            if any(counts):
                print(f"| {cause} | " + " | ".join(map(str, counts)) + " |")
        print("\n\"other single fact\", by case of diagnosis.late_errors:\n")
        print("| domain | case | " + " | ".join(f"{policy} {stretch}" for stretch in stretches for policy in WHOLE_POLICIES) + " |")
        print("| --- | --- |" + " --: |" * (2 * len(stretches)))
        for domain, kind in sorted({case for policy in WHOLE_POLICIES for stretch in stretches for case in results[policy][2][stretch]}):
            print(f"| {domain} | {kind} | " + " | ".join(str(results[policy][2][stretch][domain, kind]) for stretch in stretches for policy in WHOLE_POLICIES) + " |")
        print()


if __name__ == "__main__":
    main()
