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
    "vc2_fixeddict_nesting",
    "vc2_default_values",
    
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


vc2_fixeddict_nesting = {}
"""
A lookup ``{fixeddict_type: [fixeddict_type, ...], ...}``.

This lookup enumerates the fixeddicts which may be directly contained by the
fixed dictionary types in this module.

This hierarchical information is used by user-facing tools to allow (e.g.)
recursive selection of a particular dictionary to display.
"""


vc2_default_values = {}
"""
A lookup ``{fixeddict_type: {key: default_value, ...}, ...}``

For each fixeddict type below, provides a sensible default value for each key.
The defaults are generally chosen to produce a minimal, but valid, bitstream.

Where a particular fixeddict entry is a list, the value listed in this lookup
should be treated as the default value to use for list entries.

.. warning::
    
    For default values containing a :py:class:`bitarray.bitarray` or any other
    mutable type, users must take care to copy the default value before
    mutating it.
"""


################################################################################
# parse_info header
################################################################################

ParseInfo = fixeddict(
    "ParseInfo",
    Entry("padding", formatter=Bits()),
    Entry("parse_info_prefix",
          friendly_formatter=(lambda prefix:
              "Correct"
              if prefix == PARSE_INFO_PREFIX else
              "INCORRECT"
          ),
          formatter=Hex(8)),
    Entry("parse_code",
          enum=ParseCodes,
          formatter=Hex(2)),
    Entry("next_parse_offset"),
    Entry("previous_parse_offset"),
    
    # Computed value: The byte offset of the start of this parse_info block in
    # the bitstream.
    Entry("_offset"),
)
"""
(10.5.1) Parse info header defined by ``parse_info()``.
"""

vc2_default_values[ParseInfo] = ParseInfo(
    padding=bitarray(),
    parse_info_prefix=PARSE_INFO_PREFIX,
    parse_code=ParseCodes.end_of_sequence,
    next_parse_offset=0,
    previous_parse_offset=0,
)

################################################################################
# sequence_header header and internal structures
################################################################################

ParseParameters = fixeddict(
    "ParseParameters",
    Entry("major_version"),
    Entry("minor_version"),
    Entry("profile", enum=Profiles),
    Entry("level", enum=Levels),
)
"""
(11.2.1) Sequence header defined by ``parse_parameters()``.
"""

vc2_default_values[ParseParameters] = ParseParameters(
    major_version=3,
    minor_version=0,
    profile=Profiles.high_quality,
    level=Levels.unconstrained,
)

FrameSize = fixeddict(
    "FrameSize",
    Entry("custom_dimensions_flag", formatter=Bool()),
    Entry("frame_width"),
    Entry("frame_height"),
)
"""
(11.4.3) Frame size override defined by ``frame_size()``.
"""

vc2_default_values[FrameSize] = FrameSize(
    custom_dimensions_flag=False,
    frame_width=1,
    frame_height=1,
)

ColorDiffSamplingFormat = fixeddict(
    "ColorDiffSamplingFormat",
    Entry("custom_color_diff_format_flag", formatter=Bool()),
    Entry("color_diff_format_index", enum=ColorDifferenceSamplingFormats),
)
"""
(11.4.4) Color-difference sampling override defined by
``color_diff_sampling_format()``.
"""

vc2_default_values[ColorDiffSamplingFormat] = ColorDiffSamplingFormat(
    custom_color_diff_format_flag=False,
    color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
)

ScanFormat = fixeddict(
    "ScanFormat",
    Entry("custom_scan_format_flag", formatter=Bool()),
    Entry("source_sampling", enum=SourceSamplingModes),
)
"""
(11.4.5) Scan format override defined by ``scan_format()``.
"""

vc2_default_values[ScanFormat] = ScanFormat(
    custom_scan_format_flag=False,
    source_sampling=SourceSamplingModes.progressive,
)

