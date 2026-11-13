"""How good a dream's notes are, read line by line against the truth of P1. Owner: P4b.

Every fact that holds after session N is correct, stale, wrong (a value it never had) or missing from the notes.
Every note line that states no live fact is stale (a fact that stopped holding), invented (a known fact with a value
it never had), a duplicate, or unmatched (nothing in the truth by that name). Unmatched lines are split by whether
their words appear in the transcripts read so far: a dream may record what the user said and the answer key missed.

A dream names things its own way ("Ann Leckie's books" for Ann Leckie, "groceries" for grocery, a document by a
title of its own), so lines are matched to facts by domain and by the words of their name, never by label.
"""

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import cache

from exam.questions import DOCUMENT_TITLE_FIELD
from truth.timeline import FactId, Timeline, words

FACT_OUTCOMES = ("correct", "stale", "wrong", "missing")
LINE_OUTCOMES = ("stale", "invented", "duplicate", "unmatched_supported", "unmatched_unsupported", "prose", "unparsed")

# Which domain a "## " heading holds, by the first keyword it contains.
SECTION_KEYWORDS = (
    ("like", "preference"),
    ("to-do", "todo"),
    ("todo", "todo"),
    ("task", "todo"),
    ("calendar", "calendar"),
    ("event", "calendar"),
    ("goal", "goal"),
    ("document", "content"),
    ("expense", "expense"),
    ("step", "steps"),
)

# Two names match when one's word stems contain the other's, or when they share this share of stems.
# Document elements are sentences the dream paraphrases ("Benchmarking shows 62% latency reduction..."), so they match looser.
NAME_SIMILARITY = 0.75
ELEMENT_SIMILARITY = 0.5
EXACT = 2.0
# Share of a line's stems that must appear in the transcripts for an unmatched line to count as supported.
SUPPORTED_SHARE = 0.75


@dataclass(frozen=True)
class NoteFact:
    domain: str
    name: str          # what the line is about: an item, task, event, goal subject, document element, "date type", date
    value: object      # like/dislike, a date, a number, or True when the line only says the fact exists
    line: str
    block: int | None = None  # for document lines, which "### " block of the notes they sit in


@dataclass
class ParsedNotes:
    facts: list[NoteFact] = field(default_factory=list)
    prose: list[str] = field(default_factory=list)      # document fields outside the format ("- Platform: LinkedIn")
    unparsed: list[str] = field(default_factory=list)   # lines that fit no section or no line shape
    document_titles: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TruthFact:
    fact: FactId
    name: str
    current: object         # None when the fact does not hold after session N
    earlier: tuple          # values it held before, oldest first, without the current one
    document: str | None = None
    compare_value: bool = True


@dataclass
class Comparison:
    facts: Counter = field(default_factory=Counter)  # (domain, outcome) over the facts that hold after session N
    fact_outcomes: dict = field(default_factory=dict)  # FactId -> (outcome, value after session N) for those facts
    lines: Counter = field(default_factory=Counter)  # (domain, outcome) over note lines that state no live fact
    lenient: int = 0           # invented lines saying "dislike" about a like that was removed
    fuzzy_matches: int = 0     # lines matched to a fact by similar, not identical, name
    paraphrased: Counter = field(default_factory=Counter)  # domain -> correct live facts whose line names them in other words
    exact_matches: int = 0
    examples: list[tuple[str, str, str]] = field(default_factory=list)  # (outcome, domain, line or fact name)

    def fact_total(self, outcome: str | None = None) -> int:
        return sum(count for (_, each), count in self.facts.items() if outcome in (None, each))

    def line_total(self, outcome: str | None = None) -> int:
        return sum(count for (_, each), count in self.lines.items() if outcome in (None, each))


# --- Reading the notes --------------------------------------------------------------------------


def parse_notes(notes: str) -> ParsedNotes:
    parsed = ParsedNotes()
    domain = None
    block = -1
    for line in notes.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith("## "):
            domain = section_domain(text[3:])
            continue
        if text.startswith("### "):
            # A document heading opens a document block wherever the dream put it ("## Meeting notes" happens).
            domain = "content"
            block += 1
            heading = text[4:]
            parsed.document_titles[block] = heading.split(": ", 1)[1] if ": " in heading else heading
            continue
        bullet = re.fullmatch(r"[-*] (.+)", text)
        if bullet and re.fullmatch(r"(?:.*: )?\(.*\)", bullet.group(1)):
            continue  # "- (none)", "- Daily step goal: (none)" and other placeholders
        if domain is None or bullet is None:
            parsed.unparsed.append(line)
            continue
        if domain == "content":
            parse_document_line(line, bullet.group(1), block, parsed)
            continue
        note_fact = parse_line(domain, bullet.group(1), line)
        if note_fact is None:
            parsed.unparsed.append(line)
        else:
            parsed.facts.append(note_fact)
    return parsed


