"""Why the grid's repetition 1 answers differently from repetition 0, from P7a's cache with a cap of $0. Owner: P7c.

  uv run python -m final.repetitions records
  PYTHONHASHSEED=0 uv run python -m final.repetitions flips --personas marketing_manager
  PYTHONHASHSEED=0 uv run python -m final.repetitions dreams
  uv run python -m final.repetitions signs
  PYTHONHASHSEED=0 uv run python -m final.repetitions trace --personas marketing_manager --policies every-1 triggered-phrases-any every-5 --fact expense 1

records: what the raw responses of each repetition say about the model, its settings, the dates and the cache key.
flips: every question whose class changed between repetitions, split by whether the notes the exam read changed.
dreams: how much the notes after the same dream move between repetitions, per policy and window length.
signs: sign tests on the noise table of docs/p7/tables.md, rebuilt from data/p7-runs.csv.
trace: how the notes hold one fact after each dream, per repetition: the first dream and every dream that changed it.
"""

import argparse
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from itertools import product
from math import comb

from answering.client import RESULTS, BudgetedClient
from diagnosis.invented import related_lines
from dreaming import quality
from final.grid import DATA, PERIOD, POLICIES, THROUGH
from policies.engine import PolicyRun, run_policy
from policies.run import policy_named
from truth.changes import persona_changes, personas
from truth.timeline import build_timeline

BUDGET_NAME = "p7a"
REPETITIONS = (0, 1)
COMPARED = ("every-1", "triggered-phrases-any")
# The columns of docs/p7/tables.md "Noise between repetitions": each policy, then three paired differences.
PAIRS = (("every-1", "triggered-phrases-any"), ("every-1", "every-5"), ("triggered-phrases-any", "every-5"))


def cached_run(persona: str, policy: str, repetition: int) -> PolicyRun:
    """A grid run from the cache. Raises BudgetExceeded if any call is missing, since the cap is $0."""
    return run_policy(policy_named(policy, BUDGET_NAME, 0.0), PERIOD, persona, BudgetedClient(BUDGET_NAME, 0.0), through=THROUGH, repetition=repetition)


# --- records ------------------------------------------------------------------------------------------------------


def raw_records(repetition: int):
    """(kind, persona, file name, record) of every raw response cached for the repetition."""
    for path in sorted((RESULTS / "raw" / "p5" / f"r{repetition}").glob(f"*/{PERIOD}/*/*.json")):
        yield path.parts[-4], path.parts[-2], path.name, json.loads(path.read_text())


