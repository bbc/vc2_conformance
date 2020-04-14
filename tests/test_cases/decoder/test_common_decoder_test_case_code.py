import pytest

from vc2_data_tables import ParseCodes

from io import BytesIO

from vc2_conformance.state import State

from vc2_conformance.bitstream import (
    Deserialiser,
    BitstreamReader,
    parse_sequence,
)

from vc2_conformance.test_cases.decoder.common import make_dummy_end_of_sequence


def test_make_dummy_end_of_sequence():
    # Should deserialise correctly
    f = BytesIO(make_dummy_end_of_sequence())
    with Deserialiser(BitstreamReader(f)) as des:
        parse_sequence(des, State())

    assert len(des.context["data_units"]) == 1
    assert (
        des.context["data_units"][0]["parse_info"]["parse_code"]
        == ParseCodes.end_of_sequence
    )
