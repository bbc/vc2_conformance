r"""
The :py:mod:`vc2_conformance.encoder.pictures` module contains simple routines
for compressing pictures in a VC-2 bitstream.

The picture encoding behaviour used by the encoder is encapsulated by the
:py:func:`make_picture_data_units` function which turns a series of pictures
(given as raw pixel values) into a series of
:py:class:`DataUnits <vc2_conformance.bitstream.DataUnit>`:

.. autofunction:: make_picture_data_units


Encoding algorithm
------------------

Depending on the lossy/lossless coding mode chosen, one of two simple
algorithms is used.

Lossless mode
`````````````

In lossless mode, every slice's ``qindex`` will be set to 0 (no quantization)
and all transform coefficients will be coded verbatim (though trailing zeros
will be coded implicitly).

Slices will be sized as large as necessary, though as small as possible.

The smallest ``slice_size_scaler`` possible will be used for each coded picture
independently.

.. note::

    In principle, lossless modes may occasionally make use of quantization to
    achieve better compression. For example where all transform coefficients
    are a multiple of the same quantisation factor. This encoder, however, does
    not do this.

Lossy mode
``````````

In lossy mode the ``qindex`` for each slice is chosen on a slice-by-slice
basis. The encoder tests quantization indices starting at zero and stopping
when the transform coefficients fit into the slice.

Slices are sized such that the picture slice data in the bitstream totals
:py:class:`~vc2_conformance.codec_features.CodecFeatures`\
``["picture_bytes"]``.

For the high quality profile, the smallest ``slice_size_scaler`` which can
encode a slice where a single component consumes a whole slice is used for
every picture.

.. warning::

    The total size of picture slice data may differ from
    :py:class:`~vc2_conformance.codec_features.CodecFeatures`\
    ``["picture_bytes"]`` by up to ``slice_size_scaler`` bytes (for high
    quality profile formats) or one byte (for low delay profile formats). This
    will occur when the number of bytes (or multiple of ``slice_size_scaler``
    bytes) is not exactly divisible by the required number of picture bytes.

.. warning::

    The total number of bytes used to encode each picture, once other coding
    overheads (such as headers) will be higher than
    :py:class:`~vc2_conformance.codec_features.CodecFeatures`\
    ``["picture_bytes"]``.

.. note::

    This codec may not always produce highest quality pictures possible in
    lossy modes. For example, sometimes chosing higher quantisation indices can
    produce fewer coding artefacts, particularly in concatenated coding
    applications. Similarly, higher picture quality may sometimes be obtained
    by setting later transform coefficients to zero enabling a lower
    quantization index to be used. Other more sophisticated schemes may also
    directly tweak transform coefficients.


Use of pseudocode
-----------------

This module uses the pseudocode-derived
:py:mod:`vc2_conformance.pseudocode.picture_encoding` module for its
forward-DWT and :py:mod:`vc2_conformance.pseudocode.quantization` for
quantization. Other pseudocode routines are also used where possible, for
example for computing slice dimensions.

"""

from itertools import count

from collections import namedtuple

from fractions import Fraction

from copy import deepcopy

from vc2_data_tables import (
    QUANTISATION_MATRICES,
    Profiles,
    ParseCodes,
)

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_conformance.pseudocode.vc2_math import mean, intlog2

from vc2_conformance.pseudocode.arrays import width, height

from vc2_conformance.pseudocode.state import State

from vc2_conformance.pseudocode.video_parameters import set_coding_parameters

from vc2_conformance.pseudocode.picture_encoding import picture_encode

from vc2_conformance.codec_features import codec_features_to_trivial_level_constraints

from vc2_conformance.constraint_table import allowed_values_for, ValueSet

from vc2_conformance.level_constraints import LEVEL_CONSTRAINTS

from vc2_conformance.pseudocode.slice_sizes import (
    slice_bytes,
    slice_left,
    slice_right,
    slice_top,
    slice_bottom,
)

from vc2_conformance.pseudocode.quantization import forward_quant

from vc2_conformance.bitstream import (
    HQSlice,
    LDSlice,
    TransformData,
    QuantMatrix,
    PictureHeader,
    SliceParameters,
    TransformParameters,
    ExtendedTransformParameters,
    WaveletTransform,
    PictureParse,
    DataUnit,
    ParseInfo,
    FragmentParse,
    FragmentHeader,
    FragmentData,
)

from vc2_conformance.bitstream.exp_golomb import signed_exp_golomb_length

from vc2_conformance.encoder.exceptions import (
    MissingQuantizationMatrixError,
    IncompatibleLevelAndExtendedTransformParametersError,
    PictureBytesSpecifiedForLosslessModeError,
    InsufficientHQPictureBytesError,
    InsufficientLDPictureBytesError,
    LosslessUnsupportedByLowDelayError,
)


