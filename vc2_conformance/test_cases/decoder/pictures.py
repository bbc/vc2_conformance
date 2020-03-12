"""
Tests which verify that codecs correctly process pictures in a stream.
"""

from bitarray import bitarray

from vc2_data_tables import (
    Profiles,
    ParseCodes,
)

from vc2_conformance.slice_sizes import slice_bytes

from vc2_conformance.vc2_math import intlog2

from vc2_conformance.state import State

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.picture_generators import (
    moving_sprite,
    mid_gray,
    linear_ramps,
)

from vc2_conformance.encoder import (
    make_sequence,
)

from vc2_conformance.test_cases.decoder.common import (
    make_dummy_end_of_sequence,
)


def generate_filled_padding(
    padding_length_bits,
    filler=b"\x00",
    byte_align=0,
):
    """
    Generate a :py:class:`~bitarray.bitarray` ``padding_length_bits`` long
    containing repeated copies of ``filler``. If byte_align is non-zero, the
    generated bit array will have a sufficient number of 0s at the start to
    byte-align the first copy of ``filler`` assuming the padding starts at
    a bit address specified by ``byte_align``.
    
    Parameters
    ==========
    padding_length_bits : int
        Number of padding bits to generate.
    filler : bytes
        Filler bytes to be used.
    byte_align : int
        If given, byte-align the filler assuming that the padding starts from
        the provided bit-address.
    """
    byte_alignment_bits = (8 - (byte_align % 8)) % 8
    
    required_bytes = (padding_length_bits - byte_alignment_bits + 7) // 8
    filler_repeats = (required_bytes + len(filler) - 1) // len(filler)
    
    # Add repeated filler
    padding = bitarray()
    padding.frombytes(filler * filler_repeats)
    
    # Add byte-alignment bits
    if byte_alignment_bits:
        padding = bitarray("0" * byte_alignment_bits) + padding
    
    # Trim any excess
    return padding[:padding_length_bits]


def fill_hq_slice_padding(
    state,
    sx,
    sy,
    hq_slice,
    component,
    filler,
    byte_align=False,
    min_length=0,
):
    """
    Given a :py:class:`~vc2_conformance.bitstream.HQSlice`, mutate it in-place
    such that the slice size remains the same, (or becomes
    min_length*slice_size_scaler + 4 bytes, whichever is greater) but the
    specified component's bounded block padding data is set to repeated copies
    of ``filler``. All transform data will be forced to zeros.
    
    Parameters
    ==========
    state : :py:class:`~vc2_conformance.state.State`
        A state dictionary containing at least ``slice_size_scaler``.
    sx, sy : int
        The slice coordinates. (Not used but present for consistency with
        :py:func:`fill_ld_slice_padding`.
    hq_slice : :py:class:`~vc2_conformance.bitstream.HQSlice`
        The slice to modify.
    component : "Y", "C1" or "C2"
        The component to stuff with filler data.
    filler : bytes
        A byte string to use as filler. Will be repeated as many times as
        necessary to fill the available space.
    byte_align : bool
        If True, insert the filler bytes on a byte-aligned boundary.
    min_length : int
        The minimum total length field for the modified slice
    """
    assert len(filler) > 0
    
    # Force picture content to zeros
    for c in ["y_transform", "c1_transform", "c2_transform"]:
        for i in range(len(hq_slice[c])):
            hq_slice[c][i] = 0
    
    # Make the designated slice take up the full size
    total_length = (
        hq_slice["slice_y_length"] +
        hq_slice["slice_c1_length"] +
        hq_slice["slice_c2_length"]
    )
    
    total_length = max(min_length, total_length)
    
    hq_slice["slice_y_length"] = 0
    hq_slice["slice_c1_length"] = 0
    hq_slice["slice_c2_length"] = 0
    hq_slice["slice_{}_length".format(component.lower())] = total_length
    
    # Work out how many padding bits we have to fill
    total_bytes = total_length * state["slice_size_scaler"]
    total_bits = total_bytes * 8
    bits_used_by_zeros = len(hq_slice["{}_transform".format(component.lower())])
    padding_bits = total_bits - bits_used_by_zeros
    
    # Generate the padding
    if padding_bits > 0:
        padding = generate_filled_padding(
            padding_bits,
            filler,
            # NB: All blocks in a HQ slice are byte aligned so all we need to
            # compensate for is the zeroed transform coeffs themselves
            bits_used_by_zeros if byte_align else 0,
        )
    else:
        # Zero or -ve padding (i.e. there is no space for padding)
        padding = bitarray()
    
    hq_slice["{}_block_padding".format(component.lower())] = padding