def records() -> None:
    texts, usages = {}, {}
    print("| repetition | kind | calls | model | thinking | effort | temperature | repeat | max_tokens | stop_reason | service_tier / geo / speed | mean input tokens | mean output tokens | mean thinking tokens | calls per day |")
    print("| --: | --- | --: | --- | --- | --- | --- | --- | --- | --- | --- | --: | --: | --: | --- |")
    for repetition in REPETITIONS:
        by_kind = defaultdict(list)
        for kind, persona, name, record in raw_records(repetition):
            by_kind[kind].append(record)
            texts[repetition, kind, persona, name] = record["text"]
            usages[repetition, kind, persona, name] = record["usage"]
        for kind, kind_records in sorted(by_kind.items()):
            def values(read) -> str:
                return ", ".join(f"{value} ({count})" for value, count in Counter(read(record) for record in kind_records).most_common())
            max_tokens = Counter(record["request"]["max_tokens"] for record in kind_records)
            cells = [
                repetition, kind, len(kind_records), values(lambda record: record["model"]), values(lambda record: json.dumps(record["thinking"])),
                values(lambda record: record["effort"]), values(lambda record: record["temperature"]), values(lambda record: record["request"]["repeat"]),
                f"{len(max_tokens)} distinct, {min(max_tokens)}-{max(max_tokens)}", values(lambda record: record["stop_reason"]),
                values(lambda record: f"{record['usage'].get('service_tier')} / {record['usage'].get('inference_geo')} / {record['usage'].get('speed')}"),
                f"{statistics.mean(record['usage']['input_tokens'] for record in kind_records):,.0f}",
                f"{statistics.mean(record['usage']['output_tokens'] for record in kind_records):,.0f}",
                f"{statistics.mean((record['usage'].get('output_tokens_details') or {}).get('thinking_tokens', 0) for record in kind_records):,.0f}",
                values(lambda record: record["time"][:10]),
            ]
            print("| " + " | ".join(map(str, cells)) + " |")
    shared = [key for key in texts if key[0] == 0 and (1, *key[1:]) in texts]
    same_text = sum(texts[key] == texts[(1, *key[1:])] for key in shared)
    print(f"\nrequests cached in both repetitions under the same key (same notes, sessions and questions): {len(shared)}; "
          f"with the same response text: {same_text}")
    for kind in ("dream", "exam"):
        kind_shared = [key for key in shared if key[1] == kind]
        def mean_tokens(repetition: int, read) -> float:
            return statistics.mean(read(usages[(repetition, *key[1:])]) for key in kind_shared)
        output = [mean_tokens(repetition, lambda usage: usage["output_tokens"]) for repetition in REPETITIONS]
        thinking = [mean_tokens(repetition, lambda usage: (usage.get("output_tokens_details") or {}).get("thinking_tokens", 0)) for repetition in REPETITIONS]
        print(f"- {kind}: {len(kind_shared)}, same text {sum(texts[key] == texts[(1, *key[1:])] for key in kind_shared)}; "
              f"mean output tokens r0 {output[0]:,.0f}, r1 {output[1]:,.0f}; mean thinking tokens r0 {thinking[0]:,.0f}, r1 {thinking[1]:,.0f}")
    print("\nfirst and last dream of each persona's s1-210 grid, per repetition (dreams that read a session after s210 belong to the whole runs and are left out)")
    print("| persona | r0 first | r0 last | r1 first | r1 last |\n| --- | --- | --- | --- | --- |")
    for persona in personas(PERIOD):
        cells = [persona]
        for repetition in REPETITIONS:
            times = sorted(record["time"] for kind, each, _, record in raw_records(repetition) if kind == "dream" and each == persona and grid_dream(record))
            cells += [times[0], times[-1]]
        print("| " + " | ".join(cells) + " |")


def grid_dream(record: dict) -> bool:
    """Whether a dream belongs to s1-210: the dream prompt numbers the sessions it reads."""
    return max(int(number) for number in re.findall(r'<session number="(\d+)"', record["request"]["user"])) <= THROUGH


# --- flips --------------------------------------------------------------------------------------------------------


def note_state(question, notes: str, comparison: quality.Comparison, state: dict) -> str:
    """How the notes hold what the question asks: compare_notes' outcome for a live fact; for a total, whether every item
    of its range is correct in the notes; for anything else, whether any line is about it."""
    if question.fact in comparison.fact_outcomes:
        return comparison.fact_outcomes[question.fact][0]
    if question.fact is None:
        start, end = re.findall(r"\d{4}-\d{2}-\d{2}", question.prompt)[:2]
        in_range = [fact for fact, value in state.items() if fact[0] == question.domain and start <= value.get("date", fact[1][0]) <= end]
        held = all(comparison.fact_outcomes.get(fact, ("missing",))[0] == "correct" for fact in in_range)
        return "total complete" if held else "total incomplete"
    return "some line about it" if related_lines(notes, question) else "no line about it"


def exam_states(run: PolicyRun) -> dict[str, tuple[str, tuple[str, ...], str]]:
    """question_id -> (note state, the note lines about it, outcome) for every question of the run."""
    timeline = build_timeline(persona_changes(run.period, run.persona))
    steps = {step.session_id: step for step in run.steps}
    found = {}
    for exam in run.exams:
        notes = steps[exam.session_id].notes
        comparison = quality.compare_notes(notes, timeline, exam.session_id)
        state = timeline.state_after(exam.session_id)
        for question, question_grade in zip(exam.questions, exam.grades, strict=True):
            lines = tuple(sorted(line.strip() for line in related_lines(notes, question)))
            found[question.question_id] = (note_state(question, notes, comparison, state), lines, question_grade.outcome)
    return found


