r"""
Structured dictionaries to hold VC-2 bitstream values in a hierarchy which
strongly mimics the bitstream structure.
"""

from bitarray import bitarray

from vc2_conformance.structured_dict import structured_dict, Value

from vc2_conformance._string_formatters import Hex

from vc2_conformance.tables import (
    PARSE_INFO_PREFIX,
    ParseCodes,
    PictureCodingModes,
    BaseVideoFormats,
    Profiles,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PresetFrameRates,
    PresetPixelAspectRatios,
    PresetSignalRanges,
    PresetColorSpecs,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    WaveletFilters,
)

from vc2_conformance.bitstream.vc2.structured_dicts import (
    LDSliceArray,
    HQSliceArray,
)


__all__ = [
    "ParseInfo",
    
    "SequenceHeader",
    "ParseParameters",
    "SourceParameters",
    "FrameSize",
    "ColorDiffSamplingFormat",
    "ScanFormat",
    "FrameRate",
    "PixelAspectRatio",
    "CleanArea",
    "SignalRange",
    "ColorSpec",
    "ColorPrimaries",
    "ColorMatrix",
    "TransferFunction",
    
    "AuxiliaryData",
    "Padding",
    
    "TransformParameters",
    "ExtendedTransformParameters",
    "SliceParameters",
    "QuantMatrix",
    
    "PictureParse",
    "PictureHeader",
    "WaveletTransform",
    
    "FragmentParse",
    "FragmentHeader",
    
    "DataUnit",
    "Sequence",
]


################################################################################
# parse_info header
################################################################################

@structured_dict
class ParseInfo(object):
    """
    (10.5.1) Parse info header defined by ``parse_info()``.
    """
    
    parse_info_prefix = Value(default=PARSE_INFO_PREFIX,
                              friendly_formatter=(lambda prefix:
                                  "Correct"
                                  if prefix == PARSE_INFO_PREFIX else
                                  "INCORRECT"
                              ),
                              formatter=Hex(8))
    parse_code = Value(enum=ParseCodes, formatter=Hex(2))
    next_parse_offset = Value(default=0)
    previous_parse_offset = Value(default=0)

################################################################################
# sequence_header header and internal structures
################################################################################

@structured_dict
class ParseParameters(object):
    """
    (11.2.1) Sequence header defined by ``parse_parameters()``.
    """
    
    major_version = Value(default=3)
    minor_version = Value(default=0)
    profile = Value(default=Profiles.high_quality, enum=Profiles)
    level = Value(default=0)


@structured_dict
class FrameSize(object):
    """
    (11.4.3) Frame size override defined by ``frame_size()``.
    """
    
    custom_dimensions_flag = Value(default=False)
    frame_width = Value()
    frame_height = Value()


@structured_dict
class ColorDiffSamplingFormat(object):
    """
    (11.4.4) Color-difference sampling override defined by
    ``color_diff_sampling_format()``.
    """
    
    custom_color_diff_format_flag = Value(default=False)
    color_diff_format_index = Value(enum=ColorDifferenceSamplingFormats)


@structured_dict
class ScanFormat(object):
    """
    (11.4.5) Scan format override defined by ``scan_format()``.
    """
    
    custom_scan_format_flag = Value(default=False)
    source_sampling = Value(enum=SourceSamplingModes)


@structured_dict
class FrameRate(object):
    """
    (11.4.6) Frame-rate override defined by ``frame_rate()``.
    """
    
    custom_frame_rate_flag = Value(default=False)
    index = Value(enum=PresetFrameRates)
    frame_rate_numer = Value()
    frame_rate_denom = Value()


@structured_dict
class PixelAspectRatio(object):
    """
    (11.4.7) Pixel aspect ratio override defined by ``pixel_aspect_ratio()``
    (errata: also listed as ``aspect_ratio()`` in some parts of the spec).
    """
    
    custom_pixel_aspect_ratio_flag = Value(default=False)
    index = Value(enum=PresetPixelAspectRatios)
    pixel_aspect_ratio_numer = Value()
    pixel_aspect_ratio_denom = Value()


