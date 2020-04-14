"""
Tests which verify that codecs correctly process pictures in a stream.
"""

from bitarray import bitarray

from itertools import cycle, count, islice

from copy import deepcopy

from enum import Enum

from vc2_data_tables import (
    Profiles,
    ParseCodes,
)

from vc2_conformance._py2x_compat import zip

from vc2_conformance.slice_sizes import slice_bytes

from vc2_conformance.vc2_math import intlog2

from vc2_conformance.state import State

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.picture_generators import (
    moving_sprite,
    static_sprite,
    mid_gray,
    linear_ramps,
)

from vc2_conformance.picture_encoding import filter_bit_shift

from vc2_conformance.encoder import make_sequence

from vc2_conformance.test_cases.decoder.common import make_dummy_end_of_sequence


def generate_filled_padding(
    padding_length_bits, filler=b"\x00", byte_align=0,
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
    state, sx, sy, hq_slice, component, filler, byte_align=False, min_length=0,
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
        hq_slice["slice_y_length"]
        + hq_slice["slice_c1_length"]
        + hq_slice["slice_c2_length"]
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
    state, sx, sy, ld_slice, component, filler, byte_align=False,
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
    slice_data_bits = 8 * slice_bytes(state, sx, sy)
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
            padding_bits, filler, data_start_offset_bits if byte_align else 0,
        )
    else:
        padding = bitarray()

    ld_slice["{}_block_padding".format(component.lower())] = padding


def generate_exp_golomb_with_ascending_lengths(sign=1):
    """
    Generate a series of integers whose signed exp-golmb encodings have
    sequentially growing lengths.
    
    Yields an infinite series of (length, int) pairs with the same sign as the
    ``sign`` argument.
    """
    yield (1, 0)

    for int_bits, exp_golomb_bits in zip(count(1), count(4, 2)):
        yield (
            exp_golomb_bits,
            ((1 << int_bits) - 1) * (1 if sign > 0 else -1),
        )


class UnsatisfiableBlockSizeError(ValueError):
    """
    Thrown when trying to generate values for a particular block fails.
    """


def generate_exp_golomb_with_length(num_values, required_length):
    """
    Given a target number of bits, produce ``num_values`` whose signed
    exp-Golomb encoding is ``required_length`` bits long. Raises a
    :py:exc:`UnsatisfiableBlockSizeError` if the required length cannot be
    achieved with ``num_values``.
    
    This function tries to keep the length and the magnitudes of the returned
    numbers as low as possible. Returned numbers will alternate in sign.
    
    Parameters
    ==========
    num_values : int
        The number of values to return.
    required_length : int
        The number of bits which the returned values must take up when encoded
        as signed exp-golomb codes.
    
    Returns
    =======
    values : [int, ...]
    """
    # The basis of the algorithm used by this function is as follows. We start
    # out with num_values zeros. One by one, we increment each value to
    # increase its length, e.g. for num_values == 4:
    #
    #     Step 0: [0,  0, 0,  0]    Step 5: [3, -1, 1, -1]
    #     Step 1: [1,  0, 0,  0]    Step 6: [3, -3, 1, -1]
    #     Step 2: [1, -1, 0,  0]    Step 7: [3, -3, 3, -1]
    #     Step 3: [1, -1, 1,  0]    Step 8: [3, -3, 3, -3]
    #     Step 4: [1, -1, 1, -1]    Step 9: [7, -3, 3, -3]
    #
    # The algorithm then terminates successfully when the total length reaches
    # the required amount, or fails if it exceeds it.
    #
    # For the first num_values steps, the number of bits required increases
    # from num_values to num_values + 3*num_values. For every subsequent step,
    # the number of bits increases by 2. Clearly, then, there are some values
    # which this algorithm will never be able to reach because they don't sit
    # on a multiple of 2 or 3 boundary.
    #
    # To work-around the multiple-of-2-or-3 problem, if the algoritm fails to
    # find a match, the whole process is repeated with the last one or two
    # values fixed at zero, offsetting the starting number of bits by 1 or 2,
    # potentially enabling a solution to be found.

    for num_values, required_length, extra_zeros in [
        (num_values, required_length, []),
        (num_values - 1, required_length - 1, [0]),
        (num_values - 2, required_length - 2, [0, 0]),
    ]:
        # Skip impossible lengths
        if num_values < 0 or required_length < 0:
            continue
        elif num_values == 0 and required_length != 0:
            continue

        # For each value in num_values, an iterator which generates increasingly
        # long (length, int) pairs.
        iterators = [
            iter(generate_exp_golomb_with_ascending_lengths(sign))
            for sign in islice(cycle([+1, -1]), num_values)
        ]

        lengths_and_values = [next(it) for it in iterators]

        iterator_to_increment = cycle(range(len(iterators)))

        while True:
            current_length = sum(length for length, value in lengths_and_values)
            if current_length == required_length:
                return [value for length, value in lengths_and_values] + extra_zeros
            elif current_length < required_length:
                i = next(iterator_to_increment)
                lengths_and_values[i] = next(iterators[i])
            else:  # if current_length > required_length:
                break

    raise UnsatisfiableBlockSizeError(
        "Cannot create a series of {} signed integers "
        "exactly {} bits long.".format(num_values, required_length,)
    )


