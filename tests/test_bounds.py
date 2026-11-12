import re

from answering.bounds import CallLog, measure_exams
from answering.format_totals import with_totals
from answering.client import Completion
from exam.questions import build_exam
from truth.changes import persona_changes
from truth.timeline import build_timeline


class UnknownToEverything:
    """Answers every question "unknown" and remembers what it was asked."""

    thinking = {"type": "disabled"}

    def __init__(self):
        self.requests = []

    def complete(self, run, system, user, max_tokens, repeat=0):
        self.requests.append((user, repeat))
        question_count = len(re.findall(r"^\d+\. ", user, flags=re.MULTILINE))
        text = "<answers>\n" + "\n".join(f"{number}: unknown" for number in range(1, question_count + 1)) + "\n</answers>"
        return Completion(text, 0, 0, 0.0, False, "default", {"type": "disabled"}, "low", "fake")


def test_ceiling_gets_the_truth_after_the_session_floor_gets_nothing_and_noise_reuses_the_ceiling():
    client = UnknownToEverything()
    exam_runs = measure_exams("weekly", "software_engineer".split(), ["ceiling", "floor", "noise"], 23, CallLog(client, dry_run=False))

    # every=23 keeps only the first exam (session 7): one call each for ceiling, floor and noise repeats 1 and 2.
    assert [repeat for _, repeat in client.requests] == [0, 0, 1, 2]
    ceiling_prompt, floor_prompt = client.requests[0][0], client.requests[1][0]
    assert "Bonobo" not in ceiling_prompt  # liked from session 17 on: not yet in the notes after session 7
    assert "trail running" in ceiling_prompt
    assert floor_prompt.startswith("<notes>\n\n</notes>")
    assert [(exam_run.measure, exam_run.repeat) for exam_run in exam_runs] == [("ceiling", 0), ("floor", 0), ("noise", 0), ("noise", 1), ("noise", 2)]
    assert exam_runs[0].grades is exam_runs[2].grades


def test_weekly_totals_match_every_weekly_aggregate_of_the_exam():
    timeline = build_timeline(persona_changes("weekly", "software_engineer"))
    aggregates = [question for question in build_exam("weekly", "software_engineer") if question.probe == "aggregate"]
    label = {"expense": r"food expenses \$([\d.]+)", "steps": r"(\d+) steps"}
    for question in aggregates:
        start = re.findall(r"\d{4}-\d{2}-\d{2}", question.prompt)[0]
        notes = with_totals("", timeline.state_after(question.session_id))
        week_line = next(line for line in notes.splitlines() if line.startswith(f"- Week {start} "))
        assert float(re.search(label[question.domain], week_line).group(1)) == question.current["value"], question.question_id
    assert len(aggregates) == 44
