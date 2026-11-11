import json

import pytest

from truth.changes import MEMORA_DATA, extract_changes, load_sessions, personas
from truth.evidence import content_snapshot_mismatches, persona_report


def session(period, persona, number):
    return json.loads((MEMORA_DATA / period / persona / "conversations" / f"session_{number:04d}.json").read_text())


def summary(changes):
    return [(change.action, change.domain, change.key, change.value, change.previous) for change in changes]


def test_value_update_replaces_the_liked_item():
    changes = extract_changes(session("weekly", "academic_researcher", 40))

    assert summary(changes) == [
        ("remove", "preference", ("movies", "actors", "Joan Crawford"), None, {"preference": "like"}),
        ("add", "preference", ("movies", "actors", "Grace Kelly"), {"preference": "like"}, None),
    ]


def test_genre_category_comes_from_the_persona_archetype():
    # "experimental" is both a movie genre and a music genre in Memora's metadata.
    [change] = extract_changes(session("monthly", "software_engineer", 196))

    assert change.key == ("music", "genres", "experimental")


def test_content_delete_reverts_budget_and_removes_one_element():
    changes = extract_changes(session("weekly", "academic_researcher", 85))

    assert summary(changes) == [
        ("update", "content", ("project_proposal_2", "budget"), {"value": 1100000}, {"value": 875000}),
        (
            "remove",
            "content",
            ("project_proposal_2", "objectives", "Design and implement a federated learning architecture compliant with regional healthcare data privacy regulations."),
            None,
            {"value": "Design and implement a federated learning architecture compliant with regional healthcare data privacy regulations."},
        ),
    ]


def test_rescheduled_event_keeps_memora_anchor_on_creation_date():
    # The user says "next Tuesday" (2025-06-10); Memora stores "+19 days" from created_at 2025-06-03.
    [change] = extract_changes(session("weekly", "academic_researcher", 150))

    assert (change.action, change.value["event_date"]) == ("update", "2025-06-22")


def test_failed_content_edit_changes_nothing():
    assert extract_changes(session("quarterly", "academic_researcher", 295)) == []


# Both are Memora defects: its forgetting evidence matches preferences by item name only, and these names
# are still current in another subcategory (Mediterranean as a climate, Vampire Weekend as already listened).
KNOWN_MEMORA_DEFECTS = {
    ("weekly", "sales_manager", "pref_travel_general_163"),
    ("quarterly", "creative_designer", "pref_music_general_1991"),
}


@pytest.mark.parametrize("period", ["weekly", "monthly", "quarterly"])
def test_extraction_reproduces_memora_evidence(period):
    for persona in personas(period):
        report = persona_report(period, persona)

        assert report["precondition_failures"] == []
        assert content_snapshot_mismatches(load_sessions(period, persona)) == []
        failing = {(period, persona, check.question_id) for check in report["checks"] if not check.matches}
        assert failing <= KNOWN_MEMORA_DEFECTS
