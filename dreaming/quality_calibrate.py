"""Calibrate the line-by-line comparison: perfect notes must read 100% correct, with nothing extra. Owner: P4b.

    uv run python -m dreaming.quality_calibrate weekly monthly quarterly

Checks render_notes(state_after(N)) of every persona at every exam session N (multiples of 7) and prints every miss.
"""

import sys

from answering.notes import render_notes
from dreaming.quality import compare_notes, is_title_or_prose
from exam.questions import EXAM_STEP
from truth.changes import persona_changes, personas
from truth.timeline import build_timeline


def calibrate(period: str) -> tuple[int, int, int]:
    """(notes checked, notes with any miss, live facts checked) over every persona and exam session of the period."""
    checked = misses = facts = 0
    for persona in personas(period):
        timeline = build_timeline(persona_changes(period, persona))
        last_session = max(version.valid_from for version in timeline.versions)
        for session_id in range(EXAM_STEP, last_session + EXAM_STEP, EXAM_STEP):
            state = timeline.state_after(session_id)
            live = sum(not is_title_or_prose(domain, key) for domain, key in state)
            comparison = compare_notes(render_notes(state), timeline, session_id)
            checked += 1
            facts += live
            perfect = comparison.fact_total("correct") == comparison.fact_total() == live
            if not perfect or comparison.line_total() or comparison.fuzzy_matches:
                misses += 1
                print(f"  miss {period}/{persona} N={session_id}: {dict(comparison.facts)} {dict(comparison.lines)} {comparison.examples[:3]}")
    return checked, misses, facts


if __name__ == "__main__":
    for period in sys.argv[1:]:
        checked, misses, facts = calibrate(period)
        print(f"{period}: {checked} perfect notes, {facts} live facts, {misses} with any line not correct")
