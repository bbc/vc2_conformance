"""
The :py:mod:`vc2_conformance.codec_features` module defines the
:py:class:`CodecFeatures` :py:mod:`~vc2_conformance.fixeddict` which is used to
describe codec and video format configurations. These are used to control the
test case generators (:py:mod:`vc2_conformance.test_cases`) and encoder
(:py:mod:`vc2_conformance.encoder`).

.. autofixeddict:: CodecFeatures

The :py:func:`read_codec_features_csv` may be used to read these structures
from a CSV. This functionality is used by the :ref:`vc2-test-case-generator`
script.

.. autofunction:: read_codec_features_csv

.. autoexception:: InvalidCodecFeaturesError

Finally, the following function may be used when determining level-related
restrictions which apply to a set of :py:class:`CodecFeatures`.

.. autofunction:: codec_features_to_trivial_level_constraints

"""

import csv

from itertools import count, islice, product

from string import ascii_uppercase

from functools import partial

from fractions import Fraction

from collections import OrderedDict

from vc2_data_tables import (
    Levels,
    Profiles,
    PictureCodingModes,
    WaveletFilters,
    ColorDifferenceSamplingFormats,
    BaseVideoFormats,
    SourceSamplingModes,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
)

from vc2_conformance.pseudocode.video_parameters import (
    set_source_defaults,
    picture_dimensions,
)

from vc2_conformance.pseudocode.state import State

from vc2_conformance.pseudocode.slice_sizes import slices_have_same_dimensions

from vc2_conformance.fixeddict import fixeddict, Entry


__all__ = [
    "CodecFeatures",
    "InvalidCodecFeaturesError",
    "read_codec_features_csv",
    "codec_features_to_trivial_level_constraints",
]


CodecFeatures = fixeddict(
    "CodecFeatures",
    Entry("name"),
    # (11.2.1)
    Entry("level", enum=Levels),
    Entry("profile", enum=Profiles),
    # (11.1)
    Entry("picture_coding_mode", enum=PictureCodingModes),
    # (11.4)
    Entry("video_parameters"),  # VideoParameters
    # (12.4.1) and (12.4.4.1)
    Entry("wavelet_index", enum=WaveletFilters),
    Entry("wavelet_index_ho", enum=WaveletFilters),
    Entry("dwt_depth"),
    Entry("dwt_depth_ho"),
    # (12.4.5.2)
    Entry("slices_x"),
    Entry("slices_y"),
    # (14)
    Entry("fragment_slice_count"),
    # Bitrate control
    Entry("lossless"),  # Bool
    Entry("picture_bytes"),  # None if lossless, int otherwise
    # (12.4.5.3)
    Entry("quantization_matrix"),
)
"""
A definition of a set of coding features supported by a video codec
implementation. In practice, a particular codec's feature set may be defined by
a collection of these, defining support for several picture formats.

Parameters
==========
name : str
    A unique, human-readable name to identify this collection of features (e.g.
    ``"uhd_over_hd_sdi"``).
level : :py:class:`~vc2_data_tables.Levels`
    The VC-2 level. The user is responsible for choosing settings below which
    actually conform to this level.
profile : :py:class:`~vc2_data_tables.Profiles`
    The VC-2 profile to use.
picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`
    The picture coding mode to use.
video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    The video format to use.
wavelet_index, wavelet_index_ho : :py:class:`~vc2_data_tables.WaveletFilters`
    The wavelet transform to use. For symmetric transforms, both values must be
    equal.
dwt_depth and dwt_depth_ho : int
    The transform depths to use. For symmetric transforms, dwt_depth_ho must be
    zero.
slices_x and slices_y : int
    The number of picture slices, horizontally and vertically.
fragment_slice_count : int
    If fragmented pictures are in use, should be non-zero and contain the
    maximum number of slices to include in each fragment. Otherwise, should be
    zero.
lossless : bool
    If True, lossless variable-bit-rate coding will be used. If false,
    fixed-rate lossy coding is used.
picture_bytes : int or None
    When ``lossless`` is False, this gives the number of bytes per picture to
    use. Slices will be assigned (as close to) the same number of bytes each as
    possible. If ``lossless`` is True, this value should be None.
quantization_matrix : None or {level: {orient: value, ...}, ...}
    None or a hierarchy of dictionaries as constructed by the ``quant_matrix``
    pseudocode function (12.4.5.3). If None, the default quantization matrix
    will be used.
"""


