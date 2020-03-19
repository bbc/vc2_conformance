"""
Generate complete VC-2 sequences
================================

This module provides the :py:func:`make_sequence` function which produces
:py:class:`vc2_conformance.bitstream.Sequence` objects containing pictures
compressed according to the required codec specifications.

.. autofunction:: make_sequence

"""

from functools import partial

from vc2_data_tables import ParseCodes

from vc2_conformance.level_constraints import (
    LEVEL_SEQUENCE_RESTRICTIONS,
)

from vc2_conformance.bitstream import (
    Sequence,
    DataUnit,
    ParseInfo,
    Padding,
    AuxiliaryData,
)

from vc2_conformance.symbol_re import make_matching_sequence

from vc2_conformance.encoder.sequence_header import (
    make_sequence_header_data_unit,
)

from vc2_conformance.encoder.pictures import (
    make_picture_data_units,
)


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
    features and encoding the specified set of pictures.
    
    Parameters
    ==========
    codec_features : :py:class:`~vc2_conformance.codec_features.CodecFeatures`
    pictures : [{"Y": [[s, ...], ...], "C1": ..., "C2": ..., "pic_num": int}, ...]
        The pictures to be encoded in the bitstream. If ``pic_num`` is omitted,
        ``picture_number`` fields will be omitted in the output.
        See :py:mod:`vc2_conformance.encoder.pictures` for details of the
        picture compression process.
    *data_unit_patterns : str
        Any additional arguments will be interpreted as
        :py:mod:`vc2_conformance.symbol_re` regular expressions which control
        the data units produced in the stream. This may be used to cause
        additional data units (e.g. padding) to be inserted into the stream.
    minimum_qindex : int
        Keyword-only argument. Default 0. Specifies the minimum quantization
        index to be used. Must be 0 for lossless codecs.
    
    Returns
    =======
    sequence : :py:class:`vc2_conformance.bitstream.Sequence`
        The VC-2 bitstream sequence, ready for serialization using
        :py:func:`~vc2_conformance.bitstream.vc2_autofill.autofill_and_serialise_sequence`.
    """
    minimum_qindex = kwargs.pop("minimum_qindex", 0)
    assert not kwargs, "Unexpected arguments: {}".format(kwargs)
    
    pictures_only_sequence = Sequence(data_units=[])
    for picture in pictures:
        pictures_only_sequence["data_units"].extend(
            make_picture_data_units(codec_features, picture, minimum_qindex)
        )
    
    # Fill in all other required bitstream data units
    picture_only_data_unit_names = [
        data_unit["parse_info"]["parse_code"].name
        for data_unit in pictures_only_sequence["data_units"]
    ]
    required_data_unit_names = make_matching_sequence(
        picture_only_data_unit_names,
        # (10.4.1) Sequences start with a sequence header and end with an end
        # of sequence data unit
        "sequence_header .* end_of_sequence",
        # Certain levels may provide additional constraints
        LEVEL_SEQUENCE_RESTRICTIONS[codec_features["level"]].sequence_restriction_regex,
        *data_unit_patterns,
        symbol_priority=[
            "padding_data",
            "sequence_header",
        ]
    )
    
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
        picture_parse_code = pictures_only_sequence["data_units"][0]["parse_info"]["parse_code"]
        data_unit_makers[picture_parse_code.name] = partial(
            pictures_only_sequence["data_units"].pop,
            0,
        )
    
    return Sequence(data_units=[
        data_unit_makers[data_unit_name]()
        for data_unit_name in required_data_unit_names
    ])
