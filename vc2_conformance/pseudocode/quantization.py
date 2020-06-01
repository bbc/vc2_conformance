"""
Quantization-related VC-2 pseudocode routines (13.3).
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_conformance.pseudocode.vc2_math import sign

__all__ = [
    "inverse_quant",
    "forward_quant",
    "quant_factor",
    "quant_offset",
]


@ref_pseudocode
def inverse_quant(quantized_coeff, quant_index):
    """(13.3.1)"""
    magnitude = abs(quantized_coeff)
    if magnitude != 0:
        magnitude *= quant_factor(quant_index)
        magnitude += quant_offset(quant_index)
        magnitude += 2
        magnitude //= 4
    return sign(quantized_coeff) * magnitude


@ref_pseudocode(deviation="inferred_implementation")
def forward_quant(coeff, quant_index):
    """(13.3.1) Based on the informative note 1."""
    magnitude = abs(coeff)
    if coeff >= 0:
        return (4 * magnitude) // quant_factor(quant_index)
    else:
        return -((4 * magnitude) // quant_factor(quant_index))


@ref_pseudocode
def quant_factor(index):
    """(13.3.2)"""
    base = 2 ** (index // 4)
    if (index % 4) == 0:
        return 4 * base
    elif (index % 4) == 1:
        return ((503829 * base) + 52958) // 105917
    elif (index % 4) == 2:
        return ((665857 * base) + 58854) // 117708
    elif (index % 4) == 3:
        return ((440253 * base) + 32722) // 65444


@ref_pseudocode
def quant_offset(index):
    """(13.3.2)"""
    if index == 0:
        offset = 1
    elif index == 1:
        offset = 2
    else:
        offset = (quant_factor(index) + 1) // 2
    return offset
