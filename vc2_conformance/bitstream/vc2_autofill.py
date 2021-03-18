"""
The :py:mod:`vc2_conformance.bitstream.vc2_autofill` module provides auto-fill
routines for automatically computing certain values for the context
dictionaries used by the :py:mod:`vc2_conformance.bitstream.vc2`
:py:mod:`~vc2_conformance.bitstream.serdes` functions. These values include the
picture number and parse offset fields which can't default to a simple fixed
value.

In the common case, the :py:func:`autofill_and_serialise_stream` function may
be used to serialise a complete :py:class:`~vc2_conformance.bitstream.Stream`,
with sensible defaults provided for all fields (including picture numbers and
next/previous parse offsets).

.. autofunction:: autofill_and_serialise_stream

Autofill value routines
-----------------------

The following functions implement autofill routines for specific bitstream
values.

.. autofunction:: autofill_picture_number

.. autofunction:: autofill_major_version

.. autofunction:: autofill_parse_offsets

.. autofunction:: autofill_parse_offsets_finalize


Autofill value dictionary
-------------------------

.. autodata:: vc2_default_values_with_auto
    :annotation:

.. autodata:: AUTO
    :annotation:

"""

from copy import deepcopy

from sentinels import Sentinel

from vc2_data_tables import (
    PARSE_INFO_HEADER_BYTES,
    ParseCodes,
)

from vc2_conformance.version_constraints import (
    MINIMUM_MAJOR_VERSION,
    preset_frame_rate_version_implication,
    preset_signal_range_version_implication,
    preset_color_spec_version_implication,
    preset_color_primaries_version_implication,
    preset_color_matrix_version_implication,
    preset_transfer_function_version_implication,
    wavelet_transform_version_implication,
    parse_code_version_implication,
    profile_version_implication,
)

from vc2_conformance.pseudocode.state import State

from vc2_conformance.bitstream.io import BitstreamWriter
from vc2_conformance.bitstream.serdes import Serialiser

from vc2_conformance.bitstream.vc2 import parse_stream

from vc2_conformance.bitstream.vc2_fixeddicts import (
    vc2_default_values,
    ParseInfo,
    AuxiliaryData,
    Padding,
    ParseParameters,
    PictureParse,
    PictureHeader,
    FragmentParse,
    FragmentHeader,
    FrameRate,
    SignalRange,
    ColorSpec,
    ColorPrimaries,
    ColorMatrix,
    TransferFunction,
    TransformParameters,
    ExtendedTransformParameters,
)

from vc2_conformance.pseudocode.parse_code_functions import (
    is_picture,
    is_fragment,
)


__all__ = [
    "AUTO",
    "vc2_default_values_with_auto",
    "autofill_picture_number",
    "autofill_major_version",
    "autofill_parse_offsets",
    "autofill_parse_offsets_finalize",
    "autofill_and_serialise_stream",
]


AUTO = Sentinel("AUTO")
"""
A constant which may be placed in a
:py:mod:`~vc2_conformance.bitstream.vc2_fixeddicts` fixed dictionary field to
indicate that the various ``autofill_*`` functions in this module should
automatically compute a value for that field.
"""

vc2_default_values_with_auto = deepcopy(vc2_default_values)
"""
Like :py:data:`vc2_conformance.bitstreams.vc2_default_values` but with
:py:data:`AUTO` set as the default value for all fields which support it.
"""

vc2_default_values_with_auto[ParseInfo]["next_parse_offset"] = AUTO
vc2_default_values_with_auto[ParseInfo]["previous_parse_offset"] = AUTO
vc2_default_values_with_auto[ParseParameters]["major_version"] = AUTO
vc2_default_values_with_auto[PictureHeader]["picture_number"] = AUTO
vc2_default_values_with_auto[FragmentHeader]["picture_number"] = AUTO


def get_auto(d, field_name, dtype):
    """
    For internal use. Get a value from the dictionary d, falling back on the
    :py:data:`vc2_default_values_with_auto` default value.

    Parameters
    ==========
    d : dict
    field_name: str
    dtype: :py:class:~`vc2_conformance.bitstream.vc2_fixeddicts` instance
    """
    if field_name in d:
        return d[field_name]
    else:
        return vc2_default_values_with_auto[dtype][field_name]