FrameRate = fixeddict(
    "FrameRate",
    Entry("custom_frame_rate_flag", formatter=Bool()),
    Entry("index", enum=PresetFrameRates),
    Entry("frame_rate_numer"),
    Entry("frame_rate_denom"),
)
"""
(11.4.6) Frame-rate override defined by ``frame_rate()``.
"""

vc2_default_values[FrameRate] = FrameRate(
    custom_frame_rate_flag=False,
    index=PresetFrameRates.fps_25,
    frame_rate_numer=25,
    frame_rate_denom=1,
)

PixelAspectRatio = fixeddict(
    "PixelAspectRatio",
    Entry("custom_pixel_aspect_ratio_flag", formatter=Bool()),
    Entry("index", enum=PresetPixelAspectRatios),
    Entry("pixel_aspect_ratio_numer"),
    Entry("pixel_aspect_ratio_denom"),
)
"""
(11.4.7) Pixel aspect ratio override defined by ``pixel_aspect_ratio()``
(errata: also listed as ``aspect_ratio()`` in some parts of the spec).
"""

vc2_default_values[PixelAspectRatio] = PixelAspectRatio(
    custom_pixel_aspect_ratio_flag=False,
    index=PresetPixelAspectRatios.ratio_1_1,
    pixel_aspect_ratio_numer=1,
    pixel_aspect_ratio_denom=1,
)

CleanArea = fixeddict(
    "CleanArea",
    Entry("custom_clean_area_flag", formatter=Bool()),
    Entry("clean_width"),
    Entry("clean_height"),
    Entry("left_offset"),
    Entry("top_offset"),
)
"""
(11.4.8) Clean areas override defined by ``clean_area()``.
"""

vc2_default_values[CleanArea] = CleanArea(
    custom_clean_area_flag=False,
    clean_width=1,
    clean_height=1,
    left_offset=0,
    top_offset=0,
)

SignalRange = fixeddict(
    "SignalRange",
    Entry("custom_signal_range_flag", formatter=Bool()),
    Entry("index", enum=PresetSignalRanges),
    Entry("luma_offset"),
    Entry("luma_excursion"),
    Entry("color_diff_offset"),
    Entry("color_diff_excursion"),
)
"""
(11.4.9) Signal range override defined by ``signal_range()``.
"""

vc2_default_values[SignalRange] = SignalRange(
    custom_signal_range_flag=False,
    index=PresetSignalRanges.video_8bit_full_range,
    luma_offset=0,
    luma_excursion=1,
    color_diff_offset=0,
    color_diff_excursion=1,
)

ColorPrimaries = fixeddict(
    "ColorPrimaries",
    Entry("custom_color_primaries_flag", formatter=Bool()),
    Entry("index", enum=PresetColorPrimaries),
)
"""
(11.4.10.2) Colour primaries override defined by ``color_primaries()``.
"""

vc2_default_values[ColorPrimaries] = ColorPrimaries(
    custom_color_primaries_flag=False,
    index=PresetColorPrimaries.hdtv,
)


ColorMatrix = fixeddict(
    "ColorMatrix",
    Entry("custom_color_matrix_flag", formatter=Bool()),
    Entry("index", enum=PresetColorMatrices),
)
"""
(11.4.10.3) Colour matrix override defined by ``color_matrix()``.
"""

vc2_default_values[ColorMatrix] = ColorMatrix(
    custom_color_matrix_flag=False,
    index=PresetColorMatrices.hdtv,
)

TransferFunction = fixeddict(
    "TransferFunction",
    Entry("custom_transfer_function_flag", formatter=Bool()),
    Entry("index", enum=PresetTransferFunctions),
)
"""
(11.4.10.4) Transfer function override defined by ``transfer_function()``.
"""

vc2_default_values[TransferFunction] = TransferFunction(
    custom_transfer_function_flag=False,
    index=PresetTransferFunctions.tv_gamma,
)

ColorSpec = fixeddict(
    "ColorSpec",
    Entry("custom_color_spec_flag", formatter=Bool()),
    Entry("index", enum=PresetColorSpecs),
    Entry("color_primaries"),  # ColorPrimaries
    Entry("color_matrix"),  # ColorMatrix
    Entry("transfer_function"),  # TransferFunction
)
"""
(11.4.10.1) Colour specification override defined by ``color_spec()``.
"""