def flip_kind(first: tuple, second: tuple) -> str:
    """Whether the notes the two exams read say the same about the question."""
    if first[1] == second[1]:
        return "same note lines"
    if first[0] == second[0]:
        return "other lines, same state"
    return "other state"


FLIP_KINDS = ("same note lines", "other lines, same state", "other state")


def flips(persona_names: list[str], policies: list[str], show: bool) -> None:
    print("Net change in correct answers from r0 to r1 (r1 correct and r0 not, minus the reverse), split by what the notes the two exams read say about the question.\n")
    print("| persona | policy | asked | r0 correct | r1 correct | r1 − r0 | questions whose class changed | " + " | ".join(f"net, {kind}" for kind in FLIP_KINDS)
          + " | live facts correct in r0 notes | in r1 notes |\n| --- | --- |" + " --: |" * (7 + len(FLIP_KINDS)))
    totals = defaultdict(Counter)
    for persona in persona_names:
        for policy in policies:
            first, second = exam_states(cached_run(persona, policy, 0)), exam_states(cached_run(persona, policy, 1))
            net = Counter()
            by_question = Counter()
            changed = 0
            for question_id, state in first.items():
                other = second[question_id]
                if state[2] != other[2]:
                    changed += 1
                    net[flip_kind(state, other)] += (other[2] == "correct") - (state[2] == "correct")
                    # The same question at every exam: the id without its session (all weekly totals of a domain together).
                    by_question[re.sub(r"/s\d+/", "/", question_id)] += (other[2] == "correct") - (state[2] == "correct")
                    if show and (other[2] == "correct") != (state[2] == "correct"):
                        print(f"  {policy} {question_id}: r0 {state[2]} ({state[0]}), r1 {other[2]} ({other[0]}), {flip_kind(state, other)}")
            if show:
                print(f"  {policy}, net change per question asked, largest first: "
                      + ", ".join(f"{question} {count:+d}" for question, count in sorted(by_question.items(), key=lambda item: -abs(item[1])) if count))
            correct = [sum(state[2] == "correct" for state in each.values()) for each in (first, second)]
            live = [Counter(state[0] for state in each.values() if state[0] in quality.FACT_OUTCOMES) for each in (first, second)]
            live_share = [f"{counts['correct']}/{sum(counts.values())}" for counts in live]
            print(f"| {persona} | {policy} | {len(first)} | {correct[0]} | {correct[1]} | {correct[1] - correct[0]:+d} | {changed} | "
                  + " | ".join(f"{net[kind]:+d}" for kind in FLIP_KINDS) + f" | {live_share[0]} | {live_share[1]} |")
            totals[policy].update(asked=len(first), difference=correct[1] - correct[0], changed=changed, **{kind: net[kind] for kind in FLIP_KINDS},
                                  live_first=live[0]["correct"], live_second=live[1]["correct"])
    if len(persona_names) > 1:
        print("\n| policy | asked | r1 − r0 | questions whose class changed | " + " | ".join(f"net, {kind}" for kind in FLIP_KINDS)
              + " | live facts correct in notes, r1 − r0 |\n| --- |" + " --: |" * (4 + len(FLIP_KINDS)))
        for policy, total in totals.items():
            print(f"| {policy} | {total['asked']} | {total['difference']:+d} | {total['changed']} | " + " | ".join(f"{total[kind]:+d}" for kind in FLIP_KINDS)
                  + f" | {total['live_second'] - total['live_first']:+d} |")


# --- dreams -------------------------------------------------------------------------------------------------------


def dream_shares(run: PolicyRun) -> dict[int, tuple[int, float, str]]:
    """dream session -> (sessions it read, share of the live facts correct in the notes after it, the notes)."""
    timeline = build_timeline(persona_changes(run.period, run.persona))
    shares = {}
    for step in run.steps:
        if step.dreamt:
            comparison = quality.compare_notes(step.notes, timeline, step.session_id)
            shares[step.session_id] = (step.sessions_read, comparison.fact_total("correct") / comparison.fact_total() if comparison.fact_total() else 1.0, step.notes)
    return shares


def window(sessions_read: int) -> str:
    return "1" if sessions_read == 1 else "2-3" if sessions_read <= 3 else "4+"


