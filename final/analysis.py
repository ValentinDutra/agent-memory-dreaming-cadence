"""P7b: the analysis of P7a's two CSVs, as Markdown tables and SVG charts. Never calls the API.

    PYTHONHASHSEED=0 uv run python -m final.analysis data/p7-runs.csv data/p7-probes.csv --output docs/p7

The unit of every interval is the persona (docs/p7-interfaz.md): repetitions are averaged inside a persona,
then personas are resampled with replacement. A comparison between two policies is the mean, over the
resampled personas, of the difference inside each persona.
"""

import argparse
import csv
import hashlib
import math
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from final import charts

POLICIES = ("never", "every-1", "every-5", "every-10", "every-20", "every-50", "triggered-phrases-any")
FIXED_BY_COST = ("never", "every-50", "every-20", "every-10", "every-5", "every-1")
TRIGGERED = "triggered-phrases-any"
PAIRS = (("every-1", TRIGGERED), ("every-1", "every-5"), (TRIGGERED, "every-5"))
GRID = "s1-210"
STRETCHES = ("s1-210", "s211-420", "s421-end")
WHOLE_RUNS = (("startup_founder", "every-1"), ("startup_founder", "every-5"), ("academic_researcher", "every-1"), ("academic_researcher", "every-5"))
PROBES = ("new", "recent_change", "stable", "never_existed", "aggregate")
PROBE_LABELS = {"new": "new", "recent_change": "recent_change", "stable": "stable (unchanged)", "never_existed": "never_existed (decoy)", "aggregate": "aggregate (total)"}
DOMAINS = ("preference", "todo", "calendar", "goal", "content", "expense", "steps")
COUNTS = (
    ("official", "official", "asked"),
    ("lenient", "lenient", "asked"),
    ("official without marked", "reachable_official", "reachable_asked"),
    ("lenient without marked", "reachable_lenient", "reachable_asked"),
)
PROBE_COLUMNS = ("asked", "official", "lenient", "reachable_asked", "reachable_official", "reachable_lenient")
BOOTSTRAP_SEED = 20261113
RESAMPLES = 10_000
# With n personas, a resample is one given persona n times with probability n**-n: 25 % for 2 and 3.7 % for 3, above 2.5 %,
# so the 95 % percentile interval of 3 or fewer personas is only the lowest and highest persona. From 4 on it is 0.4 % or less.
MINIMUM_PERSONAS_FOR_INTERVAL = 4


@dataclass(frozen=True)
class Interval:
    mean: float
    low: float
    high: float
    personas: int


def read_rows(path: str) -> list[dict]:
    with open(path, newline="") as file:
        return [{key: number(value) for key, value in row.items()} for row in csv.DictReader(file)]


def number(text: str):
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            pass
    return text


def bootstrap(values: list[float]) -> Interval:
    """Mean over personas and its 95% percentile interval, resampling personas with replacement.

    The same seed for every call: two lists of the same length are resampled with the same indices.
    """
    generator = random.Random(BOOTSTRAP_SEED)
    count = len(values)
    means = sorted(math.fsum(generator.choices(values, k=count)) / count for _ in range(RESAMPLES))
    return Interval(math.fsum(values) / count, means[round(0.025 * (RESAMPLES - 1))], means[round(0.975 * (RESAMPLES - 1))], count)


def ratio(rows: list[dict], numerator: str, denominator: str) -> float | None:
    """The persona's rate: numerator / denominator in each repetition, averaged over the repetitions."""
    rates = [row[numerator] / row[denominator] for row in rows if row[denominator]]
    return math.fsum(rates) / len(rates) if rates else None


def mean_of(rows: list[dict], column: str) -> float:
    return math.fsum(row[column] for row in rows) / len(rows)


