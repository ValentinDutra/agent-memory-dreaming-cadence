from collections import Counter

from diagnosis.growth import standardized


def test_more_totals_at_the_same_rate_is_mix_not_rate():
    # Every cell keeps its rate and only the number of questions per cell changes: the observed rate triples,
    # the rate on the first stretch's mix must not move, and the first stretch's rates must explain all of it.
    first = {("expense", "aggregate"): Counter(asked=10, invented=1), ("preference", "stable"): Counter(asked=30)}
    later = {("expense", "aggregate"): Counter(asked=30, invented=3), ("preference", "stable"): Counter(asked=10)}
    observed, same_mix, first_rates = standardized(first, later, "invented")
    assert (observed, same_mix, first_rates) == (3 / 40, 1 / 40, 3 / 40)
