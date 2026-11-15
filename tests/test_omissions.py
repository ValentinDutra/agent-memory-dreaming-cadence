from dreaming.transcripts import load_transcripts
from final.omissions import follow_up


def test_what_follows_a_fact_splits_the_dream_from_memora():
    # The three costliest omissions of P7 and a plain to-do (docs/p8a-omisiones.md §3.2).
    content_writer = {session.session_id: session for session in load_transcripts("monthly", "content_writer")}
    marketing_manager = {session.session_id: session for session in load_transcripts("monthly", "marketing_manager")}
    assert follow_up(content_writer[15], "23.05") == "taken back"           # "Oh, I was actually just making a general comment."
    assert follow_up(content_writer[29], "Call family") == "said done"      # "How was the conversation?" "It went well"
    assert follow_up(marketing_manager[1], "20.27") == "other weekday"      # "a Tuesday night" on Sunday 2025-06-01
    assert follow_up(content_writer[100], "Plan literary event attendance") == "plain"
