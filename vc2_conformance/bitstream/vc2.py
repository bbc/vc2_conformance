r"""
:py:class:`BitstreamValue`\ s for each of VC-2 bitstream structures.
"""

from vc2_conformance.bitstream import (
    Concatenation,
    LabelledConcatenation,
    NBits,
    UInt,
    SInt,
    Bool,
    Maybe,
    Array,
    RectangularArray,
    SubbandArray,
    ByteAlign,
    BoundedBlock,
    FunctionValue,
    ensure_bitstream_value,
    LDSliceArray,
    HQSliceArray,
)

from vc2_conformance.bitstream._util import (
    indent,
    concat_labelled_strings,
    function_property,
    ordinal_indicator,
)

from vc2_conformance.bitstream.formatters import Hex

from vc2_conformance.tables import (
    PARSE_INFO_PREFIX,
    ParseCodes,
    PictureCodingModes,
    BASE_VIDEO_FORMAT_PARAMETERS,
    BaseVideoFormats,
    Profiles,
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PresetFrameRates,
    PRESET_FRAME_RATES,
    PresetPixelAspectRatios,
    PRESET_PIXEL_ASPECT_RATIOS,
    PresetSignalRanges,
    PresetColorSpecs,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    WaveletFilters,
)

from vc2_conformance.math import intlog2


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
]


################################################################################
# parse_info header
################################################################################

class ParseInfo(LabelledConcatenation):
    """
    (10.5.1) Parse info header defined by ``parse_info()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"parse_info_prefix"`` (:py:class:`NBits`)
    * ``"parse_code"`` (:py:class:`NBits` containing :py:class:`ParseCodes`)
    * ``"next_parse_offset"`` (:py:class:`NBits`)
    * ``"previous_parse_offset"`` (:py:class:`NBits`)
    """
    
    def __init__(self):
        super(ParseInfo, self).__init__(
            "parse_info:",
            (
                "parse_info_prefix",
                NBits(
                    PARSE_INFO_PREFIX,
                    length=32,
                    formatter=Hex(8),
                    get_value_name=(lambda v:
                        "Correct" if v == PARSE_INFO_PREFIX else "Incorrect"
                    ),
                ),
            ),
            (
                "parse_code",
                NBits(ParseCodes.end_of_sequence, length=8, formatter=Hex(2), enum=ParseCodes),
            ),
            ("next_parse_offset", NBits(0, length=32)),
            ("previous_parse_offset", NBits(0, length=32)),
        )
        
        self._data_length = FunctionValue(ParseInfo.compute_data_length, self)
        self._is_low_delay = FunctionValue(ParseInfo.compute_is_low_delay, self)
        self._is_high_quality = FunctionValue(ParseInfo.compute_is_high_quality, self)
    
    @property
    def data_length(self):
        """
        A :py:class:`BitstreamValue` containing the length in bytes of the data
        block following this :py:class:`ParseInfo` header. May be 'None' if the
        length is not indicated by the header.
        """
        return self._data_length
    
    @property
    def is_low_delay(self):
        """
        A :py:class:`BitstreamValue` which indicates if the parse code
        associated with this :py:class:`ParseInfo` is for a low-delay picture
        or fragment.
        """
        return self._is_low_delay
    
    @property
    def is_high_quality(self):
        """
        A :py:class:`BitstreamValue` which indicates if the parse code
        associated with this :py:class:`ParseInfo` is for a high-quality
        picture or fragment.
        """
        return self._is_high_quality
    
    @staticmethod
    def compute_data_length(parse_info):
        """
        Given a :py:class:`ParseInfo`, compute the expected length of the next
        data unit.  For picture and fragment parse codes, this value may be
        invalid.  Otherwise, returns a number of bytes.
        """
        next_parse_offset = parse_info["next_parse_offset"].value
        
        if next_parse_offset == 0:
            return None
        else:
            # (10.5.1) "The parse info header shall consist of 13 bytes"
            return next_parse_offset - 13
    
    @staticmethod
    def compute_is_low_delay(parse_info):
        """
        Given a :py:class:`ParseInfo`, return whether the following data unit
        is for a low-delay picture or fragment.
        """
        # NB: Will throw an exception unknown parse codes (this is acceptable
        # since users of this value should be robust to exceptions).
        return parse_info["parse_code"].value.is_low_delay
    
    @staticmethod
    def compute_is_high_quality(parse_info):
        """
        Given a :py:class:`ParseInfo`, return whether the following data unit
        is for a high-quality picture or fragment.
        """
        # NB: Will throw an exception unknown parse codes (this is acceptable
        # since users of this value should be robust to exceptions).
        return parse_info["parse_code"].value.is_high_quality

################################################################################
# sequence_header header and internal structures
################################################################################