def read_dict_list_csv(csvfile):
    """
    Read a CSV whose first column contains key names and each subsequent column
    describes a dictionary with corresponding values.

    For example::

        a,one,ayy
        b,two,bee
        c,three,see

    Would become::

        [
            {
                "a": "one",
                "b": "two",
                "c": "three",
            },
            {
                "a": "ayy",
                "b": "bee",
                "c": "see",
            },
        ]

    The first column always gives dictionary keys. Rows whose first column is
    empty or contains only a string starting with a ``#`` (hash) character
    are ignored entirely. Leading and trailing whitespace will be stripped.
    """
    out = []
    for row in csv.reader(csvfile):
        # Skip empty rows
        if len(row) == 0:
            continue

        # Skip comment rows or rows with an empty first cell
        key = row[0].strip()
        if not key or key.startswith("#"):
            continue

        # Accumulate values
        for i, value in enumerate(row[1:]):
            if i >= len(out):
                out.append({})
            value = value.strip()
            if value:
                out[i][key] = value.strip()

    return out


def spreadsheet_column_names():
    """
    Generates an infinite sequence of spreadsheet column names (e.g. A, B, ...,
    Y, Z, AA, AB, ...).
    """
    for length in count(1):
        for name in product(ascii_uppercase, repeat=length):
            yield "".join(name)


def parse_int_enum(int_enum_type, value):
    """
    Parse a string containing an :py:class:`~enum.IntEnum` name or integer
    literal into the corresponding type.
    """
    try:
        number = int(value)
    except ValueError:
        for entry in int_enum_type:
            if entry.name == value:
                number = entry
                break
        else:
            raise ValueError(
                "{} is not a valid {}".format(
                    value,
                    int_enum_type.__name__,
                )
            )

    return int_enum_type(number)


def parse_int_at_least(minimum, value):
    """
    Parse a string containing an integer, raising a :py:exc:`ValueError` if the
    value is below the specified threshold.
    """
    value = int(value)
    if value < minimum:
        raise ValueError("{} < {}".format(value, minimum))
    else:
        return value


def parse_bool(value):
    """
    Parse a wide-ish array of CSV-style bool values.
    """
    lower_value = value.lower()

    if lower_value in ("1", "true", "t", "y", "yes"):
        return True
    elif lower_value in ("0", "false", "f", "n", "no"):
        return False
    else:
        raise ValueError("{} is not a valid boolean".format(value))


def parse_quantization_matrix(dwt_depth, dwt_depth_ho, value):
    """
    Parse a quantization matrix, presented as a series of whitespace-separated
    integers. Values are given in ascending order of level and subands are
    ordered as L, LL, H, HL, LH, HH (i.e. bitstream order in (12.4.5.3)).
    """
    values = iter(filter(None, value.split()))

    out = {}

    try:
        if dwt_depth_ho == 0:
            out[0] = {"LL": int(next(values))}
        else:
            out[0] = {"L": int(next(values))}
            for level in range(1, dwt_depth_ho + 1):
                out[level] = {"H": int(next(values))}
        for level in range(dwt_depth_ho + 1, dwt_depth + dwt_depth_ho + 1):
            out[level] = {
                "HL": int(next(values)),
                "LH": int(next(values)),
                "HH": int(next(values)),
            }
    except StopIteration:
        raise ValueError(
            "Expected {} values in quantisation matrix.".format(
                dwt_depth + dwt_depth_ho + 1
            )
        )

    try:
        next(values)
        raise ValueError(
            "Expected {} values in quantisation matrix.".format(
                dwt_depth + dwt_depth_ho + 1
            )
        )
    except StopIteration:
        pass

    return out


class InvalidCodecFeaturesError(ValueError):
    """
    Raised by :py:func:`read_codec_features_csv` encounters a problem with the
    data presented in a codec features listing CSV file.
    """