vc2_default_values[ColorSpec] = ColorSpec(
    custom_color_spec_flag=False,
    index=PresetColorSpecs.hdtv,
)

vc2_fixeddict_nesting[ColorSpec] = [ColorPrimaries, ColorMatrix, TransferFunction]

SourceParameters = fixeddict(
    "SourceParameters",
    Entry("frame_size"),  # FrameSize
    Entry("color_diff_sampling_format"),  # ColorDiffSamplingFormat
    Entry("scan_format"),  # ScanFormat
    Entry("frame_rate"),  # FrameRate
    Entry("pixel_aspect_ratio"),  # PixelAspectRatio
    Entry("clean_area"),  # CleanArea
    Entry("signal_range"),  # SignalRange
    Entry("color_spec"),  # ColorSpec
)
"""
(11.4.1) Video format overrides defined by ``source_parameters()``.
"""

vc2_default_values[SourceParameters] = SourceParameters()

vc2_fixeddict_nesting[SourceParameters] = [
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
    Entry("padding", formatter=Bits()),
    Entry("parse_parameters"),  # ParseParameters
    Entry("base_video_format", enum=BaseVideoFormats),
    Entry("video_parameters"),  # SourceParameters
    Entry("picture_coding_mode", enum=PictureCodingModes),
)
"""
(11.1) Sequence header defined by ``sequence_header()``.
"""

vc2_default_values[SequenceHeader] = SequenceHeader(
    padding=bitarray(),
    base_video_format=BaseVideoFormats.custom_format,
    picture_coding_mode=PictureCodingModes.pictures_are_frames,
)

vc2_fixeddict_nesting[SequenceHeader] = [ParseParameters, SourceParameters]


################################################################################
# auxiliary_data and padding
################################################################################

AuxiliaryData = fixeddict(
    "AuxiliaryData",
    Entry("padding", formatter=Bits()),
    Entry("bytes", formatter=Bytes()),
)
"""
(10.4.4) Auxiliary data block (as per auxiliary_data()).
"""

vc2_default_values[AuxiliaryData] = AuxiliaryData(
    padding=bitarray(),
    bytes=b"",
)


Padding = fixeddict(
    "Padding",
    Entry("padding", formatter=Bits()),
    Entry("bytes", formatter=Bytes()),
)
"""
(10.4.5) Padding data block (as per padding()).
"""

vc2_default_values[Padding] = Padding(
    padding=bitarray(),
    bytes=b"",
)


################################################################################
# transform_parameters and associated structures
################################################################################

ExtendedTransformParameters = fixeddict(
    "ExtendedTransformParameters",
    Entry("asym_transform_index_flag"),
    Entry("wavelet_index_ho", enum=WaveletFilters),
    Entry("asym_transform_flag"),
    Entry("dwt_depth_ho"),
)
"""
(12.4.4.1) Extended (horizontal-only) wavelet transform parameters defined by
``extended_transform_parameters()``.
"""

vc2_default_values[ExtendedTransformParameters] = ExtendedTransformParameters(
    asym_transform_index_flag=False,
    wavelet_index_ho=WaveletFilters.haar_with_shift,
    asym_transform_flag=False,
    dwt_depth_ho=0,
)

SliceParameters = fixeddict(
    "SliceParameters",
    Entry("slices_x"),
    Entry("slices_y"),
    Entry("slice_bytes_numerator"),
    Entry("slice_bytes_denominator"),
    Entry("slice_prefix_bytes"),
    Entry("slice_size_scaler"),
)
"""
(12.4.5.2) Slice dimension parameters defined by ``slice_parameters()``.
"""

vc2_default_values[SliceParameters] = SliceParameters(
    slices_x=1,
    slices_y=1,
    slice_bytes_numerator=1,
    slice_bytes_denominator=1,
    slice_prefix_bytes=0,
    slice_size_scaler=1,
)

