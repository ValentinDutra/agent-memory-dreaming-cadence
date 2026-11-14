from final.analysis import bootstrap, ratio


def test_one_persona_resampled_has_an_interval_of_width_zero_at_its_p5_accuracy():
    # P5 §4.1: every-5 on monthly/academic_researcher s1-210, repetition 0, 529/593 official and 529/585 without marked.
    # The same row twice stands for two repetitions with the same result: their average is that row.
    row = {"repetition": 0, "asked": 593, "official": 529, "reachable_asked": 585, "reachable_official": 529}
    persona = [row, {**row, "repetition": 1}]
    interval = bootstrap([ratio(persona, "official", "asked")] * 10)
    assert (round(100 * interval.mean, 1), round(100 * ratio(persona, "reachable_official", "reachable_asked"), 1)) == (89.2, 90.4)
    assert interval.high - interval.low == 0
