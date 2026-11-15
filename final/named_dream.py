"""P8b: the named dream (dreaming.dream_named) under triggered-phrases-any, against P4a's dream from P7. Owner: P8b.

  PYTHONHASHSEED=0 uv run python -m final.named_dream estimate
  PYTHONHASHSEED=0 uv run python -m final.named_dream run --repetition 0 --limit 3.00
  PYTHONHASHSEED=0 uv run python -m final.named_dream compare > results/p8b/compare.txt

estimate: what is still to pay per persona and repetition, after the p8b cache, with final.grid's cost model plus the
longer rules (final.omissions.estimate). Calls nothing.
run: pays the 10 personas of one repetition in order, under the p8b ledger, with the cache under results/raw/p8b/.
A network timeout resumes that persona once from the cache; a second failure in a row, or any other error (the usage
limit's 400, the budget), stops the run.
compare: every fact the dream's sessions bring, paired with the same fact in the same dream of P7's run (the phrase
detector does not read the notes, so both dream after the same sessions), and the exam's four counts.
"""

import argparse
import statistics
from collections import Counter, defaultdict
from math import comb

import anthropic

from answering.client import BudgetedClient, BudgetExceeded
from dreaming import dream, dream_named, quality
from final.analysis import BOOTSTRAP_SEED, bootstrap
from final.grid import PERIOD, THROUGH, Estimator
from final.omissions import INPUT_DOLLARS_PER_TOKEN, TOKENS_PER_CHARACTER, aimed_at, cached_run, cause, cost, list_kind, walk
from final.repetitions import REPETITIONS
from policies.engine import run_policy, score
from policies.run import policy_named
from truth.changes import persona_changes, personas
from truth.timeline import build_timeline

POLICY = "triggered-phrases-any"
BUDGET_NAME = "p8b"
CACHE_PREFIX = "p8b"
NETWORK_ERRORS = (anthropic.APITimeoutError, anthropic.APIConnectionError)
COUNTS = (("official", "correct", "asked"), ("lenient", "lenient", "asked"),
          ("official without marked", "reachable_correct", "reachable_asked"), ("lenient without marked", "reachable_lenient", "reachable_asked"))


def named_run(persona: str, repetition: int, client):
    # The phrase detector never calls the model, so the policy needs no budget of its own.
    return run_policy(policy_named(POLICY, BUDGET_NAME, 0.0), PERIOD, persona, client,
                      through=THROUGH, repetition=repetition, dream_function=dream_named.dream, cache_prefix=CACHE_PREFIX)


# --- estimate -----------------------------------------------------------------------------------------------------


class Served:
    """A client with a cap of $0 that counts the dreams and exams the p8b cache answers before the first it cannot."""

    def __init__(self):
        self.client = BudgetedClient(BUDGET_NAME, 0.0)
        self.thinking, self.effort = self.client.thinking, self.client.effort
        self.served = Counter()

    def complete(self, run: str, system: str, user: str, max_tokens: int, repeat: int = 0):
        completion = self.client.complete(run, system, user, max_tokens, repeat=repeat)
        self.served["dream" if "/dream/" in run else "exam"] += 1
        return completion


def still_to_pay(estimator: Estimator, persona: str, repetition: int) -> tuple[int, int, float]:
    requests = estimator.requests(persona, POLICY, repetition, THROUGH)
    probe = Served()
    try:
        named_run(persona, repetition, probe)
    except BudgetExceeded:
        pass
    served = probe.served
    extra = TOKENS_PER_CHARACTER * (len(dream_named.RULES) - len(dream.RULES)) * INPUT_DOLLARS_PER_TOKEN
    dreams = [cost + extra for request, cost in requests if request[0] == "dream"][served["dream"]:]
    exams = [cost for request, cost in requests if request[0] == "exam"][served["exam"]:]
    return len(dreams), len(exams), sum(dreams) + sum(exams)