class SequenceHeader(LabelledConcatenation):
    """
    (11.1) Sequence header defined by ``sequence_header()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"parse_parameters"`` (:py:class:`ParseParameters`)
    * ``"base_video_format"`` (:py:class:`UInt` containing
      :py:class:`BaseVideoFormats`)
    * ``"video_parameters"`` (:py:class:`SourceParameters`)
    * ``"picture_coding_mode"`` (:py:class:`UInt` containing
      :py:class:`PictureCodingModes`)
    
    In addition, the following :py:class:`BitstreamValue`-wrapped properties
    are provided which contain *computed* values based on the above which are
    required to correctly parse the bitstream.
    
    * :py:attr:`luma_dimensions`
    * :py:attr:`color_diff_dimensions`
    """
    
    def __init__(self):
        super(SequenceHeader, self).__init__(
            "sequence_header:",
            ("parse_parameters", ParseParameters()),
            (
                "base_video_format",
                UInt(BaseVideoFormats.custom_format, enum=BaseVideoFormats),
            ),
            ("video_parameters", SourceParameters()),
            (
                "picture_coding_mode",
                UInt(PictureCodingModes.pictures_are_frames, enum=PictureCodingModes),
            ),
        )
        
        self._luma_dimensions = FunctionValue(SequenceHeader.compute_luma_dimensions, self)
        self._color_diff_dimensions = FunctionValue(SequenceHeader.compute_color_diff_dimensions, self)
    
    @property
    def luma_dimensions(self):
        """
        A :py:class:`BitstreamValue` containing a (width, height) tuple giving
        the luminance picture size specified by this sequence header.
        """
        return self._luma_dimensions
    
    @property
    def color_diff_dimensions(self):
        """
        A :py:class:`BitstreamValue` containing a (width, height) tuple giving
        the color-difference picture size specified by this sequence header.
        """
        return self._color_diff_dimensions
    
    
    @staticmethod
    def compute_base_video_format_parameters(sequence_header):
        """
        Given a :py:class:`SequenceHeader`, return the corresponding
        :py:class:`BaseVideoFormatParameters`. Raises a KeyError if the base
        video format is not recognised.
        """
        return BASE_VIDEO_FORMAT_PARAMETERS[
                BaseVideoFormats(sequence_header["base_video_format"].value)]
    
    @staticmethod
    def compute_luma_dimensions(sequence_header):
        """
        (11.6.2) Compute the the (width, height) of the luminance picture
        component, as defined in a :py:class:`SequenceHeader`.
        """
        # NB: Try using the overridden frame-size first since, if this is
        # defined, it doesn't matter if the base video format raises a
        # KeyError.
        frame_size = sequence_header["video_parameters"]["frame_size"]
        if frame_size["custom_dimensions_flag"].value:
            # (11.4.3) frame_size() -- Override with custom values
            luma_width = frame_size["frame_width"].value
            luma_height = frame_size["frame_height"].value
        else:
            # (11.4.2) set_source_defaults()
            base = SequenceHeader.compute_base_video_format_parameters(sequence_header)
            luma_width = base.frame_width
            luma_height = base.frame_height
        
        if sequence_header["picture_coding_mode"].value == PictureCodingModes.pictures_are_fields:
            luma_height //= 2
        
        return (luma_width, luma_height)
    
    @staticmethod
    def compute_color_diff_dimensions(sequence_header):
        """
        (11.6.2) The (width, height) of the colour difference picture
        component, as defined in a :py:class:`SequenceHeader`.
        """
        color_diff_width, color_diff_height = SequenceHeader.compute_luma_dimensions(sequence_header)

        # NB: Try using the overridden frame-size first since, if this is
        # defined, it doesn't matter if the base video format raises a
        # KeyError.
        color_diff_sampling_format = sequence_header["video_parameters"]["color_diff_sampling_format"]
        if color_diff_sampling_format["custom_color_diff_format_flag"].value:
            # (11.4.4) color_diff_sampling_format() -- Override color diff
            # sampling format
            color_diff_format_index = color_diff_sampling_format["color_diff_format_index"].value
        else:
            # (11.4.2) set_source_defaults() -- Start off with preset color diff
            # sampling format aand source sampling mode
            base = SequenceHeader.compute_base_video_format_parameters(sequence_header)
            color_diff_format_index = base.color_diff_format_index
        
        if color_diff_format_index == ColorDifferenceSamplingFormats.color_4_2_2:
            color_diff_width //= 2
        elif color_diff_format_index == ColorDifferenceSamplingFormats.color_4_2_0:
            color_diff_width //= 2
            color_diff_height //= 2
        
        return color_diff_width, color_diff_height


class ParseParameters(LabelledConcatenation):
    """
    (11.2.1) Sequence header defined by ``parse_parameters()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"major_version"`` (:py:class:`UInt`)
    * ``"minor_version"`` (:py:class:`UInt`)
    * ``"profile"`` (:py:class:`UInt` containing :py:class:`Profiles`)
    * ``"level"`` (:py:class:`UInt`)
    """
    
    def __init__(self):
        super(ParseParameters, self).__init__(
            "parse_parameters:",
            ("major_version", UInt(3)),
            ("minor_version", UInt(0)),
            ("profile", UInt(Profiles.high_quality, enum=Profiles)),
            ("level", UInt(0)),
        )


