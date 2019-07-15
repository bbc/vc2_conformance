"""
:py:mod:`vc2_conformance.bitstream.vc2_autofill`: VC-2 bitstream value auto-fill utilities
==========================================================================================

This module provides auto-fill routines for automatically computing certain
values for the context dictionaries used by the
:py:mod:`vc2_conformance.bitstream.vc2`
:py:mod:`~vc2_conformance.bitstream.serdes` functions.
"""

from copy import deepcopy

from sentinels import Sentinel

from vc2_conformance.tables import (
    PARSE_INFO_HEADER_BYTES,
    ParseCodes,
)

from vc2_conformance.state import State

from vc2_conformance.bitstream.io import BitstreamWriter
from vc2_conformance.bitstream.serdes import Serialiser

from vc2_conformance.bitstream.vc2 import parse_sequence

from vc2_conformance.bitstream.vc2_fixeddicts import (
    vc2_default_values,
    ParseInfo,
    AuxiliaryData,
    Padding,
    PictureParse,
    PictureHeader,
    FragmentParse,
    FragmentHeader,
)


__all__ = [
    "AUTO",
    "vc2_default_values_with_auto",
    "autofill_picture_number",
    "autofill_parse_offsets",
    "autofill_parse_offsets_finalize",
    "autofill_and_serialise_sequence",
]


AUTO = Sentinel("AUTO")
"""
A constant which may be placed in a
:py:mod;`~vc2_conformance.bitstream.vc2_fixeddicts` fixed dictionary field to
indicate that :py:func:`autofill` should automatically compute a value for that
field.
"""

vc2_default_values_with_auto = deepcopy(vc2_default_values)
"""
Like :py:data:`vc2_conformance.bitstreams.vc2_default_values` but with 'AUTO'
set as the default value for all fields which support it.
"""

vc2_default_values_with_auto[ParseInfo]["next_parse_offset"] = AUTO
vc2_default_values_with_auto[ParseInfo]["previous_parse_offset"] = AUTO
vc2_default_values_with_auto[PictureHeader]["picture_number"] = AUTO
vc2_default_values_with_auto[FragmentHeader]["picture_number"] = AUTO


def autofill_picture_number(sequence, initial_picture_number=0):
    """
    Given a :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.Sequence`,
    find all picture_number fields which are absent or contain the
    :py:data:`AUTO` sentinel and automatically fill them with consecutive
    picture numbers.
    """
    last_picture_number = (initial_picture_number - 1) & 0xFFFFFFFF
    
    for data_unit in sequence.get("data_units", []):
        parse_code = data_unit.get("parse_info", {}).get("parse_code")
        
        # Get the current picture/fragment header (in 'header') and determine if
        # the picture number should be incremented in this picture/fragment or
        # not ('increment' is True if an incremented picture number should be
        # used, False otherwise)
        if parse_code in (
            ParseCodes.low_delay_picture,
            ParseCodes.high_quality_picture,
        ):
            picture_parse = data_unit.setdefault("picture_parse", PictureParse())
            header = picture_parse.setdefault("picture_header", PictureHeader())
            increment = True
        elif parse_code in (
            ParseCodes.low_delay_picture_fragment,
            ParseCodes.high_quality_picture_fragment,
        ):
            fragment_parse = data_unit.setdefault("fragment_parse", FragmentParse())
            header = fragment_parse.setdefault("fragment_header", FragmentHeader())
            increment = header.get(
                "fragment_slice_count",
                vc2_default_values_with_auto[FragmentHeader]["fragment_slice_count"]
            ) == 0
        else:
            # Not a picture; move on!
            continue
        
        if header.get("picture_number", AUTO) is AUTO:
            if increment:
                header["picture_number"] = (last_picture_number + 1) & 0xFFFFFFFF
            else:
                header["picture_number"] = last_picture_number
        
        last_picture_number = header["picture_number"]