def grid_cells(runs: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """(persona, policy) -> its s1-210 grid rows, one per repetition. The `whole` rows repeat repetition 0 and are left out."""
    cells = defaultdict(list)
    for row in runs:
        if row["scope"] == GRID and row["stretch"] == GRID:
            cells[row["persona"], row["policy"]].append(row)
    return cells


def probe_cells(probes: list[dict], column: str) -> dict[tuple[str, str, str], list[dict]]:
    """(persona, policy, probe or domain) -> s1-210 counts summed over the other column, one dict per repetition."""
    sums = defaultdict(lambda: dict.fromkeys(PROBE_COLUMNS, 0))
    for row in probes:
        if row["scope"] == GRID and row["stretch"] == GRID:
            counts = sums[row["persona"], row["policy"], row[column], row["repetition"]]
            for name in PROBE_COLUMNS:
                counts[name] += row[name]
    cells = defaultdict(list)
    for (persona, policy, value, _), counts in sorted(sums.items()):
        cells[persona, policy, value].append(counts)
    return cells


def complete_personas(cells: dict) -> list[str]:
    """Personas with repetition 0 of every policy: only they enter the grid analysis, so every policy has the same personas."""
    personas = {persona for persona, _ in cells}
    return sorted(persona for persona in personas if all(any(row["repetition"] == 0 for row in cells.get((persona, policy), [])) for policy in POLICIES))


def per_persona(cells: dict, personas: list[str], key, measure) -> list[float]:
    values = [measure(cells.get(key(persona), [])) if cells.get(key(persona)) else None for persona in personas]
    return [value for value in values if value is not None]


def paired(cells: dict, personas: list[str], key_a, key_b, measure) -> list[float]:
    differences = []
    for persona in personas:
        rows_a, rows_b = cells.get(key_a(persona)), cells.get(key_b(persona))
        if rows_a and rows_b:
            value_a, value_b = measure(rows_a), measure(rows_b)
            if value_a is not None and value_b is not None:
                differences.append(value_a - value_b)
    return differences


def has_interval(interval: Interval) -> bool:
    return interval.personas >= MINIMUM_PERSONAS_FOR_INTERVAL


def percent(interval: Interval) -> str:
    return f"{100 * interval.mean:.1f} " + (f"[{100 * interval.low:.1f}, {100 * interval.high:.1f}]" if has_interval(interval) else "[—]")


def points(interval: Interval) -> str:
    return f"{100 * interval.mean:+.1f} " + (f"[{100 * interval.low:+.1f}, {100 * interval.high:+.1f}]" if has_interval(interval) else "[—]")


def dollars(interval: Interval) -> str:
    return f"{interval.mean:.4f} " + (f"[{interval.low:.4f}, {interval.high:.4f}]" if has_interval(interval) else "[—]")


def table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "| --- |" + " --: |" * (len(header) - 1)]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    return "\n".join(lines)


def counted(numerator: str, denominator: str):
    return lambda rows: ratio(rows, numerator, denominator)


def sample_section(runs: list[dict], cells: dict, personas: list[str]) -> str:
    every_persona = sorted({row["persona"] for row in runs})
    rows = []
    for persona in every_persona:
        repetitions = [",".join(str(row["repetition"]) for row in sorted(cells.get((persona, policy), []), key=lambda row: row["repetition"])) or "-" for policy in POLICIES]
        rows.append([persona, "yes" if persona in personas else "no", *repetitions])
    return (
        "## Sample\n\nRepetitions in the s1-210 grid, per persona and policy. Only complete personas (repetition 0 of all 7 policies) enter the grid tables. "
        f"Intervals need at least {MINIMUM_PERSONAS_FOR_INTERVAL} complete personas; with fewer, tables show the mean and [—].\n\n" + table(["persona", "complete", *POLICIES], rows)
    )


def main_section(cells: dict, personas: list[str]) -> tuple[str, dict]:
    rows, intervals = [], {}
    for policy in POLICIES:
        key = lambda persona, policy=policy: (persona, policy)
        dreams = bootstrap(per_persona(cells, personas, key, lambda rows: mean_of(rows, "dreams")))
        maintenance = bootstrap(per_persona(cells, personas, key, lambda rows: mean_of(rows, "maintenance_cost")))
        exam = bootstrap(per_persona(cells, personas, key, lambda rows: mean_of(rows, "exam_cost")))
        accuracies = {name: bootstrap(per_persona(cells, personas, key, counted(numerator, denominator))) for name, numerator, denominator in COUNTS}
        intervals[policy] = (maintenance, accuracies)
        rows.append([policy, maintenance.personas, f"{dreams.mean:.1f}", dollars(maintenance), f"{exam.mean:.4f}", *(percent(accuracies[name]) for name, _, _ in COUNTS)])
    header = ["policy", "personas", "dreams", "maintenance $ (dreams + detector)", "exam $ (not in the policy)", *(f"{name} %" for name, _, _ in COUNTS)]
    text = (
        "## Accuracy and cost per policy, s1-210\n\nMean over personas of each persona's rate (repetitions averaged first), with a 95% interval from "
        f"{RESAMPLES:,} persona resamples (seed {BOOTSTRAP_SEED}). Costs are $ per persona over s1-210.\n\n" + table(header, rows)
    )
    return text, intervals


