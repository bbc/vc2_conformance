"""
Shared utilities used by several test case generators.
"""

from io import BytesIO

from vc2_data_tables import (
    Profiles,
    ParseCodes,
    PARSE_INFO_HEADER_BYTES,
)

from vc2_conformance.pseudocode.state import State

from vc2_conformance.bitstream import (
    Serialiser,
    BitstreamWriter,
    ParseInfo,
    parse_info,
    vc2_default_values,
)


def make_dummy_end_of_sequence(previous_parse_offset=PARSE_INFO_HEADER_BYTES):
    """
    Make (and serialise) an end-of-sequence data unit to be placed within a
    padding data unit.
    """
    f = BytesIO()
    state = State()
    context = ParseInfo(
        parse_code=ParseCodes.end_of_sequence,
        next_parse_offset=0,
        previous_parse_offset=previous_parse_offset,
    )
    with Serialiser(BitstreamWriter(f), context, vc2_default_values) as ser:
        parse_info(ser, state)

    return f.getvalue()


def iter_transform_parameters_in_sequence(codec_features, sequence):
    """
    Iterate over all of the transform parameters in a sequence.

    Generates a series of
    :py:class:`~vc2_conformance.bitstream.TransformParameters` dicts, one for
    each picture present in the provided
    :py:class:`~vc2_conformance.bitstream.Sequence`.

    NB: This function assumes the stream is conformant.
    """
    for data_unit in sequence["data_units"]:
        # Get the TransformParameters for the current picture/fragment data
        # unit
        if "picture_parse" in data_unit:
            tp = data_unit["picture_parse"]["wavelet_transform"]["transform_parameters"]
            yield tp
        elif "fragment_parse" in data_unit:
            if "transform_parameters" in data_unit["fragment_parse"]:
                yield data_unit["fragment_parse"]["transform_parameters"]


def iter_slices_in_sequence(codec_features, sequence):
    """
    Iterate over all of the slices in a sequence.

    Generates a series of (:py:class:`~vc2_conformance.pseudocode.state.State`, sx, sy,
    :py:class:`~vc2_conformance.bitstream.LDSlice` or
    :py:class:`~vc2_conformance.bitstream.HQSlice`) tuples, one for each slice
    present in the provided :py:class:`~vc2_conformance.bitstream.Sequence`.
    The state dictionary will be populated as required by the two
    ``fill_*_slice_padding`` functions.

    NB: This function assumes the stream is conformant (i.e. has the correct
    number of slices, all fragments are present and in order etc).
    """
    sx = sy = 0

    state = None

    for data_unit in sequence["data_units"]:
        # Get the TransformData/FragmentData (td_or_fd) and SliceParameters
        # (sp) for the current picture/fragment data unit
        td_or_fd = None
        sp = None
        if "picture_parse" in data_unit:
            wt = data_unit["picture_parse"]["wavelet_transform"]
            td_or_fd = wt["transform_data"]
            sp = wt["transform_parameters"]["slice_parameters"]
        elif "fragment_parse" in data_unit:
            if "fragment_data" in data_unit["fragment_parse"]:
                td_or_fd = data_unit["fragment_parse"]["fragment_data"]
            if "transform_parameters" in data_unit["fragment_parse"]:
                sp = data_unit["fragment_parse"]["transform_parameters"][
                    "slice_parameters"
                ]

        # Got transform parameters
        if sp is not None:
            if codec_features["profile"] == Profiles.high_quality:
                state = State(
                    slice_prefix_bytes=sp["slice_prefix_bytes"],
                    slice_size_scaler=sp["slice_size_scaler"],
                    slices_x=sp["slices_x"],
                    slices_y=sp["slices_y"],
                )
            elif codec_features["profile"] == Profiles.low_delay:
                state = State(
                    slice_bytes_numerator=sp["slice_bytes_numerator"],
                    slice_bytes_denominator=sp["slice_bytes_denominator"],
                    slices_x=sp["slices_x"],
                    slices_y=sp["slices_y"],
                )

        # Got some slices
        if td_or_fd is not None:
            if codec_features["profile"] == Profiles.high_quality:
                slices = td_or_fd["hq_slices"]
            elif codec_features["profile"] == Profiles.low_delay:
                slices = td_or_fd["ld_slices"]

            for slice in slices:
                yield (state, sx, sy, slice)

                sx += 1
                if sx >= state["slices_x"]:
                    sx = 0

                    sy += 1
                    if sy >= state["slices_y"]:
                        sy = 0
