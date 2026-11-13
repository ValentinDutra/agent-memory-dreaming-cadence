"""Measure a detector alone against the truth of P1: per session, its verdict against session_change. Owner: P5b.

The label of session s is what s did to the truth: "none", "add" (only new facts) or "change". The detector that reads
notes gets the perfect notes after s-1 (P3's render_notes of the truth), so that "something the notes do not reflect"
means exactly the label. This script reads the truth to measure; the detectors never do.

Run:
  uv run python -m policies.triggered_detector phrases weekly/* monthly/*
  uv run python -m policies.triggered_detector model weekly/software_engineer monthly/academic_researcher:210 --dry-run
"""

import argparse
from collections import Counter
from dataclasses import dataclass

from answering.client import BudgetedClient
from answering.notes import render_notes
from dreaming.transcripts import load_transcripts
from policies.session_changes import SESSION_CHANGES, session_change
from policies.triggered import VERDICTS, Detection, ModelDetector, PhraseDetector, Screened
from truth.changes import persona_changes, personas
from truth.timeline import Timeline, build_timeline

BUDGET_NAME = "p5b"
DETECTOR_THINKING = {"type": "disabled"}
# Haiku 5.5 short-prompt prices (answering/client.py); ~4 characters per token for the dry-run estimate.
INPUT_DOLLARS_PER_CHARACTER = 0.10 / 1_000_000 / 4


@dataclass(frozen=True)
class Verdicted:
    period: str
    persona: str
    session_id: int
    label: str
    domains: frozenset[str]          # domains of the facts the session changed or added
    changed_domains: frozenset[str]  # domains of the facts that held before and changed or stopped holding
    detection: Detection


def detector_named(name: str, limit: float):
    if name == "phrases":
        return PhraseDetector()
    client = BudgetedClient(BUDGET_NAME, limit, thinking=DETECTOR_THINKING, effort="low")
    model = ModelDetector(client, with_notes=name.endswith("model-notes"))
    return Screened(model) if name.startswith("screened-") else model


def slice_members(spec: str) -> list[tuple[str, str, int | None]]:
    """"monthly/academic_researcher:210" -> sessions 1-210 of one persona; "weekly/*" -> every persona, every session."""
    name, _, through = spec.partition(":")
    period, persona = name.split("/")
    return [(period, each, int(through) if through else None) for each in (personas(period) if persona == "*" else [persona])]


def session_domains(timeline: Timeline, session_id: int) -> tuple[frozenset[str], frozenset[str]]:
    changed = timeline.changed_between(session_id - 1, session_id)
    return (
        frozenset(domain for domain, _ in changed),
        frozenset(domain for (domain, _), (before, _) in changed.items() if before is not None),
    )


def measure(detector, period: str, persona: str, through: int | None, dry_run: bool) -> tuple[list[Verdicted], float]:
    """The verdicts, and the estimated cost of the calls (0 for the phrases)."""
    timeline = build_timeline(persona_changes(period, persona))
    sessions = [session for session in load_transcripts(period, persona) if through is None or session.session_id <= through]
    run = f"p5/r0/decide/{detector.name}{'-perfect' if getattr(detector, 'with_notes', False) else ''}/{period}/{persona}"
    verdicts = []
    estimate = 0.0
    for session in sessions:
        notes = render_notes(timeline.state_after(session.session_id - 1))
        if isinstance(detector, (ModelDetector, Screened)):
            model = detector.model if isinstance(detector, Screened) else detector
            estimate += len(model.prompt(notes, session)) * INPUT_DOLLARS_PER_CHARACTER
        if dry_run:
            continue
        domains, changed_domains = session_domains(timeline, session.session_id)
        verdicts.append(Verdicted(
            period, persona, session.session_id, session_change(timeline, session.session_id),
            domains, changed_domains, detector.detect(notes, session, run),
        ))
    return verdicts, estimate


def rate(part: int, whole: int) -> str:
    return f"{part}/{whole} ({part / whole:.0%})" if whole else "-"


def report(title: str, verdicts: list[Verdicted]) -> None:
    confusion = Counter((each.label, each.detection.verdict) for each in verdicts)
    print(f"\n### {title}: {len(verdicts)} sessions")
    print("| truth \\ verdict | " + " | ".join(VERDICTS) + " |\n| --- |" + " --: |" * len(VERDICTS))
    for label in SESSION_CHANGES:
        print(f"| {label} | " + " | ".join(str(confusion[label, verdict]) for verdict in VERDICTS) + " |")

    print("\n| target | fires | precision | recall |\n| --- | --: | --: | --: |")
    for target, positive, flagged in (
        ("any fact (add or change)", lambda each: each.label != "none", lambda each: each.detection.verdict != "none"),
        ("change only", lambda each: each.label == "change", lambda each: each.detection.verdict == "change"),
    ):
        fired = [each for each in verdicts if flagged(each)]
        relevant = [each for each in verdicts if positive(each)]
        hits = sum(positive(each) for each in fired)
        print(f"| {target} | {rate(len(fired), len(verdicts))} | {rate(hits, len(fired))} | {rate(hits, len(relevant))} |")

    domains = sorted({domain for each in verdicts for domain in each.domains})
    print("\n| domain | sessions with a fact | flagged (any) | sessions with a change | flagged change |\n| --- | --: | --: | --: | --: |")
    for domain in domains:
        with_fact = [each for each in verdicts if domain in each.domains]
        with_change = [each for each in verdicts if domain in each.changed_domains]
        print(
            f"| {domain} | {len(with_fact)} | {rate(sum(each.detection.verdict != 'none' for each in with_fact), len(with_fact))} "
            f"| {len(with_change)} | {rate(sum(each.detection.verdict == 'change' for each in with_change), len(with_change))} |"
        )

    cost = sum(each.detection.cost for each in verdicts)
    input_tokens = sum(each.detection.input_tokens for each in verdicts)
    if cost:
        print(f"\ncost ${cost:.4f} | ${cost / len(verdicts):.6f} per session | {input_tokens / len(verdicts):.0f} input tokens per session")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("detector", choices=("phrases", "model", "model-notes", "screened-model"))
    parser.add_argument("slices", nargs="+", help='"period/persona[:through]" or "period/*"')
    parser.add_argument("--limit", type=float, default=1.50, help="dollar cap of the p5b budget")
    parser.add_argument("--dry-run", action="store_true", help="estimate the cost of the calls and call nothing")
    arguments = parser.parse_args()
    detector = detector_named(arguments.detector, arguments.limit)
    model = detector.model if isinstance(detector, Screened) else detector
    spent_before = model.client.spent() if isinstance(model, ModelDetector) else 0.0
    for spec in arguments.slices:
        verdicts = []
        for period, persona, through in slice_members(spec):
            measured, estimate = measure(detector, period, persona, through, arguments.dry_run)
            if arguments.dry_run:
                print(f"{period}/{persona}: estimated input ${estimate:.4f} (output ~2 tokens per session)")
            verdicts.extend(measured)
        if verdicts:
            report(f"{arguments.detector} on {spec}", verdicts)
    if isinstance(model, ModelDetector) and not arguments.dry_run:
        print(f"\np5b spent: ${spent_before:.4f} before, ${model.client.spent():.4f} after")


if __name__ == "__main__":
    main()
