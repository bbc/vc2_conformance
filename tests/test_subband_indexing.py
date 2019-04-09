import pytest

from vc2_conformance.subband_indexing import (
    index_to_subband,
    subband_to_index,
)

def test_index_to_subband():
    # DC only
    assert index_to_subband(0, 0, 0) == (0, "DC")
    with pytest.raises(ValueError):
        index_to_subband(1, 0, 0)
    
    # 2D only
    assert index_to_subband(0, 2, 0) == (0, "LL")
    assert index_to_subband(1, 2, 0) == (1, "HL")
    assert index_to_subband(2, 2, 0) == (1, "LH")
    assert index_to_subband(3, 2, 0) == (1, "HH")
    assert index_to_subband(4, 2, 0) == (2, "HL")
    assert index_to_subband(5, 2, 0) == (2, "LH")
    assert index_to_subband(6, 2, 0) == (2, "HH")
    with pytest.raises(ValueError):
        index_to_subband(7, 2, 0)
    
    # Horizontal and 2D
    assert index_to_subband(0, 2, 3) == (0, "L")
    assert index_to_subband(1, 2, 3) == (1, "H")
    assert index_to_subband(2, 2, 3) == (2, "H")
    assert index_to_subband(3, 2, 3) == (3, "H")
    assert index_to_subband(4, 2, 3) == (4, "HL")
    assert index_to_subband(5, 2, 3) == (4, "LH")
    assert index_to_subband(6, 2, 3) == (4, "HH")
    assert index_to_subband(7, 2, 3) == (5, "HL")
    assert index_to_subband(8, 2, 3) == (5, "LH")
    assert index_to_subband(9, 2, 3) == (5, "HH")
    with pytest.raises(ValueError):
        index_to_subband(10, 2, 0)

def test_subband_to_index():
    # DC only
    assert index_to_subband(0, 0, 0) == (0, "DC")
    with pytest.raises(ValueError):
        index_to_subband(1, 0, 0)
    
    # 2D only
    assert index_to_subband(0, 2, 0) == (0, "LL")
    assert index_to_subband(1, 2, 0) == (1, "HL")
    assert index_to_subband(2, 2, 0) == (1, "LH")
    assert index_to_subband(3, 2, 0) == (1, "HH")
    assert index_to_subband(4, 2, 0) == (2, "HL")
    assert index_to_subband(5, 2, 0) == (2, "LH")
    assert index_to_subband(6, 2, 0) == (2, "HH")
    with pytest.raises(ValueError):
        index_to_subband(7, 2, 0)
    
    # Horizontal and 2D
    assert index_to_subband(0, 2, 3) == (0, "L")
    assert index_to_subband(1, 2, 3) == (1, "H")
    assert index_to_subband(2, 2, 3) == (2, "H")
    assert index_to_subband(3, 2, 3) == (3, "H")
    assert index_to_subband(4, 2, 3) == (4, "HL")
    assert index_to_subband(5, 2, 3) == (4, "LH")
    assert index_to_subband(6, 2, 3) == (4, "HH")
    assert index_to_subband(7, 2, 3) == (5, "HL")
    assert index_to_subband(8, 2, 3) == (5, "LH")
    assert index_to_subband(9, 2, 3) == (5, "HH")
    with pytest.raises(ValueError):
        index_to_subband(10, 2, 0)