def estimate() -> None:
    estimator = Estimator()
    print("| persona | repetition | dreams to pay | exams to pay | $ |\n| --- | --: | --: | --: | --: |")
    total = 0.0
    for repetition in REPETITIONS:
        for persona in personas(PERIOD):
            dreams, exams, dollars = still_to_pay(estimator, persona, repetition)
            total += dollars
            print(f"| {persona} | {repetition} | {dreams} | {exams} | {dollars:.4f} |")
    print(f"\ntotal still to pay: ${total:.4f}; {BUDGET_NAME} spent so far: ${BudgetedClient(BUDGET_NAME, 0.0).spent():.4f}")


# --- run ----------------------------------------------------------------------------------------------------------


def run(repetition: int, limit: float) -> None:
    client = BudgetedClient(BUDGET_NAME, limit)
    for persona in personas(PERIOD):
        for attempt in (1, 2):
            spent = client.spent()
            try:
                finished = named_run(persona, repetition, client)
            except NETWORK_ERRORS as error:
                print(f"{persona} r{repetition}: network error on attempt {attempt}: {type(error).__name__}: {error}", flush=True)
                if attempt == 2:
                    raise SystemExit(f"stopped: the same persona failed twice in a row; {BUDGET_NAME} spent ${client.spent():.4f}")
                continue
            except Exception as error:
                raise SystemExit(f"stopped at {persona} r{repetition}: {type(error).__name__}: {error}; {BUDGET_NAME} spent ${client.spent():.4f}")
            print(f"{persona} r{repetition}: done, {finished.dreams()} dreams, ${client.spent() - spent:.4f} this persona, "
                  f"{BUDGET_NAME} spent ${client.spent():.4f}", flush=True)
            break


# --- compare ------------------------------------------------------------------------------------------------------


def mcnemar(fixed: int, broken: int) -> float:
    """Exact two-sided p that the discordant pairs split this way or more unevenly if either direction were as likely."""
    pairs = fixed + broken
    if not pairs:
        return 1.0
    tail = sum(comb(pairs, k) for k in range(min(fixed, broken) + 1)) / 2 ** pairs
    return min(1.0, 2 * tail)


def group(encounter) -> str:
    if encounter.encounter == "removal":
        return "removal"
    if encounter.reason != "said":
        return encounter.reason
    if encounter.follow_up != "plain":
        return "said, Memora takes it back"
    aimed = encounter.domain in ("todo", "preference") or (encounter.domain == "content" and list_kind(encounter.fact) == "not named")
    return "said, plain, aimed at" if aimed else "said, plain, other"


GROUPS = ("said, plain, aimed at", "said, plain, other", "said, Memora takes it back", "like to dislike", "relative date", "not said", "removal")


def wrong(encounter) -> bool:
    return encounter.outcome not in ("correct", "deleted")


def pair_table(title: str, pairs: dict) -> None:
    """pairs: key -> (first encounter, second encounter)."""
    print(f"### {title}\n")
    print("| group | domain | pairs | first wrong | second wrong | fixed (first wrong, second right) | broken (first right, second wrong) | both wrong | McNemar p |")
    print("| --- | --- | --: | --: | --: | --: | --: | --: | --: |")
    rows = defaultdict(Counter)
    for first, second in pairs.values():
        for key in ((group(first), first.domain), (group(first), "all")):
            rows[key].update(pairs=1, first=int(wrong(first)), second=int(wrong(second)), fixed=int(wrong(first) and not wrong(second)),
                             broken=int(wrong(second) and not wrong(first)), both=int(wrong(first) and wrong(second)))
    for (name, domain), counts in sorted(rows.items(), key=lambda item: (GROUPS.index(item[0][0]), item[0][1] != "all", item[0][1])):
        if counts["first"] or counts["second"]:
            print(f"| {name} | {domain} | {counts['pairs']} | {counts['first']} | {counts['second']} | {counts['fixed']} | {counts['broken']} | {counts['both']} | "
                  f"{mcnemar(counts['fixed'], counts['broken']):.4f} |")
    print()