def read_codec_features_csv(csvfile):
    """
    Read a set of :py:class:`CodecFeatures` from a CSV file in the format
    described by :ref:`codec-features`.

    ..
        If you're reading this, you probably can't click on the reference
        above... It points to the 'Defining codec features' section of
        ``docs/user_guide/generating_test_cases.rst``

    Parameters
    ==========
    csvfile : iterable
        An iterable of lines from a CSV file, e.g. an open :py:class:`file`
        object.

    Returns
    =======
    codec_feature_sets : OrderedDict([(name, :py:class:`CodecFeatures`), ...])

    Raises
    ======
    :py:exc:`InvalidCodecFeaturesError`
        Raised if the provided CSV contains invalid or incomplete data.

        .. note::

            Validation largely extends only to syntactic issues (e.g. invalid
            integer values, 'picture_bytes' being specified for lossless
            formats etc). It does not include validation of 'deeper' issues
            such as too-small picture_bytes values or parameters not being
            permitted by the specified level.
    """
    csv_columns = read_dict_list_csv(csvfile)

    out = OrderedDict()

    for i, column in zip(islice(spreadsheet_column_names(), 1, None), csv_columns):
        if not column:
            continue

        def pop(field_name, parser, *default_):
            """
            Check for the existance of a value in the current column and return
            the native-type version of it. If a third argument, 'default', is
            given, the default value will be returned if the field contains the
            string "default".
            """
            assert len(default_) in (0, 1)
            try:
                value = column.pop(field_name)
                if default_ and value.lower() == "default":
                    return default_[0]
                else:
                    return parser(value)
            except KeyError:
                raise InvalidCodecFeaturesError(
                    "Missing entry for '{}' in '{}' column".format(
                        field_name,
                        name,
                    )
                )
            except ValueError as e:
                raise InvalidCodecFeaturesError(
                    "Invalid entry for '{}' in '{}' column: {} ({})".format(
                        field_name,
                        name,
                        value,
                        e,
                    )
                )

        features = CodecFeatures()

        # Create default names for columns where not provided
        if "name" not in column:
            name = "column_{}".format(i)
        else:
            name = column.pop("name")
        name = name.strip()

        features["name"] = name

        # Check for name uniqueness
        if name in out:
            raise InvalidCodecFeaturesError(
                "Name '{}' used more than once".format(name)
            )

        out[name] = features

        # Parse basic fields
        for field_name, field_type in [
            ("level", partial(parse_int_enum, Levels)),
            ("profile", partial(parse_int_enum, Profiles)),
            ("picture_coding_mode", partial(parse_int_enum, PictureCodingModes)),
            ("wavelet_index", partial(parse_int_enum, WaveletFilters)),
            ("wavelet_index_ho", partial(parse_int_enum, WaveletFilters)),
            ("dwt_depth", partial(parse_int_at_least, 0)),
            ("dwt_depth_ho", partial(parse_int_at_least, 0)),
            ("slices_x", partial(parse_int_at_least, 1)),
            ("slices_y", partial(parse_int_at_least, 1)),
            ("fragment_slice_count", partial(parse_int_at_least, 0)),
            ("lossless", parse_bool),
        ]:
            features[field_name] = pop(field_name, field_type)

        features["video_parameters"] = set_source_defaults(
            pop(
                "base_video_format",
                partial(parse_int_enum, BaseVideoFormats),
            )
        )

        # Parse integer video_parameters fields
        for field_name, field_type in [
            ("frame_width", partial(parse_int_at_least, 1)),
            ("frame_height", partial(parse_int_at_least, 1)),
            (
                "color_diff_format_index",
                partial(parse_int_enum, ColorDifferenceSamplingFormats),
            ),
            ("source_sampling", partial(parse_int_enum, SourceSamplingModes)),
            ("top_field_first", parse_bool),
            ("frame_rate_numer", partial(parse_int_at_least, 1)),
            ("frame_rate_denom", partial(parse_int_at_least, 1)),
            ("pixel_aspect_ratio_numer", partial(parse_int_at_least, 1)),
            ("pixel_aspect_ratio_denom", partial(parse_int_at_least, 1)),
            ("clean_width", partial(parse_int_at_least, 0)),
            ("clean_height", partial(parse_int_at_least, 0)),
            ("left_offset", partial(parse_int_at_least, 0)),
            ("top_offset", partial(parse_int_at_least, 0)),
            ("luma_offset", partial(parse_int_at_least, 0)),
            ("luma_excursion", partial(parse_int_at_least, 1)),
            ("color_diff_offset", partial(parse_int_at_least, 0)),
            ("color_diff_excursion", partial(parse_int_at_least, 1)),
            ("color_primaries_index", partial(parse_int_enum, PresetColorPrimaries)),
            ("color_matrix_index", partial(parse_int_enum, PresetColorMatrices)),
            (
                "transfer_function_index",
                partial(parse_int_enum, PresetTransferFunctions),
            ),
        ]:
            features["video_parameters"][field_name] = pop(
                field_name,
                field_type,
                features["video_parameters"][field_name],
            )

        # Parse picture_bytes option
        if features["lossless"]:
            if "picture_bytes" in column:
                raise InvalidCodecFeaturesError(
                    "Entry provided for 'picture_bytes' when lossless mode "
                    "specified for '{}' column".format(
                        name,
                    )
                )
            features["picture_bytes"] = None
        else:
            features["picture_bytes"] = pop(
                "picture_bytes",
                partial(parse_int_at_least, 1),
            )

        # Parse quantisation matrix
        features["quantization_matrix"] = pop(
            "quantization_matrix",
            partial(
                parse_quantization_matrix,
                features["dwt_depth"],
                features["dwt_depth_ho"],
            ),
            None,
        )

        # Check for extraneous rows
        if column:
            raise InvalidCodecFeaturesError(
                "Unrecognised row(s): {}".format(
                    ", ".join(set(column)),
                )
            )

    return out