def fill_ld_slice_padding(
    state,
    sx,
    sy,
    ld_slice,
    component,
    filler,
    byte_align=False,
):
    """
    Given a :py:class:`~vc2_conformance.bitstream.LDSlice`, mutate it in-place
    such that the slice size remains the same, but the
    specified component's bounded block padding data is set to repeated copies
    of ``filler``. All transform data will be forced to zeros.
    
    Parameters
    ==========
    state : :py:class:`~vc2_conformance.state.State`
        A state dictionary containing at least:
        
        * ``slices_x``
        * ``slices_y``
        * ``slice_bytes_numerator``
        * ``slice_bytes_denominator``
    sx, sy : int
        The slice coordinates
    ld_slice : :py:class:`~vc2_conformance.bitstream.LDSlice`
        The slice to modify.
    component : "Y", "C"
        The component to stuff with filler data.
    filler : bytes
        A byte string to use as filler. Will be repeated as many times as
        necessary to fill the available space.
    byte_align : bool
        If True, insert the filler bytes on a byte-aligned boundary.
    """
    assert len(filler) > 0
    
    # Force picture content to zeros
    for c in ["y_transform", "c_transform"]:
        for i in range(len(ld_slice[c])):
            ld_slice[c][i] = 0
    
    # Work out the slice's size
    slice_data_bits = 8*slice_bytes(state, sx, sy)
    slice_data_bits -= 7
    length_field_bits = intlog2(slice_data_bits)
    slice_data_bits -= length_field_bits
    
    # Force the specified component to the full length
    if component == "Y":
        ld_slice["slice_y_length"] = slice_data_bits
    else:
        ld_slice["slice_y_length"] = 0
    
    # Work out the size of the padding bits
    bits_used_by_zeros = len(ld_slice["{}_transform".format(component.lower())])
    padding_bits = slice_data_bits - bits_used_by_zeros
    
    data_start_offset_bits = 7 + length_field_bits
    
    if padding_bits > 0:
        padding = generate_filled_padding(
            padding_bits,
            filler,
            data_start_offset_bits if byte_align else 0,
        )
    else:
        padding = bitarray()
    
    ld_slice["{}_block_padding".format(component.lower())] = padding


def iter_slices_in_sequence(codec_features, sequence):
    """
    Iterate over all of the slices in a sequence.
    
    Utility for use with :py:class:`fill_hq_slice_padding` and
    :py:class:`fill_ld_slice_padding`.
    
    Generates a series of (:py:class:`~vc2_conformance.state.State`, sx, sy,
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
                sp = data_unit["fragment_parse"]["transform_parameters"]["slice_parameters"]
        
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


#@decoder_test_case_generator
#def slice_padding_data(codec_features):
#    """
#    Picture slices (13.5.3) and (13.5.4) may contain padding bits beyond the
#    end of the transform coefficients for each picture component. These test
#    cases check that decoders correctly ignore these values. Padding values
#    will be filled with the following (where slice sizes are sufficiently large
#    to allow it).
#    
#    * Zeros
#    * Non-zero data
#    * A the bits which encode an end-of-sequence data unit (which must be ignored)
#    """
#    sequence = make_sequence(
#        codec_features,
#        # These pictures encode to all zeros which should give the highest
#        # possible compression.
#        mid_gray(
#            codec_features["video_parameters"],
#            codec_features["picture_coding_mode"],
#        ),
#    )
#    
#    # TODO: Use iter_slices_in_sequence and fill_*_slice_padding to generate
#    # versions with different padding bytes