def section_domain(heading: str) -> str | None:
    folded = heading.casefold()
    return next((domain for keyword, domain in SECTION_KEYWORDS if keyword in folded), None)


def parse_line(domain: str, text: str, line: str) -> NoteFact | None:
    if domain == "preference":
        match = re.fullmatch(r"(.+?)(?: \([^()]*\))?: (like|dislike)", text, flags=re.IGNORECASE)
        return match and NoteFact(domain, match.group(1), match.group(2).casefold(), line)
    if domain == "todo":
        match = re.fullmatch(r"(.+?)(?: \([^()]*\))?", text)
        return NoteFact(domain, match.group(1), True, line)
    if domain == "calendar":
        match = re.fullmatch(r"(.+?):? (\d{4}-\d{2}-\d{2})(?: \(.*\))?", text) or re.fullmatch(r"(.+?)(?: \([^()]*\))?", text)
        return NoteFact(domain, match.group(1), match.group(2) if match.lastindex == 2 else None, line)
    if domain == "goal":
        steps = re.fullmatch(r"daily step goal: ([\d,]+)(?: steps)?", text, flags=re.IGNORECASE)
        if steps:
            return NoteFact(domain, "daily_steps", number(steps.group(1)), line)
        budget = re.fullmatch(r"weekly budget for (.+?)(?: expenses)?: \$?([\d,.]+)", text, flags=re.IGNORECASE)
        return budget and NoteFact(domain, budget.group(1), number(budget.group(2)), line)
    if domain == "expense":
        match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) (.+?): \$?([\d,.]+)", text)
        return match and NoteFact(domain, f"{match.group(1)} {match.group(2)}", number(match.group(3)), line)
    if domain == "steps":
        match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}): ([\d,]+)(?: steps)?", text)
        return match and NoteFact(domain, match.group(1), number(match.group(2)), line)
    return None


def parse_document_line(line: str, text: str, block: int, parsed: ParsedNotes) -> None:
    """Indented bullets are list elements; "- field:" opens a list; "- budget: $n" is the budget; other "- field: value" is prose."""
    if block < 0:
        parsed.unparsed.append(line)
        return
    indented = line[: len(line) - len(line.lstrip())] != ""
    budget = re.fullmatch(r"budget: \$?([\d,.]+)", text, flags=re.IGNORECASE)
    if indented:
        parsed.facts.append(NoteFact("content", text, True, line, block))
    elif budget:
        parsed.facts.append(NoteFact("content", "budget", number(budget.group(1)), line, block))
    elif text.endswith(":"):
        return
    elif re.fullmatch(r"[\w /-]{1,40}: .+", text):
        parsed.prose.append(line)
    else:
        parsed.facts.append(NoteFact("content", text, True, line, block))


def number(text: str) -> float:
    return round(float(text.replace(",", "").rstrip(".")), 2)


# --- The truth after session N, in the same terms -----------------------------------------------


def truth_facts(timeline: Timeline, session_id: int) -> list[TruthFact]:
    """Every fact that held at some point up to session_id, except document titles and prose."""
    versions_by_fact = defaultdict(list)
    for version in sorted(timeline.versions, key=lambda version: version.valid_from):
        if version.valid_from <= session_id and not is_title_or_prose(version.domain, version.key):
            versions_by_fact[version.domain, version.key].append(version)
    facts = []
    for fact, versions in versions_by_fact.items():
        domain, key = fact
        values = []
        for version in versions:
            value = projected_value(domain, version.value)
            if not values or values[-1] != value:
                values.append(value)
        current_version = next((version for version in versions if version.holds_after(session_id)), None)
        current = projected_value(domain, current_version.value) if current_version else None
        earlier = tuple(value for value in values if value != current)
        # Memora's stored date of a rescheduled event does not match what the user said (P1 defect 1); the exam asks only if it exists.
        compare_value = not (domain == "calendar" and len(values) > 1)
        facts.append(TruthFact(fact, fact_name(domain, key, versions[-1].value), current, earlier, key[0] if domain == "content" else None, compare_value))
    return facts