@structured_dict
class CleanArea(object):
    """
    (11.4.8) Clean areas override defined by ``clean_area()``.
    """
    
    custom_clean_area_flag = Value(default=False)
    clean_width = Value()
    clean_height = Value()
    left_offset = Value()
    top_offset = Value()


@structured_dict
class SignalRange(object):
    """
    (11.4.9) Signal range override defined by ``signal_range()``.
    """
    
    custom_signal_range_flag = Value(default=False)
    index = Value(enum=PresetSignalRanges)
    luma_offset = Value()
    luma_excursion = Value()
    color_diff_offset = Value()
    color_diff_excursion = Value()


@structured_dict
class ColorPrimaries(object):
    """
    (11.4.10.2) Colour primaries override defined by ``color_primaries()``.
    """
    
    custom_color_primaries_flag = Value(default=False)
    index = Value(enum=PresetColorPrimaries)


@structured_dict
class ColorMatrix(object):
    """
    (11.4.10.3) Colour matrix override defined by ``color_matrix()``.
    """
    
    custom_color_matrix_flag = Value(default=False)
    index = Value(enum=PresetColorMatrices)


@structured_dict
class TransferFunction(object):
    """
    (11.4.10.4) Transfer function override defined by ``transfer_function()``.
    """
    
    custom_transfer_function_flag = Value(default=False)
    index = Value(enum=PresetTransferFunctions)

@structured_dict
class ColorSpec(object):
    """
    (11.4.10.1) Colour specification override defined by ``color_spec()``.
    """
    
    custom_color_spec_flag = Value(default=False)
    index = Value(enum=PresetColorSpecs)
    color_primaries = Value() # type=ColorPrimaries
    color_matrix = Value() # type=ColorMatrix
    transfer_function = Value() # type=TransferFunction

@structured_dict
class SourceParameters(object):
    """
    (11.4.1) Video format overrides defined by ``source_parameters()``.
    """
    
    frame_size = Value(default_factory=FrameSize)
    color_diff_sampling_format = Value(default_factory=ColorDiffSamplingFormat)
    scan_format = Value(default_factory=ScanFormat)
    frame_rate = Value(default_factory=FrameRate)
    pixel_aspect_ratio = Value(default_factory=PixelAspectRatio)
    clean_area = Value(default_factory=CleanArea)
    signal_range = Value(default_factory=SignalRange)
    color_spec = Value(default_factory=ColorSpec)




@structured_dict
class SequenceHeader(object):
    """
    (11.1) Sequence header defined by ``sequence_header()``.
    """
    
    padding = Value(default_factory=bitarray)
    parse_parameters = Value(default_factory=ParseParameters)
    base_video_format = Value(default=BaseVideoFormats.custom_format,
                              enum=BaseVideoFormats)
    video_parameters = Value(default_factory=SourceParameters)
    picture_coding_mode = Value(default=PictureCodingModes.pictures_are_frames,
                                enum=PictureCodingModes)


################################################################################
# auxiliary_data and padding
################################################################################

@structured_dict
class AuxiliaryData(object):
    """
    (10.4.4) Auxiliary data block (as per auxiliary_data()).
    """
    
    padding = Value(default_factory=bitarray)
    bytes = Value(default_factory=bytes)


@structured_dict
class Padding(object):
    """
    (10.4.5) Padding data block (as per padding()).
    """
    
    padding = Value(default_factory=bitarray)
    bytes = Value(default_factory=bytes)


################################################################################
# transform_parameters and associated structures
################################################################################


@structured_dict
class ExtendedTransformParameters(object):
    """
    (12.4.4.1) Extended (horizontal-only) wavelet transform parameters defined
    by ``extended_transform_parameters()``.
    """
    
    asym_transform_index_flag = Value(default=False)
    wavelet_index_ho = Value(enum=WaveletFilters)
    asym_transform_flag = Value(default=False)
    dwt_depth_ho = Value()


