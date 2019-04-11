"""
Parse code classification functions defined by VC-2 in (Table 10.2).

These functions all take a 'state' dictionary containing at least
``parse_code`` which should be an int or :py:class:`ParseCodes` enum value.
"""

__all__ = [
    "is_seq_header",
    "is_end_of_sequence",
    "is_auxiliary_data",
    "is_padding_data",
    "is_picture",
    "is_ld_picture",
    "is_hq_picture",
    "is_fragment",
    "is_ld_fragment",
    "is_hq_fragment",
    "using_dc_prediction",
]

is_seq_header       = lambda state: bool(state["parse_code"] == 0x00)
is_end_of_sequence  = lambda state: bool(state["parse_code"] == 0x10)
is_auxiliary_data   = lambda state: bool((state["parse_code"] & 0xF8) == 0x20)
is_padding_data     = lambda state: bool(state["parse_code"] == 0x30)

# Errata: the is_*_picture functions in the spec also return True for
# fragments. (The implementation below only returns True for pictures).
is_picture          = lambda state: bool((state["parse_code"] & 0x8C) == 0x88)
is_ld_picture       = lambda state: bool((state["parse_code"] & 0xFC) == 0xC8)
is_hq_picture       = lambda state: bool((state["parse_code"] & 0xFC) == 0xE8)

is_fragment         = lambda state: bool((state["parse_code"] & 0x0C) == 0x0C)
is_ld_fragment      = lambda state: bool((state["parse_code"] & 0xFC) == 0xCC)
is_hq_fragment      = lambda state: bool((state["parse_code"] & 0xFC) == 0xEC)

using_dc_prediction = lambda state: bool((state["parse_code"] & 0x28) == 0x08)
