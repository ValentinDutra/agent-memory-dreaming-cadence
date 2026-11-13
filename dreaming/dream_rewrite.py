"""Variant compared by P4a: the same prompt as dreaming/dream.py, but the model rewrites the whole notes."""

import re

from answering.client import BudgetedClient
from dreaming.dream import MAX_TOKENS, SYSTEM, DreamResult, canonical, dream_prompt
from dreaming.transcripts import Session

REWRITE_FORMAT = "Reply with the complete updated notes inside <notes> tags: every fact that is still true, changed or not."


def dream(notes: str, sessions: list[Session], client: BudgetedClient, run: str) -> DreamResult:
    completion = client.complete(run, SYSTEM, dream_prompt(notes, sessions, REWRITE_FORMAT), max_tokens=MAX_TOKENS)
    return DreamResult(canonical(extract_notes(completion.text)), completion.input_tokens, completion.output_tokens, completion.cost, completion.from_cache)


def extract_notes(text: str) -> str:
    blocks = re.findall(r"<notes>\n?(.*?)\n?</notes>", text, flags=re.DOTALL)
    return blocks[-1].strip() if blocks else ""