def pairs_section(cells: dict, personas: list[str]) -> str:
    rows = []
    for policy_a, policy_b in PAIRS:
        key_a, key_b = (lambda persona, policy=policy_a: (persona, policy)), (lambda persona, policy=policy_b: (persona, policy))
        for name, numerator, denominator in COUNTS:
            differences = paired(cells, personas, key_a, key_b, counted(numerator, denominator))
            ahead = sum(difference > 0 for difference in differences)
            behind = sum(difference < 0 for difference in differences)
            rows.append([f"{policy_a} − {policy_b}", name, points(bootstrap(differences)), f"{ahead} / {len(differences) - ahead - behind} / {behind}"])
        cost = bootstrap(paired(cells, personas, key_a, key_b, lambda rows: mean_of(rows, "maintenance_cost")))
        cost_ratio = bootstrap([a / b for a, b in zip(per_persona(cells, personas, key_a, lambda rows: mean_of(rows, "maintenance_cost")), per_persona(cells, personas, key_b, lambda rows: mean_of(rows, "maintenance_cost")))])
        rows.append([f"{policy_a} − {policy_b}", "maintenance $", dollars(cost), f"ratio {cost_ratio.mean:.2f} " + (f"[{cost_ratio.low:.2f}, {cost_ratio.high:.2f}]" if has_interval(cost_ratio) else "[—]")])
    return (
        "## Paired differences, s1-210\n\nInside each resampled persona: policy A minus policy B, in points of accuracy (or $). "
        "Last column: personas where A is ahead / tied / behind.\n\n" + table(["A − B", "count", "difference [95%]", "personas A > / = / < B"], rows)
    )


def unit_section(cells: dict, personas: list[str]) -> str:
    """Why the persona is the unit: the interval over personas against one that treats every question as independent."""
    rows = []
    for policy in POLICIES:
        persona_rows = [cells[persona, policy] for persona in personas]
        accuracy = bootstrap([ratio(rows, "official", "asked") for rows in persona_rows])
        first = [next(row for row in rows if row["repetition"] == 0) for rows in persona_rows]
        asked = sum(row["asked"] for row in first)
        pooled = sum(row["official"] for row in first) / asked
        question_width = 2 * 1.96 * math.sqrt(pooled * (1 - pooled) / asked)
        repeated = [rows for rows in persona_rows if {row["repetition"] for row in rows} >= {0, 1}]
        repetition_gap = [abs(by_repetition(rows, 0) - by_repetition(rows, 1)) for rows in repeated]
        spread = statistics.stdev(ratio(rows, "official", "asked") for rows in persona_rows) if len(persona_rows) > 1 else None
        rows.append([
            policy, f"{100 * (accuracy.high - accuracy.low):.1f}" if has_interval(accuracy) else "—", f"{100 * question_width:.1f}", f"{100 * spread:.1f}" if len(persona_rows) > 1 else "—",
            f"{100 * math.fsum(repetition_gap) / len(repetition_gap):.1f} ({len(repetition_gap)})" if repetition_gap else "-",
        ])
    return (
        "## Why the persona is the unit\n\nWidth of the 95% interval of official accuracy, in points: resampling personas, against a binomial interval over every "
        "question of repetition 0 as if they were independent. Spread across personas (standard deviation) and the mean gap between the two repetitions "
        "of the same persona (personas with both).\n\n" + table(["policy", "persona bootstrap", "questions as independent", "sd across personas", "mean |rep 0 − rep 1| (personas)"], rows)
    )


def by_repetition(rows: list[dict], repetition: int, numerator: str = "official", denominator: str = "asked") -> float:
    row = next(row for row in rows if row["repetition"] == repetition)
    return row[numerator] / row[denominator]