class DanglingTransformValueType(Enum):
    """
    The four different ways a transform coefficient can dangle off the end of a
    bounded block.
    """

    zero_dangling = 0
    """
    A zero value (1 bit) is encoded entirely beyond the end of the bounded
    block.
    """

    sign_dangling = 1
    """
    The final bit (the sign bit) of a non-zero exp-golomb value is dangling
    beyond the end of the bounded block.
    """

    stop_and_sign_dangling = 2
    """
    The final two bits (the stop bit and sign bit) of a non-zero exp-golomb
    value is dangling beyond the end of the bounded block.
    """

    lsb_stop_and_sign_dangling = 3
    """
    The final three bits (the least significant bit, stop bit and sign bit) of
    a non-zero exp-golomb value is dangling beyond the end of the bounded
    block.
    """


def generate_dangling_transform_values(block_bits, num_values, dangle_type, magnitude):
    """
    Generates sets of values which can be encoded into a ``block_bits`` bit
    long bounded block where some value is entirely or partly beyond the end of
    the bounded block.
    
    Parameters
    ==========
    block_bits : int
        The number of bits in the bounded block.
    num_values : int
        The number of values to be returned.
    dangle_type : :py:class:`DanglingTransformValueType`
        The type of dangling value to produce.
    magnitude : int
        The magnitude of the dangling value, in bits (for two's compliment
        representation). Ignored when dangle_type is
        :py:attr:`DanglingTransformValueType.zero_dangling`. When
        :py:attr:`DanglingTransformValueType.lsb_stop_and_sign_dangling`, the
        two's complement representation will actually be magnitude+1 bits.
    
    Returns
    =======
    values : [value, ...]
        ``num_values`` transform coefficients which, when encoded in a bounded
        block ``block_bits`` long will contain a dangling value of the
        requested type.

    Raises
    ======
        Raises :py:exc:`UnsatisfiableBlockSizeError` if no series of
        ``num_values`` could be produced meeting these requirements. This
        should only occur for degenerate cases (e.g.  near-zero block_bits or
        num_values or large magnitude values).
    """
    # Degenerate case: Can't do anything with no values...
    if num_values == 0:
        raise UnsatisfiableBlockSizeError("Number of values is 0")

    # Pick a value to dangle over the end of the block and the number of bits
    # of the value to be kept *inside* the block
    exp_golomb_length = (2 * magnitude) + 2
    value, length = {
        DanglingTransformValueType.zero_dangling: (0, 0),
        DanglingTransformValueType.sign_dangling: (
            -((1 << magnitude) - 1),
            exp_golomb_length - 1,
        ),
        DanglingTransformValueType.stop_and_sign_dangling: (
            -((1 << magnitude) - 1),
            exp_golomb_length - 2,
        ),
        DanglingTransformValueType.lsb_stop_and_sign_dangling: (
            -(1 << magnitude),
            exp_golomb_length - 3,
        ),
    }[dangle_type]

    # Degenerate case: Can't fit the non-dangling part within the allowed space
    if length > block_bits:
        raise UnsatisfiableBlockSizeError("Block too small for non-dangling part.")

    # Put as many non-zero values in-front of our target value as possible such
    # that all but 'length' bits of the bounded block are filled.
    values_before = []
    # NB: Range below means we try at most num_values - 1 values, i.e. we
    # always leave one value to use as our dangling value
    for num_values_before in reversed(range(min(block_bits - length + 1, num_values,))):
        try:
            values_before = generate_exp_golomb_with_length(
                num_values_before, block_bits - length,
            )
            break
        except UnsatisfiableBlockSizeError:
            values_before = None

    # Degenrate case: we can't pad the leading space in the block to fill all
    # but length bits. Should only occur for ludicrously small blocks/lengths.
    if values_before is None:
        raise UnsatisfiableBlockSizeError("Can't align dangling value.")

    return values_before + [value] + [0] * (num_values - len(values_before) - 1)


