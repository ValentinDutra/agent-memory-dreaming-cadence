from final.repetitions import sign_test, swapped_extreme


def test_nine_personas_of_ten_on_one_side_is_the_sign_test_and_the_swap_test_of_one_column():
    # docs/p7/tables.md: every-1 − triggered-phrases-any rose in 9 of the 10 personas from r0 to r1.
    values = [2.4, 0.7, 0.2, 1.7, 1.1, 1.7, 1.4, -0.3, 1.1, 1.0]
    assert sign_test(values) == (9, 1, 0, 11 / 1024, 22 / 1024)
    assert swapped_extreme({"every-1 − triggered-phrases-any": values}, 9) == 22 / 1024
