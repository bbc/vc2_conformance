import pytest

from io import BytesIO

from copy import deepcopy

from collections import defaultdict

from vc2_data_tables import (
    ParseCodes,
    BaseVideoFormats,
    BASE_VIDEO_FORMAT_PARAMETERS,
)

from vc2_conformance.pseudocode.state import State

from vc2_conformance.bitstream import (
    Serialiser,
    BitstreamWriter,
    vc2_default_values,
    Sequence,
    DataUnit,
    ParseInfo,
    SequenceHeader,
    SourceParameters,
    FrameSize,
    Padding,
    sequence_header,
)

from vc2_conformance.level_constraints import (
    LEVEL_SEQUENCE_RESTRICTIONS,
    LevelSequenceRestrictions,
)

from vc2_conformance.test_cases.decoder import (
    replace_sequence_headers,
    source_parameters_encodings,
    repeated_sequence_headers,
)

from sample_codec_features import MINIMAL_CODEC_FEATURES


def test_replace_sequence_headers():
    orig_seq = Sequence(
        data_units=[
            DataUnit(
                parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                sequence_header=SequenceHeader(
                    base_video_format=0, video_parameters=SourceParameters(),
                ),
            ),
            DataUnit(
                parse_info=ParseInfo(parse_code=ParseCodes.padding_data),
                padding=Padding(),
            ),
            DataUnit(
                parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                sequence_header=SequenceHeader(
                    base_video_format=0, video_parameters=SourceParameters(),
                ),
            ),
        ]
    )
    orig_seq_copy = deepcopy(orig_seq)

    new_sequence_header = SequenceHeader(
        base_video_format=100,
        video_parameters=SourceParameters(
            frame_size=FrameSize(custom_dimensions_flag=True),
        ),
    )
    new_seq = replace_sequence_headers(orig_seq, new_sequence_header)

    # Original not modified
    assert orig_seq == orig_seq_copy

    assert len(new_seq["data_units"]) == 3

    sh0 = new_seq["data_units"][0]["sequence_header"]
    sh2 = new_seq["data_units"][2]["sequence_header"]

    # Non-sequence header data unit should not have changed
    assert new_seq["data_units"][1] == orig_seq["data_units"][1]

    # Should have replaced sequence headers
    assert sh0 == new_sequence_header
    assert sh2 == new_sequence_header

    # ...with copies
    assert sh0 is not new_sequence_header
    assert sh2 is not new_sequence_header


def test_source_parameters_encodings():
    codec_features = MINIMAL_CODEC_FEATURES

    test_cases = list(source_parameters_encodings(codec_features))

    base_video_formats = set()
    flag_states = defaultdict(set)
    decoder_states_and_parameters = []

    for test_case in test_cases:
        for sequence in test_case.value["sequences"]:
            sh = sequence["data_units"][0]["sequence_header"]

            # Capture all base video formats
            base_video_formats.add(sh["base_video_format"])

            # Capture all flag values
            to_visit = [sh]
            while to_visit:
                d = to_visit.pop(0)
                for field, value in d.items():
                    if field.endswith("_flag"):
                        flag_states[field].add(value)
                    if isinstance(value, dict):
                        to_visit.append(value)

            # Capture actual resulting codec configuration
            state = State()
            with Serialiser(BitstreamWriter(BytesIO()), sh, vc2_default_values) as ser:
                video_parameters = sequence_header(ser, state)
            decoder_states_and_parameters.append((state, video_parameters))

    # Special cases: our MINIMAL_CODEC_FEATURES configuration overrides the
    # frame size, frame rate and clean area fields with tiny sizes and so these
    # options are always set to custom
    assert flag_states.pop("custom_dimensions_flag") == set([True])
    assert flag_states.pop("custom_clean_area_flag") == set([True])
    assert flag_states.pop("custom_frame_rate_flag") == set([True])

    # Expect all flag states to have been execercised
    assert all(value == set([True, False]) for value in flag_states.values())

    # Expect all base video formats with matching top-field-first setting to be
    # tried
    assert base_video_formats == set(
        base_video_format
        for base_video_format in BaseVideoFormats
        if (
            codec_features["video_parameters"]["top_field_first"]
            == BASE_VIDEO_FORMAT_PARAMETERS[base_video_format].top_field_first
        )
    )

    # Final decoder states must all be identical (i.e. encoded values must be
    # identical
    assert all(
        state_and_params == decoder_states_and_parameters[0]
        for state_and_params in decoder_states_and_parameters[1:]
    )


@pytest.yield_fixture
def level_sequence_restrictions():
    # Fixture which reverts any monkeypatches made to LEVEL_SEQUENCE_RESTRICTIONS
    old = deepcopy(LEVEL_SEQUENCE_RESTRICTIONS)
    try:
        yield LEVEL_SEQUENCE_RESTRICTIONS
    finally:
        LEVEL_SEQUENCE_RESTRICTIONS.clear()
        LEVEL_SEQUENCE_RESTRICTIONS.update(old)


@pytest.mark.parametrize("restricted_sequence", [True, False])
def test_repeated_sequence_headers(level_sequence_restrictions, restricted_sequence):
    if restricted_sequence:
        LEVEL_SEQUENCE_RESTRICTIONS[0] = LevelSequenceRestrictions(
            "", ".  high_quality_picture+ .",
        )

    codec_features = MINIMAL_CODEC_FEATURES

    stream = repeated_sequence_headers(codec_features)

    if not restricted_sequence:
        for sequence in stream["sequences"]:
            # All sequence headers must be identical
            sh_count = 0
            for data_unit in sequence["data_units"]:
                if data_unit["parse_info"]["parse_code"] == ParseCodes.sequence_header:
                    sh_count += 1

                    sh = data_unit["sequence_header"]
                    assert sh == sequence["data_units"][0]["sequence_header"]

            # Multiple sequence headers must be present
            assert sh_count >= 3
    else:
        assert stream is None
