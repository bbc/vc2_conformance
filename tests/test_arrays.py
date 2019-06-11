import pytest

from vc2_conformance.arrays import (
    array,
    width,
    height,
    row,
    column,
)


class TestArray(object):
    
    def test_empty(self):
        assert array(0, 0) == []
    
    def test_singleton(self):
        assert array(1, 1) == [[None]]
    
    def test_2d(self):
        assert array(3, 4) == [
            [None, None, None],
            [None, None, None],
            [None, None, None],
            [None, None, None],
        ]
    
    def test_initial_value(self):
        assert array(2, 2, 123) == [
            [123, 123],
            [123, 123],
        ]


def test_width():
    assert width(array(0, 0)) == 0
    assert width(array(10, 20)) == 10


def test_height():
    assert height(array(0, 0)) == 0
    assert height(array(10, 20)) == 20


@pytest.fixture
def num_array():
    a = array(5, 3)
    for x in range(width(a)):
        for y in range(height(a)):
            a[y][x] = x + (y*10)
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