def cut_off_value_at_end_of_hq_slice(
    state, sx, sy, hq_slice, component, dangle_type, magnitude, min_length=0,
):
    """
    Given a :py:class:`~vc2_conformance.bitstream.HQSlice`, mutate it in-place
    such that the slice size remains the same, (or becomes
    min_length*slice_size_scaler + 4 bytes, whichever is greater) but the
    specified component's bounded block contains a value whose last bits are
    off the end of the bounded block.
    
    Parameters
    ==========
    state : :py:class:`~vc2_conformance.state.State`
        A state dictionary containing at least ``slice_size_scaler``.
    sx, sy : int
        The slice coordinates. (Not used but present for consistency with
        :py:func:`cut_off_value_at_end_of_hq_slice`.
    hq_slice : :py:class:`~vc2_conformance.bitstream.HQSlice`
        The slice to modify.
    component : "Y", "C1" or "C2"
        The component in which to place the dangling value.
    dangle_type : :py:class:`DanglingTransformValueType`
        The type of dangling value to produce.
    magnitude : int
        The magnitude of the dangling value, in bits. Ignored when dangle_type
        is :py:attr:`DanglingTransformValueType.lsb_stop_and_sign_dangling`.
    min_length : int
        The minimum total length field for the modified slice
    
    Raises
    ======
    UnsatisfiableBlockSizeError
        If unable to create the specified type of dangling values in the space
        and transform components available. Should only occur in degenerate
        cases.
    """
    # Make the designated slice have at least 16 bits (this should allow for
    # plenty of flexibility
    total_length = (
        hq_slice["slice_y_length"]
        + hq_slice["slice_c1_length"]
        + hq_slice["slice_c2_length"]
    )

    total_length = max(min_length, total_length)

    if total_length < 2:
        raise UnsatisfiableBlockSizeError("Slices too small")

    if component == "Y":
        hq_slice["slice_y_length"] = 2
        hq_slice["slice_c1_length"] = 0
        hq_slice["slice_c2_length"] = total_length - 2
    elif component == "C1":
        hq_slice["slice_y_length"] = 0
        hq_slice["slice_c1_length"] = 2
        hq_slice["slice_c2_length"] = total_length - 2
    elif component == "C2":
        hq_slice["slice_y_length"] = 0
        hq_slice["slice_c1_length"] = total_length - 2
        hq_slice["slice_c2_length"] = 2

    # Work out length of component to truncate
    block_bytes = 2 * state["slice_size_scaler"]
    block_bits = block_bytes * 8

    # Work out how many transform coeffs are in this component
    num_values = len(hq_slice["{}_transform".format(component.lower())])

    # Force picture content to zeros
    for c in ["y_transform", "c1_transform", "c2_transform"]:
        for i in range(len(hq_slice[c])):
            hq_slice[c][i] = 0

    # Fill requested component with dangling values
    values = generate_dangling_transform_values(
        block_bits, num_values, dangle_type, magnitude,
    )
    hq_slice["{}_transform".format(component.lower())] = values


