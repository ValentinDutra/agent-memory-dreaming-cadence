import pytest

from truth.changes import Change, persona_changes
from truth.timeline import build_timeline, evidence_check, state_after, text_support

LIKE = {"preference": "like"}
DISLIKE = {"preference": "dislike"}

# weekly/academic_researcher, sessions 5, 40, 50 and 88: the favorite actor changes twice, then turns into a dislike.
ACTORS = [
    Change(5, "2025-06-01", "add", "preference", ("actors", "Joan Crawford"), LIKE),
    Change(40, "2025-06-02", "remove", "preference", ("actors", "Joan Crawford"), None, LIKE),
    Change(40, "2025-06-02", "add", "preference", ("actors", "Grace Kelly"), LIKE),
    Change(50, "2025-06-03", "remove", "preference", ("actors", "Grace Kelly"), None, LIKE),
    Change(50, "2025-06-03", "add", "preference", ("actors", "Rita Hayworth"), LIKE),
    Change(88, "2025-06-04", "update", "preference", ("actors", "Rita Hayworth"), DISLIKE, LIKE),
]


def test_state_after_includes_the_changes_of_that_session():
    assert state_after(ACTORS, 39) == {("preference", ("actors", "Joan Crawford")): LIKE}
    assert state_after(ACTORS, 40) == {("preference", ("actors", "Grace Kelly")): LIKE}
    assert state_after(ACTORS, 88) == {("preference", ("actors", "Rita Hayworth")): DISLIKE}


def test_changed_between_reports_the_net_change_only():
    changed = build_timeline(ACTORS).changed_between(39, 50)

    assert changed == {
        ("preference", ("actors", "Joan Crawford")): (LIKE, None),
        ("preference", ("actors", "Rita Hayworth")): (None, LIKE),
    }


def test_failed_preconditions_are_reported_and_the_newest_statement_wins():
    changes = [
        Change(1, "2025-06-01", "remove", "preference", ("actors", "Joan Crawford"), None, LIKE),
        Change(2, "2025-06-01", "update", "preference", ("actors", "Grace Kelly"), LIKE, DISLIKE),
        Change(3, "2025-06-01", "update", "preference", ("actors", "Grace Kelly"), DISLIKE, DISLIKE),
        Change(4, "2025-06-01", "add", "preference", ("actors", "Grace Kelly"), LIKE),
    ]

    timeline = build_timeline(changes)

    assert [(item.kind, item.change.session_id) for item in timeline.inconsistencies] == [
        ("remove_missing", 1),
        ("update_missing", 2),
        ("previous_mismatch", 3),
        ("add_existing", 4),
    ]
    assert timeline.state_after(4) == {("preference", ("actors", "Grace Kelly")): LIKE}


@pytest.mark.parametrize(
    "mention, text, expected",
    [
        # weekly/software_engineer session 33, turn 10
        ("Buy groceries", "I actually finished buying groceries, so you can remove that from my to-do list.", "full"),
        # weekly/content_writer session 124, turn 16
        ("1980s", "I actually used to love 80s music, but now I don't really enjoy it anymore.", "full"),
        # weekly/marketing_manager session 86, turn 9: the replaced artist is never named
        ("Taylor Swift", "My music taste has definitely shifted, and I'm really into SZA these days.", "absent"),
    ],
)
def test_text_support_tolerates_paraphrase_but_not_omission(mention, text, expected):
    assert text_support(mention, text) == expected


def test_truth_reproduces_memora_evidence_for_preferences_and_todos():
    timeline = build_timeline(persona_changes("weekly", "software_engineer"))

    outcomes = {
        outcome
        for (family, _, outcome), _ in evidence_check("weekly", "software_engineer", timeline).items()
        if family.startswith(("pref_", "activity_todos"))
    }

    assert outcomes <= {"in_truth", "in_truth_since_earlier_version", "removed"}