@structured_dict
class SliceParameters(object):
    """
    (12.4.5.2) Slice dimension parameters defined by ``slice_parameters()``.
    """
    
    slices_x = Value(default=1)
    slices_y = Value(default=1)
    
    slice_bytes_numerator = Value()
    slice_bytes_denominator = Value()
    
    slice_prefix_bytes = Value()
    slice_size_scaler = Value()


@structured_dict
class QuantMatrix(object):
    """
    (12.4.5.3) Custom quantisation matrix override defined by ``quant_matrix()``.
    """
    
    custom_quant_matrix = Value(default=False)
    quant_matrix = Value()  # type=[int, ...]

@structured_dict
class TransformParameters(object):
    """
    (12.4.1) Wavelet transform parameters defined by ``transform_parameters()``.
    """
    
    wavelet_index = Value(default=WaveletFilters.deslauriers_dubuc_9_7,
                          enum=WaveletFilters)
    dwt_depth = Value(default=0)
    extended_transform_parameters = Value(default_factory=ExtendedTransformParameters)
    slice_parameters = Value(default_factory=SliceParameters)
    quant_matrix = Value(default_factory=QuantMatrix)


################################################################################
# picture_parse and associated structures
################################################################################


@structured_dict
class PictureHeader(object):
    """
    (12.2) Picture header information defined by ``picture_header()``.
    """
    
    picture_number = Value(default=0)


@structured_dict
class WaveletTransform(object):
    """
    (12.3) Wavelet parameters and coefficients defined by
    ``wavelet_transform()``.
    """
    
    transform_parameters = Value(default_factory=TransformParameters)
    padding = Value(default_factory=bitarray)
    ld_transform_data = Value()  # type=LDSliceArray
    hq_transform_data = Value()  # type=HQSliceArray


@structured_dict
class PictureParse(object):
    """
    (12.1) A picture data unit defined by ``picture_parse()``
    """
    
    padding1 = Value(default_factory=bitarray)
    picture_header = Value(default_factory=PictureHeader)
    padding2 = Value(default_factory=bitarray)
    wavelet_transform = Value(default_factory=WaveletTransform)


################################################################################
# fragment_parse and associated structures
################################################################################

@structured_dict
class FragmentHeader(object):
    """
    (14.2) Fragment header defined by ``fragment_header()``.
    """
    
    picture_number = Value(default=0)
    fragment_data_length = Value(default=0)
    fragment_slice_count = Value(default=0)
    fragment_x_offset = Value()
    fragment_y_offset = Value()

@structured_dict
class FragmentParse(object):
    """
    (14.1) A fragment data unit defined by ``picture_parse()`` containing part
    of a picture.
    """
    
    padding1 = Value(default_factory=bitarray)
    fragment_header = Value(default_factory=FragmentHeader)
    padding2 = Value(default_factory=bitarray)
    transform_parameters = Value()  # type=TransformParameters
    ld_fragment_data = Value()  # type=LDSliceArray
    hq_fragment_data = Value()  # type=HQSliceArray


################################################################################
# Sequences
################################################################################

@structured_dict
class DataUnit(object):
    """
    A data unit (e.g. sequence header or picture) and its associated parse
    info. Based on the values read by parse_sequence() (10.4.1) in each
    iteration.
    """
    
    parse_info = Value(default_factory=ParseInfo)
    
    sequence_header = Value()  # type=SequenceHeader
    picture_parse = Value()  # type=PictureParse
    fragment_parse = Value()  # type=FragmentParse
    auxiliary_data = Value()  # type=AuxiliaryData
    padding = Value()  # type=Padding


@structured_dict
def Sequence(object):
    """
    (10.4.1) A VC-2 sequence.
    """
    
    data_units = Value()  # type=[DataUnit, ...]
