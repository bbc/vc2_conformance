r"""
:py:mod:`vc2_conformance.bitstream.vc2_fixeddicts`: VC-2 Bitstream Structures
=============================================================================

:py:mod:`~vc2_conformance.fixeddict` definitions for holding VC-2 bitstream
values in a hierarchy which strongly mimics the bitstream structure.
"""

from bitarray import bitarray

from vc2_conformance.fixeddict import fixeddict, Entry

from vc2_conformance._string_formatters import (
    Hex,
    Bool,
    Bits,
    Bytes,
    List,
    Object,
    MultilineList,
)

from vc2_conformance.state import State

from vc2_conformance.tables import (
    PARSE_INFO_PREFIX,
    ParseCodes,
    PictureCodingModes,
    BaseVideoFormats,
    Profiles,
    Levels,
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
    
    "PictureHeader",
    "TransformData",
    "WaveletTransform",
    "PictureParse",
    
    "LDSlice",
    "HQSlice",
    
    "FragmentHeader",
    "FragmentData",
    "FragmentParse",
    
    "DataUnit",
    "Sequence",
]


fixeddict_nesting = {}
"""
A lookup ``{fixeddict_type: [fixeddict_type, ...], ...}``.

This lookup enumerates the fixeddicts which may be directly contained by the
fixed dictionary types in this module.

This hierarchical information is used by user-facing tools to allow (e.g.)
recursive selection of a particular dictionary to display.
"""


################################################################################
# parse_info header
################################################################################

ParseInfo = fixeddict(
    "ParseInfo",
    Entry("padding", default_factory=bitarray, formatter=Bits()),
    Entry("parse_info_prefix",
          default=PARSE_INFO_PREFIX,
          friendly_formatter=(lambda prefix:
              "Correct"
              if prefix == PARSE_INFO_PREFIX else
              "INCORRECT"
          ),
          formatter=Hex(8)),
    Entry("parse_code",
          default=ParseCodes.end_of_sequence,
          enum=ParseCodes,
          formatter=Hex(2)),
    Entry("next_parse_offset", default=0),
    Entry("previous_parse_offset", default=0),
)
"""
(10.5.1) Parse info header defined by ``parse_info()``.
"""

################################################################################
# sequence_header header and internal structures
################################################################################

ParseParameters = fixeddict(
    "ParseParameters",
    Entry("major_version", default=3),
    Entry("minor_version", default=0),
    Entry("profile", default=Profiles.high_quality, enum=Profiles),
    Entry("level", default=Levels.unconstrained, enum=Levels),
)
"""
(11.2.1) Sequence header defined by ``parse_parameters()``.
"""

FrameSize = fixeddict(
    "FrameSize",
    Entry("custom_dimensions_flag", default=False, formatter=Bool()),
    Entry("frame_width"),
    Entry("frame_height"),
)
"""
(11.4.3) Frame size override defined by ``frame_size()``.
"""

ColorDiffSamplingFormat = fixeddict(
    "ColorDiffSamplingFormat",
    Entry("custom_color_diff_format_flag", default=False, formatter=Bool()),
    Entry("color_diff_format_index", enum=ColorDifferenceSamplingFormats),
)
"""
(11.4.4) Color-difference sampling override defined by
``color_diff_sampling_format()``.
"""

ScanFormat = fixeddict(
    "ScanFormat",
    Entry("custom_scan_format_flag", default=False, formatter=Bool()),
    Entry("source_sampling", enum=SourceSamplingModes),
)
"""
(11.4.5) Scan format override defined by ``scan_format()``.
"""

FrameRate = fixeddict(
    "FrameRate",
    Entry("custom_frame_rate_flag", default=False, formatter=Bool()),
    Entry("index", enum=PresetFrameRates),
    Entry("frame_rate_numer"),
    Entry("frame_rate_denom"),
)
"""
(11.4.6) Frame-rate override defined by ``frame_rate()``.
"""

PixelAspectRatio = fixeddict(
    "PixelAspectRatio",
    Entry("custom_pixel_aspect_ratio_flag", default=False, formatter=Bool()),
    Entry("index", enum=PresetPixelAspectRatios),
    Entry("pixel_aspect_ratio_numer"),
    Entry("pixel_aspect_ratio_denom"),
)
"""
(11.4.7) Pixel aspect ratio override defined by ``pixel_aspect_ratio()``
(errata: also listed as ``aspect_ratio()`` in some parts of the spec).
"""