def repetition_section(cells: dict, personas: list[str]) -> str:
    """Noise between repetitions: repetition 1 minus repetition 0, per persona and policy, and for the paired differences."""
    repeated = [persona for persona in personas if all({row["repetition"] for row in cells[persona, policy]} >= {0, 1} for policy in POLICIES)]
    if not repeated:
        return "## Noise between repetitions, s1-210\n\nNo persona has both repetitions of every policy."
    decisions = ("dreams", "sessions_read", "exams", "asked")
    differing = [
        f"{policy} on {persona}" for persona in repeated for policy in POLICIES
        if len({tuple(row[column] for column in decisions) for row in cells[persona, policy]}) > 1
    ]
    parts = [f"Runs whose {', '.join(decisions)} differ between repetitions: {', '.join(differing) if differing else 'none'}."]
    for name, numerator, denominator in (COUNTS[0], COUNTS[2]):
        gaps = {(persona, policy): by_repetition(cells[persona, policy], 1, numerator, denominator) - by_repetition(cells[persona, policy], 0, numerator, denominator) for persona in repeated for policy in POLICIES}
        pair_gaps = {
            (persona, pair): gaps[persona, pair[0]] - gaps[persona, pair[1]] for persona in repeated for pair in PAIRS
        }
        rows = [[persona, *(f"{100 * gaps[persona, policy]:+.1f}" for policy in POLICIES), *(f"{100 * pair_gaps[persona, pair]:+.1f}" for pair in PAIRS)] for persona in repeated]
        summaries = (
            ("mean", lambda values: math.fsum(values) / len(values), "+.1f"),
            ("mean of absolute values", lambda values: math.fsum(map(abs, values)) / len(values), ".1f"),
            ("largest absolute value", lambda values: max(map(abs, values)), ".1f"),
            ("personas above zero", lambda values: sum(value > 0 for value in values) / 100, ".0f"),
        )
        for label, summary, form in summaries:
            rows.append([
                label, *(format(100 * summary([gaps[persona, policy] for persona in repeated]), form) for policy in POLICIES),
                *(format(100 * summary([pair_gaps[persona, pair] for persona in repeated]), form) for pair in PAIRS),
            ])
        header = ["persona", *POLICIES, *(f"{policy_a} − {policy_b}" for policy_a, policy_b in PAIRS)]
        parts.append(f"### {name}\n\n" + table(header, rows))
    return (
        "## Noise between repetitions, s1-210\n\nRepetition 1 minus repetition 0, in points, per persona: first for each policy, then for each paired difference "
        f"(how much A − B moves when the same persona is run again). {len(repeated)} personas with both repetitions of every policy.\n\n" + "\n\n".join(parts)
    )


def invented_section(cells: dict, personas: list[str]) -> str:
    """`nothing_logged` both ways (decision 2) and `partial_total` as a diagnostic only (decision 3)."""
    measures = (
        ("invented, current rule", lambda rows: ratio(rows, "invented", "asked")),
        ("invented, nothing_logged as stale", lambda rows: ratio([{**row, "kept": row["invented"] - row["nothing_logged"]} for row in rows], "kept", "asked")),
        ("stale, current rule", lambda rows: ratio(rows, "stale", "asked")),
        ("stale, nothing_logged as stale", lambda rows: ratio([{**row, "grown": row["stale"] + row["nothing_logged"]} for row in rows], "grown", "asked")),
        ("invented without marked, current rule", lambda rows: ratio(rows, "reachable_invented", "reachable_asked")),
        ("invented without marked, nothing_logged as stale", lambda rows: ratio([{**row, "kept": row["reachable_invented"] - row["reachable_nothing_logged"]} for row in rows], "kept", "reachable_asked")),
    )
    rows = []
    for policy in POLICIES:
        key = lambda persona, policy=policy: (persona, policy)
        first = [next(row for row in cells[persona, policy] if row["repetition"] == 0) for persona in personas]
        totals = {column: sum(row[column] for row in first) for column in ("invented", "nothing_logged", "partial_total", "reachable_invented", "reachable_nothing_logged")}
        rows.append([
            policy, *(percent(bootstrap(per_persona(cells, personas, key, measure))) for _, measure in measures),
            f"{totals['invented']} → {totals['invented'] - totals['nothing_logged']}", f"{totals['reachable_invented']} → {totals['reachable_invented'] - totals['reachable_nothing_logged']}", totals["partial_total"],
        ])
    header = ["policy", *(f"{name} %" for name, _ in measures), "invented, rep 0, all personas: current → reclassified", "same without marked", "partial_total (diagnostic)"]
    return (
        "## Invented answers both ways, s1-210\n\nRates per question, mean over personas [95%]. Reclassifying `nothing_logged` moves answers from invented to stale; "
        "accuracy does not change. `partial_total` counts invented totals that are the sum of some of the true entries: a diagnostic, never part of the official count.\n\n"
        + table(header, rows)
    )


