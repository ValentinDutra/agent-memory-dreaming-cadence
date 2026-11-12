"""The only door to the Anthropic API in P3: one model, one temperature, a spending cap and a cache of raw responses."""

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import anthropic
from dotenv import load_dotenv

MODEL = "claude-haiku-5-5"
# Claude Haiku 5.5 takes no temperature, top_p or top_k (https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide):
# sampling stays at the model's default, so repeat runs measure its noise. Thinking and effort are the knobs left,
# fixed per client and recorded in every raw response.
TEMPERATURE = "model default (not settable)"
THINKING = {"type": "adaptive"}
EFFORT = "medium"

# A git worktree has no .env of its own; ENV_FILE points it at the main checkout's.
ENV_FILE = Path(os.environ.get("ENV_FILE", Path(__file__).resolve().parent.parent / ".env"))
RESULTS = Path(__file__).resolve().parent.parent / "results"

# Dollars per million tokens. Above LONG_PROMPT_TOKENS input tokens the whole request is billed at the long rate.
LONG_PROMPT_TOKENS = 100_000
INPUT_PRICE = {"short": 0.10, "long": 0.50}
OUTPUT_PRICE = {"short": 0.50, "long": 2.50}
# Anthropic bills cache writes at 1.25x and cache reads at 0.1x the input price.
CACHE_WRITE_FACTOR = 1.25
CACHE_READ_FACTOR = 0.10


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    cost: float       # dollars billed when the response was first fetched
    from_cache: bool  # True when read from results/raw instead of calling the API
    temperature: str
    thinking: dict
    effort: str
    model: str


def cost_of(usage: dict) -> float:
    cache_write = usage.get("cache_creation_input_tokens") or 0
    cache_read = usage.get("cache_read_input_tokens") or 0
    prompt_tokens = usage["input_tokens"] + cache_write + cache_read
    tier = "long" if prompt_tokens > LONG_PROMPT_TOKENS else "short"
    input_dollars = (usage["input_tokens"] + CACHE_WRITE_FACTOR * cache_write + CACHE_READ_FACTOR * cache_read) * INPUT_PRICE[tier]
    return (input_dollars + usage["output_tokens"] * OUTPUT_PRICE[tier]) / 1_000_000


def worst_case_cost(prompt_text: str, max_tokens: int) -> float:
    """An upper bound before the call: a BPE token is never shorter than one byte."""
    prompt_bytes = len(prompt_text.encode())
    return cost_of({"input_tokens": prompt_bytes, "output_tokens": max_tokens})


class BudgetedClient:
    """Calls the model only while the dollars recorded in results/spend/<budget_name>.jsonl stay under limit_dollars.

    The ledger persists across runs, so the cap holds for the whole process (P3a, P3b or P3), not for one script.
    """

    def __init__(self, budget_name: str, limit_dollars: float, thinking: dict = THINKING, effort: str = EFFORT):
        self.budget_name = budget_name
        self.limit_dollars = limit_dollars
        self.thinking = thinking
        self.effort = effort
        self._client = None

    @property
    def ledger(self) -> Path:
        return RESULTS / "spend" / f"{self.budget_name}.jsonl"

    def spent(self) -> float:
        if not self.ledger.exists():
            return 0.0
        return sum(json.loads(line)["cost"] for line in self.ledger.read_text().splitlines() if line)

    def complete(self, run: str, system: str, user: str, max_tokens: int, repeat: int = 0) -> Completion:
        """One message. The same request (and repeat number) is answered from results/raw/<run>/ for free."""
        request = {"model": MODEL, "thinking": self.thinking, "effort": self.effort, "system": system, "user": user, "max_tokens": max_tokens, "repeat": repeat}
        digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:20]
        raw_file = RESULTS / "raw" / run / f"{digest}.json"
        if raw_file.exists():
            record = json.loads(raw_file.read_text())
            return completion_from(record, from_cache=True)

        spent = self.spent()
        worst_case = worst_case_cost(system + user, max_tokens)
        if spent + worst_case > self.limit_dollars:
            raise BudgetExceeded(f"{self.budget_name}: spent ${spent:.4f}, next call up to ${worst_case:.4f}, cap ${self.limit_dollars:.2f}")

        response = self.client().messages.create(
            model=MODEL,
            thinking=self.thinking,
            output_config={"effort": self.effort},
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        usage = response.usage.model_dump()
        record = {
            "request": request,
            "text": "".join(block.text for block in response.content if block.type == "text"),
            "stop_reason": response.stop_reason,
            "usage": usage,
            "cost": cost_of(usage),
            "model": response.model,
            "temperature": TEMPERATURE,
            "thinking": self.thinking,
            "effort": self.effort,
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        raw_file.parent.mkdir(parents=True, exist_ok=True)
        raw_file.write_text(json.dumps(record, indent=1))
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a") as ledger:
            ledger.write(json.dumps({"time": record["time"], "run": run, "raw": raw_file.name, "usage": usage, "cost": record["cost"]}) + "\n")
        return completion_from(record, from_cache=False)

    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            load_dotenv(ENV_FILE)
            self._client = anthropic.Anthropic()
        return self._client


def completion_from(record: dict, from_cache: bool) -> Completion:
    return Completion(
        text=record["text"],
        input_tokens=record["usage"]["input_tokens"],
        output_tokens=record["usage"]["output_tokens"],
        cost=record["cost"],
        from_cache=from_cache,
        temperature=record["temperature"],
        thinking=record["thinking"],
        effort=record["effort"],
        model=record["model"],
    )