def get_quantization_marix(codec_features):
    """
    Get the quantization matrix (in the form of the ``quant_matrix`` entry in
    ``state``) based on the provided ``codec_features``.

    Throws
    :py:exc:`vc2_conformance.encoder.exceptions.MissingQuantizationMatrixError`
    if a matrix is not provided when no default is available.
    """
    if codec_features["quantization_matrix"] is None:
        transform_details = (
            codec_features["wavelet_index"],
            codec_features["wavelet_index_ho"],
            codec_features["dwt_depth"],
            codec_features["dwt_depth_ho"],
        )
        if transform_details not in QUANTISATION_MATRICES:
            raise MissingQuantizationMatrixError(codec_features)
        return QUANTISATION_MATRICES[transform_details]
    else:
        return codec_features["quantization_matrix"]


def serialize_quantization_matrix(matrix):
    """
    Given a quantization matrix as a hierarchy of dictionaries, returns the
    serial list of matrix values for use in a VC-2 bitstream.
    """
    out = []
    for level, orients in sorted(matrix.items()):
        for orient, value in sorted(
            orients.items(),
            key=lambda ov: ["L", "H", "LL", "HL", "LH", "HH"].index(ov[0]),
        ):
            out.append(value)
    return out


@ref_pseudocode(deviation="inferred_implementation")
def apply_dc_prediction(band):
    """(13.4) Inverse of dc_prediction."""
    for y in reversed(range(0, height(band))):
        for x in reversed(range(0, width(band))):
            if x > 0 and y > 0:
                prediction = mean(band[y][x - 1], band[y - 1][x - 1], band[y - 1][x])
            elif x > 0 and y == 0:
                prediction = band[0][x - 1]
            elif x == 0 and y > 0:
                prediction = band[y - 1][0]
            else:
                prediction = 0
            band[y][x] -= prediction


def calculate_coeffs_bits(coeffs):
    """
    Calculate the number of bits required to represent the supplied sequence of
    coefficients using signed exp-golomb coding within a bounded block.

    Parameters
    ==========
    coeffs : [int, ...]

    Returns
    =======
    num_bits : int
    """
    num_bits = 0

    skip_zeros = True
    for coeff in reversed(coeffs):
        if skip_zeros and coeff == 0:
            continue
        else:
            skip_zeros = False
            num_bits += signed_exp_golomb_length(coeff)

    return num_bits


def calculate_hq_length_field(coeffs, slice_size_scaler):
    """
    Compute a HQ picture slice length field for a set of coefficients.
    """
    multiple = 8 * slice_size_scaler
    return (calculate_coeffs_bits(coeffs) + multiple - 1) // multiple


def quantize_coeffs(qindex, coeff_values, quant_matrix_values):
    """
    Quantize a set of coefficient values.

    Parameters
    ==========
    qindex : int
        The base quantization index.
    coeff_values : [int, ...]
        The coefficients to be quantized.
    quant_matrix_values : [int, ...]
        For each entry in ``coeff_value``, the corresponding quantization
        matrix value.

    Returns
    =======
    quantized_coeff_values : [int, ...]
    """
    return [
        forward_quant(
            coeff_value,
            max(0, qindex - quant_matrix_value),
        )
        for coeff_value, quant_matrix_value in zip(
            coeff_values,
            quant_matrix_values,
        )
    ]


ComponentCoeffs = namedtuple("ComponentCoeffs", "coeff_values,quant_matrix_values")
"""
A tuple containing (in bitstream order) the transform coefficients and
corresponding quantisation matrix values for a particular picture component
within a picture slice.
"""

SliceCoeffs = namedtuple("SliceCoeffs", "Y,C1,C2")
"""
A tuple of :py:class:`ComponentCoeffs` tuples giving the transform coefficients
described by a picture slice.
"""