def breakdown_section(probes: list[dict], personas: list[str], column: str, values: tuple[str, ...], labels: dict, output: Path, chart_name: str) -> str:
    cells = probe_cells(probes, column)
    parts, chart_values = [], {}
    for name, numerator, denominator in (COUNTS[0], COUNTS[2]):
        rows = []
        for policy in POLICIES:
            cells_row = []
            for value in values:
                rates = per_persona(cells, personas, lambda persona, policy=policy, value=value: (persona, policy, value), counted(numerator, denominator))
                if not rates:
                    cells_row.append("-")
                    continue
                interval = bootstrap(rates)
                cells_row.append(percent(interval) + (f" ({interval.personas})" if interval.personas < len(personas) else ""))
                if name == "official":
                    chart_values[policy, value] = (100 * interval.mean, 100 * interval.low, 100 * interval.high)
            rows.append([policy, *cells_row])
        parts.append(f"### {name}\n\n" + table(["policy", *(labels.get(value, value) for value in values)], rows))
    pair_rows = []
    for policy_a, policy_b in PAIRS:
        differences = []
        for value in values:
            key_a = lambda persona, policy=policy_a, value=value: (persona, policy, value)
            key_b = lambda persona, policy=policy_b, value=value: (persona, policy, value)
            found = paired(cells, personas, key_a, key_b, counted("official", "asked"))
            differences.append(points(bootstrap(found)) if found else "-")
        pair_rows.append([f"{policy_a} − {policy_b}", *differences])
    parts.append("### Paired differences, official (points)\n\n" + table(["A − B", *(labels.get(value, value) for value in values)], pair_rows))
    chart = charts.grouped_bar_chart(f"Official accuracy by {column}, s1-210 (mean over personas, 95% interval)", list(values), [*FIXED_BY_COST, TRIGGERED], chart_values, "% correct")
    (output / chart_name).write_text(chart)
    note = f"Mean over personas [95%]; a number in parentheses is how many personas were asked that {column}. Chart: `{chart_name}`."
    return f"## Accuracy by {column}, s1-210\n\n{note}\n\n" + "\n\n".join(parts)


def whole_section(runs: list[dict], output: Path) -> str:
    """every-1 − every-5 per stretch on the whole personas. Two personas: no interval over personas, only each persona's numbers."""
    cells = {(row["persona"], row["policy"], row["stretch"]): row for row in runs if row["scope"] == "whole" and row["repetition"] == 0}
    complete = [(persona, policy) for persona, policy in WHOLE_RUNS if all((persona, policy, stretch) in cells for stretch in STRETCHES)]
    missing = [f"{policy} on {persona}" for persona, policy in WHOLE_RUNS if (persona, policy) not in complete]
    accuracy_rows = []
    for persona, policy in complete:
        for name, numerator, denominator in (COUNTS[0], COUNTS[2]):
            accuracy_rows.append([persona, policy, name, *(f"{cells[persona, policy, stretch][numerator]}/{cells[persona, policy, stretch][denominator]} ({100 * cells[persona, policy, stretch][numerator] / cells[persona, policy, stretch][denominator]:.1f})" for stretch in STRETCHES)])
    available = (
        "## Whole personas: accuracy per stretch\n\nRepetition 0, every planned whole run with all three stretches. "
        f"Missing: {', '.join(missing) if missing else 'none'}.\n\n" + (table(["persona", "policy", "count", *STRETCHES], accuracy_rows) if accuracy_rows else "No whole run has all three stretches.")
    )
    personas = sorted({persona for persona, _ in complete if all((persona, name) in complete for name in ("every-1", "every-5"))})
    rows, series = [], {}
    for persona in personas:
        for name, numerator, denominator in (COUNTS[0], COUNTS[2]):
            gaps = []
            for stretch in STRETCHES:
                first, fifth = cells[persona, "every-1", stretch], cells[persona, "every-5", stretch]
                rate_first, rate_fifth = first[numerator] / first[denominator], fifth[numerator] / fifth[denominator]
                gaps.append(100 * (rate_first - rate_fifth))
                rows.append([persona, stretch, name, f"{first[numerator]}/{first[denominator]} ({100 * rate_first:.1f})", f"{fifth[numerator]}/{fifth[denominator]} ({100 * rate_fifth:.1f})", f"{gaps[-1]:+.1f}"])
            series[f"{persona}, {name}"] = gaps
    if not personas:
        (output / "whole-persona-gap.svg").unlink(missing_ok=True)
        return available + "\n\n## Whole personas: every-1 − every-5 per stretch\n\nNo persona has every-1 and every-5 on all three stretches."
    (output / "whole-persona-gap.svg").write_text(charts.stretch_chart("every-1 − every-5 per stretch, whole personas", list(STRETCHES), series, "points"))
    return available + (
        f"\n\n## Whole personas: every-1 − every-5 per stretch\n\nRepetition 0. With {len(personas)} persona(s) there is no interval over personas: these are each persona's own numbers. "
        "Chart: `whole-persona-gap.svg`.\n\n" + table(["persona", "stretch", "count", "every-1", "every-5", "every-1 − every-5 (points)"], rows)
    )