def autofill_parse_offsets(sequence):
    """
    Given a :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.Sequence`,
    find and fill in all next_parse_offset and previous_parse_offset fields
    which are absent or contain the :py:data:`AUTO` sentinel.
    
    In many (but ont all) cases computing these field values is most
    straight-forwardly done post seriallisation. In these cases, fields in the
    sequence will be autofilled with '0'. These fields should then subsequently
    be ammended by :py:func:`autofill_parse_offsets_finalize`.
    """
    next_parse_offsets_to_autofill = []
    previous_parse_offsets_to_autofill = []
    
    for data_unit_index, data_unit in enumerate(sequence.get("data_units", [])):
        parse_info = data_unit.setdefault("parse_info", ParseInfo())
        parse_code = parse_info.get("parse_code")
        
        if parse_code in (ParseCodes.auxiliary_data, ParseCodes.padding_data):
            # The length of padding and aux. data fields are determined by the
            # next_parse_offset field so these should be auto-fillled based on the
            # length of padding/aux data present.
            if parse_info.get("next_parse_offset", AUTO) is AUTO:
                if parse_code == ParseCodes.auxiliary_data:
                    data = data_unit.get("auxiliary_data", {}).get("bytes",
                        vc2_default_values_with_auto[AuxiliaryData]["bytes"]
                    )
                elif parse_code == ParseCodes.padding_data:
                    data = data_unit.get("padding", {}).get("bytes",
                        vc2_default_values_with_auto[Padding]["bytes"]
                    )
                parse_info["next_parse_offset"] = PARSE_INFO_HEADER_BYTES + len(data)
        
        if parse_info.get("next_parse_offset", AUTO) is AUTO:
            parse_info["next_parse_offset"] = 0
            next_parse_offsets_to_autofill.append(data_unit_index)
        
        if parse_info.get("previous_parse_offset", AUTO) is AUTO:
            parse_info["previous_parse_offset"] = 0
            previous_parse_offsets_to_autofill.append(data_unit_index)
    
    return (next_parse_offsets_to_autofill, previous_parse_offsets_to_autofill)


def autofill_parse_offsets_finalize(
    bitstream_writer,
    sequence,
    next_parse_offsets_to_autofill,
    previous_parse_offsets_to_autofill,
):
    """
    Finalize the autofillling of next and previous parse offsets by directly
    modifying the seriallised bitstream.
    
    Parameters
    ==========
    bitstream_writer : :py:class:`~vc2_conformance.bitstream.BitstreamWriter`
        A :py:class:`~vc2_conformance.bitstream.BitstreamWriter` set up to
        write to the already-serialised bitstream.
    sequence : :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.Sequence`
        The context dictionary used to serialies the bitstream. Since computed
        values added to these dictionaries by the serialisation process, it may
        be necessary to use the dictionary provided by
        :py:attr:`vc2_conformance.bitstream.Serialiser.context`. This is
        because the Serialiser may have replaced some dictionaries during
        serialisation.
    next_parse_offsets_to_autofill, previous_parse_offsets_to_autofill
        The arrays of parse info indices whose next and previous parse offsets
        remain to be auto-filled.
    """
    end_of_sequence_offset = bitstream_writer.tell()
    
    for index in next_parse_offsets_to_autofill:
        if index == len(sequence["data_units"]) - 1:
            next_parse_offset = 0
        else:
            next_parse_offset = (
                sequence["data_units"][index+1]["parse_info"]["_offset"] -
                sequence["data_units"][index]["parse_info"]["_offset"]
            )
        byte_offset = sequence["data_units"][index]["parse_info"]["_offset"]
        bitstream_writer.seek(byte_offset + 4 + 1)  # Seek past prefix and parse code
        bitstream_writer.write_uint_lit(4, next_parse_offset)
        bitstream_writer.flush()
    
    for index in previous_parse_offsets_to_autofill:
        if index == 0:
            previous_parse_offset = 0
        else:
            previous_parse_offset = (
                sequence["data_units"][index]["parse_info"]["_offset"] -
                sequence["data_units"][index-1]["parse_info"]["_offset"]
            )
        byte_offset = sequence["data_units"][index]["parse_info"]["_offset"]
        bitstream_writer.seek(byte_offset + 4 + 1 + 4)  # Seek past prefix, parse code and next offset
        bitstream_writer.write_uint_lit(4, previous_parse_offset)
        bitstream_writer.flush()
    
    bitstream_writer.seek(*end_of_sequence_offset)


def autofill_and_serialise_sequence(file, sequence):
    """
    Given a :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.Sequence` dictionary describing a VC-2 sequence,
    seriallise that into the supplied file.
    
    Parameters
    ==========
    file : file-like object
        A file open for binary writing. The seriallised bitstream will be
        written to this file.
    sequence : :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.Sequence`
        The sequence to be serialised. Unspecified values will be filled in
        from :py:data:`vc2_default_values_with_auto`. Supported fields
        containing :py:class:`AUTO` will be autofilled with suitably computed
        values using:
        
        * :py:func:`autofill_picture_number`
        * :py:func:`autofill_parse_offsets`
        * :py:func:`autofill_parse_offsets_finalize`
    """
    autofill_picture_number(sequence)
    (
        next_parse_offsets_to_autofill,
        previous_parse_offsets_to_autofill,
    ) = autofill_parse_offsets(sequence)
    
    writer = BitstreamWriter(file)
    with Serialiser(writer, sequence, vc2_default_values_with_auto) as serdes:
        parse_sequence(serdes, State())
    writer.flush()
    
    autofill_parse_offsets_finalize(
        writer,
        serdes.context,
        next_parse_offsets_to_autofill,
        previous_parse_offsets_to_autofill,
    )
