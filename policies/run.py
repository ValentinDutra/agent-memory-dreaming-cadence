"""Run any policy of P5, fixed or triggered, with the engine, and print the tables of the consolidated report. Owner: P5.

  uv run python -m policies.run monthly/academic_researcher:210 --policies never every-1 every-5 triggered-phrases-any \
      --budget-name p5 --limit 1.00 --check-cache

--check-cache runs with a cap of $0: a policy whose dreams, detector calls or exams are not all cached stops at the
first call it would pay, and is reported as such. Without it, the runs pay what is missing up to --limit.
"""

import argparse

from answering.client import BudgetedClient, BudgetExceeded
from exam.questions import EXAM_STEP
from policies import fixed, triggered_run
from policies.engine import run_policy


def policy_named(name: str, budget_name: str, limit: float):
    if name == "never" or name.startswith("every-"):
        return fixed.policy_named(name)
    return triggered_run.policy_named(name, limit, budget_name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slices", nargs="+", help='"period/persona[:through]"')
    parser.add_argument("--policies", nargs="+", required=True)
    parser.add_argument("--repetition", type=int, default=0)
    parser.add_argument("--exam-every", type=int, default=EXAM_STEP)
    parser.add_argument("--budget-name", default="p5")
    parser.add_argument("--limit", type=float, default=1.00)
    parser.add_argument("--check-cache", action="store_true", help="pay nothing; report the policies that are not fully cached")
    arguments = parser.parse_args()
    limit = 0.0 if arguments.check_cache else arguments.limit
    client = BudgetedClient(arguments.budget_name, limit)
    spent_before = client.spent()
    runs = []
    for spec in arguments.slices:
        period, persona, through = triggered_run.slice_of(spec)
        for name in arguments.policies:
            try:
                runs.append(run_policy(policy_named(name, arguments.budget_name, limit), period, persona, client, arguments.exam_every, through, arguments.repetition))
            except BudgetExceeded as error:
                if not arguments.check_cache:
                    raise
                print(f"{name} on {spec}: not fully cached ({error})")
    if runs:
        triggered_run.report(runs)
    print(f"\n{arguments.budget_name} spent: ${spent_before:.4f} before, ${client.spent():.4f} after")


if __name__ == "__main__":
    main()
