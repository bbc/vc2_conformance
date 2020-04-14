import pytest

from vc2_conformance.bitstream.exceptions import OutOfRangeError

from vc2_conformance.bitstream import exp_golomb


@pytest.mark.parametrize(
    "value,length",
    [
        # Low numbers
        (0, 1),
        (1, 3),
        (2, 3),
        (3, 5),
        (4, 5),
        (5, 5),
        (6, 5),
        (7, 7),
        (8, 7),
        # Very large numbers
        ((1 << 100) - 2, (99 * 2) + 1),
        ((1 << 100) - 1, (100 * 2) + 1),
    ],
)
def test_exp_golomb_length(value, length):
    assert exp_golomb.exp_golomb_length(value) == length


def test_exp_golomb_length_range_check():
    with pytest.raises(OutOfRangeError):
        exp_golomb.exp_golomb_length(-1)


@pytest.mark.parametrize(
    "value,length",
    [
        # Zero
        (0, 1),
        # Low numbers (+ve)
        (1, 4),
        (2, 4),
        (3, 6),
        (4, 6),
        (5, 6),
        (6, 6),
        (7, 8),
        (8, 8),
        # Low numbers (-ve)
        (-1, 4),
        (-2, 4),
        (-3, 6),
        (-4, 6),
        (-5, 6),
        (-6, 6),
        (-7, 8),
        (-8, 8),
        # Very large numbers
        ((1 << 100) - 2, (99 * 2) + 2),
        ((1 << 100) - 1, (100 * 2) + 2),
        (-((1 << 100) - 2), (99 * 2) + 2),
        (-((1 << 100) - 1), (100 * 2) + 2),
    ],
)
def test_signed_exp_golomb_length(value, length):
    assert exp_golomb.signed_exp_golomb_length(value) == length