CleanArea = fixeddict(
    "CleanArea",
    Entry("custom_clean_area_flag", default=False, formatter=Bool()),
    Entry("clean_width"),
    Entry("clean_height"),
    Entry("left_offset"),
    Entry("top_offset"),
)
"""
(11.4.8) Clean areas override defined by ``clean_area()``.
"""

SignalRange = fixeddict(
    "SignalRange",
    Entry("custom_signal_range_flag", default=False, formatter=Bool()),
    Entry("index", enum=PresetSignalRanges),
    Entry("luma_offset"),
    Entry("luma_excursion"),
    Entry("color_diff_offset"),
    Entry("color_diff_excursion"),
)
"""
(11.4.9) Signal range override defined by ``signal_range()``.
"""

ColorPrimaries = fixeddict(
    "ColorPrimaries",
    Entry("custom_color_primaries_flag", default=False, formatter=Bool()),
    Entry("index", enum=PresetColorPrimaries),
)
"""
(11.4.10.2) Colour primaries override defined by ``color_primaries()``.
"""


ColorMatrix = fixeddict(
    "ColorMatrix",
    Entry("custom_color_matrix_flag", default=False, formatter=Bool()),
    Entry("index", enum=PresetColorMatrices),
)
"""
(11.4.10.3) Colour matrix override defined by ``color_matrix()``.
"""

TransferFunction = fixeddict(
    "TransferFunction",
    Entry("custom_transfer_function_flag", default=False, formatter=Bool()),
    Entry("index", enum=PresetTransferFunctions),
)
"""
(11.4.10.4) Transfer function override defined by ``transfer_function()``.
"""

ColorSpec = fixeddict(
    "ColorSpec",
    Entry("custom_color_spec_flag", default=False, formatter=Bool()),
    Entry("index", enum=PresetColorSpecs),
    Entry("color_primaries"),  # ColorPrimaries
    Entry("color_matrix"),  # ColorMatrix
    Entry("transfer_function"),  # TransferFunction
)
"""
(11.4.10.1) Colour specification override defined by ``color_spec()``.
"""

fixeddict_nesting[ColorSpec] = [ColorPrimaries, ColorMatrix, TransferFunction]

SourceParameters = fixeddict(
    "SourceParameters",
    Entry("frame_size", default_factory=FrameSize),  # FrameSize
    Entry("color_diff_sampling_format",
          default_factory=ColorDiffSamplingFormat),  # ColorDiffSamplingFormat
    Entry("scan_format", default_factory=ScanFormat),  # ScanFormat
    Entry("frame_rate", default_factory=FrameRate),  # FrameRate
    Entry("pixel_aspect_ratio",
          default_factory=PixelAspectRatio),  # PixelAspectRatio
    Entry("clean_area", default_factory=CleanArea),  # CleanArea
    Entry("signal_range", default_factory=SignalRange),  # SignalRange
    Entry("color_spec", default_factory=ColorSpec),  # ColorSpec
)
"""
(11.4.1) Video format overrides defined by ``source_parameters()``.
"""

fixeddict_nesting[SourceParameters] = [
    FrameSize,
    ColorDiffSamplingFormat,
    ScanFormat,
    FrameRate,
    PixelAspectRatio,
    CleanArea,
    SignalRange,
    ColorSpec,
]

SequenceHeader = fixeddict(
    "SequenceHeader",
    Entry("padding", default_factory=bitarray, formatter=Bits()),
    Entry("parse_parameters",
          default_factory=ParseParameters),  # ParseParameters
    Entry("base_video_format",
          default=BaseVideoFormats.custom_format,
          enum=BaseVideoFormats),
    Entry("video_parameters",
          default_factory=SourceParameters),  # SourceParameters
    Entry("picture_coding_mode",
          default=PictureCodingModes.pictures_are_frames,
          enum=PictureCodingModes),
)
"""
(11.1) Sequence header defined by ``sequence_header()``.
"""

fixeddict_nesting[SequenceHeader] = [ParseParameters, SourceParameters]


################################################################################
# auxiliary_data and padding
################################################################################

AuxiliaryData = fixeddict(
    "AuxiliaryData",
    Entry("padding", default_factory=bitarray, formatter=Bits()),
    Entry("bytes", default_factory=bytes, formatter=Bytes()),
)
"""
(10.4.4) Auxiliary data block (as per auxiliary_data()).
"""


