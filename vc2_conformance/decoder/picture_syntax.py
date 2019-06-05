"""
:py:mod:`vc2_conformance.picture_syntax`: (12) Picture Syntax
=============================================================
"""

from vc2_conformance.metadata import ref_pseudocode

from vc2_conformance.decoder.io import (
    tell,
    read_uint_lit,
    read_uint,
    read_bool,
)

from vc2_conformance.tables import (
    PictureCodingModes,
)

from vc2_conformance.decoder.exceptions import (
    NonConsecutivePictureNumbers,
    EarliestFieldHasOddPictureNumber,
)


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
    this_picture_header_offset = tell(state)  ## Not in spec
    
    state["picture_number"] = read_uint_lit(state, 4)
    
    # (12.2) Picture numbers in a sequence must increment by 1 and wrap after
    # (2^32-1) back to zero
    ## Begin not in spec
    if "_last_picture_number" in state:
        expected_picture_number = (state["_last_picture_number"] + 1) & 0xFFFFFFFF
        if state["picture_number"] != expected_picture_number:
            raise NonConsecutivePictureNumbers(
                state["_last_picture_header_offset"],
                state["_last_picture_number"],
                this_picture_header_offset,
                state["picture_number"],
            )
    state["_last_picture_number"] = state["picture_number"]
    state["_last_picture_header_offset"] = this_picture_header_offset
    ## End not in spec
    
    # (12.2) When coded as fields, the first field in the stream must have an
    # even picture number.
    ## Begin not in spec
    if state["_picture_coding_mode"] == PictureCodingModes.pictures_are_fields:
        early_field = state["_num_pictures_in_sequence"] % 2 == 0
        even_number = state["picture_number"] % 2 == 0
        if early_field and not even_number:
            raise EarliestFieldHasOddPictureNumber(state["picture_number"])
    state["_num_pictures_in_sequence"] += 1
    ## End not in spec


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
    state["dwt_depth"] = read_uint(state)
    state["wavelet_index_ho"] = state["wavelet_index"]
    state["dwt_depth_ho"] = 0
    if (state["major_version"] >= 3):
        extended_transform_parameters(state)
    slice_parameters(state)
    quant_matrix(state)


@ref_pseudocode
def extended_transform_parameters(state):
    """(12.4.4.1)"""
    asym_transform_index_flag = read_bool(state)
    if (asym_transform_index_flag):
        state["wavelet_index_ho"] = read_uint(state)
    asym_transform_flag = read_bool(state)
    if (asym_transform_flag):
        state["dwt_depth_ho"] = read_uint(state)


@ref_pseudocode
def slice_parameters(state):
    """(12.4.5.2)"""
    state["slices_x"] = read_uint(state)
    state["slices_y"] = read_uint(state)
    if is_ld_picture(state) or is_ld_fragment(state):
        state["slice_bytes_numerator"] = read_uint(state)
        state["slice_bytes_denominator"] = read_uint(state)
    if is_hq_picture(state) or is_hq_fragment(state):
        state["slice_prefix_bytes"] = read_uint(state)
        state["slice_size_scaler"] = read_uint(state)


@ref_pseudocode
def quant_matrix(state):
    """(12.4.5.3)"""
    custom_quant_matrix = read_bool(state)
    if(custom_quant_matrix):
        if (state["dwt_depth_ho"] == 0):
            state["quant_matrix"][0]["LL"] = read_uint(state)
        else:
            state["quant_matrix"][0]["L"] = read_uint(state)
            for level in range(1, state["dwt_depth_ho"] + 1):
                state["quant_matrix"][level]["H"] = read_uint(state)
        for level in range(state["dwt_depth_ho"] + 1,
                           state["dwt_depth_ho"] + state["dwt_depth"] + 1):
            state["quant_matrix"][level]["HL"] = read_uint(state)
            state["quant_matrix"][level]["LH"] = read_uint(state)
            state["quant_matrix"][level]["HH"] = read_uint(state)
    else:
        set_quant_matrix(state)
