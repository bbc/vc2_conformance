import pytest

import os

import sys

from io import BytesIO

from copy import deepcopy

from collections import defaultdict

from vc2_data_tables import (
    ParseCodes,
    BaseVideoFormats,
    BASE_VIDEO_FORMAT_PARAMETERS,
)

from vc2_conformance.state import State

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

from vc2_conformance.test_cases.decoder import (
    replace_sequence_header_options,
    source_parameters_encodings,
)

# Add test root directory to path for sample_codec_features test utility module
sys.path.append(os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
))

from sample_codec_features import MINIMAL_CODEC_FEATURES


def test_replace_sequence_header_options():
    orig_seq = Sequence(data_units=[
        DataUnit(
            parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
            sequence_header=SequenceHeader(
                base_video_format=0,
                video_parameters=SourceParameters(),
            ),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=ParseCodes.padding_data),
            padding=Padding(),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
            sequence_header=SequenceHeader(
                base_video_format=0,
                video_parameters=SourceParameters(),
            ),
        ),
    ])
    orig_seq_copy = deepcopy(orig_seq)
    
    new_base_video_format = 100
    new_video_parameters = SourceParameters(
        frame_size=FrameSize(custom_dimensions_flag=True),
    )
    new_seq = replace_sequence_header_options(
        orig_seq,
        new_base_video_format,
        new_video_parameters,
    )
    
    # Original not modified
    assert orig_seq == orig_seq_copy
    
    assert len(new_seq["data_units"]) == 3
    
    sh0 = new_seq["data_units"][0]["sequence_header"]
    sh2 = new_seq["data_units"][2]["sequence_header"]
    
    # Non-sequence header data unit should not have changed
    assert new_seq["data_units"][1] == orig_seq["data_units"][1]
    
    # Should have replaced base video formats
    assert sh0["base_video_format"] == new_base_video_format
    assert sh2["base_video_format"] == new_base_video_format
    
    # Should have replaced source parameters with a copy
    assert sh0["video_parameters"] == new_video_parameters
    assert sh0["video_parameters"] is not new_video_parameters
    
    assert sh2["video_parameters"] == new_video_parameters
    assert sh2["video_parameters"] is not new_video_parameters


def test_source_parameters_encodings():
    codec_features = MINIMAL_CODEC_FEATURES
    
    all_sequences = list(source_parameters_encodings(codec_features))
    
    base_video_formats = set()
    flag_states = defaultdict(set)
    decoder_states_and_parameters = []
    
    for sequence in all_sequences:
        sh = sequence.value["data_units"][0]["sequence_header"]
        
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
            codec_features["video_parameters"]["top_field_first"] ==
            BASE_VIDEO_FORMAT_PARAMETERS[base_video_format].top_field_first
        )
    )
    
    # Final decoder states must all be identical (i.e. encoded values must be
    # identical
    assert all(
        state_and_params == decoder_states_and_parameters[0]
        for state_and_params in decoder_states_and_parameters[1:]
    )