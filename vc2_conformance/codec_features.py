"""
Codec feature definitions
=========================

Tests are generated to target a codecs implementing a particular set of
features. The :py:class:`CodecFeatures`
:py:class:`~vc2_conformance.fixeddict.fixeddict` enumerates specific
combinations of features supported by a codec.

.. autoclass:: CodecFeatures

.. autofunction:: read_codec_features_csv

.. autoexception:: InvalidCodecFeaturesError

"""

import csv

from itertools import count, islice, product

from string import ascii_uppercase

from functools import partial

from numbers import Number

from vc2_conformance.video_parameters import set_source_defaults

from vc2_data_tables import (
    Levels,
    Profiles,
    PictureCodingModes,
    WaveletFilters,
    ColorDifferenceSamplingFormats,
    BaseVideoFormats,
    QUANTISATION_MATRICES,
    SourceSamplingModes,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
)

from vc2_conformance.fixeddict import fixeddict, Entry


__all__ = [
    "CodecFeatures",
    "InvalidCodecFeaturesError",
    "read_codec_features_csv",
]


CodecFeatures = fixeddict(
    "CodecFeatures",
    Entry("name"),
    # (11.2.1)
    Entry("level", enum=Levels),
    Entry("profile", enum=Profiles),
    Entry("major_version"),
    Entry("minor_version"),
    # (11.1)
    Entry("picture_coding_mode", enum=ColorDifferenceSamplingFormats),
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

* ``name``: A unique, human-readable name to identify this collection of
  features (e.g. 'uhd_over_hd_sdi').
* ``level``: The :py:class:`~vc2_data_tables.Levels` giving the codec level
  this feature set shold correspond with.
* ``profile``: The :py:class:`~vc2_data_tables.Profiles` giving the VC-2
  profile to use.
* ``major_version`` and ``minor_version``: The VC-2 major and minor version
  numbers to use.
* ``picture_coding_mode``: The :py:class:`~vc2_data_tables.PictureCodingModes`
  to use.
* ``video_parameters``: The
  :py:class:`~vc2_conformance.video_parameters.VideoParameters`
  describing the video format to use.
* ``wavelet_index`` and ``wavelet_index_ho``: The
  :py:class:`~vc2_data_tables.WaveletFilters` to use.
* ``dwt_depth`` and ``dwt_depth_ho``: The transform depths to use.
* ``slices_x`` and ``slices_y``: The number of picture slices, horizontally and
  vertically.
* ``fragment_slice_count``: If fragmented pictures are in use, should be
  non-zero and contain the maximum number of slices to include in each
  fragment. Otherwise, should be zero.
* ``lossless``: If True, lossless variable-bit-rate coding will be used. If
  false, fixed-rate lossy coding is used.
* ``picture_bytes``: When ``lossless`` is False, this gives the number of bytes
  per picture to use. Slices will be assigned (as close to) the same number of
  bytes each as possible. If True, this value should be None.
* ``quantization_matrix``: None or a hierarchy of dictionaries as constructed
  by the ``quant_matrix`` pseudocode function (12.4.5.3). If None, the default
  quantization matrix will be used.
"""


def read_dict_list_csv(csvfile):
    """
    Read a CSV whose contents consists of a series of dictionaries whose
    columns define dictionaries of values defined by their rows. For example::
    
        a,one,ay
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
                "a": "ay",
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
            raise ValueError("{} is not a valid {}".format(
                value,
                int_enum_type.__name__,
            ))
    
    return int_enum_type(number)


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
    values = filter(None, value.split())
    
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
        raise ValueError("Expected {} values in quantisation matrix.".format(
            dwt_depth + dwt_depth_ho + 1
        ))
    
    try:
        next(values)
        raise ValueError("Expected {} values in quantisation matrix.".format(
            dwt_depth + dwt_depth_ho + 1
        ))
    except StopIteration:
        pass
    
    return out
    
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
        raise ValueError("Expected {} values in quantisation matrix.".format(
            dwt_depth + dwt_depth_ho + 1
        ))
    
    try:
        next(values)
        raise ValueError("Expected {} values in quantisation matrix.".format(
            dwt_depth + dwt_depth_ho + 1
        ))
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
    Read a set of :py:class:`CodecFeatures` dictionaries from a CSV file.
    
    The CSV file must be laid out as illustrated below:
    
        ========================= ===================  ===================
        name                      lossy_mode           lossless_mode
        ========================= ===================  ===================
        # (11.2.1)
        level                     unconstrained        unconstrained
        profile                   high_quality         high_quality
        major_version             3                    3
        minor_version             0                    0
        # (11.1)
        base_video_format         hd1080p_50           hd1080p_50
        picture_coding_mode       pictures_are_frames  pictures_are_frames
        # (11.4.3)
        frame_width               default              default
        frame_height              default              default
        # (11.4.4)
        color_diff_format_index   default              default
        # (11.4.5)
        source_sampling           default              default
        top_field_first           default              default
        # (11.4.6)
        frame_rate_numer          default              default
        frame_rate_denom          default              default
        # (11.4.7)
        pixel_aspect_ratio_numer  default              default
        pixel_aspect_ratio_denom  default              default
        # (11.4.8)
        clean_width               default              default
        clean_height              default              default
        left_offset               default              default
        top_offset                default              default
        # (11.4.9)
        luma_offset               default              default
        luma_excursion            default              default
        color_diff_offset         default              default
        color_diff_excursion      default              default
        # (11.4.10)
        color_primaries_index     default              default
        color_matrix_index        default              default
        transfer_function_index   default              default
        # (12.4.1) and (12.4.4.1)
        wavelet_index             le_gall_5_3          haar_no_shift
        wavelet_index_ho          le_gall_5_3          haar_no_shift
        dwt_depth                 2                    2
        dwt_depth_ho              0                    0
        # (12.4.5.2)
        slices_x                  120                  120
        slices_y                  108                  108
        # (14)
        fragment_slice_count      60                   60
        #
        lossless                  FALSE                TRUE
        picture_bytes             1036800
        # (12.4.5.3)
        quantization_matrix       default              default
        ========================= ===================  ===================
    
    Column B onward contain configurations which a codec claims to support.
    Each row defines the value of a particular codec feature (except empty rows
    or rows starting with a ``#`` which are ignored).
    
    The following rows must be defined:
        
    * ``level`` (int or :py:class:`~vc2_data_tables.Levels` name)
    * ``profile`` (int or :py:class:`~vc2_data_tables.Profiles` name)
    * ``major_version`` (int)
    * ``minor_version`` (int)
    * ``base_video_format`` (int or :py:class:`~vc2_data_tables.BaseVideoFormats` name)
    * ``picture_coding_mode`` (int or :py:class:`~vc2_data_tables.PictureCodingModes` name)
    * ``frame_width`` (int or ``default``)
    * ``frame_height`` (int or ``default``)
    * ``color_diff_format_index`` (int or
      :py:class:`~vc2_data_tables.ColorDifferenceSamplingFormats` name or
      ``default``)
    * ``source_sampling`` (int or
      :py:class:`~vc2_data_tables.SourceSamplingModes` name or
      ``default``)
    * ``top_field_first`` (``TRUE``, ``FALSE`` or ``default``)
    * ``frame_rate_numer`` (int or ``default``)
    * ``frame_rate_denom`` (int or ``default``)
    * ``pixel_aspect_ratio_numer`` (int or ``default``)
    * ``pixel_aspect_ratio_denom`` (int or ``default``)
    * ``clean_width`` (int or ``default``)
    * ``clean_height`` (int or ``default``)
    * ``left_offset`` (int or ``default``)
    * ``top_offset`` (int or ``default``)
    * ``luma_offset`` (int or ``default``)
    * ``luma_excursion`` (int or ``default``)
    * ``color_diff_offset`` (int or ``default``)
    * ``color_diff_excursion`` (int or ``default``)
    * ``color_primaries_index`` (int or
      :py:class:`~vc2_data_tables.PresetColorPrimaries` name or
      ``default``)
    * ``color_matrix_index`` (int or
      :py:class:`~vc2_data_tables.PresetColorMatrices` name or
      ``default``)
    * ``transfer_function_index`` (int or
      :py:class:`~vc2_data_tables.PresetTransferFunctions` name or
      ``default``)
    * ``wavelet_index`` (int or
      :py:class:`~vc2_data_tables.WaveletFilters` name)
    * ``wavelet_index_ho`` (int or
      :py:class:`~vc2_data_tables.WaveletFilters` name)
    * ``dwt_depth`` (int)
    * ``dwt_depth_ho`` (int)
    * ``slices_x`` (int)
    * ``slices_y`` (int)
    * ``fragment_slice_count`` (int)
    * ``lossless`` (``TRUE`` or ``FALSE``)
    * ``picture_bytes`` (int or absent)
    * ``quantization_matrix`` (whitespace separated ints)
    
    The 'name' row may be used to specify a human-readable name for a
    particular configuration.
    
    Parameters related to video formatting may be set to ``default``. In this
    case, the value specified in the ``base_video_format`` row will be used.
    Otherwise, the base video format will be overridden.
    
    The ``base_video_format`` specified is provided purely as a shorthand for
    entering values into this table. The value specified here may not
    correspond to the ``base_video_format`` value which is encoded into
    bitstreams.
    
    The ``fragment_slice_count`` row, non-zero, indicates fragmented pictures
    should be used and gives the maximum number of slices to include in each
    fragment. If the value is zero, fragmented pictures will not be used.
    
    The ``lossless`` row specifies if (variable length) lossless coding should
    be used. If True, the ``picture_bytes`` field must be left empty. If
    ``lossless`` is set to ``FALSE``, fixed-bitrate lossy compression is used
    with ``picture_bytes`` giving the number of bytes to compress each picture
    into. All slices will have the same size (to within 1 byte).
    
    The ``quantization_matrix`` row may be set to ``default`` to specify tha
    the default quantisation matrix for the wavelet is to be used.
    Alternatively, it may be set to a series of ``dwt_depth + dwt_depth_ho +
    1`` whitespace separated integers. These correspond to the quantisation
    matrix values in bitstream order as defined by the ``quant_matrix``
    pseudocode function (12.4.5.3).
    
    Parameters
    ==========
    csvfile : iterable
        An iterable of lines from a CSV file, e.g. an open :py:class:`file`
        object.
    
    Returns
    =======
    codec_feature_sets : [:py:class:`CodecFeatures`, ...]
    
    Raises
    ======
    :py:exc:`InvalidCodecFeaturesError`
        Raised if the provided CSV contains invalid or incomplete data.
    """
    csv_columns = read_dict_list_csv(csvfile)
    
    out = []
    
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
                    "Invalid entry for '{}' in '{}' column: {}".format(
                        field_name,
                        name,
                        value,
                    )
                )
        
        features = CodecFeatures()
        out.append(features)
        
        # Create default names for columns where not provided
        if "name" not in column:
            name = "column_{}".format(i)
        else:
            name = column.pop("name")
        
        features["name"] = name
        
        # Parse basic fields
        for field_name, field_type in [
            ("level", partial(parse_int_enum, Levels)),
            ("profile", partial(parse_int_enum, Profiles)),
            ("major_version", int),
            ("minor_version", int),
            ("picture_coding_mode", partial(parse_int_enum, PictureCodingModes)),
            ("wavelet_index", partial(parse_int_enum, WaveletFilters)),
            ("wavelet_index_ho", partial(parse_int_enum, WaveletFilters)),
            ("dwt_depth", int),
            ("dwt_depth_ho", int),
            ("slices_x", int),
            ("slices_y", int),
            ("fragment_slice_count", int),
            ("lossless", parse_bool),
        ]:
            features[field_name] = pop(field_name, field_type)
        
        features["video_parameters"] = set_source_defaults(pop(
            "base_video_format",
            partial(parse_int_enum, BaseVideoFormats),
        ))
        
        # Parse integer video_parameters fields
        for field_name, field_type in [
            ("frame_width", int),
            ("frame_height", int),
            ("color_diff_format_index", partial(parse_int_enum, ColorDifferenceSamplingFormats)),
            ("source_sampling", partial(parse_int_enum, SourceSamplingModes)),
            ("top_field_first", parse_bool),
            ("frame_rate_numer", int),
            ("frame_rate_denom", int),
            ("pixel_aspect_ratio_numer", int),
            ("pixel_aspect_ratio_denom", int),
            ("clean_width", int),
            ("clean_height", int),
            ("left_offset", int),
            ("top_offset", int),
            ("luma_offset", int),
            ("luma_excursion", int),
            ("color_diff_offset", int),
            ("color_diff_excursion", int),
            ("color_primaries_index", partial(parse_int_enum, PresetColorPrimaries)),
            ("color_matrix_index", partial(parse_int_enum, PresetColorMatrices)),
            ("transfer_function_index", partial(parse_int_enum, PresetTransferFunctions)),
        ]:
            features["video_parameters"][field_name] = pop(
                field_name,
                field_type,
                features["video_parameters"][field_name],
            )
        
        # Data-rate options
        if features["lossless"]:
            if "picture_bytes" in column:
                raise InvalidCodecFeaturesError(
                    "Entry provided for 'picture_bytes' when lossless mode "
                    "specified for '{}' column".format(
                        field_name,
                        name,
                    )
                )
        else:
            features["picture_bytes"] = pop("picture_bytes", int)
        
        # Quantisation matrix
        features["quantization_matrix"] = pop(
            "quantization_matrix",
            partial(
                parse_quantization_matrix,
                features["dwt_depth"],
                features["dwt_depth_ho"],
            ),
            None,
        )
        
        # Check default quantisation matrix available if default specified
        if features["quantization_matrix"] is None:
            if (
                features["wavelet_index"],
                features["wavelet_index_ho"],
                features["dwt_depth"],
                features["dwt_depth_ho"],
            ) not in QUANTISATION_MATRICES:
                raise InvalidCodecFeaturesError(
                    "Default quantisation matrix specified for '{}' column "
                    "but none is defined.".format(
                        field_name,
                        name,
                    )
                )
        
        # Check for extraneous rows
        if column:
            raise InvalidCodecFeaturesError(
                "Unrecognised row(s): {}".format(
                    ", ".join(set(column)),
                )
            )
    
    return out