def get_transform_parameters(data_unit):
    """
    For internal use. Given a
    :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.DataUnit`, if the data
    unit contains a picture or the first fragment of a fragmented picture,
    returns the
    :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.TransformParameters`,
    creating an empty one if it is not defined.  Otherwise returns None.
    """
    parse_code = get_auto(data_unit.get("parse_info", {}), "parse_code", ParseInfo)
    if is_picture(State(parse_code=parse_code)):
        return (
            data_unit.setdefault("picture_parse", {})
            .setdefault("wavelet_transform", {})
            .setdefault("transform_parameters", {})
        )
    elif (
        is_fragment(State(parse_code=parse_code))
        and get_auto(
            data_unit.get("fragment_parse", {}).get("fragment_header", {}),
            "fragment_slice_count",
            FragmentHeader,
        )
        == 0
    ):
        return data_unit.setdefault("fragment_parse", {}).setdefault(
            "transform_parameters", {}
        )
    else:
        return None


def autofill_picture_number(stream, initial_picture_number=0):
    """
    Given a :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.Stream`,
    find all picture_number fields which are absent or contain the
    :py:data:`AUTO` sentinel and automatically fill them with consecutive
    picture numbers. Numbering is restarted for each sequence.
    """
    for sequence in stream.get("sequences", []):
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
                increment = (
                    header.get(
                        "fragment_slice_count",
                        vc2_default_values_with_auto[FragmentHeader][
                            "fragment_slice_count"
                        ],
                    )
                    == 0
                )
            else:
                # Not a picture; move on!
                continue

            if header.get("picture_number", AUTO) is AUTO:
                if increment:
                    header["picture_number"] = (last_picture_number + 1) & 0xFFFFFFFF
                else:
                    header["picture_number"] = last_picture_number

            last_picture_number = header["picture_number"]


def autofill_major_version(stream):
    """
    Given a :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.Stream`, find
    all ``major_version`` fields which are set to the :py:data:`AUTO` sentinel
    and automatically set them to the appropriate version number for the
    features used by this stream.

    As a side effect, this function will automatically remove the
    :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.ExtendedTransformParameters`
    field whenever it appears in
    :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.TransformParameters`
    if the major_version evaluates to less than 3. This change will only be
    made when ``major_version`` was set to AUTO in a proceeding sequence
    header, if the field was explicitly set to a particular value, no changes
    will be made to any transform parameters dicts which follow.
    """
    for sequence in stream.get("sequences", []):
        # Compute the major version number to be used according to (11.2.2)
        major_version = MINIMUM_MAJOR_VERSION
        for data_unit in sequence.get("data_units", []):
            parse_code = get_auto(
                data_unit.get("parse_info", {}), "parse_code", ParseInfo
            )

            # Check parse code version requirements
            major_version = max(
                major_version, parse_code_version_implication(parse_code)
            )

            if parse_code == ParseCodes.sequence_header:
                sequence_header = data_unit.get("sequence_header", {})

                # Check profile version requirements
                parse_parameters = sequence_header.get("parse_parameters", {})
                profile = get_auto(parse_parameters, "profile", ParseParameters)
                major_version = max(major_version, profile_version_implication(profile))

                # Check video parameter preset version parameters

                source_parameters = sequence_header.get("video_parameters", {})

                frame_rate = source_parameters.get("frame_rate", {})
                if get_auto(frame_rate, "custom_frame_rate_flag", FrameRate):
                    index = get_auto(frame_rate, "index", FrameRate)
                    major_version = max(
                        major_version, preset_frame_rate_version_implication(index)
                    )

                signal_range = source_parameters.get("signal_range", {})
                if get_auto(signal_range, "custom_signal_range_flag", SignalRange):
                    index = get_auto(signal_range, "index", SignalRange)
                    major_version = max(
                        major_version, preset_signal_range_version_implication(index)
                    )

                color_spec = source_parameters.get("color_spec", {})
                if get_auto(color_spec, "custom_color_spec_flag", ColorSpec):
                    index = get_auto(color_spec, "index", ColorSpec)
                    major_version = max(
                        major_version, preset_color_spec_version_implication(index)
                    )

                    if index == 0:
                        color_primaries = color_spec.get("color_primaries", {})
                        if get_auto(
                            color_primaries,
                            "custom_color_primaries_flag",
                            ColorPrimaries,
                        ):
                            index = get_auto(color_primaries, "index", ColorPrimaries)
                            major_version = max(
                                major_version,
                                preset_color_primaries_version_implication(index),
                            )

                        color_matrix = color_spec.get("color_matrix", {})
                        if get_auto(
                            color_matrix, "custom_color_matrix_flag", ColorMatrix
                        ):
                            index = get_auto(color_matrix, "index", ColorMatrix)
                            major_version = max(
                                major_version,
                                preset_color_matrix_version_implication(index),
                            )

                        transfer_function = color_spec.get("transfer_function", {})
                        if get_auto(
                            transfer_function,
                            "custom_transfer_function_flag",
                            TransferFunction,
                        ):
                            index = get_auto(
                                transfer_function, "index", TransferFunction
                            )
                            major_version = max(
                                major_version,
                                preset_transfer_function_version_implication(index),
                            )
            else:
                # Check wavelet symmetry version parameters
                tp = get_transform_parameters(data_unit)
                if tp is not None:
                    etp = tp.get("extended_transform_parameters", {})

                    wavelet_index = get_auto(tp, "wavelet_index", TransformParameters)

                    wavelet_index_ho = wavelet_index
                    if get_auto(
                        etp, "asym_transform_index_flag", ExtendedTransformParameters
                    ):
                        wavelet_index_ho = get_auto(
                            etp, "wavelet_index_ho", ExtendedTransformParameters
                        )

                    dwt_depth_ho = 0
                    if get_auto(
                        etp, "asym_transform_flag", ExtendedTransformParameters
                    ):
                        dwt_depth_ho = get_auto(
                            etp, "dwt_depth_ho", ExtendedTransformParameters
                        )

                    major_version = max(
                        major_version,
                        wavelet_transform_version_implication(
                            wavelet_index, wavelet_index_ho, dwt_depth_ho
                        ),
                    )

        # Modify sequence headers to include the correct version number,
        # additionally, remove ExtendedTransformParameters where defined when
        # AUTO has been used. Where AUTO has been used,
        # ExtendedTransformParameters can be safely removed when major_version
        # is not 3 (since a symmetric transform must have been applied). When
        # AUTO has not been used, we leave it up to the user to make the
        # version and ETP existance match up.
        auto_used = False
        for data_unit in sequence.get("data_units", []):
            parse_code = get_auto(
                data_unit.get("parse_info", {}), "parse_code", ParseInfo
            )
            if parse_code == ParseCodes.sequence_header:
                # Case: Auto-set version number if required
                sequence_header = data_unit.setdefault("sequence_header", {})
                parse_parameters = sequence_header.setdefault("parse_parameters", {})
                if get_auto(parse_parameters, "major_version", ParseParameters) is AUTO:
                    parse_parameters["major_version"] = major_version
                    auto_used = True
                else:
                    auto_used = False
            else:
                tp = get_transform_parameters(data_unit)
                if tp is not None and auto_used:
                    # Case: Remove ExtendedTransformParameters if required
                    if major_version < 3 and "extended_transform_parameters" in tp:
                        del tp["extended_transform_parameters"]