def persona_section(cells: dict, personas: list[str]) -> str:
    rows = []
    for persona in personas:
        rate = {policy: ratio(cells[persona, policy], "official", "asked") for policy in POLICIES}
        rows.append([
            persona, *(f"{100 * rate[policy]:.1f}" for policy in POLICIES), *(f"{100 * (rate[policy_a] - rate[policy_b]):+.1f}" for policy_a, policy_b in PAIRS),
            cells[persona, "never"][0]["asked"] - cells[persona, "never"][0]["reachable_asked"],
        ])
    header = ["persona", *POLICIES, *(f"{policy_a} − {policy_b}" for policy_a, policy_b in PAIRS), "marked"]
    return "## Official accuracy per persona, s1-210\n\nRepetitions averaged; differences in points. Last column: marked questions in the grid.\n\n" + table(header, rows)


def chart_section(intervals: dict, output: Path) -> str:
    panels = []
    for name in ("official", "official without marked"):
        panel = {}
        for policy, (maintenance, accuracies) in intervals.items():
            accuracy = accuracies[name]
            panel[policy] = ((maintenance.mean, maintenance.low, maintenance.high), (100 * accuracy.mean, 100 * accuracy.low, 100 * accuracy.high))
        panels.append((f"{name}, s1-210", panel))
    chart = charts.cost_accuracy_chart(panels, FIXED_BY_COST, TRIGGERED, "$ per persona to keep the memory (dreams + detector, no exams)", "% correct")
    (output / "accuracy-vs-cost.svg").write_text(chart)
    return "Main chart: `accuracy-vs-cost.svg` (fixed cadences joined in order of k, triggered-phrases-any apart; whiskers are the 95% intervals on both axes)."


def report(runs: list[dict], probes: list[dict], output: Path) -> str:
    cells = grid_cells(runs)
    personas = complete_personas(cells)
    sections = [sample_section(runs, cells, personas)]
    if personas:
        main, intervals = main_section(cells, personas)
        sections += [
            main, chart_section(intervals, output), pairs_section(cells, personas), unit_section(cells, personas), invented_section(cells, personas),
            breakdown_section(probes, personas, "probe", PROBES, PROBE_LABELS, output, "accuracy-by-probe.svg"),
            breakdown_section(probes, personas, "domain", DOMAINS, {}, output, "accuracy-by-domain.svg"),
            persona_section(cells, personas),
            repetition_section(cells, personas),
        ]
    sections.append(whole_section(runs, output))
    return "\n\n".join(sections) + "\n"


def fingerprint(path: str) -> str:
    content = Path(path).read_bytes()
    return f"`{path}`: {content.count(b'\n') - 1} rows, sha256 {hashlib.sha256(content).hexdigest()[:16]}"


def main():
    parser = argparse.ArgumentParser(description="P7b: Markdown tables and SVG charts from P7a's CSVs, with persona-level bootstrap intervals.")
    parser.add_argument("runs", help="data/p7-runs.csv")
    parser.add_argument("probes", help="data/p7-probes.csv")
    parser.add_argument("--output", default="docs/p7", help="directory for tables.md and the SVG charts")
    arguments = parser.parse_args()
    output = Path(arguments.output)
    output.mkdir(parents=True, exist_ok=True)
    header = f"# P7 tables\n\nGenerated by `PYTHONHASHSEED=0 uv run python -m final.analysis {arguments.runs} {arguments.probes} --output {arguments.output}`.\n\n- {fingerprint(arguments.runs)}\n- {fingerprint(arguments.probes)}\n\n"
    text = header + report(read_rows(arguments.runs), read_rows(arguments.probes), output)
    (output / "tables.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