def dreams(persona_names: list[str], policies: list[str]) -> None:
    """The same dream (same policy and session, so the same window) in both repetitions: how far apart the notes after it are."""
    print("Live facts correct in the notes after each dream, r0 against r1, the same dream in both (decisions are identical). Points.\n")
    print("| policy | window (sessions read) | dreams | mean in r0 | mean in r1 | mean r1 − r0 | mean abs(r1 − r0) | dreams that moved more than 2 points |")
    print("| --- | --- | --: | --: | --: | --: | --: | --: |")
    per_persona = defaultdict(dict)
    identical = Counter()
    for policy in policies:
        groups = defaultdict(list)
        for persona in persona_names:
            first, second = dream_shares(cached_run(persona, policy, 0)), dream_shares(cached_run(persona, policy, 1))
            for session_id, (sessions_read, share, notes) in first.items():
                identical[policy] += notes == second[session_id][2]
                pair = (100 * share, 100 * second[session_id][1])
                groups[window(sessions_read)].append(pair)
                groups["all"].append(pair)
            per_persona[persona][policy] = statistics.mean(100 * (second[session_id][1] - share) for session_id, (_, share, _) in first.items())
        for name in ("1", "2-3", "4+", "all"):
            pairs = groups.get(name)
            if not pairs:
                continue
            differences = [second - first for first, second in pairs]
            print(f"| {policy} | {name} | {len(pairs)} | {statistics.mean(first for first, _ in pairs):.1f} | {statistics.mean(second for _, second in pairs):.1f} | "
                  f"{statistics.mean(differences):+.2f} | {statistics.mean(abs(difference) for difference in differences):.2f} | {sum(abs(difference) > 2 for difference in differences)} |")
    print("\nThe notes after each dream accumulate, so the dreams of one run are not independent: per persona, mean r1 − r0 over its dreams (points).\n")
    print("| persona | " + " | ".join(policies) + " |\n| --- |" + " --: |" * len(policies))
    for persona, means in per_persona.items():
        print(f"| {persona} | " + " | ".join(f"{means[policy]:+.2f}" for policy in policies) + " |")
    for policy in policies:
        values = [means[policy] for means in per_persona.values()]
        print(f"\n{policy}: personas above zero {sum(value > 0 for value in values)}, below {sum(value < 0 for value in values)}; "
              f"sign-flip test on the mean, two-sided: {sign_flip(values):.4f}; dreams whose notes are the same text in r0 and r1: {identical[policy]}")


# --- trace --------------------------------------------------------------------------------------------------------


def trace(persona: str, policies: list[str], fact: tuple) -> None:
    timeline = build_timeline(persona_changes(PERIOD, persona))
    for policy, repetition in product(policies, REPETITIONS):
        changes, previous = [], None
        for step in cached_run(persona, policy, repetition).steps:
            if step.dreamt:
                held = quality.compare_notes(step.notes, timeline, step.session_id).fact_outcomes.get(fact, ("not live",))[0]
                if held != previous:
                    changes.append(f"s{step.session_id} {held}")
                previous = held
        print(f"- {policy} r{repetition}: " + ", ".join(changes))


# --- signs --------------------------------------------------------------------------------------------------------


def noise_columns(count: str, total: str) -> tuple[list[str], dict[str, list[float]]]:
    """persona -> r1 − r0 in points for each column of the noise table, from data/p7-runs.csv (s1-210)."""
    accuracy = {}
    with (DATA / "p7-runs.csv").open(newline="") as file:
        for row in csv.DictReader(file):
            if row["scope"] == "s1-210":
                accuracy[row["persona"], row["policy"], int(row["repetition"])] = 100 * int(row[count]) / int(row[total])
    names = list(personas(PERIOD))
    columns = {}
    for policy in POLICIES:
        columns[policy] = [round(accuracy[persona, policy, 1] - accuracy[persona, policy, 0], 1) for persona in names]
    for first, second in PAIRS:
        columns[f"{first} − {second}"] = [round(
            (accuracy[persona, first, 1] - accuracy[persona, second, 1]) - (accuracy[persona, first, 0] - accuracy[persona, second, 0]), 1) for persona in names]
    return names, columns


