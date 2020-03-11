import pytest

import os

import sys

from io import BytesIO

from vc2_conformance.bitstream import autofill_and_serialise_sequence

from vc2_conformance.test_cases import DECODER_TEST_CASE_GENERATOR_REGISTRY

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
    "test_case",
    DECODER_TEST_CASE_GENERATOR_REGISTRY.generate_test_cases(
        MINIMAL_CODEC_FEATURES,
    ),
)
def test_all_decoder_test_cases(test_case):
    # Must produce a valid bitstream containing pictures with the correct
    # format
    
    def output_picture_callback(picture, video_parameters):
        assert video_parameters == MINIMAL_CODEC_FEATURES["video_parameters"]
    
    state = State(
        _output_picture_callback=output_picture_callback,
    )
    
    f = BytesIO()
    autofill_and_serialise_sequence(f, test_case.value)
    
    f.seek(0)
    init_io(state, f)
    parse_sequence(state)