def autofill_parse_offsets(stream):
    """
    Given a :py:class:`~vc2_conformance.bitstream.Stream`,
    find and fill in all next_parse_offset and previous_parse_offset fields
    which are absent or contain the :py:data:`AUTO` sentinel.

    In many (but not all) cases computing these field values is most
    straight-forwardly done post serialisation. In these cases, fields in the
    stream will be autofilled with '0'. These fields should then subsequently
    be ammended by :py:func:`autofill_parse_offsets_finalize`.
    """
    next_parse_offsets_to_autofill = []
    previous_parse_offsets_to_autofill = []

    for sequence_index, sequence in enumerate(stream.get("sequences", [])):
        for data_unit_index, data_unit in enumerate(sequence.get("data_units", [])):
            parse_info = data_unit.setdefault("parse_info", ParseInfo())
            parse_code = parse_info.get("parse_code")

            if parse_code in (ParseCodes.auxiliary_data, ParseCodes.padding_data):
                # The length of padding and aux. data fields are determined by the
                # next_parse_offset field so these should be auto-fillled based on the
                # length of padding/aux data present.
                if parse_info.get("next_parse_offset", AUTO) is AUTO:
                    if parse_code == ParseCodes.auxiliary_data:
                        data = data_unit.get("auxiliary_data", {}).get(
                            "bytes",
                            vc2_default_values_with_auto[AuxiliaryData]["bytes"],
                        )
                    elif parse_code == ParseCodes.padding_data:
                        data = data_unit.get("padding", {}).get(
                            "bytes", vc2_default_values_with_auto[Padding]["bytes"]
                        )
                    parse_info["next_parse_offset"] = PARSE_INFO_HEADER_BYTES + len(
                        data
                    )

            if parse_info.get("next_parse_offset", AUTO) is AUTO:
                parse_info["next_parse_offset"] = 0
                next_parse_offsets_to_autofill.append((sequence_index, data_unit_index))

            if parse_info.get("previous_parse_offset", AUTO) is AUTO:
                parse_info["previous_parse_offset"] = 0
                previous_parse_offsets_to_autofill.append(
                    (sequence_index, data_unit_index)
                )

    return (next_parse_offsets_to_autofill, previous_parse_offsets_to_autofill)