def compare(repetitions: tuple[int, ...]) -> None:
    old, new = {}, {}
    for persona in personas(PERIOD):
        for repetition in repetitions:
            old[persona, repetition] = cached_run(persona, POLICY, repetition)
            new[persona, repetition] = cached_run(persona, POLICY, repetition, dream_function=dream_named.dream, cache_prefix=CACHE_PREFIX)
    walked = {}
    for name, runs in (("old", old), ("new", new)):
        for key, (policy_run, replies) in runs.items():
            walked[name, key] = walk(policy_run, replies, set())

    def encounters(name: str, repetition: int) -> dict:
        return {(encounter.persona, encounter.dream, encounter.fact, encounter.change_session): encounter
                for persona in personas(PERIOD) for encounter in walked[name, (persona, repetition)][0]}

    print("## 1. Facts the sessions bring, paired: the same fact in the same dream\n")
    print("Wrong: compare_notes does not find the new value after the dream (for a removal, a line about it is still there).\n")
    for repetition in repetitions:
        first, second = encounters("old", repetition), encounters("new", repetition)
        pair_table(f"P4a's dream (first) against the named dream (second), r{repetition}", {key: (first[key], second[key]) for key in first})
    if len(repetitions) == 2:
        first, second = encounters("old", 0), encounters("old", 1)
        pair_table("noise: P4a's dream r0 (first) against P4a's dream r1 (second)", {key: (first[key], second[key]) for key in first})
        first, second = encounters("new", 0), encounters("new", 1)
        pair_table("noise: the named dream r0 (first) against the named dream r1 (second)", {key: (first[key], second[key]) for key in first})

    print("## 2. Answers lost per cause (final.omissions episodes), summed over the 10 personas\n")
    names = ("omitted, said, plain", "omitted, said, Memora takes it back", "omitted, like to dislike", "omitted, relative date", "removal kept", "lost")
    print("| dream | rep | " + " | ".join(names) + " | no episode | unmarked wrong answers | of plain: aimed at |\n| --- | --: |" + " --: |" * (len(names) + 3))
    for name in ("old", "new"):
        for repetition in repetitions:
            episodes = [episode for persona in personas(PERIOD) for episode in walked[name, (persona, repetition)][1]]
            answers = sum(len(walked[name, (persona, repetition)][2]) for persona in personas(PERIOD))
            aimed = sum(cost(episode) for episode in episodes if cause(episode) == "omitted, said, plain" and aimed_at(episode))
            explained = [sum(cost(episode) for episode in episodes if cause(episode) == each) for each in names]
            print(f"| {name} | {repetition} | " + " | ".join(f"{each:.1f}" for each in explained) + f" | {answers - sum(explained):.1f} | {answers} | {aimed:.1f} |")
    print()

    print("## 3. The exam, four counts (s1-210, 10 personas)\n")
    print("| count | rep | P4a's dream | named dream | named − P4a, points: mean over personas [95% bootstrap] | personas up / same / down |\n| --- | --- | --: | --: | --: | --: |")
    for label, numerator, denominator in COUNTS:
        for chosen in [(repetition,) for repetition in repetitions] + ([repetitions] if len(repetitions) == 2 else []):
            totals = Counter()
            differences = []
            for persona in personas(PERIOD):
                rates = {}
                for name, runs in (("old", old), ("new", new)):
                    scores = [score(runs[persona, repetition][0]) for repetition in chosen]
                    totals[name, "numerator"] += sum(getattr(each, numerator) for each in scores)
                    totals[name, "denominator"] += sum(getattr(each, denominator) for each in scores)
                    rates[name] = statistics.mean(getattr(each, numerator) / getattr(each, denominator) for each in scores)
                differences.append(rates["new"] - rates["old"])
            interval = bootstrap(differences)
            shown = "both" if len(chosen) == 2 else str(chosen[0])
            print(f"| {label} | {shown} | {totals['old', 'numerator']}/{totals['old', 'denominator']} ({totals['old', 'numerator'] / totals['old', 'denominator']:.1%}) | "
                  f"{totals['new', 'numerator']}/{totals['new', 'denominator']} ({totals['new', 'numerator'] / totals['new', 'denominator']:.1%}) | "
                  f"{100 * interval.mean:+.2f} [{100 * interval.low:+.2f}, {100 * interval.high:+.2f}] | "
                  f"{sum(value > 0 for value in differences)} / {sum(value == 0 for value in differences)} / {sum(value < 0 for value in differences)} |")
    print(f"\n(bootstrap: 10,000 resamples of the personas, seed {BOOTSTRAP_SEED}, final.analysis.bootstrap)\n")

    print("## 4. Outcomes of the exam answers, and what the notes hold beyond the truth (mean per dream)\n")
    line_domains = ("preference", "todo", "content", "expense")
    print("| dream | rep | correct | stale | missing | invented | unparseable | note characters | lines tied to no fact: "
          + " | ".join(line_domains) + " | all | prose lines |\n| --- | --: |" + " --: |" * (8 + len(line_domains)))
    for name, runs in (("old", old), ("new", new)):
        for repetition in repetitions:
            outcomes, lines, characters, dreams = Counter(), Counter(), 0, 0
            for persona in personas(PERIOD):
                policy_run = runs[persona, repetition][0]
                outcomes += score(policy_run).outcomes
                timeline = build_timeline(persona_changes(PERIOD, persona))
                for step in policy_run.steps:
                    if step.dreamt:
                        comparison = quality.compare_notes(step.notes, timeline, step.session_id)
                        for (domain, outcome), count in comparison.lines.items():
                            if outcome.startswith("unmatched"):
                                lines[domain] += count
                                lines["all"] += count
                            elif outcome == "prose":
                                lines["prose"] += count
                        characters += len(step.notes)
                        dreams += 1
            print(f"| {name} | {repetition} | " + " | ".join(str(outcomes[outcome]) for outcome in ("correct", "stale", "missing", "invented", "unparseable"))
                  + f" | {characters / dreams:,.0f} | " + " | ".join(f"{lines[domain] / dreams:.2f}" for domain in (*line_domains, "all", "prose")) + " |")
    print()

    print("## 5. Cost of the runs (dollars billed when each response was first fetched)\n")
    print("| dream | rep | dreams | dream $ | exam $ | output tokens per dream |\n| --- | --: | --: | --: | --: | --: |")
    for name, runs in (("old", old), ("new", new)):
        for repetition in repetitions:
            persona_runs = [runs[persona, repetition][0] for persona in personas(PERIOD)]
            dreams = sum(each.dreams() for each in persona_runs)
            output = sum(step.dream_output_tokens for each in persona_runs for step in each.steps)
            print(f"| {name} | {repetition} | {dreams} | {sum(each.dream_cost() for each in persona_runs):.4f} | {sum(each.exam_cost() for each in persona_runs):.4f} | {output / dreams:.0f} |")
    print(f"\n{BUDGET_NAME} ledger: ${BudgetedClient(BUDGET_NAME, 0.0).spent():.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("estimate")
    paying = commands.add_parser("run")
    paying.add_argument("--repetition", type=int, required=True)
    paying.add_argument("--limit", type=float, required=True)
    comparing = commands.add_parser("compare")
    comparing.add_argument("--repetitions", type=int, nargs="+", default=list(REPETITIONS))
    arguments = parser.parse_args()
    if arguments.command == "estimate":
        estimate()
    elif arguments.command == "run":
        run(arguments.repetition, arguments.limit)
    else:
        compare(tuple(arguments.repetitions))


if __name__ == "__main__":
    main()