def quantize_to_fit(target_size, coeff_sets, align_bits=1, minimum_qindex=0):
    """
    Find the quantisation index necessary to reduce a several sets of transform
    coefficients to total a target length in bits.

    Each block of quantized transform coefficients is assumed to be padded to a
    whole multiple of align_bits bits.

    Parameters
    ==========
    target_size : int
        Target size, in bytes.
    coeff_sets : [:py:class:`ComponentCoeffs`, ...]
        A series of sets of coeffs to be quantised and concatenated, along with
        their corresponding quantisation matrix values.
    align_bits : int
        The size of each block will be rounded up to a whole multiple of this
        value. Use this to, for example, force lengths to be a whole number of
        bytes (set to 8) or some slice_size_scaler (set to
        8*slice_size_scaler).
    minimum_qindex : int
        If provided, gives the quantization index to start with when trying to
        find a suitable quantization index.

    Returns
    =======
    qindex : int
        The quantisation index chosen.
    [[int, ...], ...]
        For each set of coefficients provided, the quantised coefficient
        values.
    """
    assert target_size >= 0

    for qindex in count(minimum_qindex):
        quantized_coeff_sets = [
            quantize_coeffs(
                qindex,
                component_coeffs.coeff_values,
                component_coeffs.quant_matrix_values,
            )
            for component_coeffs in coeff_sets
        ]

        total_length = sum(
            # Round each block's length to whole multiple of align_bits
            ((calculate_coeffs_bits(quantized_coeffs) + align_bits - 1) // align_bits)
            * align_bits
            for quantized_coeffs in quantized_coeff_sets
        )

        if total_length <= target_size:
            return (qindex, quantized_coeff_sets)


def transform_and_slice_picture(codec_features, picture):
    """
    Transform a picture provided using a forward DWT and DC prediction
    according to the :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    dictionary provided. Returns transform coefficients grouped by picture
    slice.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
        The picture to be encoded. This picture will be compressed using a
        simple VC-2 encoder implementation. It does not necessarily produce the
        most high-quality encodings.

    Returns
    =======
    slice_coeffs : [[:py:class:`SliceCoeffs`, ...], ...]
        A 2D array containing, for each picture slice, the transform
        coefficients and corresponding quantisation matrix values in bitstream
        order.
    """
    # Perform a forward DWT
    state = State(
        wavelet_index=codec_features["wavelet_index"],
        wavelet_index_ho=codec_features["wavelet_index_ho"],
        dwt_depth=codec_features["dwt_depth"],
        dwt_depth_ho=codec_features["dwt_depth_ho"],
        slices_x=codec_features["slices_x"],
        slices_y=codec_features["slices_y"],
        picture_coding_mode=codec_features["picture_coding_mode"],
    )
    set_coding_parameters(state, codec_features["video_parameters"])

    # NB: picture_encode corrupts the supplied picture arrays so a copy is
    # provided here
    picture_encode(state, deepcopy(picture))

    # Perform DC prediction
    if codec_features["profile"] == Profiles.low_delay:
        if state["dwt_depth_ho"] == 0:
            apply_dc_prediction(state["y_transform"][0]["LL"])
            apply_dc_prediction(state["c1_transform"][0]["LL"])
            apply_dc_prediction(state["c2_transform"][0]["LL"])
        else:
            apply_dc_prediction(state["y_transform"][0]["L"])
            apply_dc_prediction(state["c1_transform"][0]["L"])
            apply_dc_prediction(state["c2_transform"][0]["L"])

    # Load quantisation matrix
    state["quant_matrix"] = get_quantization_marix(codec_features)

    # Divide the picture into slices and collect together transform
    # coefficients in bitstream order (along with associated quantisation
    # matrix values)
    slice_coeffs = [
        [
            SliceCoeffs(
                ComponentCoeffs([], []),
                ComponentCoeffs([], []),
                ComponentCoeffs([], []),
            )
            for _ in range(state["slices_x"])
        ]
        for _ in range(state["slices_y"])
    ]

    # NB: Iteration order for level and orient are critical here
    for transform in ["y_transform", "c1_transform", "c2_transform"]:
        comp = transform.split("_")[0].upper()
        for level, orients in sorted(state[transform].items()):
            for orient, coeffs in sorted(
                orients.items(),
                key=lambda orient_coeffs: ["L", "LL", "H", "HL", "LH", "HH"].index(
                    orient_coeffs[0]
                ),
            ):

                sxs = [
                    (
                        slice_left(state, sx, comp, level),
                        slice_right(state, sx, comp, level),
                    )
                    for sx in range(state["slices_x"])
                ]
                sys = [
                    (
                        slice_top(state, sy, comp, level),
                        slice_bottom(state, sy, comp, level),
                    )
                    for sy in range(state["slices_y"])
                ]

                for sy, (y1, y2) in enumerate(sys):
                    for sx, (x1, x2) in enumerate(sxs):
                        for y in range(y1, y2):
                            for x in range(x1, x2):
                                sc = getattr(slice_coeffs[sy][sx], comp)
                                sc.coeff_values.append(coeffs[y][x])
                                sc.quant_matrix_values.append(
                                    state["quant_matrix"][level][orient]
                                )

    return slice_coeffs


def make_hq_slice(
    y_transform,
    c1_transform,
    c2_transform,
    total_length,
    qindex,
    slice_size_scaler=1,
):
    """
    Create a :py:class:`vc2_conformance.bitstream.HQSlice` containing the
    provided already-quantized coefficients.

    Parameters
    ==========
    y_transform : [int, ...]
    c1_transform : [int, ...]
    c2_transform : [int, ...]
        Quantized transform coefficients for this slice, in bitstream order.
    total_length : int or None
        If an integer, the ``slice_c2_length`` field will be set such that all
        three length fields sum to ``total_length``. Note that this length
        value is given in multiples of slice_size_scaler bytes and that this
        total length does not account for the size of the length fields and
        qindex fields also present in the slice.

        If None, the ``slice_c2_length`` field will be set to the minimum
        multiple of slice_size_scaler bytes which the ``c2_transform``
        coefficients can fit into.
    qindex : int
        The quantization index used to quantise the provided coefficient.s
    slice_size_scaler : int
    """
    # Compute component lengths
    y_length = calculate_hq_length_field(y_transform, slice_size_scaler)
    c1_length = calculate_hq_length_field(c1_transform, slice_size_scaler)
    if total_length is None:
        c2_length = calculate_hq_length_field(c2_transform, slice_size_scaler)
    else:
        c2_length = total_length - y_length - c1_length

    return HQSlice(
        qindex=qindex,
        slice_y_length=y_length,
        slice_c1_length=c1_length,
        slice_c2_length=c2_length,
        y_transform=y_transform,
        c1_transform=c1_transform,
        c2_transform=c2_transform,
    )


def make_ld_slice(y_transform, c_transform, qindex):
    """
    Create a :py:class:`vc2_conformance.bitstream.LDSlice` containing the
    provided already-quantized coefficients.

    Parameters
    ==========
    y_transform : [int, ...]
    c_transform : [int, ...]
        Quantized transform coefficients for this slice, in bitstream order.
    qindex : int
        The quantization index used to quantise the provided coefficient.s
    """
    return LDSlice(
        qindex=qindex,
        slice_y_length=calculate_coeffs_bits(y_transform),
        y_transform=y_transform,
        c_transform=c_transform,
    )


def make_transform_data_hq_lossless(transform_coeffs, minimum_slice_size_scaler=1):
    """
    Pack transform coefficients into HQ picture slices in a
    :py:class:`TransformData`, computing the required slice_size_scaler.

    Parameters
    ==========
    transform_coeffs : [[:py:class:`SliceCoeffs`, ...], ...]
    minimum_slice_size_scaler : int
        Specifies the minimum slice_size_scaler to be used for high quality
        pictures. Ignored in low delay mode.

    Returns
    =======
    slice_size_scaler : int
    transform_data : :py:class:`vc2_conformance.bitstream.TransformData`
    """
    # Initially, the slice_size_scaler is assumed to be 1. If any of the length
    # fields which result are > 255 we will need to revise this, along with all
    # of the length values.
    transform_data = TransformData(
        hq_slices=[
            make_hq_slice(
                transform_coeffs_slice.Y.coeff_values,
                transform_coeffs_slice.C1.coeff_values,
                transform_coeffs_slice.C2.coeff_values,
                total_length=None,
                qindex=0,
                slice_size_scaler=1,
            )
            for transform_coeffs_row in transform_coeffs
            for transform_coeffs_slice in transform_coeffs_row
        ]
    )

    # Find the minimum slice size scaler possible
    max_length = max(
        max(
            hq_slice["slice_y_length"],
            hq_slice["slice_c1_length"],
            hq_slice["slice_c2_length"],
        )
        for hq_slice in transform_data["hq_slices"]
    )
    slice_size_scaler = max(1, minimum_slice_size_scaler, (max_length + 254) // 255)

    # Adjust slice lengths accordingly
    for hq_slice in transform_data["hq_slices"]:
        hq_slice["slice_y_length"] += slice_size_scaler - 1
        hq_slice["slice_y_length"] //= slice_size_scaler

        hq_slice["slice_c1_length"] += slice_size_scaler - 1
        hq_slice["slice_c1_length"] //= slice_size_scaler

        hq_slice["slice_c2_length"] += slice_size_scaler - 1
        hq_slice["slice_c2_length"] //= slice_size_scaler

    return slice_size_scaler, transform_data


def get_safe_lossy_hq_slice_size_scaler(picture_bytes, num_slices):
    """
    Return a slice_size_scaler which is guaranteed to be large enough for any
    slice in a lossy HQ picture.

    Parameters
    ==========
    picture_bytes : int
        The total number of bytes the picture slices should take up (i.e.
        including ``qindex`` and ``slice_{y,c1,c2}_length`` fields). Must allow
        at least 4 bytes per slice.
    num_slices : int
        Number of slices per picture.

    Returns
    =======
    slice_size_scaler : int
        A safe slice size scaler to use.
    """
    max_slice_bytes = (picture_bytes + num_slices - 1) // num_slices
    max_length_field_value = max_slice_bytes - 4

    # Find the smallest slice size scaler which lets this size fit into an 8
    # bit length field.
    slice_size_scaler = (max_length_field_value + 254) // 255

    return max(1, slice_size_scaler)


def make_transform_data_hq_lossy(
    picture_bytes, transform_coeffs, minimum_qindex=0, minimum_slice_size_scaler=1
):
    """
    Quantize and pack transform coefficients into HQ picture slices in a
    :py:class:`TransformData`.

    Raises :py:exc:`InsufficientHQPictureBytesError` if ``picture_bytes`` is too
    small.

    Parameters
    ==========
    picture_bytes : int
        The total number of bytes the picture slices should take up (i.e.
        including ``qindex`` and ``slice_{y,c1,c2}_length`` fields). Must allow
        at least 4 bytes per slice. When slice sizes are large enough to
        require a slice_size_scaler larger than 1, ``picture_bytes -
        4*num_slices`` must be a multiple of ``slice_size_scaler``, otherwise
        the total picture size will deviate by up to ``slice_size_scaler``
        bytes from ``picture_bytes``.
    transform_coeffs : [[:py:class:`SliceCoeffs`, ...], ...]
    minimum_qindex : int
        If provided, gives the quantization index to start with when trying to
        find a suitable quantization index.
    minimum_slice_size_scaler : int
        Specifies the minimum slice_size_scaler to be used for high quality
        pictures. Ignored in low delay mode.

    Returns
    =======
    slice_size_scaler : int
    transform_data : :py:class:`vc2_conformance.bitstream.TransformData`
    """
    slices_x = width(transform_coeffs)
    slices_y = height(transform_coeffs)

    # Determine the largest size a slice could be
    num_slices = slices_x * slices_y

    # Find the smallest slice size scaler which lets this size fit into 8 bits
    slice_size_scaler = max(
        get_safe_lossy_hq_slice_size_scaler(picture_bytes, num_slices),
        minimum_slice_size_scaler,
    )

    # Work out the total bitstream space available after slice overheads are
    # accounted for (NB: 4 bytes overhead per slice due to qindex and
    # slice_{y,c1,c2}_length fields).
    total_coeff_bytes = picture_bytes - (num_slices * 4)

    if total_coeff_bytes < 0:
        raise InsufficientHQPictureBytesError()

    # We'll repurpose slice_bytes (13.5.3.2) to compute the number of
    # slice_size_scaler bytes available for transform coefficients in each
    # picture slice. (i.e. it won't compute the size of the slice in bytes but
    # the number of slice_size_scaler bytes available for transform
    # coefficients in each slice).
    state = State(
        slices_x=slices_x,
        slices_y=slices_y,
        slice_bytes_numerator=total_coeff_bytes,
        slice_bytes_denominator=num_slices * slice_size_scaler,
    )

    transform_data = TransformData(hq_slices=[])
    for sy, transform_coeffs_row in enumerate(transform_coeffs):
        for sx, transform_coeffs_slice in enumerate(transform_coeffs_row):
            # NB: Actually calculates multiples of slice_size_scaler bytes
            # after all length/qindex fields accounted for. See comment above
            # "state = State(".
            total_length = slice_bytes(state, sx, sy)
            target_size = 8 * slice_size_scaler * total_length

            # Quantize each slice to fit
            qindex, (y_transform, c1_transform, c2_transform) = quantize_to_fit(
                target_size,
                transform_coeffs_slice,
                8 * slice_size_scaler,
                minimum_qindex,
            )
            transform_data["hq_slices"].append(
                make_hq_slice(
                    y_transform,
                    c1_transform,
                    c2_transform,
                    total_length,
                    qindex,
                    slice_size_scaler,
                )
            )

    return slice_size_scaler, transform_data


def interleave(a, b):
    """
    Return a list containing the interleaving of elements from the lists a and
    b, first element from 'a' first.
    """
    out = []
    for va, vb in zip(a, b):
        out.append(va)
        out.append(vb)
    return out


def make_transform_data_ld_lossy(picture_bytes, transform_coeffs, minimum_qindex=0):
    """
    Quantize and pack transform coefficients into LD picture slices in a
    :py:class:`TransformData`.

    Raises :py:exc:`InsufficientLDPictureBytesError` if ``picture_bytes`` is too
    small.

    Parameters
    ==========
    picture_bytes : int
        The total number of bytes the picture slices should take up (i.e.
        including qindex and slice_y_length fields). Must be at least 1 byte
        per slice.
    transform_coeffs : [[:py:class:`SliceCoeffs`, ...], ...]
    minimum_qindex : int
        If provided, gives the quantization index to start with when trying to
        find a suitable quantization index.

    Returns
    =======
    transform_data : :py:class:`vc2_conformance.bitstream.TransformData`
    """
    # Used by slice_bytes
    state = State(
        slices_x=width(transform_coeffs),
        slices_y=height(transform_coeffs),
        slice_bytes_numerator=picture_bytes,
        slice_bytes_denominator=width(transform_coeffs) * height(transform_coeffs),
    )

    transform_data = TransformData(ld_slices=[])
    for sy, transform_coeffs_row in enumerate(transform_coeffs):
        for sx, transform_coeffs_slice in enumerate(transform_coeffs_row):
            target_size = 8 * slice_bytes(state, sx, sy)
            target_size -= 7  # qindex field
            target_size -= intlog2(target_size)  # slice_y_length field

            if target_size < 0:
                raise InsufficientLDPictureBytesError()

            # Interleave color components
            y_coeffs = transform_coeffs_slice.Y
            c_coeffs = ComponentCoeffs(
                coeff_values=interleave(
                    transform_coeffs_slice.C1.coeff_values,
                    transform_coeffs_slice.C2.coeff_values,
                ),
                quant_matrix_values=interleave(
                    transform_coeffs_slice.C1.quant_matrix_values,
                    transform_coeffs_slice.C2.quant_matrix_values,
                ),
            )

            # Quantize each slice to fit
            qindex, (y_transform, c_transform) = quantize_to_fit(
                target_size,
                [y_coeffs, c_coeffs],
                minimum_qindex=minimum_qindex,
            )
            transform_data["ld_slices"].append(
                make_ld_slice(
                    y_transform,
                    c_transform,
                    qindex,
                )
            )

    return transform_data


def make_quant_matrix(codec_features):
    """
    Create a :py:class:`vc2_conformance.bitstream.QuantMatrix` given a set of
    codec features.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`

    Returns
    =======
    quant_matrix : :py:class:`vc2_conformance.bitstream.QuantMatrix`
    """
    if codec_features["quantization_matrix"] is None:
        return QuantMatrix(custom_quant_matrix=False)
    else:
        return QuantMatrix(
            custom_quant_matrix=True,
            quant_matrix=serialize_quantization_matrix(
                codec_features["quantization_matrix"]
            ),
        )


def decide_extended_transform_flag(codec_features, flag_name, required):
    """
    Decide what asym_transform*_flag setting to use, accounting for level
    restrictions.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    flag_name : str
        The name of the flag to be decided (e.g. "asym_transform_index_flag").
    required : str
        If True, require this flag to be True, if False, the flag may be set to
        True or False, as allowed by the level, preferring False.

    Returns
    =======
    flag : bool

    Raises
    ======
    vc2_conformance.encoder.exceptions.IncompatibleLevelAndExtendedTransformParametersError
        If ``required`` is True but the level prohibits the flag.
    """
    # The flag states which we could use to encode the required value
    usable_flags = [True] if required else [False, True]

    # The allowed flag values according to the current level
    constrained_values = codec_features_to_trivial_level_constraints(codec_features)
    permitted_flags = allowed_values_for(
        LEVEL_CONSTRAINTS, flag_name, constrained_values
    )

    # Warning: Slight bodge/special case handled here...
    #
    # The make_extended_transform_parameters function (and by extension, this
    # function) is required to return an ExtendedTransformParameters object
    # even for streams with major_version < 3 which don't contain that field.
    #
    # To handle this case, we treat an empty constraint table entry as allowing
    # 'False' as a valid flag option when in reality for < v3 streams no value
    # is permitted.
    #
    # Note that we will still raise
    # IncompatibleLevelAndExtendedTransformParametersError if required is True
    # in this case. We also don't allow False if the level specifically
    # requires the flag to be True (i.e. we only allow it when the level gives
    # no values).
    if permitted_flags == ValueSet():
        permitted_flags.add_value(False)

    try:
        return next(flag for flag in usable_flags if flag in permitted_flags)
    except StopIteration:
        raise IncompatibleLevelAndExtendedTransformParametersError(codec_features)


def make_extended_transform_parameters(codec_features):
    """
    Create a :py:class:`vc2_conformance.bitstream.ExtendedTransformParameters`
    given a set of codec features. The encoding used will be as short as
    possible for the specified codec configuration.
    """

    etp = ExtendedTransformParameters()

    etp["asym_transform_index_flag"] = decide_extended_transform_flag(
        codec_features,
        "asym_transform_index_flag",
        codec_features["wavelet_index"] != codec_features["wavelet_index_ho"],
    )
    if etp["asym_transform_index_flag"]:
        etp["wavelet_index_ho"] = codec_features["wavelet_index_ho"]

    etp["asym_transform_flag"] = decide_extended_transform_flag(
        codec_features,
        "asym_transform_flag",
        codec_features["dwt_depth_ho"] != 0,
    )
    if etp["asym_transform_flag"]:
        etp["dwt_depth_ho"] = codec_features["dwt_depth_ho"]

    return etp


def make_picture_parse(
    codec_features, picture, minimum_qindex=0, minimum_slice_size_scaler=1
):
    """
    Compress a picture.

    Raises :py:exc:`PictureBytesSpecifiedForLosslessModeError` if
    ``picture_bytes`` is specifiied for a lossless coding mode.

    Raises :py:exc:`InsufficientLDPictureBytesError`
    :py:exc:`InsufficientHQPictureBytesError` if ``picture_bytes`` is too small
    for the coding mode used.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
        The picture to be encoded. This picture will be compressed using a
        simple VC-2 encoder implementation. It does not necessarily produce the
        most high-quality encodings. If ``pic_num`` is omitted,
        ``picture_number`` fields will be omitted in the output.
    minimum_qindex : int
        Specifies the minimum quantization index to be used. Must be 0 for
        lossless codecs.
    minimum_slice_size_scaler : int
        Specifies the minimum slice_size_scaler to be used for high quality
        pictures. Ignored in low delay mode.

    Returns
    =======
    transform_data : :py:class:`vc2_conformance.bitstream.TransformData`
        The transform data, ready for serialization.
    """
    # Apply transform and split into slices
    transform_coeffs = transform_and_slice_picture(codec_features, picture)

    picture_header = PictureHeader()
    if "pic_num" in picture:
        picture_header["picture_number"] = picture["pic_num"]

    slice_parameters = SliceParameters(
        slices_x=codec_features["slices_x"],
        slices_y=codec_features["slices_y"],
    )

    # Quantize coefficients as required and set slice_size_scaler (HQ Only) and
    # slice_bytes (LD only)
    if codec_features["profile"] == Profiles.high_quality:
        if codec_features["lossless"]:
            assert minimum_qindex == 0
            if codec_features["picture_bytes"] is not None:
                raise PictureBytesSpecifiedForLosslessModeError(codec_features)
            slice_size_scaler, transform_data = make_transform_data_hq_lossless(
                transform_coeffs,
                minimum_slice_size_scaler,
            )
        else:
            try:
                slice_size_scaler, transform_data = make_transform_data_hq_lossy(
                    codec_features["picture_bytes"],
                    transform_coeffs,
                    minimum_qindex,
                    minimum_slice_size_scaler,
                )
            except InsufficientHQPictureBytesError:
                # Re-raise with codec features dict
                raise InsufficientHQPictureBytesError(codec_features)

        # NB: For simplicity, this implementation currently does not support
        # setting the slice prefix bytes to anything except zero since this is
        # not required by any existing VC-2 level. The assumption that this is
        # OK is verified in
        # ``tests/encoder/test_level_constraints_assumptions.py``.
        #
        # In addition, the `codec_features_to_trivial_level_constraints`
        # function assumes that this value is always 0 too.
        slice_parameters["slice_prefix_bytes"] = 0
        slice_parameters["slice_size_scaler"] = slice_size_scaler
    elif codec_features["profile"] == Profiles.low_delay:
        if codec_features["lossless"]:
            raise LosslessUnsupportedByLowDelayError(codec_features)
        try:
            transform_data = make_transform_data_ld_lossy(
                codec_features["picture_bytes"],
                transform_coeffs,
                minimum_qindex,
            )
        except InsufficientLDPictureBytesError:
            # Re-raise with codec features dict
            raise InsufficientLDPictureBytesError(codec_features)

        slice_bytes_fraction = Fraction(
            codec_features["picture_bytes"],
            codec_features["slices_x"] * codec_features["slices_y"],
        )
        slice_parameters["slice_bytes_numerator"] = slice_bytes_fraction.numerator
        slice_parameters["slice_bytes_denominator"] = slice_bytes_fraction.denominator

    transform_parameters = TransformParameters(
        wavelet_index=codec_features["wavelet_index"],
        dwt_depth=codec_features["dwt_depth"],
        # NB: We *always* include an ExtendedTransformParameters field. This
        # field will later be removed (if not supported by the major_version
        # chosen for the stream) using the
        # :py:func:`vc2_conformance.bitstream.vc2_autofill.autofill_major_version`
        # function.
        extended_transform_parameters=make_extended_transform_parameters(
            codec_features
        ),
        slice_parameters=slice_parameters,
        quant_matrix=make_quant_matrix(codec_features),
    )

    wavelet_transform = WaveletTransform(
        transform_parameters=transform_parameters,
        transform_data=transform_data,
    )

    return PictureParse(
        picture_header=picture_header,
        wavelet_transform=wavelet_transform,
    )


def make_picture_parse_data_unit(
    codec_features, picture, minimum_qindex=0, minimum_slice_size_scaler=1
):
    """
    Create a :py:class:`~vc2_conformance.bitstream.DataUnit` object containing
    a (possibly lossily compressed) picture.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
        The picture to be encoded. This picture will be compressed using a
        simple VC-2 encoder implementation. It does not necessarily produce the
        most high-quality encodings. If ``pic_num`` is omitted,
        ``picture_number`` fields will be omitted in the output.
    minimum_qindex : int
        Specifies the minimum quantization index to be used. Must be 0 for
        lossless codecs.
    minimum_slice_size_scaler : int
        Specifies the minimum slice_size_scaler to be used for high quality
        pictures. Ignored in low delay mode.

    Returns
    =======
    data_unit : :py:class:`vc2_conformance.bitstream.DataUnit`
    """
    assert codec_features["fragment_slice_count"] == 0

    return DataUnit(
        parse_info=ParseInfo(
            parse_code=(
                ParseCodes.high_quality_picture
                if codec_features["profile"] == Profiles.high_quality
                else ParseCodes.low_delay_picture
                if codec_features["profile"] == Profiles.low_delay
                else None  # Unreachable, unless a new profile is added
            )
        ),
        picture_parse=make_picture_parse(
            codec_features, picture, minimum_qindex, minimum_slice_size_scaler
        ),
    )


def make_fragment_parse_data_units(
    codec_features, picture, minimum_qindex=0, minimum_slice_size_scaler=1
):
    r"""
    Create a series of :py:class:`DataUnits
    <vc2_conformance.bitstream.DataUnit>` encoding a (possibly lossily
    compressed) picture.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
        The picture to be encoded. This picture will be compressed using a
        simple VC-2 encoder implementation. It does not necessarily produce the
        most high-quality encodings. If ``pic_num`` is omitted,
        ``picture_number`` fields will be omitted in the output.
    minimum_qindex : int
        Specifies the minimum quantization index to be used. Must be 0 for
        lossless codecs.
    minimum_slice_size_scaler : int
        Specifies the minimum slice_size_scaler to be used for high quality
        pictures. Ignored in low delay mode.

    Returns
    =======
    fragment_data_units : [:py:class:`vc2_conformance.bitstream.DataUnit`, ...]
    """
    assert codec_features["fragment_slice_count"] != 0

    # To avoid repeating ourselves, the fragmented picture is assembled from
    # the parts of a ready-made piture_parse.
    picture_parse = make_picture_parse(
        codec_features, picture, minimum_qindex, minimum_slice_size_scaler
    )

    wavelet_transform = picture_parse["wavelet_transform"]

    transform_parameters = wavelet_transform["transform_parameters"]
    transform_data = wavelet_transform["transform_data"]

    if codec_features["profile"] == Profiles.high_quality:
        parse_code = ParseCodes.high_quality_picture_fragment
        slices_name = "hq_slices"
    elif codec_features["profile"] == Profiles.low_delay:
        parse_code = ParseCodes.low_delay_picture_fragment
        slices_name = "ld_slices"

    fragment_data_units = []

    # Add the first fragment containing the transform parameters
    fragment_data_units.append(
        DataUnit(
            parse_info=ParseInfo(parse_code=parse_code),
            fragment_parse=FragmentParse(
                fragment_header=FragmentHeader(
                    fragment_data_length=0,
                    fragment_slice_count=0,
                ),
                transform_parameters=transform_parameters,
            ),
        )
    )

    # A count of how many slices worth of space remain in the current
    # (slice-containing) fragment. Initially set to zero as we don't have any
    # picture containing fragments.
    fragment_slices_remaining = 0

    # Add the remaining fragments containing the picture slices
    slice_iterator = iter(transform_data[slices_name])
    for sy in range(codec_features["slices_y"]):
        for sx in range(codec_features["slices_x"]):
            # If the current fragment is full, start a new one
            if fragment_slices_remaining == 0:
                fragment_slices_remaining = codec_features["fragment_slice_count"]
                fragment_data_units.append(
                    DataUnit(
                        parse_info=ParseInfo(parse_code=parse_code),
                        fragment_parse=FragmentParse(
                            fragment_header=FragmentHeader(
                                fragment_data_length=0,
                                # NB: Will be incremented in the next step(s)
                                fragment_slice_count=0,
                                fragment_x_offset=sx,
                                fragment_y_offset=sy,
                            ),
                            fragment_data=FragmentData(
                                {
                                    # NB: Will be populated in the next step(s)
                                    slices_name: [],
                                }
                            ),
                        ),
                    )
                )

            # Add the slice to the current fragment
            fragment_parse = fragment_data_units[-1]["fragment_parse"]
            fragment_parse["fragment_header"]["fragment_slice_count"] += 1
            fragment_parse["fragment_data"][slices_name].append(next(slice_iterator))
            fragment_slices_remaining -= 1

    # Populate picture_number field in fragment headers, if one is provided
    if "pic_num" in picture:
        for data_unit in fragment_data_units:
            fragment_header = data_unit["fragment_parse"]["fragment_header"]
            fragment_header["picture_number"] = picture["pic_num"]

    return fragment_data_units


def make_picture_data_units(
    codec_features,
    picture,
    minimum_qindex=0,
    minimum_slice_size_scaler=1,
):
    r"""
    Create a seires of one or more :py:class:`DataUnits
    <vc2_conformance.bitstream.DataUnit>` containing a compressed version of
    the supplied picture.

    When ``codec_features["fragment_slice_count"]`` is 0, a single picture
    parse data unit will be produced. otherwise a series of two or more
    fragment parse data units will be produced.

    A simple wrapper around :py:func:`make_picture_parse_data_unit` and
    :py:func:`make_fragment_parse_data_units`.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    picture : {"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}
        The picture to be encoded. This picture will be compressed using a
        simple VC-2 encoder implementation. It does not necessarily produce the
        most high-quality encodings. If ``pic_num`` is omitted,
        ``picture_number`` fields will be omitted in the output.
    minimum_qindex : int
        Specifies the minimum quantization index to be used. Must be 0 for
        lossless codecs.
    minimum_slice_size_scaler : int
        Specifies the minimum slice_size_scaler to be used for high quality
        pictures. Ignored in low delay mode.

    Returns
    =======
    data_units : [:py:class:`vc2_conformance.bitstream.DataUnit`, ...]
    """
    if codec_features["fragment_slice_count"] == 0:
        return [
            make_picture_parse_data_unit(
                codec_features, picture, minimum_qindex, minimum_slice_size_scaler
            )
        ]
    else:
        return make_fragment_parse_data_units(
            codec_features, picture, minimum_qindex, minimum_slice_size_scaler
        )
