import pytest

from vc2_conformance import vc2_math


@pytest.mark.parametrize(
    "value,expectation",
    [
        # Example values from (5.5.3)
        (25, 5),
        (32, 5),
        # Other values
        (1, 0),
        (2, 1),
        (3, 2),
        (4, 2),
        (5, 3),
        (6, 3),
        (7, 3),
        (8, 3),
        (9, 4),
    ],
)
@pytest.mark.parametrize("implementation", [vc2_math.intlog2, vc2_math.intlog2_float])
def test_intlog2(implementation, value, expectation):
    out = implementation(value)
    assert out == expectation
    assert isinstance(out, int)


def test_intlog2_equal_to_intlog2_float():
    # Ensure the integer implementation produces identical results to the
    # as-described-in-spec float version.
    for n in range(1, 100000):
        assert vc2_math.intlog2(n) == vc2_math.intlog2_float(n)


@pytest.mark.parametrize(
    "value,expectation", [(-10, -1), (-1, -1), (0, 0), (1, 1), (10, 1)]
)
def test_sign(value, expectation):
    out = vc2_math.sign(value)
    assert out == expectation


@pytest.mark.parametrize(
    "value,expectation",
    [(9, 10), (10, 10), (11, 11), (12, 12), (13, 13), (14, 14), (15, 15), (16, 15)],
)
def test_clip(value, expectation):
    out = vc2_math.clip(value, 10, 15)
    assert out == expectation


@pytest.mark.parametrize(
    "values,expectation",
    [
        # Exactly divide
        ((15, 15), 15),
        ((10, 20), 15),
        ((20, 10), 15),
        ((10, 20, 30, 40), 25),
        # Rounding down
        ((10, 11, 13, 15), 12),  # Actually 12.25
        # Rounding up
        ((10, 11, 12, 13), 12),  # Actually 11.5
        ((10, 12, 14, 15), 13),  # Actually 12.75
    ],
)
def test_mean(values, expectation):
    out = vc2_math.mean(values)
    assert isinstance(out, int)
    assert out == expectation
