import pytest

from io import BytesIO

from vc2_data_tables import Profiles

from vc2_conformance.state import State

from vc2_conformance.bitstream import (
    autofill_and_serialise_stream,
    BitstreamReader,
    Deserialiser,
    parse_stream,
)

from vc2_conformance.test_cases.decoder.absent_next_parse_offset import (
    absent_next_parse_offset,
)

from sample_codec_features import MINIMAL_CODEC_FEATURES


@pytest.mark.parametrize("profile", Profiles)
@pytest.mark.parametrize("fragment_slice_count", [0, 1])
def test_next_parse_offset_is_zero(profile, fragment_slice_count):
    # Verify that the next parse offset really is zero after serialisation

    # Generate
    codec_features = dict(
        MINIMAL_CODEC_FEATURES,
        profile=profile,
        fragment_slice_count=fragment_slice_count,
    )
    stream = absent_next_parse_offset(codec_features)

    # Serialise
    f = BytesIO()
    autofill_and_serialise_stream(f, stream)

    # Deserialise
    f.seek(0)
    with Deserialiser(BitstreamReader(f)) as des:
        parse_stream(des, State())
    decoded_stream = des.context

    # Only the sequence header at the start should have a next_parse_offset
    # defined.
    next_parse_offset_is_zero = [
        data_unit["parse_info"]["next_parse_offset"] == 0
        for seq in decoded_stream["sequences"]
        for data_unit in seq["data_units"]
    ]
    assert not next_parse_offset_is_zero[0]
    assert all(next_parse_offset_is_zero[1:])