def autofill_parse_offsets_finalize(
    bitstream_writer,
    stream,
    next_parse_offsets_to_autofill,
    previous_parse_offsets_to_autofill,
):
    """
    Finalize the autofillling of next and previous parse offsets by directly
    modifying the serialised bitstream.

    Parameters
    ==========
    bitstream_writer : :py:class:`~vc2_conformance.bitstream.io.BitstreamWriter`
        A :py:class:`~vc2_conformance.bitstream.io.BitstreamWriter` set up to
        write to the already-serialised bitstream.
    stream : :py:class:`~vc2_conformance.bitstream.Stream`
        The context dictionary used to serialies the bitstream. Since computed
        values added to these dictionaries by the serialisation process, it may
        be necessary to use the dictionary provided by
        :py:attr:`vc2_conformance.bitstream.Serialiser.context`, rather than
        the one passed into the Serialiser. This is because the Serialiser may
        have replaced some dictionaries during serialisation.
    next_parse_offsets_to_autofill, previous_parse_offsets_to_autofill
        The arrays of parse info indices whose next and previous parse offsets
        remain to be auto-filled.
    """
    end_of_sequence_offset = bitstream_writer.tell()

    for sequence_index, data_unit_index in next_parse_offsets_to_autofill:
        sequence = stream["sequences"][sequence_index]

        if data_unit_index == len(sequence["data_units"]) - 1:
            next_parse_offset = 0
        else:
            next_parse_offset = (
                sequence["data_units"][data_unit_index + 1]["parse_info"]["_offset"]
                - sequence["data_units"][data_unit_index]["parse_info"]["_offset"]
            )
        byte_offset = sequence["data_units"][data_unit_index]["parse_info"]["_offset"]
        bitstream_writer.seek(byte_offset + 4 + 1)  # Seek past prefix and parse code
        bitstream_writer.write_uint_lit(4, next_parse_offset)
        bitstream_writer.flush()

    for sequence_index, data_unit_index in previous_parse_offsets_to_autofill:
        sequence = stream["sequences"][sequence_index]

        if data_unit_index == 0:
            previous_parse_offset = 0
        else:
            previous_parse_offset = (
                sequence["data_units"][data_unit_index]["parse_info"]["_offset"]
                - sequence["data_units"][data_unit_index - 1]["parse_info"]["_offset"]
            )
        byte_offset = sequence["data_units"][data_unit_index]["parse_info"]["_offset"]
        bitstream_writer.seek(
            byte_offset + 4 + 1 + 4
        )  # Seek past prefix, parse code and next offset
        bitstream_writer.write_uint_lit(4, previous_parse_offset)
        bitstream_writer.flush()

    bitstream_writer.seek(*end_of_sequence_offset)


def autofill_and_serialise_stream(file, stream):
    """
    Given a :py:class:`~vc2_conformance.bitstream.vc2_fixeddicts.Stream`
    dictionary describing a VC-2 stream, serialise that into the supplied
    file.

    Parameters
    ==========
    file : file-like object
        A file open for binary writing. The serialised bitstream will be
        written to this file.
    stream : :py:class:`~vc2_conformance.Stream`
        The stream to be serialised. Unspecified values will be auto-filled if
        possible. See :ref:`bitstream-fixeddicts` for the default auto-fill
        values.

        .. note::

            Internally, auto-fill values are taken from
            :py:data:`vc2_default_values_with_auto`.

            Supported fields containing the special value :py:class:`AUTO` will
            be autofilled with suitably computed values. Specifically:

            * Picture numbers will set to incrementing values (starting at 0,
              or continuing from the value used by the previous picture) by
              :py:func:`autofill_picture_number`.
            * The ``major_version`` field will be populated by
              :py:func:`autofill_major_version` and, if appropriate, extended
              transform parameters fields will be removed.
            * Next and previous parse offsets will be calculated automatically
              by
              :py:func:`autofill_parse_offsets`
              and
              :py:func:`autofill_parse_offsets_finalize`.
    """
    autofill_picture_number(stream)
    autofill_major_version(stream)
    (
        next_parse_offsets_to_autofill,
        previous_parse_offsets_to_autofill,
    ) = autofill_parse_offsets(stream)

    writer = BitstreamWriter(file)
    with Serialiser(writer, stream, vc2_default_values_with_auto) as serdes:
        parse_stream(serdes, State())
    writer.flush()

    autofill_parse_offsets_finalize(
        writer,
        serdes.context,
        next_parse_offsets_to_autofill,
        previous_parse_offsets_to_autofill,
    )
