"""Questions exam.unreachable marks now and did not mark at a git revision, or the other way round. Owner: P6a.

  uv run python -m diagnosis.marks_diff 5fc7cc4 weekly monthly

The old exam/unreachable.py is read with `git show <revision>:exam/unreachable.py` and loaded beside the current one.
"""

import importlib.util
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from exam.unreachable import unreachable
from truth.changes import personas


def module_at(revision: str):
    source = subprocess.run(["git", "show", f"{revision}:exam/unreachable.py"], capture_output=True, text=True, check=True).stdout
    path = Path(tempfile.mkdtemp()) / "unreachable_at_revision.py"
    path.write_text(source)
    spec = importlib.util.spec_from_file_location("unreachable_at_revision", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def in_first_210(question_ids: set[str]) -> int:
    return sum(int(question_id.split("/")[2][1:]) <= 210 for question_id in question_ids)


def main() -> None:
    revision, *periods = sys.argv[1:]
    old = module_at(revision)
    print("| period/persona | added | added in s1-210 | removed | removed in s1-210 |\n| --- | --: | --: | --: | --: |")
    totals = Counter()
    for period in periods:
        for persona in personas(period):
            before, after = old.unreachable(period, persona), unreachable(period, persona)
            added, removed = set(after) - set(before), set(before) - set(after)
            row = Counter(added=len(added), added_early=in_first_210(added), removed=len(removed), removed_early=in_first_210(removed))
            totals += row
            if added or removed:
                print(f"| {period}/{persona} | {row['added']} | {row['added_early']} | {row['removed']} | {row['removed_early']} |")
    print(f"| **total** | {totals['added']} | {totals['added_early']} | {totals['removed']} | {totals['removed_early']} |")


if __name__ == "__main__":
    main()