QuantMatrix = fixeddict(
    "QuantMatrix",
    Entry("custom_quant_matrix"),
    Entry("quant_matrix"),  # [int, ...]
)
"""
(12.4.5.3) Custom quantisation matrix override defined by ``quant_matrix()``.
"""

vc2_default_values[QuantMatrix] = QuantMatrix(
    custom_quant_matrix=False,
    quant_matrix=0,
)

TransformParameters = fixeddict(
    "TransformParameters",
    Entry("wavelet_index", enum=WaveletFilters),
    Entry("dwt_depth"),
    Entry("extended_transform_parameters"),  # ExtendedTransformParameters
    Entry("slice_parameters"),  # SliceParameters
    Entry("quant_matrix"),  # QuantMatrix
)
"""
(12.4.1) Wavelet transform parameters defined by ``transform_parameters()``.
"""

vc2_default_values[TransformParameters] = TransformParameters(
    wavelet_index=WaveletFilters.haar_with_shift,
    dwt_depth=0,
)

vc2_fixeddict_nesting[TransformParameters] = [
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
    Entry("qindex"),
    
    Entry("slice_y_length"),
    
    # Transform coefficients (in bitstream order)
    Entry("y_transform", formatter=List()),
    Entry("c_transform", formatter=List()),
    
    # Unused bits from bounded blocks
    Entry("y_block_padding", formatter=Bits()),
    Entry("c_block_padding", formatter=Bits()),
    
    # Computed value: The slice coordinates.
    Entry("_sx"),
    Entry("_sy"),
)
"""
(13.5.3.1) The data associated with a single low-delay slice, defined by
``ld_slice()``.
"""

vc2_default_values[LDSlice] = LDSlice(
    qindex=0,
    slice_y_length=0,
    y_transform=0,
    c_transform=0,
    y_block_padding=bitarray(),
    c_block_padding=bitarray(),
)

HQSlice = fixeddict(
    "HQSlice",
    Entry("prefix_bytes", formatter=Bytes()),
    
    Entry("qindex"),
    
    Entry("slice_y_length"),
    Entry("slice_c1_length"),
    Entry("slice_c2_length"),
    
    # Transform coefficients (in bitstream order)
    Entry("y_transform", formatter=List()),
    Entry("c1_transform", formatter=List()),
    Entry("c2_transform", formatter=List()),
    
    # Unused bits from bounded blocks
    Entry("y_block_padding", formatter=Bits()),
    Entry("c1_block_padding", formatter=Bits()),
    Entry("c2_block_padding", formatter=Bits()),
    
    # Computed value: The slice coordinates.
    Entry("_sx"),
    Entry("_sy"),
)
"""
(13.5.4) The data associated with a single high-quality slice, defined by
``hq_slice()``.
"""

vc2_default_values[HQSlice] = HQSlice(
    prefix_bytes=b"",
    qindex=0,
    slice_y_length=0,
    slice_c1_length=0,
    slice_c2_length=0,
    y_transform=0,
    c1_transform=0,
    c2_transform=0,
    y_block_padding=bitarray(),
    c1_block_padding=bitarray(),
    c2_block_padding=bitarray(),
)

################################################################################
# picture_parse and associated structures
################################################################################


PictureHeader = fixeddict(
    "PictureHeader",
    Entry("picture_number"),
)
"""
(12.2) Picture header information defined by ``picture_header()``.
"""

vc2_default_values[PictureHeader] = PictureHeader(
    picture_number=0,
)

TransformData = fixeddict(
    "TransformData",
    Entry("ld_slices", formatter=List(formatter=Object())),  # [LDSlice, ...]
    Entry("hq_slices", formatter=List(formatter=Object())),  # [HQSlice, ...]
    
    # Computed value: A copy of the State dictionary held when processing this
    # transform data. May be used to work out how the deseriallised values
    # correspond to transform components within the slices above.
    Entry("_state"),
)
"""
(13.5.2) Transform coefficient data slices read by ``transform_data()``.
"""

