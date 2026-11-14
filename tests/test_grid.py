from final.grid import BEFORE_LOSS, check, compare_runs, probe_rows, read_runs, stretch_rows
from policies.engine import run_policy
from policies.fixed import Every
from tests.test_engine import RecordingClient


def test_a_dream_counts_in_the_stretch_of_its_session_and_the_stretches_add_up_to_the_run():
    run = run_policy(Every(50), "monthly", "startup_founder", RecordingClient())
    rows = stretch_rows(run, "whole")
    # 606 sessions; dreams after s50..s600. The dream of s250 reads s201-250 and belongs to s211-420.
    assert [(row["stretch"], row["sessions"], row["dreams"], row["sessions_read"]) for row in rows] == [
        ("s1-210", 210, 4, 200), ("s211-420", 210, 4, 200), ("s421-end", 186, 4, 200),
    ]
    assert [row["exams"] for row in rows] == [30, 30, 26]
    check(run, rows, probe_rows(run, "whole"))


def test_a_moved_count_stops_and_a_shift_past_the_noise_is_reported():
    before = read_runs(BEFORE_LOSS)
    key = ("academic_researcher", "every-5", "s1-210", "s1-210")
    # P5 §4.1: 529/593 (89.2 %). 505/593 is 85.2 %, 4.0 points away: past the noise of 2.8, within twice it.
    every_1 = ("academic_researcher", "every-1", "s1-210", "s1-210")
    after = {key: {**before[key], "official": "505"}, every_1: {**before[every_1], "dreams": "209"}}
    assert [(line["key"][1], line["moved"], line["verdict"]) for line in compare_runs(before, after)] == [
        ("every-1", ["dreams"], "stop"), ("every-5", [], "report"),
    ]