Padding = fixeddict(
    "Padding",
    Entry("padding", default_factory=bitarray, formatter=Bits()),
    Entry("bytes", default_factory=bytes, formatter=Bytes()),
)
"""
(10.4.5) Padding data block (as per padding()).
"""


################################################################################
# transform_parameters and associated structures
################################################################################

ExtendedTransformParameters = fixeddict(
    "ExtendedTransformParameters",
    Entry("asym_transform_index_flag", default=False),
    Entry("wavelet_index_ho", enum=WaveletFilters),
    Entry("asym_transform_flag", default=False),
    Entry("dwt_depth_ho"),
)
"""
(12.4.4.1) Extended (horizontal-only) wavelet transform parameters defined by
``extended_transform_parameters()``.
"""

SliceParameters = fixeddict(
    "SliceParameters",
    Entry("slices_x", default=0),
    Entry("slices_y", default=0),
    Entry("slice_bytes_numerator"),
    Entry("slice_bytes_denominator"),
    Entry("slice_prefix_bytes"),
    Entry("slice_size_scaler"),
)
"""
(12.4.5.2) Slice dimension parameters defined by ``slice_parameters()``.
"""

QuantMatrix = fixeddict(
    "QuantMatrix",
    Entry("custom_quant_matrix", default=False),
    Entry("quant_matrix"),  # [int, ...]
)
"""
(12.4.5.3) Custom quantisation matrix override defined by ``quant_matrix()``.
"""

TransformParameters = fixeddict(
    "TransformParameters",
    Entry("wavelet_index",
          default=WaveletFilters.deslauriers_dubuc_9_7,
          enum=WaveletFilters),
    Entry("dwt_depth", default=0),
    Entry("extended_transform_parameters",
          default_factory=ExtendedTransformParameters),  # ExtendedTransformParameters
    Entry("slice_parameters",
          default_factory=SliceParameters),  # SliceParameters
    Entry("quant_matrix", default_factory=QuantMatrix),  # QuantMatrix
)
"""
(12.4.1) Wavelet transform parameters defined by ``transform_parameters()``.
"""

fixeddict_nesting[TransformParameters] = [
    ExtendedTransformParameters,
    SliceParameters,
    QuantMatrix,
]

################################################################################
# Slice related structures
#
# Note that in the VC2 spec, slices are unpacked into a series of 2D arrays
# according to the transform to be performed. By contrast, the structures
# defined below mimic the layout of the transform data in the bitstream.
################################################################################

LDSlice = fixeddict(
    "LDSlice",
    Entry("qindex", default=0),
    
    Entry("slice_y_length", default=0),
    
    # Transform coefficients (in bitstream order)
    Entry("y_transform", default_factory=list, formatter=List()),
    Entry("c_transform", default_factory=list, formatter=List()),
    
    # Unused bits from bounded blocks
    Entry("y_block_padding", default_factory=bitarray, formatter=Bits()),
    Entry("c_block_padding", default_factory=bitarray, formatter=Bits()),
    
    # Computed value: The slice coordinates.
    Entry("_sx"),
    Entry("_sy"),
)
"""
(13.5.3.1) The data associated with a single low-delay slice, defined by
``ld_slice()``.
"""

HQSlice = fixeddict(
    "HQSlice",
    Entry("prefix_bytes", default=b"", formatter=Bytes()),
    
    Entry("qindex", default=0),
    
    Entry("slice_y_length", default=0),
    Entry("slice_c1_length", default=0),
    Entry("slice_c2_length", default=0),
    
    # Transform coefficients (in bitstream order)
    Entry("y_transform", default_factory=list, formatter=List()),
    Entry("c1_transform", default_factory=list, formatter=List()),
    Entry("c2_transform", default_factory=list, formatter=List()),
    
    # Unused bits from bounded blocks
    Entry("y_block_padding", default_factory=bitarray, formatter=Bits()),
    Entry("c1_block_padding", default_factory=bitarray, formatter=Bits()),
    Entry("c2_block_padding", default_factory=bitarray, formatter=Bits()),
    
    # Computed value: The slice coordinates.
    Entry("_sx"),
    Entry("_sy"),
)
"""
(13.5.4) The data associated with a single high-quality slice, defined by
``hq_slice()``.
"""

################################################################################
# picture_parse and associated structures
################################################################################


PictureHeader = fixeddict(
    "PictureHeader",
    Entry("picture_number", default=0),
)
"""
(12.2) Picture header information defined by ``picture_header()``.
"""

