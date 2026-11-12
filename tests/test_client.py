import json

import pytest

from answering import client as client_module
from answering.client import BudgetedClient, BudgetExceeded, cost_of


def test_cost_switches_to_the_long_rate_above_100k_prompt_tokens():
    assert cost_of({"input_tokens": 100_000, "output_tokens": 1_000}) == pytest.approx(0.0105)
    assert cost_of({"input_tokens": 100_001, "output_tokens": 1_000}) == pytest.approx(0.0525005)


def test_refuses_a_call_that_could_cross_the_cap_without_touching_the_api(tmp_path, monkeypatch):
    monkeypatch.setattr(client_module, "RESULTS", tmp_path)
    budget = BudgetedClient("p3-test", limit_dollars=0.01)
    budget.ledger.parent.mkdir(parents=True)
    budget.ledger.write_text(json.dumps({"cost": 0.0099}) + "\n")
    with pytest.raises(BudgetExceeded):
        budget.complete("run", "system", "x" * 10_000, max_tokens=1_000)
    assert budget._client is None
