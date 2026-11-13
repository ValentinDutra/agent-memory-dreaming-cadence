from answering.client import Completion
from dreaming.transcripts import load_transcripts, transcript
from policies.triggered import ModelDetector, PhraseDetector, Triggered
from test_transcripts import ANSWER_KEY_FIELDS, memora_session, with_answer_key_replaced


class RecordingClient:
    """Stands in for BudgetedClient: keeps every request and never calls the API."""

    def __init__(self, reply="nothing\nVerdict: none"):
        self.reply = reply
        self.requests = []

    def complete(self, run, system, user, max_tokens, repeat=0):
        self.requests.append((run, system + user))
        return Completion(self.reply, 0, 0, 0.0001, True, "", {"type": "disabled"}, "low", "fake")


def test_the_detector_never_sees_the_answer_key():
    # s30 deletes Bonobo; its turn 14 shares a fact the answer key does not record (P1 defect 2).
    real = memora_session(30)
    for with_notes in (False, True):
        client = RecordingClient()
        detector = ModelDetector(client, with_notes)
        detector.detect("## Likes and dislikes\n- Bonobo (music / artists): like", transcript(real), run="test")
        detector.detect("## Likes and dislikes\n- Bonobo (music / artists): like", transcript(with_answer_key_replaced(real)), run="test")
        prompts = [prompt for _, prompt in client.requests]
        assert prompts[0] == prompts[1]
        assert not any(field in prompts[0] for field in ANSWER_KEY_FIELDS)
        assert "I used to really like Bonobo" in prompts[0]


def test_the_phrases_on_real_sessions():
    sessions = {session.session_id: session for session in load_transcripts("monthly", "academic_researcher")}
    detector = PhraseDetector()
    assert detector.detect("", sessions[4], "").verdict == "none"     # small talk only (no_memory)
    assert detector.detect("", sessions[2], "").verdict == "new"      # "$5.16 on coffee", buried in small talk
    assert detector.detect("", sessions[29], "").verdict == "change"  # "I just finished coordinating with the research team"


def test_the_policy_dreams_on_its_target_or_after_waiting_and_shares_the_detector_cache():
    session = load_transcripts("weekly", "software_engineer")[0]
    client = RecordingClient("Verdict: new")
    detector = ModelDetector(client, with_notes=False)
    policy = Triggered(detector, "change", max_wait=3)
    assert policy.name == "triggered-model-change-wait3"
    run = f"p5/r0/decide/{policy.name}/weekly/software_engineer"
    assert not policy.decide("", [session], client, run).dream
    assert policy.decide("", [session] * 3, client, run).dream
    assert Triggered(detector, "any").decide("", [session], client, "p5/r0/decide/triggered-model-any/weekly/software_engineer").dream
    assert {request_run for request_run, _ in client.requests} == {"p5/r0/decide/model/weekly/software_engineer"}
