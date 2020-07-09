"""
The :py:mod:`vc2_conformance.decoder.fragment_syntax` module contains pseudocode
functions from (14) Fragment syntax.
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_conformance.pseudocode.parse_code_functions import using_dc_prediction

from vc2_conformance.decoder.io import (
    tell,
    read_uint_lit,
)

from vc2_conformance.decoder.exceptions import (
    FragmentedPictureRestarted,
    PictureNumberChangedMidFragmentedPicture,
    TooManySlicesInFragmentedPicture,
    FragmentSlicesNotContiguous,
)

from vc2_conformance.decoder.assertions import (
    assert_picture_number_incremented_as_expected,
)

from vc2_conformance.decoder.picture_syntax import transform_parameters

from vc2_conformance.decoder.transform_data_syntax import (
    initialize_wavelet_data,
    slice,
    dc_prediction,
)


__all__ = [
    "fragment_parse",
    "fragment_header",
    "initialize_fragment_state",
    "fragment_data",
]


@ref_pseudocode
def fragment_parse(state):
    """(14.1)"""
    fragment_header(state)
    if state["fragment_slice_count"] == 0:
        transform_parameters(state)
        initialize_fragment_state(state)
    else:
        fragment_data(state)


@ref_pseudocode
def fragment_header(state):
    """(14.2)"""
    fragment_offset = tell(state)  ## Not in spec

    state["picture_number"] = read_uint_lit(state, 4)
    picture_number_offset = tell(state)  ## Not in spec

    state["fragment_data_length"] = read_uint_lit(state, 2)
    state["fragment_slice_count"] = read_uint_lit(state, 2)

    ## Begin not in spec
    if state["fragment_slice_count"] == 0:
        # Errata: not fully defined in spec
        #
        # (14.2) Only the first fragment in a picture may have
        # fragment_slice_count==0 (and no sequence of fragments may be
        # incomplete)
        if state["_fragment_slices_remaining"] != 0:
            raise FragmentedPictureRestarted(
                state["_picture_initial_fragment_offset"],
                fragment_offset,
                state["fragment_slices_received"],
                state["_fragment_slices_remaining"],
            )

        # Errata: wrapping behaviour not constrained in spec
        #
        # (14.2) The picture number should be incremented by one, wrap correctly and
        # fields should have even-numbered picture numbers first.
        assert_picture_number_incremented_as_expected(state, picture_number_offset)

        state["_picture_initial_fragment_offset"] = fragment_offset
    else:
        # (14.2) Appart from when fragment_slice_count==0, the picture number
        # must not change
        if state["_last_picture_number"] != state["picture_number"]:
            raise PictureNumberChangedMidFragmentedPicture(
                state["_last_picture_number_offset"],
                state["_last_picture_number"],
                picture_number_offset,
                state["picture_number"],
            )

        # Errata: not specified in standard...
        #
        # (14.2) A fragmented picture must not contain any extra slices
        if state["fragment_slice_count"] > state["_fragment_slices_remaining"]:
            raise TooManySlicesInFragmentedPicture(
                state["_picture_initial_fragment_offset"],
                fragment_offset,
                state["fragment_slices_received"],
                state["_fragment_slices_remaining"],
                state["fragment_slice_count"],
            )
    ## End not in spec

    if state["fragment_slice_count"] != 0:
        state["fragment_x_offset"] = read_uint_lit(state, 2)
        state["fragment_y_offset"] = read_uint_lit(state, 2)

        # Errata: not specified in standard...
        #
        # (14.2) A fragmented picture must include all slices in raster-scan
        # order
        ## Begin not in spec
        expected_fragment_x_offset = (
            state["fragment_slices_received"] % state["slices_x"]
        )
        expected_fragment_y_offset = (
            state["fragment_slices_received"] // state["slices_x"]
        )
        if (
            state["fragment_x_offset"] != expected_fragment_x_offset
            or state["fragment_y_offset"] != expected_fragment_y_offset
        ):
            raise FragmentSlicesNotContiguous(
                state["_picture_initial_fragment_offset"],
                fragment_offset,
                state["fragment_x_offset"],
                state["fragment_y_offset"],
                expected_fragment_x_offset,
                expected_fragment_y_offset,
            )
        ## End not in spec


@ref_pseudocode
def initialize_fragment_state(state):
    """(14.3)"""
    state["y_transform"] = initialize_wavelet_data(state, "Y")
    state["c1_transform"] = initialize_wavelet_data(state, "C1")
    state["c2_transform"] = initialize_wavelet_data(state, "C2")
    state["fragment_slices_received"] = 0
    ## Begin not in spec
    state["_fragment_slices_remaining"] = state["slices_x"] * state["slices_y"]
    ## End not in spec
    state["fragmented_picture_done"] = False


@ref_pseudocode
def fragment_data(state):
    """(14.4)"""
    for s in range(state["fragment_slice_count"]):
        slice_x = (
            state["fragment_y_offset"] * state["slices_x"]
            + state["fragment_x_offset"]
            + s
        ) % state["slices_x"]
        slice_y = (
            state["fragment_y_offset"] * state["slices_x"]
            + state["fragment_x_offset"]
            + s
        ) // state["slices_x"]
        slice(state, slice_x, slice_y)
        state["fragment_slices_received"] += 1
        state["_fragment_slices_remaining"] -= 1  ## Not in spec
        if state["fragment_slices_received"] == state["slices_x"] * state["slices_y"]:
            state["fragmented_picture_done"] = True
            if using_dc_prediction(state):
                if state["dwt_depth_ho"] == 0:
                    dc_prediction(state["y_transform"][0]["LL"])
                    dc_prediction(state["c1_transform"][0]["LL"])
                    dc_prediction(state["c2_transform"][0]["LL"])
                else:
                    dc_prediction(state["y_transform"][0]["L"])
                    dc_prediction(state["c1_transform"][0]["L"])
                    dc_prediction(state["c2_transform"][0]["L"])
