import pytest

import os

import sys

from io import BytesIO

from vc2_data_tables import (
    Profiles,
    Levels,
    ParseCodes,
    PictureCodingModes,
)

from vc2_conformance.encoder.sequence import make_sequence

from vc2_conformance.picture_generators import mid_gray

from vc2_conformance.bitstream import autofill_and_serialise_sequence

from vc2_conformance.level_constraints import (
    LEVEL_SEQUENCE_RESTRICTIONS,
    LevelSequenceRestrictions,
)

# Add parent directory to path for sample_codec_features test utility module
sys.path.append(os.path.join(
    os.path.dirname(__file__),
    "..",
))

from sample_codec_features import MINIMAL_CODEC_FEATURES

from vc2_conformance.state import State

from vc2_conformance.decoder import (
    init_io,
    parse_sequence,
)


def serialize_and_decode(sequence):
    # Serialise
    f = BytesIO()
    autofill_and_serialise_sequence(f, sequence)
    
    # Setup callback to capture decoded pictures
    decoded_pictures = []
    def output_picture_callback(picture, video_parameters):
        decoded_pictures.append(picture)
    
    # Feed to conformance checking decoder
    f.seek(0)
    state = State(_output_picture_callback=output_picture_callback)
    init_io(state, f)
    parse_sequence(state)
    
    return decoded_pictures


def test_make_empty_sequence():
    seq = make_sequence(MINIMAL_CODEC_FEATURES, [])
    assert serialize_and_decode(seq) == []


@pytest.mark.parametrize("profile,fragment_slice_count", [
    # High-quality pictures
    (Profiles.high_quality, 0),
    # Low-delay pictures and fragmented pictures
    (Profiles.low_delay, 0),
    # Fragmented pictures
    (Profiles.high_quality, 1),
])
def test_picture_types(profile, fragment_slice_count):
    codec_features = MINIMAL_CODEC_FEATURES.copy()
    codec_features["profile"] = profile
    codec_features["fragment_slice_count"] = fragment_slice_count
    
    pictures = list(mid_gray(
        codec_features["video_parameters"],
        codec_features["picture_coding_mode"],
    ))
    
    seq = make_sequence(codec_features, pictures)
    
    assert serialize_and_decode(seq) == pictures


@pytest.yield_fixture
def patch_unconstratined_level_sequence_restrictions():
    # For test purposes, modify the unconstrained level so that it requires an
    # example of every non-picture data unit type to be inserted and that
    # pictures and sequence headers are interleaved
    old_value = LEVEL_SEQUENCE_RESTRICTIONS.pop(Levels.unconstrained)
    
    new_value = LevelSequenceRestrictions(
        "Test constraint....",
        (
            "sequence_header auxiliary_data "
            "(sequence_header high_quality_picture)+ "
            "padding_data end_of_sequence"
        )
    )
    LEVEL_SEQUENCE_RESTRICTIONS[Levels.unconstrained] = new_value
    
    try:
        yield
    finally:
        LEVEL_SEQUENCE_RESTRICTIONS[Levels.unconstrained] = old_value


def test_level_sequence_restrictions_obeyed(patch_unconstratined_level_sequence_restrictions):
    # Ensure two pictures (2 fields == 1 frame)
    codec_features = MINIMAL_CODEC_FEATURES.copy()
    codec_features["picture_coding_mode"] = PictureCodingModes.pictures_are_fields
    
    pictures = list(mid_gray(
        codec_features["video_parameters"],
        codec_features["picture_coding_mode"],
    ))
    assert len(pictures) == 2
    
    seq = make_sequence(codec_features, pictures)
    
    assert [
        data_unit["parse_info"]["parse_code"]
        for data_unit in seq["data_units"]
    ] == [
        ParseCodes.sequence_header,
        ParseCodes.auxiliary_data,
        ParseCodes.sequence_header,
        ParseCodes.high_quality_picture,
        ParseCodes.sequence_header,
        ParseCodes.high_quality_picture,
        ParseCodes.padding_data,
        ParseCodes.end_of_sequence,
    ]
    
    # Sanity check
    assert serialize_and_decode(seq) == pictures