class SourceParameters(LabelledConcatenation):
    """
    (11.4.1) Video format overrides defined by ``source_parameters()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"frame_size"`` (:py:class:`FrameSize`)
    * ``"color_diff_sampling_format"``
      (:py:class:`ColorDiffSamplingFormat`)
    * ``"scan_format"`` (:py:class:`ScanFormat`)
    * ``"frame_rate"`` (:py:class:`FrameRate`)
    * ``"pixel_aspect_ratio"`` (:py:class:`AspectRatio`)
    * ``"clean_area"`` (:py:class:`CleanArea`)
    * ``"signal_range"`` (:py:class:`SignalRange`)
    * ``"color_spec"`` (:py:class:`ColorSpec`)
    """
    
    def __init__(self):
        super(SourceParameters, self).__init__(
            "source_parameters:",
            ("frame_size", FrameSize()),
            ("color_diff_sampling_format", ColorDiffSamplingFormat()),
            ("scan_format", ScanFormat()),
            ("frame_rate", FrameRate()),
            ("pixel_aspect_ratio", PixelAspectRatio()),
            ("clean_area", CleanArea()),
            ("signal_range", SignalRange()),
            ("color_spec", ColorSpec()),
        )


class FrameSize(LabelledConcatenation):
    """
    (11.4.3) Frame size override defined by ``frame_size()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_dimensions_flag"`` (:py:class:`Bool`)
    * ``"frame_width"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"frame_height"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        super(FrameSize, self).__init__(
            "frame_size:",
            ("custom_dimensions_flag", flag),
            ("frame_width", Maybe(lambda: UInt(1), flag)),
            ("frame_height", Maybe(lambda: UInt(1), flag)),
        )


class ColorDiffSamplingFormat(LabelledConcatenation):
    """
    (11.4.4) Color-difference sampling override defined by
    ``color_diff_sampling_format()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_color_diff_format_flag"`` (:py:class:`Bool`)
    * ``"color_diff_format_index"`` (:py:class:`UInt` containing
      :py:class:`ColorDifferenceSamplingFormats`, in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        super(ColorDiffSamplingFormat, self).__init__(
            "color_diff_sampling_format:",
            ("custom_color_diff_format_flag", flag),
            (
                "color_diff_format_index",
                Maybe(
                    lambda: UInt(
                        ColorDifferenceSamplingFormats.color_4_4_4,
                        enum=ColorDifferenceSamplingFormats,
                    ),
                    flag,
                ),
            ),
        )


class ScanFormat(LabelledConcatenation):
    """
    (11.4.5) Scan format override defined by ``scan_format()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_scan_format_flag"`` (:py:class:`Bool`)
    * ``"source_sampling"`` (:py:class:`UInt` containing
      :py:class:`SourceSamplingModes`, in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        super(ScanFormat, self).__init__(
            "scan_format:",
            ("custom_scan_format_flag", flag),
            (
                "source_sampling",
                Maybe(
                    lambda: UInt(SourceSamplingModes.progressive, enum=SourceSamplingModes),
                    flag,
                ),
            ),
        )


class FrameRate(LabelledConcatenation):
    """
    (11.4.6) Frame-rate override defined by ``frame_rate()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_frame_rate_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetFrameRates`, in a :py:class:`Maybe`)
    * ``"frame_rate_numer"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"frame_rate_denom"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        index = Maybe(
            lambda: UInt(
                enum=PresetFrameRates,
                # Show the preset framerate in a more human-readable form than
                # the enum name
                get_value_name=(
                    lambda p:
                    "{} fps".format(PRESET_FRAME_RATES[PresetFrameRates(p)])
                ),
            ),
            flag,
        )
        is_full_custom = FunctionValue(
            lambda flag, index: flag.value and index.value == 0,
            flag,
            index,
        )
        super(FrameRate, self).__init__(
            "frame_rate:",
            ("custom_frame_rate_flag", flag),
            ("index", index),
            ("frame_rate_numer", Maybe(lambda: UInt(0), is_full_custom)),
            ("frame_rate_denom", Maybe(lambda: UInt(1), is_full_custom)),
        )


class PixelAspectRatio(LabelledConcatenation):
    """
    (11.4.7) Pixel aspect ratio override defined by ``pixel_aspect_ratio()``
    (errata: also listed as ``aspect_ratio()`` in some parts of the spec).
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_pixel_aspect_ratio_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetPixelAspectRatios`, in a :py:class:`Maybe`)
    * ``"pixel_aspect_ratio_numer"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"pixel_aspect_ratio_denom"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        index = Maybe(
            lambda: UInt(
                enum=PresetPixelAspectRatios,
                get_value_name=PixelAspectRatio._get_index_value_name
            ),
            flag,
        )
        is_full_custom = FunctionValue(
            lambda flag, index: flag.value and index.value == 0,
            flag,
            index,
        )
        super(PixelAspectRatio, self).__init__(
            "pixel_aspect_ratio:",
            ("custom_pixel_aspect_ratio_flag", flag),
            ("index", index),
            ("pixel_aspect_ratio_numer", Maybe(lambda: UInt(1), is_full_custom)),
            ("pixel_aspect_ratio_denom", Maybe(lambda: UInt(1), is_full_custom)),
        )
    
    @staticmethod
    def _get_index_value_name(index):
        """
        A 'get_value_name' compatible function to return a human-readable
        version of an aspect ratio index.
        """
        enum_value = PresetPixelAspectRatios(index)
        ratio = PRESET_PIXEL_ASPECT_RATIOS[enum_value]
        return "{}:{}".format(ratio.numerator, ratio.denominator)