def is_title_or_prose(domain: str, key: tuple[str, ...]) -> bool:
    return domain == "content" and len(key) == 2 and key[1] != "budget"


def fact_name(domain: str, key: tuple[str, ...], value: dict) -> str:
    if domain == "preference":
        return key[2]
    if domain == "content":
        return key[2] if len(key) == 3 else "budget"
    if domain == "expense":
        return f"{value['date']} {value['expense_type']}"
    return key[0]


def projected_value(domain: str, value: dict) -> object:
    if domain == "preference":
        return value["preference"]
    if domain == "calendar":
        return value["event_date"]
    if domain == "goal":
        return round(float(value["value"]), 2)
    if domain == "expense":
        return round(float(value["amount"]), 2)
    if domain == "steps":
        return round(float(value["step_count"]), 2)
    if "value" in value and not isinstance(value["value"], str):
        return round(float(value["value"]), 2)  # a document budget
    return True


def document_titles(timeline: Timeline, session_id: int) -> dict[str, str]:
    titles = {}
    for version in timeline.versions:
        if version.domain == "content" and len(version.key) == 2 and version.valid_from <= session_id:
            document_id, field_name = version.key
            if field_name == DOCUMENT_TITLE_FIELD[document_id.rsplit("_", 1)[0]]:
                titles[document_id] = version.value["value"]
    return titles


# --- Matching names -----------------------------------------------------------------------------