TransformData = fixeddict(
    "TransformData",
    Entry("ld_slices", formatter=List(formatter=Object())),  # [LDSlice, ...]
    Entry("hq_slices", formatter=List(formatter=Object())),  # [HQSlice, ...]
    
    # Computed value: A copy of the State dictionary held when processing this
    # transform data. May be used to work out how the deseriallised values
    # correspond to transform components within the slices above.
    Entry("_state", default_factory=State),
)
"""
(13.5.2) Transform coefficient data slices read by ``transform_data()``.
"""

fixeddict_nesting[TransformData] = [LDSlice, HQSlice]

WaveletTransform = fixeddict(
    "WaveletTransform",
    Entry("transform_parameters",
          default_factory=TransformParameters),  # TransformParameters
    Entry("padding", default_factory=bitarray, formatter=Bits()),
    Entry("transform_data", default_factory=TransformData),  # TransformData
)
"""
(12.3) Wavelet parameters and coefficients defined by ``wavelet_transform()``.
"""

fixeddict_nesting[WaveletTransform] = [TransformParameters, TransformData]

PictureParse = fixeddict(
    "PictureParse",
    Entry("padding1", default_factory=bitarray, formatter=Bits()),
    Entry("picture_header", default_factory=PictureHeader),  # PictureHeader
    Entry("padding2", default_factory=bitarray, formatter=Bits()),
    Entry("wavelet_transform",
          default_factory=WaveletTransform),  # WaveletTransform
)
"""
(12.1) A picture data unit defined by ``picture_parse()``
"""

fixeddict_nesting[PictureParse] = [PictureHeader, WaveletTransform]


################################################################################
# fragment_parse and associated structures
################################################################################

FragmentHeader = fixeddict(
    "FragmentHeader",
    Entry("picture_number", default=0),
    Entry("fragment_data_length", default=0),
    Entry("fragment_slice_count", default=0),
    Entry("fragment_x_offset", ),
    Entry("fragment_y_offset", ),
)
"""
(14.2) Fragment header defined by ``fragment_header()``.
"""

FragmentData = fixeddict(
    "FragmentData",
    Entry("ld_slices", formatter=List(formatter=Object())),  # LDSlice
    Entry("hq_slices", formatter=List(formatter=Object())),  # HQSlice
    
    # Computed value: A copy of the State dictionary held when processing this
    # fragment data. May be used to work out how the deseriallised values
    # correspond to transform components within the slices above.
    Entry("_state", default_factory=State),
)
"""
(14.4) Transform coefficient data slices read by ``fragment_data()``.
"""

fixeddict_nesting[FragmentData] = [LDSlice, HQSlice]

FragmentParse = fixeddict(
    "FragmentParse",
    Entry("padding1", default_factory=bitarray, formatter=Bits()),
    Entry("fragment_header",
          default_factory=FragmentHeader),  # FragmentHeader
    Entry("padding2", default_factory=bitarray, formatter=Bits()),
    Entry("transform_parameters"),  # TransformParameters
    Entry("fragment_data"),  # FragmentData
)
"""
(14.1) A fragment data unit defined by ``fragment_parse()`` containing part of a
picture.
"""

fixeddict_nesting[FragmentParse] = [FragmentHeader, TransformParameters, FragmentData]

################################################################################
# Sequences
################################################################################

DataUnit = fixeddict(
    "DataUnit",
    Entry("parse_info", default_factory=ParseInfo),  # ParseInfo
    Entry("sequence_header"),  # SequenceHeader
    Entry("picture_parse"),  # PictureParse
    Entry("fragment_parse"),  # FragmentParse
    Entry("auxiliary_data"),  # AuxiliaryData
    Entry("padding"),  # Padding
)
"""
A data unit (e.g. sequence header or picture) and its associated parse info.
Based on the values read by parse_sequence() (10.4.1) in each iteration.
"""

fixeddict_nesting[DataUnit] = [
    ParseInfo,
    SequenceHeader,
    PictureParse,
    FragmentParse,
    AuxiliaryData,
    Padding,
]

Sequence = fixeddict(
    "Sequence",
    Entry("data_units",
          default_factory=list,
          formatter=MultilineList(heading="")),  # DataUnit
    # Computed value: The State object being populated by the parser.
    Entry("_state", default_factory=State),
)
"""
(10.4.1) A VC-2 sequence.
"""

fixeddict_nesting[Sequence] = [DataUnit]