def codec_features_to_trivial_level_constraints(codec_features):
    """
    Returns the some of the values a given :py:class:`CodecFeatures` would
    assign in a :py:mod:`~vc2_conformance.level_constraints` table.

    Parameters
    ==========
    codec_features : :py:class:`CodecFeatures`

    Returns
    =======
    constrained_values : {key: concrete_value, ...}
        A partial set of :py:mod:`~vc2_conformance.level_constraints`,
        specifically containing the following keys:

        * level
        * profile
        * picture_coding_mode
        * wavelet_index
        * dwt_depth
        * slices_x
        * slices_y
        * slices_have_same_dimensions
        * custom_quant_matrix

        In addition for the low delay profile only:

        * slice_bytes_numerator
        * slice_bytes_denominator

        In addition for the high quality profile only:

        * slice_prefix_bytes

        .. note::

            In principle, more keys could be determined, however a line in the
            sand is required for what is considered 'simple' to determine and
            what requires re-implementing much of the codec. We draw the line
            at these values since all of them are straight-forward to work out.
    """
    constrained_values = {}

    # Copy across the trivial options
    for key in [
        "level",
        "profile",
        "picture_coding_mode",
        "wavelet_index",
        "dwt_depth",
        "slices_x",
        "slices_y",
    ]:
        constrained_values[key] = codec_features[key]

    # Determine if all slices have the same dimensions
    state = State(
        dwt_depth=codec_features["dwt_depth"],
        dwt_depth_ho=codec_features["dwt_depth_ho"],
        slices_x=codec_features["slices_x"],
        slices_y=codec_features["slices_y"],
        picture_coding_mode=codec_features["picture_coding_mode"],
    )
    picture_dimensions(
        state,
        codec_features["video_parameters"],
    )
    constrained_values["slices_have_same_dimensions"] = slices_have_same_dimensions(
        state
    )

    # Determine slice sizes
    if codec_features["profile"] == Profiles.low_delay:
        num_slices = codec_features["slices_x"] * codec_features["slices_y"]
        slice_bytes = Fraction(codec_features["picture_bytes"] or 0, num_slices)
        constrained_values["slice_bytes_numerator"] = slice_bytes.numerator
        constrained_values["slice_bytes_denominator"] = slice_bytes.denominator
    elif codec_features["profile"] == Profiles.high_quality:
        # NB: At the moment the test case generator cannot generate streams
        # which include prefix bytes so we assume it is zero below... (See
        # `vc2_conformance.encoder.pictures.make_picture_parse`)
        constrained_values["slice_prefix_bytes"] = 0

    # Determine custom quantisation matrix values
    constrained_values["custom_quant_matrix"] = (
        codec_features["quantization_matrix"] is not None
    )

    return constrained_values