@cache
def stems(text: str) -> frozenset[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return frozenset(word[:5] for word in words(plain) if len(word) > 1 or word.isdigit())


@cache
def similarity(line_name: str, truth_name: str, looser: bool = False) -> float:
    """EXACT for the same words; otherwise the share of stems they share, or 1 when one's stems contain the other's."""
    if plain_words(line_name) == plain_words(truth_name):
        return EXACT
    line_stems, truth_stems = stems(line_name), stems(truth_name)
    if not line_stems or not truth_stems:
        return 0.0
    shared = len(line_stems & truth_stems) / max(len(line_stems), len(truth_stems))
    if not looser and (truth_stems <= line_stems or line_stems <= truth_stems):
        return 1.0
    return shared if shared >= (ELEMENT_SIMILARITY if looser else NAME_SIMILARITY) else 0.0


@cache
def plain_words(text: str) -> tuple[str, ...]:
    return tuple(words(text))


# --- Comparing ----------------------------------------------------------------------------------


def compare_notes(notes: str, timeline: Timeline, session_id: int, transcript_text: str = "") -> Comparison:
    """Classify every live fact and every note line. transcript_text is what the dreams read up to session_id."""
    parsed = parse_notes(notes)
    truth = truth_facts(timeline, session_id)
    comparison = Comparison()
    transcript_stems = stems(transcript_text)
    groups = defaultdict(lambda: ([], []))  # group -> (note facts, truth facts)
    for truth_fact in truth:
        groups[truth_fact.document if truth_fact.fact[0] == "content" else truth_fact.fact[0]][1].append(truth_fact)
    block_documents = match_documents(parsed, truth, document_titles(timeline, session_id))
    for note_fact in parsed.facts:
        if note_fact.domain == "content":
            document = block_documents.get(note_fact.block)
            groups[document if document else f"unmatched block {note_fact.block}"][0].append(note_fact)
        else:
            groups[note_fact.domain][0].append(note_fact)
    for note_facts, truth_group in groups.values():
        match_group(note_facts, truth_group, comparison, transcript_stems)
    for line in parsed.prose:
        record_line(comparison, "content", "prose", line)
    for line in parsed.unparsed:
        record_line(comparison, "unknown", "unparsed", line)
    return comparison


def match_documents(parsed: ParsedNotes, truth: list[TruthFact], titles: dict[str, str]) -> dict[int, str]:
    """Each "### " block of the notes goes to the truth document whose list elements and title it shares most."""
    elements_by_document = defaultdict(list)
    for truth_fact in truth:
        if truth_fact.document:
            elements_by_document[truth_fact.document].append(truth_fact.name)
    lines_by_block = defaultdict(list)
    for note_fact in parsed.facts:
        if note_fact.domain == "content" and note_fact.name != "budget":
            lines_by_block[note_fact.block].append(note_fact.name)
    matches = {}
    for block, title in parsed.document_titles.items():
        def score(document: str) -> float:
            shared_elements = sum(
                any(similarity(line_name, element, looser=True) for element in elements_by_document[document])
                for line_name in lines_by_block[block]
            )
            title_score = similarity(title, titles.get(document, ""), looser=True)
            return shared_elements + min(title_score, 1.0)
        candidates = set(elements_by_document) | set(titles)
        best = max(candidates, key=score, default=None)
        if best is not None and score(best) >= ELEMENT_SIMILARITY:
            matches[block] = best
    return matches


def match_group(note_facts: list[NoteFact], truth_group: list[TruthFact], comparison: Comparison, transcript_stems: frozenset[str]) -> None:
    """Pair lines and facts one to one: closest names first, then lines whose value the fact had, then live facts."""
    candidates = []
    for line_index, note_fact in enumerate(note_facts):
        for fact_index, truth_fact in enumerate(truth_group):
            score = similarity(note_fact.name, truth_fact.name, looser=note_fact.domain == "content")
            if score:
                agreement = 2 if note_fact.value == truth_fact.current else 1 if note_fact.value in truth_fact.earlier else 0
                candidates.append((score, agreement, truth_fact.current is not None, line_index, fact_index))
    candidates.sort(reverse=True)
    line_fact = {}
    taken_facts = set()
    for score, _, _, line_index, fact_index in candidates:
        if line_index in line_fact or fact_index in taken_facts:
            continue
        line_fact[line_index] = fact_index
        taken_facts.add(fact_index)
        if score == EXACT:
            comparison.exact_matches += 1
        else:
            comparison.fuzzy_matches += 1
    lines_with_candidates = {line_index for _, _, _, line_index, _ in candidates}
    for line_index, note_fact in enumerate(note_facts):
        if line_index in line_fact:
            truth_fact = truth_group[line_fact[line_index]]
            outcome = classify_pair(note_fact, truth_fact, comparison)
            if outcome == "correct" and similarity(note_fact.name, truth_fact.name, looser=note_fact.domain == "content") != EXACT:
                comparison.paraphrased[note_fact.domain] += 1
        elif line_index in lines_with_candidates:
            record_line(comparison, note_fact.domain, "duplicate", note_fact.line)
        else:
            supported = stem_share(note_fact.name, transcript_stems) >= SUPPORTED_SHARE
            record_line(comparison, note_fact.domain, "unmatched_supported" if supported else "unmatched_unsupported", note_fact.line)
    for fact_index, truth_fact in enumerate(truth_group):
        if fact_index not in taken_facts and truth_fact.current is not None:
            record_fact(comparison, truth_fact, "missing", "(absent)")


def classify_pair(note_fact: NoteFact, truth_fact: TruthFact, comparison: Comparison) -> str:
    same = (lambda value: True) if not truth_fact.compare_value else (lambda value: note_fact.value == value)
    if truth_fact.current is not None:
        outcome = "correct" if same(truth_fact.current) else "stale" if any(same(value) for value in truth_fact.earlier) else "wrong"
        record_fact(comparison, truth_fact, outcome, note_fact.line)
        return outcome
    if any(same(value) for value in truth_fact.earlier):
        record_line(comparison, note_fact.domain, "stale", note_fact.line)
        return "stale"
    record_line(comparison, note_fact.domain, "invented", note_fact.line)
    # Decision (P2): "dislike" after a removed like is invented, and the lenient count is always reported.
    comparison.lenient += note_fact.domain == "preference" and note_fact.value == "dislike" and truth_fact.earlier[-1:] == ("like",)
    return "invented"


def stem_share(name: str, transcript_stems: frozenset[str]) -> float:
    name_stems = stems(name)
    return len(name_stems & transcript_stems) / len(name_stems) if name_stems else 0.0


def record_fact(comparison: Comparison, truth_fact: TruthFact, outcome: str, shown: str) -> None:
    comparison.facts[truth_fact.fact[0], outcome] += 1
    comparison.fact_outcomes[truth_fact.fact] = (outcome, truth_fact.current)
    if outcome != "correct":
        comparison.examples.append((f"fact {outcome}", truth_fact.fact[0], f"{truth_fact.name} | expected {truth_fact.current!r} | notes: {shown.strip()}"))


def record_line(comparison: Comparison, domain: str, outcome: str, line: str) -> None:
    comparison.lines[domain, outcome] += 1
    comparison.examples.append((f"line {outcome}", domain, line.strip()))
