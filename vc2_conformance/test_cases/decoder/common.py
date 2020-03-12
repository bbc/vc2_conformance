"""
Shared utilities used by several test case generators.
"""

from io import BytesIO

from vc2_data_tables import (
    ParseCodes,
    PARSE_INFO_HEADER_BYTES,
)

from vc2_conformance.state import State

from vc2_conformance.bitstream import (
    Serialiser,
    BitstreamWriter,
    ParseInfo,
    parse_info,
    vc2_default_values,
)


def make_dummy_end_of_sequence(previous_parse_offset=PARSE_INFO_HEADER_BYTES):
    """
    Make (and serialise) an end-of-sequence data unit to be placed within a
    padding data unit.
    """
    f = BytesIO()
    state = State()
    context = ParseInfo(
        parse_code=ParseCodes.end_of_sequence,
        next_parse_offset=0,
        previous_parse_offset=previous_parse_offset,
    )
    with Serialiser(BitstreamWriter(f), context, vc2_default_values) as ser:
        parse_info(ser, state)

    return f.getvalue()
