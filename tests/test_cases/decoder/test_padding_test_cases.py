import pytest

import os

import sys

from copy import deepcopy

from vc2_data_tables import (
    ParseCodes,
    Profiles,
    Levels,
)

from io import BytesIO

from vc2_conformance.state import State

from vc2_conformance.bitstream import (
    Deserialiser,
    BitstreamReader,
    Sequence,
    DataUnit,
    ParseInfo,
    Padding,
    parse_sequence,
)

from vc2_conformance.test_cases.decoder.padding import (
    replace_padding_data,
    make_dummy_end_of_sequence,
    padding_data,
)

# Add test root directory to path for sample_codec_features test utility module
sys.path.append(os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
))

from sample_codec_features import MINIMAL_CODEC_FEATURES


def test_replace_padding_data():
    orig_seq = Sequence(data_units=[
        DataUnit(
            parse_info=ParseInfo(parse_code=ParseCodes.padding_data),
            padding=Padding(bytes=b"foo"),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=ParseCodes.padding_data),
            padding=Padding(bytes=b"bar"),
        ),
        DataUnit(
            parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence),
        ),
    ])
    
    orig_seq_copy = deepcopy(orig_seq)
    
    new_seq = replace_padding_data(orig_seq, b"baz")
    
    # Copy returned
    assert new_seq is not orig_seq
    assert orig_seq == orig_seq_copy
    
    # Data as expected
    assert new_seq["data_units"][0]["padding"]["bytes"] == b"baz"
    assert new_seq["data_units"][1]["padding"]["bytes"] == b"baz"
    assert new_seq["data_units"][2] == orig_seq["data_units"][2]


def test_make_dummy_end_of_sequence():
    # Should deserialise correctly
    f = BytesIO(make_dummy_end_of_sequence())
    with Deserialiser(BitstreamReader(f)) as des:
        parse_sequence(des, State())
    
    assert len(des.context["data_units"]) == 1
    assert des.context["data_units"][0]["parse_info"]["parse_code"] == ParseCodes.end_of_sequence


def test_padding_data():
    codec_features = MINIMAL_CODEC_FEATURES.copy()
    test_cases = list(padding_data(codec_features))
    
    # The minimal codec feature set should not include any restrictions which
    # prevent padding being included
    assert len(test_cases) == 4
    
    # Several padding data blocks should be included in every sequence
    for test_case in test_cases:
        assert sum(
            1
            for data_unit in test_case.value["data_units"]
            if data_unit["parse_info"]["parse_code"] == ParseCodes.padding_data
        ) > 1


def test_padding_data_disallowed():
    # Chose a level which disalows padding data and check we just return no
    # test cases (rather than crashing, or producing non-conformant test
    # cases...)
    codec_features = MINIMAL_CODEC_FEATURES.copy()
    codec_features["profile"] = Profiles.low_delay
    codec_features["level"] = Levels.hd_over_sd_sdi
    test_cases = list(padding_data(codec_features))
    assert len(test_cases) == 0