def sign_test(values: list[float]) -> tuple[int, int, int, float, float]:
    """(above zero, below zero, ties, one-sided p toward the larger side, two-sided p). Ties are dropped, as in the sign test."""
    above, below = sum(value > 0 for value in values), sum(value < 0 for value in values)
    trials, larger = above + below, max(above, below)
    one_sided = sum(comb(trials, k) for k in range(larger, trials + 1)) / 2 ** trials
    return above, below, len(values) - trials, one_sided, min(1.0, 2 * one_sided)


def signs() -> None:
    for count, total in (("official", "asked"), ("reachable_official", "reachable_asked")):
        names, columns = noise_columns(count, total)
        print(f"## {count} / {total}: r1 − r0, points\n")
        print("| column | personas above zero | below | ties | sign test, one-sided | two-sided | mean | sign-flip test on the mean, two-sided |\n| --- | --: | --: | --: | --: | --: | --: | --: |")
        for column, values in columns.items():
            above, below, ties, one_sided, two_sided = sign_test(values)
            print(f"| {column} | {above} | {below} | {ties} | {one_sided:.4f} | {two_sided:.4f} | {statistics.mean(values):+.2f} | {sign_flip(values):.4f} |")
        extreme = max(max(sum(value > 0 for value in values), sum(value < 0 for value in values)) for values in columns.values())
        print(f"\nlargest count on one side in any column: {extreme} of {len(names)}")
        independent = 1 - (1 - sign_test([1.0] * extreme + [-1.0] * (len(names) - extreme))[4]) ** len(columns)
        print(f"if the {len(columns)} columns were independent, chance that at least one reaches {extreme} of {len(names)} on one side by chance: {independent:.4f}")
        print(f"swapping r0 and r1 within each persona (all columns together, 2^{len(names)} ways), share of the ways where some column reaches "
              f"{extreme} of {len(names)} on one side: {swapped_extreme(columns, extreme):.4f}")
        smallest = min((sign_flip(values), column) for column, values in columns.items())
        print(f"smallest sign-flip p: {smallest[0]:.4f} ({smallest[1]}); times {len(columns)} columns (Bonferroni): {min(1.0, smallest[0] * len(columns)):.4f}\n")


def sign_flip(values: list[float]) -> float:
    """Exact two-sided p of the mean under swapping r0 and r1 within each persona."""
    observed = abs(sum(values))
    flips = [sum(sign * value for sign, value in zip(signs, values)) for signs in product((1, -1), repeat=len(values))]
    return sum(abs(total) >= observed - 1e-9 for total in flips) / len(flips)


def swapped_extreme(columns: dict[str, list[float]], extreme: int) -> float:
    """Share of the ways to swap r0 and r1 within personas where any column has `extreme` or more personas on one side.
    Swapping a persona flips the sign of all its columns at once, so this keeps how the columns depend on each other."""
    hits = 0
    ways = list(product((1, -1), repeat=len(next(iter(columns.values())))))
    for signs in ways:
        for values in columns.values():
            flipped = [sign * value for sign, value in zip(signs, values)]
            if max(sum(value > 0 for value in flipped), sum(value < 0 for value in flipped)) >= extreme:
                hits += 1
                break
    return hits / len(ways)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("records", "flips", "dreams", "signs", "trace"))
    parser.add_argument("--personas", nargs="+", default=list(personas(PERIOD)))
    parser.add_argument("--policies", nargs="+", default=list(COMPARED))
    parser.add_argument("--show", action="store_true", help="flips: print every question that went from correct to wrong or back")
    parser.add_argument("--fact", nargs="+", help="trace: domain and key, e.g. expense 1")
    arguments = parser.parse_args()
    if arguments.command == "records":
        records()
    elif arguments.command == "flips":
        flips(arguments.personas, arguments.policies, arguments.show)
    elif arguments.command == "trace":
        trace(arguments.personas[0], arguments.policies, (arguments.fact[0], tuple(arguments.fact[1:])))
    elif arguments.command == "dreams":
        dreams(arguments.personas, arguments.policies)
    else:
        signs()


if __name__ == "__main__":
    main()