def cut_off_value_at_end_of_ld_slice(
    state, sx, sy, ld_slice, component, dangle_type, magnitude,
):
    """
    Given a :py:class:`~vc2_conformance.bitstream.LDSlice`, mutate it in-place
    such that the slice size remains the same, but the specified component's
    bounded block contains a value whose last bits are off the end of the
    bounded block.
    
    Parameters
    ==========
    state : :py:class:`~vc2_conformance.state.State`
        A state dictionary containing at least:
        
        * ``slices_x``
        * ``slices_y``
        * ``slice_bytes_numerator``
        * ``slice_bytes_denominator``
    sx, sy : int
        The slice coordinates. (Not used but present for consistency with
        :py:func:`cut_off_value_at_end_of_hq_slice`.
    ld_slice : :py:class:`~vc2_conformance.bitstream.LDSlice`
        The slice to modify.
    component : "Y" or "C"
        The component in which to place the dangling value.
    dangle_type : :py:class:`DanglingTransformValueType`
        The type of dangling value to produce.
    magnitude : int
        The magnitude of the dangling value, in bits. Ignored when dangle_type
        is :py:attr:`DanglingTransformValueType.lsb_stop_and_sign_dangling`.
    
    Raises
    ======
    UnsatisfiableBlockSizeError
        If unable to create the specified type of dangling values in the space
        and transform components available. Should only occur in degenerate
        cases.
    """
    # Make the designated slice have at least 16 bits (this should allow for
    # plenty of flexibility in fitting sensible magnitudes
    slice_data_bits = 8 * slice_bytes(state, sx, sy)
    slice_data_bits -= 7
    length_field_bits = intlog2(slice_data_bits)
    slice_data_bits -= length_field_bits

    block_bits = 16

    if slice_data_bits < block_bits:
        raise UnsatisfiableBlockSizeError("Slices too small")

    if component == "Y":
        ld_slice["slice_y_length"] = block_bits
    elif component == "C":
        ld_slice["slice_y_length"] = slice_data_bits - block_bits

    # Work out how many transform coeffs are in this component
    num_values = len(ld_slice["{}_transform".format(component.lower())])

    # Force picture content to zeros
    for c in ["y_transform", "c_transform"]:
        for i in range(len(ld_slice[c])):
            ld_slice[c][i] = 0

    # Fill requested component with dangling values
    values = generate_dangling_transform_values(
        block_bits, num_values, dangle_type, magnitude,
    )
    ld_slice["{}_transform".format(component.lower())] = values


