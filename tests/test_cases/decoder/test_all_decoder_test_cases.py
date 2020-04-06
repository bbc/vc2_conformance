import pytest

import os

import sys

import json

from io import BytesIO

from vc2_data_tables import Profiles

from vc2_conformance.bitstream import autofill_and_serialise_sequence

from vc2_conformance.test_cases import DECODER_TEST_CASE_GENERATOR_REGISTRY

from vc2_conformance.codec_features import CodecFeatures

# Add test root directory to path for sample_codec_features test utility module
sys.path.append(os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
))

from sample_codec_features import MINIMAL_CODEC_FEATURES

from vc2_conformance.state import State

from vc2_conformance.decoder import (
    init_io,
    parse_sequence,
)


@pytest.mark.parametrize(
    "codec_features,test_case",
    (
        (codec_features, test_case)
        for codec_features in [
            # High quality
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                profile=Profiles.high_quality,
            ),
            # Low delay
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                profile=Profiles.low_delay,
            ),
            # Lossless coding
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                profile=Profiles.high_quality,
                lossless=True,
                picture_bytes=0,
            ),
            # Fragmented pictures
            CodecFeatures(
                MINIMAL_CODEC_FEATURES,
                profile=Profiles.high_quality,
                fragment_slice_count=2,
            ),
        ]
        for test_case in DECODER_TEST_CASE_GENERATOR_REGISTRY.generate_test_cases(
            codec_features)
    )
)
def test_all_decoder_test_cases(codec_features, test_case):
    # Every test case for every basic video mode must produce a valid bitstream
    # containing pictures with the correct format. Any JSON metadata must also
    # be seriallisable.
    
    # Mustn't crash!
    json.dumps(test_case.metadata)
    
    def output_picture_callback(picture, video_parameters):
        assert video_parameters == codec_features["video_parameters"]
    
    state = State(
        _output_picture_callback=output_picture_callback,
    )
    
    f = BytesIO()
    autofill_and_serialise_sequence(f, test_case.value)
    
    f.seek(0)
    init_io(state, f)
    parse_sequence(state)
