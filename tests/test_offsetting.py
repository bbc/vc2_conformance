import pytest

from vc2_conformance.arrays import new_array

from vc2_conformance.offsetting import (
    offset_picture,
    remove_offset_picture,
)


def test_invertability():
    picture = {
        "Y": new_array(16, 8, 123),
        "C1": new_array(8, 4, 456),
        "C2": new_array(8, 4, 789),
    }
    state = {
        "luma_depth": 8,
        "color_diff_depth": 10,
    }
    
    remove_offset_picture(state, picture)
    assert picture["Y"][0][0] == 123 - 128
    assert picture["C1"][0][0] == 456 - 512
    assert picture["C2"][0][0] == 789 - 512
    
    offset_picture(state, picture)
    assert picture["Y"][0][0] == 123
    assert picture["C1"][0][0] == 456
    assert picture["C2"][0][0] == 789