vc2_default_values[TransformData] = TransformData()

vc2_fixeddict_nesting[TransformData] = [LDSlice, HQSlice]

WaveletTransform = fixeddict(
    "WaveletTransform",
    Entry("transform_parameters"),  # TransformParameters
    Entry("padding", formatter=Bits()),
    Entry("transform_data"),  # TransformData
)
"""
(12.3) Wavelet parameters and coefficients defined by ``wavelet_transform()``.
"""

vc2_default_values[WaveletTransform] = WaveletTransform(
    padding=bitarray(),
)

vc2_fixeddict_nesting[WaveletTransform] = [TransformParameters, TransformData]

PictureParse = fixeddict(
    "PictureParse",
    Entry("padding1", formatter=Bits()),
    Entry("picture_header"),  # PictureHeader
    Entry("padding2", formatter=Bits()),
    Entry("wavelet_transform"),  # WaveletTransform
)
"""
(12.1) A picture data unit defined by ``picture_parse()``
"""

vc2_default_values[PictureParse] = PictureParse(
    padding1=bitarray(),
    padding2=bitarray(),
)

vc2_fixeddict_nesting[PictureParse] = [PictureHeader, WaveletTransform]


################################################################################
# fragment_parse and associated structures
################################################################################

FragmentHeader = fixeddict(
    "FragmentHeader",
    Entry("picture_number"),
    Entry("fragment_data_length"),
    Entry("fragment_slice_count"),
    Entry("fragment_x_offset", ),
    Entry("fragment_y_offset", ),
)
"""
(14.2) Fragment header defined by ``fragment_header()``.
"""

vc2_default_values[FragmentHeader] = FragmentHeader(
    picture_number=0,
    fragment_data_length=0,
    fragment_slice_count=0,
    fragment_x_offset=0,
    fragment_y_offset=0,
)

FragmentData = fixeddict(
    "FragmentData",
    Entry("ld_slices", formatter=List(formatter=Object())),  # LDSlice
    Entry("hq_slices", formatter=List(formatter=Object())),  # HQSlice
    
    # Computed value: A copy of the State dictionary held when processing this
    # fragment data. May be used to work out how the deseriallised values
    # correspond to transform components within the slices above.
    Entry("_state"),
)
"""
(14.4) Transform coefficient data slices read by ``fragment_data()``.
"""

vc2_default_values[FragmentData] = FragmentData()

vc2_fixeddict_nesting[FragmentData] = [LDSlice, HQSlice]

FragmentParse = fixeddict(
    "FragmentParse",
    Entry("padding1", formatter=Bits()),
    Entry("fragment_header"),  # FragmentHeader
    Entry("padding2", formatter=Bits()),
    Entry("transform_parameters"),  # TransformParameters
    Entry("fragment_data"),  # FragmentData
)
"""
(14.1) A fragment data unit defined by ``fragment_parse()`` containing part of a
picture.
"""

vc2_default_values[FragmentParse] = FragmentParse(
    padding1=bitarray(),
    padding2=bitarray(),
)

vc2_fixeddict_nesting[FragmentParse] = [FragmentHeader, TransformParameters, FragmentData]

################################################################################
# Sequences
################################################################################

DataUnit = fixeddict(
    "DataUnit",
    Entry("parse_info"),  # ParseInfo
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

vc2_default_values[DataUnit] = DataUnit()

vc2_fixeddict_nesting[DataUnit] = [
    ParseInfo,
    SequenceHeader,
    PictureParse,
    FragmentParse,
    AuxiliaryData,
    Padding,
]

Sequence = fixeddict(
    "Sequence",
    Entry("data_units", formatter=MultilineList(heading="")),  # DataUnit
    # Computed value: The State object being populated by the parser.
    Entry("_state"),
)
"""
(10.4.1) A VC-2 sequence.
"""

vc2_default_values[Sequence] = Sequence()

vc2_fixeddict_nesting[Sequence] = [DataUnit]
