"""
The :py:mod:`vc2_conformance.encoder.sequence` module provides routines for
constructing complete VC-2 sequences.

Principally, this module implements the :py:func:`make_sequence` function which
produces :py:class:`vc2_conformance.bitstream.Sequence` objects containing
pictures compressed according to the required codec specifications. This is the
main entry point to the encoder.

.. autofunction:: make_sequence

"""

from functools import partial

from itertools import repeat

from vc2_data_tables import ParseCodes

from vc2_conformance.py2x_compat import zip

from vc2_conformance.level_constraints import LEVEL_SEQUENCE_RESTRICTIONS

from vc2_conformance.bitstream import (
    Sequence,
    DataUnit,
    ParseInfo,
    Padding,
    AuxiliaryData,
)

from vc2_conformance.symbol_re import make_matching_sequence, ImpossibleSequenceError

from vc2_conformance.encoder.exceptions import IncompatibleLevelAndDataUnitError

from vc2_conformance.encoder.sequence_header import make_sequence_header_data_unit

from vc2_conformance.encoder.pictures import make_picture_data_units


__all__ = [
    "make_sequence",
]


def make_end_of_sequence_data_unit():
    return DataUnit(
        parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence),
    )


def make_auxiliary_data_unit():
    return DataUnit(
        parse_info=ParseInfo(parse_code=ParseCodes.auxiliary_data),
        auxiliary_data=AuxiliaryData(),
    )


def make_padding_data_unit():
    return DataUnit(
        parse_info=ParseInfo(parse_code=ParseCodes.padding_data),
        padding=Padding(),
    )


def make_sequence(codec_features, pictures, *data_unit_patterns, **kwargs):
    """
    Generate a complete VC-2 bitstream based on the provided set of codec
    features and containing compressed versions of the specified set of
    pictures.

    This function also takes a small number of additional parameters which
    override certain encoder behaviours as may be required by some test case
    generators.

    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    pictures : [{"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}, ...]
        The pictures to be encoded in the bitstream. If ``pic_num`` is omitted,
        ``picture_number`` fields will also be omitted in the output (and left
        for, e.g.
        :py:func:`vc2_conformance.bitstream.autofill_and_serialise_stream` to
        assign). See :py:mod:`vc2_conformance.encoder.pictures` for details of
        the picture compression process.
    *data_unit_patterns : str
        Force the generated sequence of data units to match a specified regular
        expression. For example, ``"(. padding_data)+ end_of_sequence"`` will
        force a padding data unit to be inserted between each data unit. See
        the :py:mod:`vc2_conformance.symbol_re` module for details of the
        regular expression format.

        A sequence of data units matching all specified patterns while meeting
        the requirements of the VC-2 standard will be generated. If this is not
        possible,
        :py:exc:`vc2_conformance.encoder.exceptions.IncompatibleLevelAndDataUnitError`
        will be raised.
    minimum_qindex : int or [int, ...]
        Keyword-only argument. Default 0. Specifies the minimum quantization
        index to be used for all picture slices. If a list is provided,
        specifies the minimum quantization index separately for each picture.

        This option may be used by test cases where a particular (very high)
        quantization index must be used. Note that the encoder may still use
        larger quantization indices if a set of transform coefficients still do
        not fit into a slice so the caller must check that this has not
        occurred.

        Must be 0 for lossless coding modes.
    minimum_slice_size_scaler : int
        Keyword-only argument. Default 1. Specifies the minimum slice size
        scaler to use.

        For almost all sensible coding modes, the ``slice_size_scaler`` can be
        set to '1' -- and this encoder will do so if possible. To facilitate
        the production of test cases verifying higher values are supported,
        this option may be used to pick a larger value. The encoder may still
        use larger ``slice_size_scaler`` values if this is necessary, however.

        Only has an effect on high quality profile coding modes, will be
        ignored for the low delay profile modes.

    Returns
    =======
    sequence : :py:class:`vc2_conformance.bitstream.Sequence`
        The VC-2 bitstream sequence. This may be serialised by encapsulating
        it in a :py:class:`vc2_conformance.bitstream.Stream` and serialising it
        with
        :py:func:`~vc2_conformance.bitstream.vc2_autofill.autofill_and_serialise_stream`.

    Raises
    ======
    UnsatisfiableCodecFeaturesError
        Raised if a sequence could not be generated according to the
        requirements given.
    """
    minimum_qindices = kwargs.pop("minimum_qindex", 0)
    minimum_slice_size_scaler = kwargs.pop("minimum_slice_size_scaler", 1)
    assert not kwargs, "Unexpected arguments: {}".format(kwargs)

    if not isinstance(minimum_qindices, list):
        minimum_qindices = repeat(minimum_qindices)

    pictures_only_sequence = Sequence(data_units=[])
    for picture, minimum_qindex in zip(pictures, minimum_qindices):
        pictures_only_sequence["data_units"].extend(
            make_picture_data_units(
                codec_features,
                picture,
                minimum_qindex,
                minimum_slice_size_scaler,
            )
        )

    # Fill in all other required bitstream data units
    picture_only_data_unit_names = [
        data_unit["parse_info"]["parse_code"].name
        for data_unit in pictures_only_sequence["data_units"]
    ]
    try:
        required_data_unit_names = make_matching_sequence(
            picture_only_data_unit_names,
            # (10.4.1) Sequences start with a sequence header and end with an end
            # of sequence data unit
            "sequence_header .* end_of_sequence",
            # Certain levels may provide additional constraints
            LEVEL_SEQUENCE_RESTRICTIONS[
                codec_features["level"]
            ].sequence_restriction_regex,
            *data_unit_patterns,
            symbol_priority=["padding_data", "sequence_header"]
        )
    except ImpossibleSequenceError:
        raise IncompatibleLevelAndDataUnitError(codec_features)

    # Functions for producing the necessary data units
    #
    # {data_unit_name: fn() -> DataUnit, ...}
    data_unit_makers = {
        "sequence_header": partial(make_sequence_header_data_unit, codec_features),
        "end_of_sequence": make_end_of_sequence_data_unit,
        "auxiliary_data": make_auxiliary_data_unit,
        "padding_data": make_padding_data_unit,
    }
    if pictures_only_sequence["data_units"]:
        picture_parse_code = pictures_only_sequence["data_units"][0]["parse_info"][
            "parse_code"
        ]
        data_unit_makers[picture_parse_code.name] = partial(
            pictures_only_sequence["data_units"].pop,
            0,
        )

    return Sequence(
        data_units=[
            data_unit_makers[data_unit_name]()
            for data_unit_name in required_data_unit_names
        ]
    )
