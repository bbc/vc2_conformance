"""
The :py:mod:`vc2_conformance.decoder.picture_syntax` module contains pseudocode
functions from (12) Picture syntax.
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_conformance.constraint_table import allowed_values_for

from vc2_conformance.pseudocode.slice_sizes import slices_have_same_dimensions

from vc2_conformance.pseudocode.parse_code_functions import is_ld, is_hq

from vc2_conformance.decoder.io import (
    tell,
    byte_align,
    read_uint_lit,
    read_uint,
    read_bool,
)

from vc2_data_tables import (
    WaveletFilters,
    QUANTISATION_MATRICES,
)

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.version_constraints import (
    wavelet_transform_version_implication,
)

from vc2_conformance.decoder.assertions import (
    assert_in,
    assert_in_enum,
    assert_level_constraint,
    assert_picture_number_incremented_as_expected,
    log_version_lower_bound,
)

from vc2_conformance.decoder.exceptions import (
    ZeroSlicesInCodedPicture,
    SliceBytesHasZeroDenominator,
    SliceBytesIsLessThanOne,
    NoQuantisationMatrixAvailable,
    BadWaveletIndex,
    BadHOWaveletIndex,
    QuantisationMatrixValueNotAllowedInLevel,
    SliceSizeScalerIsZero,
)

from vc2_conformance.decoder.transform_data_syntax import transform_data


__all__ = [
    "picture_parse",
    "picture_header",
    "wavelet_transform",
    "transform_parameters",
    "extended_transform_parameters",
    "slice_parameters",
    "quant_matrix",
]


@ref_pseudocode
def picture_parse(state):
    """(12.1)"""
    byte_align(state)
    picture_header(state)
    byte_align(state)
    wavelet_transform(state)


@ref_pseudocode
def picture_header(state):
    """(12.2)"""
    state["picture_number"] = read_uint_lit(state, 4)

    # (12.2) Checks that the picture incremented by one, wraps correctly and
    # fields have even-numbered picture numbers first.
    assert_picture_number_incremented_as_expected(state, tell(state))  ## Not in spec


@ref_pseudocode
def wavelet_transform(state):
    """(12.3)"""
    transform_parameters(state)
    byte_align(state)
    transform_data(state)


@ref_pseudocode
def transform_parameters(state):
    """(12.4.1)"""
    state["wavelet_index"] = read_uint(state)

    # (12.4.1) Check wavelet type is supported
    ## Begin not in spec
    assert_in_enum(state["wavelet_index"], WaveletFilters, BadWaveletIndex)
    ## End not in spec

    # (C.3) Check level allows this wavelet type
    ## Begin not in spec
    assert_level_constraint(state, "wavelet_index", state["wavelet_index"])
    ## End not in spec

    state["dwt_depth"] = read_uint(state)

    # (C.3) Check level allows this wavelet depth
    assert_level_constraint(state, "dwt_depth", state["dwt_depth"])  ## Not in spec

    state["wavelet_index_ho"] = state["wavelet_index"]
    state["dwt_depth_ho"] = 0

    if state["major_version"] >= 3:
        extended_transform_parameters(state)

    slice_parameters(state)

    quant_matrix(state)


@ref_pseudocode
def extended_transform_parameters(state):
    """(12.4.4.1)"""
    asym_transform_index_flag = read_bool(state)
    # (C.3) Check level allows an asymmetric transform types
    ## Begin not in spec
    assert_level_constraint(
        state, "asym_transform_index_flag", asym_transform_index_flag
    )
    ## End not in spec

    if asym_transform_index_flag:
        state["wavelet_index_ho"] = read_uint(state)

        # (12.4.4.2) Check wavelet type is supported
        ## Begin not in spec
        assert_in_enum(state["wavelet_index_ho"], WaveletFilters, BadHOWaveletIndex)
        ## End not in spec

        # (C.3) Check level allows this wavelet type
        ## Begin not in spec
        assert_level_constraint(state, "wavelet_index_ho", state["wavelet_index_ho"])
        ## End not in spec

    asym_transform_flag = read_bool(state)
    # (C.3) Check level allows an asymmetric transform depths
    ## Begin not in spec
    assert_level_constraint(state, "asym_transform_flag", asym_transform_flag)
    ## End not in spec

    if asym_transform_flag:
        state["dwt_depth_ho"] = read_uint(state)

        # (C.3) Check level allows this wavelet depth
        ## Begin not in spec
        assert_level_constraint(state, "dwt_depth_ho", state["dwt_depth_ho"])
        ## End not in spec

    # (11.2.2) Log increased minimum version requirements if an asymmetric
    # transform was used.
    ## Begin not in spec
    minimum_required_version = wavelet_transform_version_implication(
        state["wavelet_index"],
        state["wavelet_index_ho"],
        state["dwt_depth_ho"],
    )
    log_version_lower_bound(state, minimum_required_version)
    ## End not in spec


@ref_pseudocode
def slice_parameters(state):
    """(12.4.5.2)"""
    state["slices_x"] = read_uint(state)
    # (C.3) Check level allows this number of horizontal slices
    assert_level_constraint(state, "slices_x", state["slices_x"])  ## Not in spec

    state["slices_y"] = read_uint(state)
    # (C.3) Check level allows this number of vertical slices
    assert_level_constraint(state, "slices_y", state["slices_y"])  ## Not in spec

    # Errata: Spec doesn't prevent zero-slice pictures
    #
    # (12.4.5.2) Must have at least once slice
    ## Begin not in spec
    if state["slices_x"] == 0 or state["slices_y"] == 0:
        raise ZeroSlicesInCodedPicture(state["slices_x"], state["slices_y"])
    ## End not in spec

    # (C.3) Check if this level expects slice counts which result in every
    # slice having the same number of transform components
    ## Begin not in spec
    assert_level_constraint(
        state, "slices_have_same_dimensions", slices_have_same_dimensions(state)
    )
    ## End not in spec

    if is_ld(state):
        state["slice_bytes_numerator"] = read_uint(state)
        # (C.3) Check level allows the specified numerator
        ## Begin not in spec
        assert_level_constraint(
            state, "slice_bytes_numerator", state["slice_bytes_numerator"]
        )
        ## End not in spec

        state["slice_bytes_denominator"] = read_uint(state)
        # (C.3) Check level allows the specified denominator
        ## Begin not in spec
        assert_level_constraint(
            state, "slice_bytes_denominator", state["slice_bytes_denominator"]
        )
        ## End not in spec

        # Errata: spec doesn't disallow a slice_bytes_denominator of zero
        #
        # (12.4.5.2) Must have non-zero slice_bytes denominator (i.e. no divide
        # by zero)
        ## Begin not in spec
        if state["slice_bytes_denominator"] == 0:
            raise SliceBytesHasZeroDenominator(state["slice_bytes_numerator"])
        ## End not in spec

        # Errata: spec doesn't disallow slice_bytes_* values which evaluate to
        # less than one byte.
        #
        # (12.4.5.2) slice_bytes_numerator/slice_bytes_denominator must be
        # greater than or equal to one byte to avoid zero-byte slices in the
        # bitstream.
        ## Begin not in spec
        if state["slice_bytes_numerator"] < state["slice_bytes_denominator"]:
            raise SliceBytesIsLessThanOne(
                state["slice_bytes_numerator"],
                state["slice_bytes_denominator"],
            )
        ## End not in spec

    if is_hq(state):
        state["slice_prefix_bytes"] = read_uint(state)
        # (C.3) Check level allows the specified prefix byte count
        ## Begin not in spec
        assert_level_constraint(
            state, "slice_prefix_bytes", state["slice_prefix_bytes"]
        )
        ## End not in spec

        state["slice_size_scaler"] = read_uint(state)

        # Errata: not enforced in spec
        #
        # (12.4.5.2) slice size scaler should not be zero
        ## Begin not in spec
        if state["slice_size_scaler"] == 0:
            raise SliceSizeScalerIsZero()
        ## End not in spec

        # (C.3) Check level allows the specified slice size scaler
        ## Begin not in spec
        assert_level_constraint(state, "slice_size_scaler", state["slice_size_scaler"])
        ## End not in spec


@ref_pseudocode
def quant_matrix(state):
    """(12.4.5.3)"""
    custom_quant_matrix = read_bool(state)
    # (C.3) Check level allows use of custom quantisation matrices
    ## Begin not in spec
    assert_level_constraint(state, "custom_quant_matrix", custom_quant_matrix)
    ## End not in spec

    if custom_quant_matrix:
        # (C.3) Check that quantisation matrix values are in the level-defined
        # range
        ## Begin not in spec
        allowed_values = allowed_values_for(
            LEVEL_CONSTRAINTS,
            "quant_matrix_values",
            state["_level_constrained_values"],
        )

        def check(quant_matrix_value):
            assert_in(
                quant_matrix_value,
                allowed_values,
                QuantisationMatrixValueNotAllowedInLevel,
                state["_level_constrained_values"],
            )

        ## End not in spec

        # NB: For historical reasons, we use a dict not an array in this
        # implementation.
        ### state["quant_matrix"] = new_array(state["dwt_depth_ho"] + state["dwt_depth"] + 1)
        state["quant_matrix"] = {}  ## Not in spec
        if state["dwt_depth_ho"] == 0:
            state["quant_matrix"][0] = {}
            state["quant_matrix"][0]["LL"] = read_uint(state)
            check(state["quant_matrix"][0]["LL"])  ## Not in spec
        else:
            state["quant_matrix"][0] = {}
            state["quant_matrix"][0]["L"] = read_uint(state)
            check(state["quant_matrix"][0]["L"])  ## Not in spec
            for level in range(1, state["dwt_depth_ho"] + 1):
                state["quant_matrix"][level] = {}
                state["quant_matrix"][level]["H"] = read_uint(state)
                check(state["quant_matrix"][level]["H"])  ## Not in spec
        for level in range(
            state["dwt_depth_ho"] + 1, state["dwt_depth_ho"] + state["dwt_depth"] + 1
        ):
            state["quant_matrix"][level] = {}
            state["quant_matrix"][level]["HL"] = read_uint(state)
            check(state["quant_matrix"][level]["HL"])  ## Not in spec
            state["quant_matrix"][level]["LH"] = read_uint(state)
            check(state["quant_matrix"][level]["LH"])  ## Not in spec
            state["quant_matrix"][level]["HH"] = read_uint(state)
            check(state["quant_matrix"][level]["HH"])  ## Not in spec
    else:
        # (12.4.5.3) If no custom quantisation matrix has been specified, a
        # default table must be available
        ## Begin not in spec
        configuration = (
            state["wavelet_index"],
            state["wavelet_index_ho"],
            state["dwt_depth"],
            state["dwt_depth_ho"],
        )
        if configuration not in QUANTISATION_MATRICES:
            raise NoQuantisationMatrixAvailable(*configuration)
        ## End not in spec

        set_quant_matrix(state)


@ref_pseudocode(deviation="inferred_implementation")
def set_quant_matrix(state):
    """(12.4.5.3)"""
    state["quant_matrix"] = QUANTISATION_MATRICES[
        (
            state["wavelet_index"],
            state["wavelet_index_ho"],
            state["dwt_depth"],
            state["dwt_depth_ho"],
        )
    ]
