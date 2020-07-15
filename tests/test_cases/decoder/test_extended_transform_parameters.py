import pytest

from copy import deepcopy

from vc2_data_tables import Profiles, WaveletFilters

from vc2_conformance.codec_features import CodecFeatures

from vc2_conformance.bitstream import ExtendedTransformParameters

from vc2_conformance.constraint_table import ValueSet

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.test_cases.decoder.extended_transform_parameters import (
    extended_transform_parameters,
)

from sample_codec_features import MINIMAL_CODEC_FEATURES


def test_version_2():
    # Should never produce output for version 2
    codec_features = CodecFeatures(MINIMAL_CODEC_FEATURES, major_version=2)
    assert len(list(extended_transform_parameters(codec_features))) == 0


def find_extended_transform_parameters(stream):
    """Return all of the ExtendedTransformParameters objects in a stream."""
    etps = []
    to_visit = [
        data_unit for seq in stream["sequences"] for data_unit in seq["data_units"]
    ]
    while to_visit:
        d = to_visit.pop(0)
        if isinstance(d, ExtendedTransformParameters):
            etps.append(d)
        elif isinstance(d, dict):
            to_visit.extend(d.values())
    return etps


@pytest.mark.parametrize("profile", Profiles)
@pytest.mark.parametrize("fragment_slice_count", [0, 1])
@pytest.mark.parametrize(
    "wavelet_index_ho,exp_asym_transform_index_flag_case",
    [(WaveletFilters.haar_no_shift, True), (WaveletFilters.haar_with_shift, False)],
)
@pytest.mark.parametrize(
    "dwt_depth_ho,exp_asym_transform_flag_case", [(0, True), (1, False)],
)
def test_forces_flags(
    profile,
    fragment_slice_count,
    wavelet_index_ho,
    exp_asym_transform_index_flag_case,
    dwt_depth_ho,
    exp_asym_transform_flag_case,
):
    codec_features = CodecFeatures(
        MINIMAL_CODEC_FEATURES,
        major_version=3,
        profile=profile,
        fragment_slice_count=fragment_slice_count,
        wavelet_index=WaveletFilters.haar_no_shift,
        wavelet_index_ho=wavelet_index_ho,
        dwt_depth=2,
        dwt_depth_ho=dwt_depth_ho,
        quantization_matrix=(
            {
                0: {"LL": 0},
                1: {"LH": 0, "HL": 0, "HH": 0},
                2: {"LH": 0, "HL": 0, "HH": 0},
            }
            if dwt_depth_ho == 0
            else {
                0: {"L": 0},
                1: {"H": 0},
                2: {"LH": 0, "HL": 0, "HH": 0},
                3: {"LH": 0, "HL": 0, "HH": 0},
            }
        ),
    )
    test_cases = list(extended_transform_parameters(codec_features))

    exp_cases = 0
    if exp_asym_transform_index_flag_case:
        exp_cases += 1
    if exp_asym_transform_flag_case:
        exp_cases += 1
    assert len(test_cases) == exp_cases

    # Check that the extra flags are set (when expected)
    for test_case in test_cases:
        etps = find_extended_transform_parameters(test_case.value)

        if test_case.subcase_name == "asym_transform_index_flag":
            assert exp_asym_transform_index_flag_case
            assert etps
            for etp in etps:
                assert etp["asym_transform_index_flag"]
                assert etp["wavelet_index_ho"] == wavelet_index_ho
        elif test_case.subcase_name == "asym_transform_flag":
            assert exp_asym_transform_flag_case
            assert etps
            for etp in etps:
                assert etp["asym_transform_flag"]
                assert etp["dwt_depth_ho"] == dwt_depth_ho
        else:
            assert False


@pytest.yield_fixture
def level_constraints():
    # Revert modifications made to LEVEL_CONSTRAINTS in this test
    old = deepcopy(LEVEL_CONSTRAINTS)
    try:
        yield LEVEL_CONSTRAINTS
    finally:
        del LEVEL_CONSTRAINTS[:]
        LEVEL_CONSTRAINTS.extend(old)


@pytest.mark.parametrize(
    "level_overrides,exp_asym_transform_index_flag_case,exp_asym_transform_flag_case",
    [
        ({"asym_transform_index_flag": ValueSet(False)}, False, True),
        ({"asym_transform_flag": ValueSet(False)}, True, False),
    ],
)
def test_level_overrides_obeyed(
    level_constraints,
    level_overrides,
    exp_asym_transform_index_flag_case,
    exp_asym_transform_flag_case,
):
    assert level_constraints[0]["level"] == ValueSet(0)
    level_constraints[0].update(level_overrides)

    codec_features = CodecFeatures(
        MINIMAL_CODEC_FEATURES,
        major_version=3,
        wavelet_index=WaveletFilters.haar_no_shift,
        wavelet_index_ho=WaveletFilters.haar_no_shift,
        dwt_depth=1,
        dwt_depth_ho=0,
    )
    test_cases = list(extended_transform_parameters(codec_features))

    exp_cases = 0
    if exp_asym_transform_index_flag_case:
        exp_cases += 1
    if exp_asym_transform_flag_case:
        exp_cases += 1
    assert len(test_cases) == exp_cases

    # Check that the extra flags are set (when expected) but not when the level
    # prohibits it
    for test_case in test_cases:
        etps = find_extended_transform_parameters(test_case.value)

        if test_case.subcase_name == "asym_transform_index_flag":
            assert exp_asym_transform_index_flag_case
            assert etps
            for etp in etps:
                assert etp["asym_transform_index_flag"]
                assert etp["wavelet_index_ho"] == WaveletFilters.haar_no_shift
        elif test_case.subcase_name == "asym_transform_flag":
            assert exp_asym_transform_flag_case
            assert etps
            for etp in etps:
                assert etp["asym_transform_flag"]
                assert etp["dwt_depth_ho"] == 0
        else:
            assert False
