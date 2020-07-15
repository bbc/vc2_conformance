"""
Parse code classification functions (Table 10.2)

These functions all take a 'state' dictionary containing at least
``parse_code`` which should be an int or :py:class:`ParseCodes` enum value.
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

__all__ = [
    "is_seq_header",
    "is_end_of_sequence",
    "is_auxiliary_data",
    "is_padding_data",
    "is_ld",
    "is_hq",
    "is_picture",
    "is_fragment",
    "using_dc_prediction",
]


@ref_pseudocode
def is_seq_header(state):
    """(Table 10.2)"""
    return state["parse_code"] == 0x00


@ref_pseudocode
def is_end_of_sequence(state):
    """(Table 10.2)"""
    return state["parse_code"] == 0x10


@ref_pseudocode
def is_auxiliary_data(state):
    """(Table 10.2)"""
    return (state["parse_code"] & 0xF8) == 0x20


@ref_pseudocode
def is_padding_data(state):
    """(Table 10.2)"""
    return state["parse_code"] == 0x30


def is_ld(state):
    """(Table 10.2)"""
    return (state["parse_code"] & 0xF8) == 0xC8


def is_hq(state):
    """(Table 10.2)"""
    return (state["parse_code"] & 0xF8) == 0xE8


@ref_pseudocode
def is_picture(state):
    """(Table 10.2)"""
    return (state["parse_code"] & 0x8C) == 0x88


@ref_pseudocode
def is_fragment(state):
    """(Table 10.2)"""
    return (state["parse_code"] & 0x0C) == 0x0C


@ref_pseudocode
def using_dc_prediction(state):
    """(Table 10.2)"""
    return (state["parse_code"] & 0x28) == 0x08