def iter_slices_in_sequence(codec_features, sequence):
    """
    Iterate over all of the slices in a sequence.
    
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


@decoder_test_case_generator
def slice_padding_data(codec_features):
    """
    Picture slices (13.5.3) and (13.5.4) may contain padding bits beyond the
    end of the transform coefficients for each picture component. These test
    cases check that decoders correctly ignore these values. Padding values
    will be filled with the following (where slice sizes are sufficiently large
    to allow it).
    
    * All-zeros
    * All-ones
    * Alternating ones and zeros
    * A the bits which encode an end-of-sequence data unit (which must be ignored)
    """
    # The values with which to fill padding data
    #
    # [(filler, byte_align, explanation), ...]
    filler_values = [
        (b"\x00", False, "all_zeros"),
        (b"\xFF", False, "all_ones"),
        (b"\xAA", False, "alternating_1s_and_0s"),
        (b"\x55", False, "alternating_0s_and_1s"),
        (make_dummy_end_of_sequence(), True, "dummy_end_of_sequence"),
    ]

    # The picture components expected
    if codec_features["profile"] == Profiles.high_quality:
        picture_components = ["Y", "C1", "C2"]
    elif codec_features["profile"] == Profiles.low_delay:
        picture_components = ["Y", "C"]

    # Generate single-frame mid-gray sequences with the specified padding data
    base_sequence = make_sequence(
        codec_features,
        # These pictures encode to all zeros which should give the highest
        # possible compression.
        mid_gray(
            codec_features["video_parameters"], codec_features["picture_coding_mode"],
        ),
    )

    for filler, byte_align, explanation in filler_values:
        for component in picture_components:
            sequence = deepcopy(base_sequence)
            for (state, sx, sy, slice) in iter_slices_in_sequence(
                codec_features, sequence,
            ):
                if codec_features["profile"] == Profiles.high_quality:
                    # For lossless coding, extend the slice size to ensure some
                    # padding data is used
                    if codec_features["lossless"]:
                        min_length = (
                            slice["slice_y_length"]
                            + slice["slice_c1_length"]
                            + slice["slice_c2_length"]
                            + 8
                        )
                    else:
                        min_length = 0

                    fill_hq_slice_padding(
                        state, sx, sy, slice, component, filler, byte_align, min_length,
                    )
                elif codec_features["profile"] == Profiles.low_delay:
                    fill_ld_slice_padding(
                        state, sx, sy, slice, component, filler, byte_align,
                    )

            yield TestCase(sequence, "{}_{}".format(component, explanation,))


@decoder_test_case_generator
def dangling_bounded_block_data(codec_features):
    """
    Picture slices (13.5.3) and (13.5.4) contain transform values in bounded
    blocks (A.4.2). These test cases include bounded blocks in which some
    encoded values lie off the end of the block. Specifically, the following
    cases are tested:
    
    * A zero value (1 bit) is encoded entirely beyond the end of the bounded
      block.
    
    * The final bit (the sign bit) of a non-zero exp-golomb value is dangling
      beyond the end of the bounded block.
    
    * The final two bits (the stop bit and sign bit) of a non-zero exp-golomb
      value is dangling beyond the end of the bounded block.
    
    * The final three bits (the least significant bit, stop bit and sign bit)
      of a non-zero exp-golomb value is dangling beyond the end of the bounded
      block.
    """
    # The magnitude of the dangling value is chosen such that even if it ends
    # up being part of the DC component, the bit-shift used by some wavelets
    # won't make it disappear entirely.
    shift = filter_bit_shift(
        State(
            wavelet_index=codec_features["wavelet_index"],
            wavelet_index_ho=codec_features["wavelet_index_ho"],
        )
    )
    magnitude = (
        (codec_features["dwt_depth"] + codec_features["dwt_depth_ho"]) * shift
    ) + 1

    # The picture components expected
    if codec_features["profile"] == Profiles.high_quality:
        picture_components = ["Y", "C1", "C2"]
    elif codec_features["profile"] == Profiles.low_delay:
        picture_components = ["Y", "C"]

    # Generate single-frame mid-gray sequences
    base_sequence = make_sequence(
        codec_features,
        mid_gray(
            codec_features["video_parameters"], codec_features["picture_coding_mode"],
        ),
    )

    # Replace with dangling values as required
    for dangle_type in DanglingTransformValueType:
        for component in picture_components:
            try:
                sequence = deepcopy(base_sequence)
                for (state, sx, sy, slice) in iter_slices_in_sequence(
                    codec_features, sequence,
                ):
                    if codec_features["profile"] == Profiles.high_quality:
                        # For lossless coding, extend the slice size to ensure some
                        # data is used
                        if codec_features["lossless"]:
                            min_length = 2
                        else:
                            min_length = 0

                        cut_off_value_at_end_of_hq_slice(
                            state,
                            sx,
                            sy,
                            slice,
                            component,
                            dangle_type,
                            magnitude,
                            min_length,
                        )
                    elif codec_features["profile"] == Profiles.low_delay:
                        cut_off_value_at_end_of_ld_slice(
                            state, sx, sy, slice, component, dangle_type, magnitude,
                        )

                yield TestCase(sequence, "{}_{}".format(dangle_type.name, component,))
            except UnsatisfiableBlockSizeError as e:
                pass


@decoder_test_case_generator
def interlace_mode(codec_features):
    """
    Static and moving synthetic image sequences which may be used to verify
    that the interlacing modes are correctly reported to display equipment.
    
    See :py:func:`vc2_conformance.picture_generators.moving_sprite` for a
    description of the still sequence.
    
    See :py:func:`vc2_conformance.picture_generators.moving_sprite` for a
    description of the moving sequence.
    """
    yield TestCase(
        make_sequence(
            codec_features,
            static_sprite(
                codec_features["video_parameters"],
                codec_features["picture_coding_mode"],
            ),
        ),
        "static_sequence",
    )

    yield TestCase(
        make_sequence(
            codec_features,
            moving_sprite(
                codec_features["video_parameters"],
                codec_features["picture_coding_mode"],
            ),
        ),
        "moving_sequence",
    )


@decoder_test_case_generator
def static_grey(codec_features):
    """
    A static mid-grey frame.
    
    This test image represents the special case of a maximally compressible
    image where the codec need not represent any transform coefficients
    explicitly.
    
    This test represents an extreme case for lossless (variable bitrate)
    codecs.
    """
    return make_sequence(
        codec_features,
        mid_gray(
            codec_features["video_parameters"], codec_features["picture_coding_mode"],
        ),
    )


@decoder_test_case_generator
def static_ramps(codec_features):
    """
    A static frame containing linear brightness ramps for white and primary
    red, green and blue (in that order, from top-to-bottom).
    
    This test may be used to check that the correct colour model information
    has been passed on to the display.
    """
    return make_sequence(
        codec_features,
        linear_ramps(
            codec_features["video_parameters"], codec_features["picture_coding_mode"],
        ),
    )
