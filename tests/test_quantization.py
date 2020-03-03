import pytest

from vc2_conformance.quantization import (
    forward_quant,
    inverse_quant,
)


def test_forward_quant():
    # Test forward-quantisation produces sane results
    qi = 3 * 4   # Equiv to divide by 2**3 = 8
    
    for n in range(-100, 100):
        n_quant = inverse_quant(forward_quant(n, qi), qi)
        assert abs(n - n_quant) < 8
