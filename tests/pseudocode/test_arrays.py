import pytest

from vc2_conformance.pseudocode.arrays import (
    new_array,
    width,
    height,
    row,
    column,
    delete_rows_after,
    delete_columns_after,
)


class TestArray(object):
    def test_1d(self):
        assert new_array(0) == []
        assert new_array(3) == [None, None, None]

    def test_2d_empty(self):
        assert new_array(0, 0) == []

    def test_2d_singleton(self):
        assert new_array(1, 1) == [[None]]

    def test_2d(self):
        assert new_array(4, 3) == [
            [None, None, None],
            [None, None, None],
            [None, None, None],
            [None, None, None],
        ]


def test_width():
    assert width(new_array(0, 0)) == 0
    assert width(new_array(20, 10)) == 10


def test_height():
    assert height(new_array(0, 0)) == 0
    assert height(new_array(20, 10)) == 20


@pytest.fixture
def num_array():
    a = new_array(3, 5)
    for x in range(width(a)):
        for y in range(height(a)):
            a[y][x] = x + (y * 10)
    return a


def test_row(num_array):
    # Get
    assert row(num_array, 0) == [0, 1, 2, 3, 4]
    assert row(num_array, 1) == [10, 11, 12, 13, 14]

    # Set
    row(num_array, 2)[1] = 999
    assert num_array[2][1] == 999


def test_coloumn(num_array):
    # Get
    assert len(column(num_array, 0)) == 3
    assert column(num_array, 0)[0] == 0
    assert column(num_array, 0)[1] == 10
    assert column(num_array, 0)[2] == 20

    assert len(column(num_array, 1)) == 3
    assert column(num_array, 1)[0] == 1
    assert column(num_array, 1)[1] == 11
    assert column(num_array, 1)[2] == 21

    # Set
    column(num_array, 2)[1] = 999
    assert num_array[1][2] == 999


def test_delete_rows_after(num_array):
    delete_rows_after(num_array, 2)
    assert num_array == [
        [0, 1, 2, 3, 4],
        [10, 11, 12, 13, 14],
    ]


def test_delete_columns_after(num_array):
    delete_columns_after(num_array, 2)
    assert num_array == [
        [0, 1],
        [10, 11],
        [20, 21],
    ]