class CleanArea(LabelledConcatenation):
    """
    (11.4.8) Clean areas override defined by ``clean_area()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_clean_area_flag"`` (:py:class:`Bool`)
    * ``"clean_width"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"clean_height"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"left_offset"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"top_offset"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        super(CleanArea, self).__init__(
            "clean_area:",
            ("custom_clean_area_flag", flag),
            ("clean_width", Maybe(lambda: UInt(1), flag)),
            ("clean_height", Maybe(lambda: UInt(1), flag)),
            ("left_offset", Maybe(UInt, flag)),
            ("top_offset", Maybe(UInt, flag)),
        )


class SignalRange(LabelledConcatenation):
    """
    (11.4.9) Signal range override defined by ``signal_range()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_signal_range_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetSignalRanges`, in a :py:class:`Maybe`)
    * ``"luma_offset"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"luma_excursion"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"color_diff_offset"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    * ``"color_diff_excursion"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        index = Maybe(lambda: UInt(enum=PresetSignalRanges), flag)
        is_full_custom = FunctionValue(
            lambda flag, index: flag.value and index.value == 0,
            flag,
            index,
        )
        super(SignalRange, self).__init__(
            "signal_range:",
            ("custom_signal_range_flag", flag),
            ("index", index),
            ("luma_offset", Maybe(lambda: UInt(0), is_full_custom)),
            ("luma_excursion", Maybe(lambda: UInt(1), is_full_custom)),
            ("color_diff_offset", Maybe(lambda: UInt(0), is_full_custom)),
            ("color_diff_excursion", Maybe(lambda: UInt(1), is_full_custom)),
        )


class ColorSpec(LabelledConcatenation):
    """
    (11.4.10.1) Colour specification override defined by ``color_spec()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_color_spec_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetColorSpecs`, in a :py:class:`Maybe`)
    * ``"color_primaries"`` (:py:class:`ColorPrimaries` in a :py:class:`Maybe`)
    * ``"color_matrix"`` (:py:class:`ColorMatrix` in a :py:class:`Maybe`)
    * ``"transfer_function"`` (:py:class:`TransferFunction` in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        index = Maybe(lambda: UInt(PresetColorSpecs.custom, enum=PresetColorSpecs), flag)
        is_full_custom = FunctionValue(
            lambda flag, index: flag.value and index.value == PresetColorSpecs.custom,
            flag,
            index,
        )
        super(ColorSpec, self).__init__(
            "color_spec:",
            ("custom_color_spec_flag", flag),
            ("index", index),
            ("color_primaries", Maybe(ColorPrimaries, is_full_custom)),
            ("color_matrix", Maybe(ColorMatrix, is_full_custom)),
            ("transfer_function", Maybe(TransferFunction, is_full_custom)),
        )


class ColorPrimaries(LabelledConcatenation):
    """
    (11.4.10.2) Colour primaries override defined by ``color_primaries()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_color_primaries_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetColorPrimaries`, in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        super(ColorPrimaries, self).__init__(
            "color_primaries:",
            ("custom_color_primaries_flag", flag),
            (
                "index",
                Maybe(
                    lambda: UInt(PresetColorPrimaries.hdtv, enum=PresetColorPrimaries),
                    flag,
                ),
            ),
        )


class ColorMatrix(LabelledConcatenation):
    """
    (11.4.10.3) Colour matrix override defined by ``color_matrix()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_color_matrix_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetColorMatrices`, in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        super(ColorMatrix, self).__init__(
            "color_matrix:",
            ("custom_color_matrix_flag", flag),
            (
                "index",
                Maybe(
                    lambda: UInt(PresetColorMatrices.hdtv, enum=PresetColorMatrices),
                    flag,
                ),
            ),
        )


class TransferFunction(LabelledConcatenation):
    """
    (11.4.10.4) Transfer function override defined by ``transfer_function()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_transfer_function_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetTransferFunctions`, in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        flag = Bool(False)
        super(TransferFunction, self).__init__(
            "transfer_function:",
            ("custom_transfer_function_flag", flag),
            (
                "index",
                Maybe(
                    lambda: UInt(PresetTransferFunctions.tv_gamma, enum=PresetTransferFunctions),
                    flag,
                ),
            ),
        )

################################################################################
# auxiliary_data and padding
################################################################################

class AuxiliaryData(Array):
    """
    (10.4.4) Auxiliary data block (as per auxiliary_data()).
    
    An :py:class:`Array` containing the bytes in the block as 8-bit
    :py:class:`NBits` values.
    """
    
    def __init__(self, parse_info=ParseInfo()):
        """
        parse_info should be the :py:class:`ParseInfo` header associated with
        this data block.
        """
        
        self._parse_info = parse_info
        
        super(AuxiliaryData, self).__init__(
            lambda: NBits(length=8, formatter=Hex(2)),
            self.parse_info.data_length,
        )
    
    @property
    def parse_info(self):
        """The :py:class:`ParseInfo` associated with this data block."""
        return self._parse_info


class Padding(Array):
    """
    (10.4.5) Padding data block (as per padding()).
    
    An :py:class:`Array` containing the bytes in the block as 8-bit
    :py:class:`NBits` values.
    """
    
    def __init__(self, parse_info=ParseInfo()):
        """
        parse_info should be the :py:class:`ParseInfo` header associated with
        this padding block.
        """
        self._parse_info = parse_info
        
        super(Padding, self).__init__(
            lambda: NBits(length=8, formatter=Hex(2)),
            self.parse_info.data_length,
        )
    
    @property
    def parse_info(self):
        """The :py:class:`ParseInfo` associated with this data block."""
        return self._parse_info


################################################################################
# transform_parameters and associated structures
################################################################################

class TransformParameters(LabelledConcatenation):
    """
    (12.4.1) Wavelet transform parameters defined by ``transform_parameters()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"wavelet_index"`` (:py:class:`WaveletFilters` in a :py:class:`UInt`)
    * ``"dwt_depth"`` (:py:class:`UInt`)
    * ``"extended_transform_parameters"``
      (:py:class:`ExtendedTransformParameters` in a :py:class:`Maybe`)
    * ``"slice_parameters"`` (:py:class:`SliceParameters`)
    * ``"quant_matrix"`` (:py:class:`QuantMatrix`)
    """
    
    def __init__(self, parse_info=ParseInfo(), sequence_header=SequenceHeader()):
        """
        ``parse_info`` should be the :py;class:`ParseInfo` header associated
        with the data block this structure is contained in.
        
        ``sequence_header`` should be the :py;class:`SequenceHeader` associated
        with the current sequence (i.e. the one most recently received).
        """
        self._parse_info = parse_info
        self._sequence_header = sequence_header
        
        self._extended = FunctionValue(TransformParameters.compute_extended, self.sequence_header)
        self._extended_transform_parameters = Maybe(ExtendedTransformParameters, self.extended)
        
        self._dwt_depth = UInt(0)
        self._dwt_depth_ho = FunctionValue(
            TransformParameters.compute_dwt_depth_ho,
            self.extended,
            self._extended_transform_parameters,
        )
        
        super(TransformParameters, self).__init__(
            "transform_parameters:",
            ("wavelet_index", UInt(WaveletFilters.deslauriers_dubuc_9_7, enum=WaveletFilters)),
            ("dwt_depth", self._dwt_depth),
            ("extended_transform_parameters", self._extended_transform_parameters),
            ("slice_parameters", SliceParameters(self.parse_info)),
            ("quant_matrix", QuantMatrix(self.dwt_depth, self.dwt_depth_ho)),
        )
    
    @property
    def parse_info(self):
        """The :py:class:`ParseInfo` associated with this data block."""
        return self._parse_info
    
    @property
    def sequence_header(self):
        """The :py:class:`SequenceHeader` associated with the current sequence."""
        return self._sequence_header
    
    @property
    def extended(self):
        """
        A :py:class:`BitstreamValue` defining whether extended transform
        parameters are in use in this :py:class:`TransformParameters`.
        """
        return self._extended
    
    @property
    def dwt_depth(self):
        """
        A :py:class:`BitstreamValue` containing the 2D wavelet depth specified
        by this structure.
        
        Alias for ``params["dwt_depth"]``, provided for symmetry with
        :py:attr:`dwt_depth_ho`.
        """
        return self._dwt_depth
    
    @property
    def dwt_depth_ho(self):
        """
        A :py:class:`BitstreamValue` containing the horizontal-only wavelet
        depth specified by this structure.
        """
        return self._dwt_depth_ho
    
    @staticmethod
    def compute_extended(sequence_header):
        """
        Does the specified :py:class:`SequenceHeader` indicate that we'll need
        the extended_transform_parameters field?
        """
        # As specified in (12.4.1)
        return sequence_header["parse_parameters"]["major_version"].value >= 3
    
    @staticmethod
    def compute_dwt_depth_ho(extended, extended_transform_parameters):
        """
        Given a :py:class:`BitstreamValue` indicating if extended transform
        parameters are in use and a :py:class:`ExtendedTransformParameters`,
        compute the chosen horizontal-only wavelet depth.
        
        Computed in the manner specified by (12.4.1) ``transform_parameters()``
        and (12.4.4.1) ``extended_transform_parameters()``.
        """
        if extended.value:
            if extended_transform_parameters["asym_transform_flag"].value:
                return extended_transform_parameters["dwt_depth_ho"].value
            else:
                return 0
        else:
            return 0


class ExtendedTransformParameters(LabelledConcatenation):
    """
    (12.4.4.1) Extended (horizontal-only) wavelet transform parameters defined
    by ``extended_transform_parameters()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"asym_transform_index_flag"`` (:py:class:`Bool`)
    * ``"wavelet_index_ho"`` (:py:class:`WaveletFilters` in a :py:class:`UInt`
      in a :py:class:`Maybe`)
    * ``"asym_transform_flag"`` (:py:class:`Bool`)
    * ``"dwt_depth_ho"`` (:py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self):
        index_flag = Bool()
        transform_flag = Bool()
        super(ExtendedTransformParameters, self).__init__(
            "extended_transform_parameters:",
            ("asym_transform_index_flag", index_flag),
            (
                "wavelet_index_ho",
                Maybe(
                    lambda: UInt(WaveletFilters.deslauriers_dubuc_9_7, enum=WaveletFilters),
                    index_flag,
                ),
            ),
            ("asym_transform_flag", transform_flag),
            ("dwt_depth_ho", Maybe(UInt, transform_flag)),
        )


class SliceParameters(LabelledConcatenation):
    """
    (12.4.5.2) Slice dimension parameters defined by ``slice_parameters()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"slices_x"`` (:py:class:`UInt`)
    * ``"slices_y"`` (:py:class:`UInt`)
    * ``"slice_bytes_numerator"`` (:py:class:`UInt` in a :py:class:`Maybe`
      predicated on a :py:attr:`ParseCodes.is_low_delay`)
    * ``"slice_bytes_denominator"`` (:py:class:`UInt` in a :py:class:`Maybe`
      predicated on a :py:attr:`ParseCodes.is_low_delay`)
    * ``"slice_prefix_bytes"`` (:py:class:`UInt` in a :py:class:`Maybe`
      predicated on a :py:attr:`ParseCodes.is_high_quality`)
    * ``"slice_size_scaler"`` (:py:class:`UInt` in a :py:class:`Maybe`
      predicated on a :py:attr:`ParseCodes.is_high_quality`)
    """
    
    def __init__(self, parse_info=ParseInfo()):
        """
        ``parse_info`` should be the :py;class:`ParseInfo` header associated
        with the data block this structure is contained in.
        """
        self._parse_info = parse_info
        
        super(SliceParameters, self).__init__(
            "slice_parameters:",
            ("slices_x", UInt(1)),
            ("slices_y", UInt(1)),
            ("slice_bytes_numerator", Maybe(lambda: UInt(1), self.parse_info.is_low_delay)),
            ("slice_bytes_denominator", Maybe(lambda: UInt(1), self.parse_info.is_low_delay)),
            ("slice_prefix_bytes", Maybe(lambda: UInt(0), self.parse_info.is_high_quality)),
            ("slice_size_scaler", Maybe(lambda: UInt(1), self.parse_info.is_high_quality)),
        )
    
    @property
    def parse_info(self):
        """The :py:class:`ParseInfo` associated with this data block."""
        return self._parse_info


class QuantMatrix(LabelledConcatenation):
    """
    (12.4.5.3) Custom quantisation matrix override defined by ``quant_matrix()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_quant_matrix"`` (:py:class:`Bool`)
    * ``"matrix"`` (a :py:class:`SubbandArray` of :py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self, dwt_depth=0, dwt_depth_ho=0):
        r"""
        ``dwt_depth`` and ``dwt_depth_ho`` should be
        :py:class:`BitstreamValue`\ s defining the 2D and horizontal-only
        wavelet transform depths.
        """
        self._dwt_depth = ensure_bitstream_value(dwt_depth)
        self._dwt_depth_ho = ensure_bitstream_value(dwt_depth_ho)
        
        flag = Bool()
        
        super(QuantMatrix, self).__init__(
            "quant_matrix:",
            ("custom_quant_matrix", flag),
            ("matrix", Maybe(lambda: SubbandArray(UInt, self.dwt_depth, self.dwt_depth_ho), flag)),
        )
    
    @property
    def dwt_depth(self):
        """
        The :py:class:`BitstreamValue` defining the 2D wavelet transform depth.
        """
        return self._dwt_depth
    
    @property
    def dwt_depth_ho(self):
        """
        The :py:class:`BitstreamValue` defining the horizontal-only wavelet
        transform depth.
        """
        return self._dwt_depth_ho


################################################################################
# picture_parse and associated structures
################################################################################


class PictureParse(LabelledConcatenation):
    """
    (12.1) A picture data unit defined by ``picture_parse()``
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"padding"`` (:py:class:`ByteAlign`)
    * ``"picture_header"`` (:py:class:`PictureHeader`)
    * ``"wavelet_transform"`` (:py:class:`WaveletTransform` in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 parse_info=ParseInfo(),
                 sequence_header=SequenceHeader()):
        """
        ``parse_info`` should be the :py;class:`ParseInfo` header associated
        with the data block this structure is contained in.
        
        ``sequence_header`` should be the :py;class:`SequenceHeader` associated
        with the current sequence (i.e. the one most recently received).
        """
        self._parse_info = parse_info
        self._sequence_header = sequence_header
        
        super(PictureParse, self).__init__(
            "picture_parse:",
            ("padding", ByteAlign()),
            ("picture_header", PictureHeader()),
            (
                "wavelet_transform",
                WaveletTransform(
                    self.parse_info,
                    self.sequence_header,
                ),
            ),
        )
    
    @property
    def parse_info(self):
        """The :py:class:`ParseInfo` associated with this data block."""
        return self._parse_info
    
    @property
    def sequence_header(self):
        """The :py:class:`SequenceHeader` associated with the current sequence."""
        return self._sequence_header


class PictureHeader(LabelledConcatenation):
    """
    (12.2) Picture header information defined by ``picture_header()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"picture_number"`` (a 32-bit :py:class:`NBits`)
    """
    
    def __init__(self):
        super(PictureHeader, self).__init__(
            "picture_header:",
            ("picture_number", NBits(length=32)),
        )


class WaveletTransform(LabelledConcatenation):
    """
    (12.3) Wavelet parameters and coefficients defined by
    ``wavelet_transform()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"transform_parameters"`` (:py:class:`TransformParameters`)
    * ``"padding"`` (:py:class:`ByteAlign`)
    * ``"ld_transform_data"`` (:py:class:`LDSliceArray` in a :py:class:`Maybe`
      predicated on this being a low-delay picture.)
    * ``"hq_transform_data"`` (:py:class:`HQSliceArray` in a :py:class:`Maybe`
      predicated on this being a high-quality picture.)
    """
    
    def __init__(self,
                 parse_info=ParseInfo(),
                 sequence_header=SequenceHeader()):
        """
        ``parse_info`` should be the :py;class:`ParseInfo` header associated
        with the data block this structure is contained in.
        
        ``sequence_header`` should be the :py;class:`SequenceHeader` associated
        with the current sequence (i.e. the one most recently received).
        """
        self._parse_info = parse_info
        self._sequence_header = sequence_header
        
        transform_parameters = TransformParameters(
            self.parse_info,
            self.sequence_header,
        )
        
        super(WaveletTransform, self).__init__(
            "wavelet_transform:",
            ("transform_parameters", transform_parameters),
            ("padding", ByteAlign()),
            (
                "ld_transform_data",
                Maybe(
                    lambda: LDSliceArray(
                        self.sequence_header,
                        transform_parameters,
                    ),
                    parse_info.is_low_delay,
                ),
            ),
            (
                "hq_transform_data",
                Maybe(
                    lambda: HQSliceArray(
                        self.sequence_header,
                        transform_parameters,
                    ),
                    parse_info.is_high_quality,
                ),
            ),
        )
    
    @property
    def parse_info(self):
        """The :py:class:`ParseInfo` associated with this data block."""
        return self._parse_info
    
    @property
    def sequence_header(self):
        """The :py:class:`SequenceHeader` associated with the current sequence."""
        return self._sequence_header


################################################################################
# fragment_parse and associated structures
################################################################################

class FragmentParse(LabelledConcatenation):
    """
    (14.1) A fragment data unit defined by ``picture_parse()`` containing part
    of a picture.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"padding"`` (:py:class:`ByteAlign`)
    * ``"fragment_header"`` (:py:class:`FragmentHeader`)
    * ``"post_header_padding"`` (:py:class:`ByteAlign`)
    * ``"transform_parameters"`` (:py:class:`TransformParameters` in a
      :py:class:`Maybe`)
    * ``"ld_fragment_data"`` (:py:class:`LDSliceArray` in a
      :py:class:`Maybe` predicated on the fragment type and picture type)
    * ``"hq_fragment_data"`` (:py:class:`HQSliceArray` in a
      :py:class:`Maybe` predicated on the fragment type and picture type)
    """
    
    def __init__(self,
                 parse_info=ParseInfo(),
                 sequence_header=SequenceHeader(),
                 previous_fragment_parse=None):
        """
        ``parse_info`` should be the :py;class:`ParseInfo` header associated
        with the data block this structure is contained in.
        
        ``sequence_header`` should be the :py;class:`SequenceHeader` associated
        with the current sequence (i.e. the one most recently received).
        
        ``previous_fragment_parse`` should be the last
        :py;class:`FragmentParse` received, or None if this is the first
        fragment received.
        """
        self._parse_info = parse_info
        self._sequence_header = sequence_header
        self._previous_fragment_parse = previous_fragment_parse
        
        fragment_header = FragmentHeader()
        
        is_fragment_parameters = fragment_header.is_fragment_parameters
        is_ld_fragment_data = FunctionValue(
            lambda fh, pi: fh.is_fragment_data.value and pi.is_low_delay.value,
            fragment_header,
            parse_info,
        )
        is_hq_fragment_data = FunctionValue(
            lambda fh, pi: fh.is_fragment_data.value and pi.is_high_quality.value,
            fragment_header,
            parse_info,
        )
        
        transform_parameters = Maybe(
            lambda: TransformParameters(self.parse_info, self.sequence_header),
            is_fragment_parameters,
        )
        
        if self.previous_fragment_parse is None:
            # Provide an arbitrary set of transform parameters if no previous
            # ones are available.
            previous_transform_parameters = TransformParameters(
                self.parse_info,
                self.sequence_header,
            )
        else:
            previous_transform_parameters = self.previous_fragment_parse.transform_parameters
        
        self._transform_parameters = FunctionValue(
            FragmentParse.compute_transform_parameters
            previous_transform_parameters,
            transform_parameters,
        )
        
        super(FragmentParse, self).__init__(
            "fragment_parse:",
            ("padding", ByteAlign()),
            ("fragment_header", fragment_header),
            ("post_header_padding", ByteAlign()),
            (
                "transform_parameters",
                transform_parameters,
            ),
            (
                "ld_fragment_data",
                Maybe(
                    LDSliceArray(
                        self.sequence_header,
                        self.transform_parameters,
                        fragment_header["fragment_x_offset"],
                        fragment_header["fragment_y_offset"],
                        fragment_header["fragment_slice_count"],
                    ),
                    is_ld_fragment_data,
                ),
            ),
            (
                "hq_fragment_data",
                Maybe(
                    HQSliceArray(
                        self.sequence_header,
                        self.transform_parameters,
                        fragment_header["fragment_x_offset"],
                        fragment_header["fragment_y_offset"],
                        fragment_header["fragment_slice_count"],
                    ),
                    is_hq_fragment_data,
                ),
            ),
        )
    
    @property
    def parse_info(self):
        """The :py:class:`ParseInfo` associated with this data block."""
        return self._parse_info
    
    @property
    def sequence_header(self):
        """The :py:class:`SequenceHeader` associated with the current sequence."""
        return self._sequence_header
    
    @property
    def previous_fragment_parse(self):
        """
        The :py:class:`FragmentParse` which came before this one (or None if
        this is the first).
        """
        return self._previous_fragment_parse
    
    @property
    def transform_parameters(self):
        """
        The :py:class:`TransformParameters` associated with the current
        fragment (i.e. the ones most recently received).
        """
        return self._transform_parameters
    
    @staticmethod
    def compute_transform_parameters(previous_transform_parameters, transform_parameters)
        """
        Determine the current :py;class:`TransformParameters` using the
        previous fragment's :py:attr:`FragmentParse.transform_parameters` and
        the :py:class:`Maybe` which contains the
        :py:class:`TransformParameters` for parameter-containing fragments in
        the current fragment..
        """
        if transform_parameters.flag:
            return transform_parameters.inner_value
        else:
            return previous_transform_parameters.value


class FragmentHeader(LabelledConcatenation):
    """
    (14.2) Fragment header defined by ``fragment_header()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"picture_number"`` (32-bit :py:class:`NBits`)
    * ``"fragment_data_length"`` (16-bit :py:class:`NBits`)
    * ``"fragment_slice_count"`` (16-bit :py:class:`NBits`)
    * ``"fragment_x_offset"`` (16-bit :py:class:`NBits`, in a
      :py:class:`Maybe`)
    * ``"fragment_y_offset"`` (16-bit :py:class:`NBits`, in a
      :py:class:`Maybe`)
    """
    
    def __init__(self):
        fragment_slice_count = NBits(fragment_slice_count, length=16)
        
        self._is_fragment_parameters = FunctionValue(
            lambda fragment_slice_count: fragment_slice_count.value == 0,
            fragment_slice_count,
        )
        self._is_fragment_data = FunctionValue(
            lambda fragment_slice_count: fragment_slice_count.value != 0,
            fragment_slice_count,
        )
        
        super(FragmentHeader, self).__init__(
            "fragment_header:",
            ("picture_number", NBits(0, length=32)),
            ("fragment_data_length", NBits(0, length=16)),
            ("fragment_slice_count", fragment_slice_count),
            ("fragment_x_offset", Maybe(lambda: NBits(length=16), self.is_fragment_data)),
            ("fragment_y_offset", Maybe(lambda: NBits(length=16), self.is_fragment_data)),
        )
    
    def is_fragment_parameters(self):
        """
        A :py:class:`BitstreamValue` which is 'True' if this fragment contains
        only transform parameter information.
        """
        return self._is_fragment_parameters
    
    def is_fragment_data(self):
        """
        A :py:class:`BitstreamValue` which is 'True' if this fragment contains
        data (not a header).
        """
        return self._is_fragment_data
