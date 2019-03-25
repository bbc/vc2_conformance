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


__all__ = [
    "ParseInfo",
    "DataUnit",
    "AuxiliaryData",
    "Padding",
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
    "PictureParse",
    "TransformParameters",
    "ExtendedTransformParameters",
    "SliceParameters",
    "QuantMatrix",
    "TransformData",
    "FragmentParse",
    "FragmentHeader",
    "FragmentData",
    "Slice",
    "LDSlice",
    "HQSlice",
    "SliceBand",
    "ColorDiffSliceBand",
]


class ParseInfo(LabelledConcatenation):
    """
    (10.5.1) Parse info header defined by ``parse_info()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"parse_info_prefix"`` (:py:class:`NBits`)
    * ``"parse_code"`` (:py:class:`NBits` containing :py:class:`ParseCodes`)
    * ``"next_parse_offset"`` (:py:class:`NBits`)
    * ``"previous_parse_offset"`` (:py:class:`NBits`)
    """
    
    def __init__(self,
                 parse_info_prefix=PARSE_INFO_PREFIX,
                 parse_code=ParseCodes.end_of_sequence,
                 next_parse_offset=0,
                 previous_parse_offset=0):
        super(ParseInfo, self).__init__(
            "parse_info:",
            (
                "parse_info_prefix",
                NBits(parse_info_prefix, 32, formatter=Hex(8)),
            ),
            (
                "parse_code",
                NBits(parse_code, 8, formatter=Hex(2), enum=ParseCodes),
            ),
            ("next_parse_offset", NBits(next_parse_offset, 32)),
            ("previous_parse_offset", NBits(previous_parse_offset, 32)),
        )


class DataUnit(LabelledConcatenation):
    """
    (10.4.1) A data unit in a parse sequence.
    
    A :py:class:`LabelledConcatenation` with the following fields (of which at
    most one will contain valid data, depending on the 'parse_code' provided:
    
    * ``"parse_info"`` (:py:class:`ParseInfo`)
    * ``"sequence_header"`` (:py:class:`SequenceHeader` in a :py:class:`Maybe`)
    * ``"picture_parse"`` (:py:class:`PictureParse` in a :py:class:`Maybe`)
    * ``"fragment_parse"`` (:py:class:`FragmentParse` in a :py:class:`Maybe`)
    * ``"auxiliary_data"`` (:py:class:`AuxiliaryData` in a :py:class:`Maybe`)
    * ``"padding"`` (:py:class:`Padding` in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 parse_code=ParseCodes.end_of_sequence,
                 length_bytes=0,
                 previous_major_version=3,
                 previous_luma_dimensions=(0, 0),
                 previous_color_diff_dimensions=(0, 0),
                 previous_slices_x=1,
                 previous_slices_y=1,
                 previous_slice_bytes_numerator=0,
                 previous_slice_bytes_denominator=1,
                 previous_slice_prefix_bytes=0,
                 previous_slice_size_scaler=1,
                 previous_dwt_depth=0,
                 previous_dwt_depth_ho=0,
                 previous_fragment_slices_received=0):
        """
        The ``parse_code`` and ``length_bytes`` arguments may be either
        constants or functions taking no arguments and producing a constant.
        
        ``parse_code`` should be an int or :py:class:`ParseCodes` (or a
        function returning one of these) and will be used to determine which
        (if any) of the contained values is included in the bitstream.
        
        ``length_bytes`` should be an int (or a function returning one) and
        give the length of this data unit as reported by the ParseInfo header.
        This value may be invalid for data units which do not need it (i.e.
        data units which are not auxiliary/padding data).
        
        The various arguments prefixed with ``previous_`` should be the
        last-known values of those parameters. These arguments are only used by
        certain data-unit types and so need not always be valid. For each of
        these parameters, an equivalent property is provided by this class
        giving the new value following the receipt of this data-unit.
        
        ``previous_major_version`` should be an int (or a function returning
        one) giving the VC-2 bitstream version in use (from the
        :py:class:`ParseParameters` header).
        
        ``previous_luma_dimensions`` and ``previous_color_diff_dimensions``
        should be (w, h) tuples (or functions returning them) giving the
        picture component dimensios for the luminance and color difference
        components respectively. Obtained from :py:class:`SequenceHeader`.
        
        ``previous_slices_x`` and ``previous_slices_y``
        should be integers (or functions returning them) giving the
        number of slices being used by the current fragment. Obtained
        from :py:class:`SliceParameters`.
        
        ``previous_slice_bytes_numerator``,
        ``previous_slice_bytes_denominator``, ``previous_slice_prefix_bytes``
        and ``previous_slice_size_scaler`` should be integers (or functions
        returning them) giving size information for the slices used by the
        current fragment. Obtained from :py:class:`SliceParameters`.
        
        ``previous_dwt_depth`` and ``previous_dwt_depth_ho`` should be integers
        (or functions returning them) giving wavelet transform depth
        information for the slices used by the current fragment. Obtained from
        :py:class:`TransformParameters` and
        :py:class:`ExtendedTransformParameters`.
        
        ``previous_fragment_slices_received`` should be an integer (or a
        function returning one) giving the number of slices received by
        previous fragments. Obtained from :py:class:`FragmentParse`.
        """
        self.parse_code = parse_code
        self.length_bytes = length_bytes
        
        self.previous_major_version = previous_major_version
        self.previous_luma_dimensions = previous_luma_dimensions
        self.previous_color_diff_dimensions = previous_color_diff_dimensions
        
        self.previous_slices_x = previous_slices_x
        self.previous_slices_y = previous_slices_y
        self.previous_slice_bytes_numerator = previous_slice_bytes_numerator
        self.previous_slice_bytes_denominator = previous_slice_bytes_denominator
        self.previous_slice_prefix_bytes = previous_slice_prefix_bytes
        self.previous_slice_size_scaler = previous_slice_size_scaler
        self.previous_dwt_depth = previous_dwt_depth
        self.previous_dwt_depth_ho = previous_dwt_depth_ho
        self.previous_fragment_slices_received = previous_fragment_slices_received
        
        super(DataUnit, self).__init__(
            ("sequence_header", Maybe(SequenceHeader(), self.is_sequence_header)),
            (
                "picture_parse",
                Maybe(
                    PictureParse(
                        parse_code=lambda: self.parse_code,
                        major_version=lambda: self.previous_major_version,
                        luma_dimensions=lambda: self.previous_luma_dimensions,
                        color_diff_dimensions=lambda: self.previous_color_diff_dimensions,
                    ),
                    self.is_picture_parse,
                ),
            ),
            # Errata: In (10.4.1) parse_sequence() this entry is called
            # fragment() but the intended function is later defined as
            # 'fragment_parse()' in (14.1).
            (
                "fragment_parse",
                Maybe(
                    FragmentParse(
                        parse_code=lambda: self.parse_code,
                        major_version=lambda: self.previous_major_version,
                        luma_dimensions=lambda: self.previous_luma_dimensions,
                        color_diff_dimensions=lambda: self.previous_color_diff_dimensions,
                        previous_fragment_slices_received=lambda: self.previous_fragment_slices_received,
                        previous_slices_x=lambda: self.previous_slices_x,
                        previous_slices_y=lambda: self.previous_slices_y,
                        previous_slice_bytes_numerator=lambda: self.previous_slice_bytes_numerator,
                        previous_slice_bytes_denominator=lambda: self.previous_slice_bytes_denominator,
                        previous_slice_prefix_bytes=lambda: self.previous_slice_prefix_bytes,
                        previous_slice_size_scaler=lambda: self.previous_slice_size_scaler,
                        previous_dwt_depth=self.previous_dwt_depth,
                        previous_dwt_depth_ho=self.previous_dwt_depth_ho,
                    ),
                    self.is_fragment_parse,
                ),
            ),
            (
                "auxiliary_data",
                Maybe(
                    AuxiliaryData(lambda: length_bytes),
                    self.is_auxiliary_data,
                ),
            ),
            (
                "padding",
                Maybe(
                    Padding(lambda: length_bytes),
                    self.is_padding,
                ),
            ),
        )
    
    parse_code = function_property()
    length_bytes = function_property()
    
    previous_major_version = function_property()
    previous_luma_dimensions = function_property()
    previous_color_diff_dimensions = function_property()
    
    previous_slices_x = function_property()
    previous_slices_y = function_property()
    previous_slice_bytes_numerator = function_property()
    previous_slice_bytes_denominator = function_property()
    previous_slice_prefix_bytes = function_property()
    previous_slice_size_scaler = function_property()
    previous_dwt_depth = function_property()
    previous_dwt_depth_ho = function_property()
    previous_fragment_slices_received = function_property()
    
    @property
    def chosen_unit(self):
        """
        Return the label string of the currently chosen data unit, or None if
        none are selected.
        """
        try:
            parse_code = ParseCodes(self.parse_code)
        except ValueError:
            return None
        
        # The logic below matches the routine in the ``parse_sequence()``
        # function in section (10.4.1) of the VC-2 spec.
        if parse_code is ParseCodes.sequence_header:
            return "sequence_header"
        elif parse_code.is_picture:
            return "picture_parse"
        elif parse_code.is_fragment:
            return "fragment_parse"
        elif parse_code is ParseCodes.auxiliary_data:
            return "auxiliary_data"
        elif parse_code is ParseCodes.padding_data:
            return "padding"
        else:
            return None
    
    def is_sequence_header(self):
        """Not to be confused with ``is_seq_header()`` from the VC-2 spec."""
        return self.chosen_unit == "sequence_header"
    
    def is_picture_parse(self):
        """Not to be confused with ``is_picture()`` from the VC-2 spec."""
        return self.chosen_unit == "picture_parse"
    
    def is_fragment_parse(self):
        """Not to be confused with ``is_fragment()`` from the VC-2 spec."""
        return self.chosen_unit == "fragment_parse"
    
    def is_auxiliary_data(self):
        """Not to be confused with ``is_auxiliary_data()`` from the VC-2 spec."""
        return self.chosen_unit == "auxiliary_data"
    
    def is_padding(self):
        """Not to be confused with ``is_padding()`` from the VC-2 spec."""
        return self.chosen_unit == "padding"
    
    @property
    def major_version(self):
        if self.is_sequence_header():
            return self["sequence_header"]["parse_parameters"]["major_version"].value
        else:
            return self.previous_major_version
    
    @property
    def luma_dimensions(self):
        if self.is_sequence_header():
            return self["sequence_header"].inner_value.luma_dimensions
        else:
            return self.previous_luma_dimensions
    
    @property
    def color_diff_dimensions(self):
        if self.is_sequence_header():
            return self["sequence_header"].inner_value.color_diff_dimensions
        else:
            return self.previous_color_diff_dimensions
    
    @property
    def slices_x(self):
        if self.is_fragment_parse():
            return self["fragment_parse"].inner_value.slices_x
        else:
            return self.previous_slices_x
    
    @property
    def slices_y(self):
        if self.is_fragment_parse():
            return self["fragment_parse"].inner_value.slices_y
        else:
            return self.previous_slices_y
    
    @property
    def slice_bytes_numerator(self):
        if self.is_fragment_parse():
            return self["fragment_parse"].inner_value.slice_bytes_numerator
        else:
            return self.previous_slice_bytes_numerator
    
    @property
    def slice_bytes_denominator(self):
        if self.is_fragment_parse():
            return self["fragment_parse"].inner_value.slice_bytes_denominator
        else:
            return self.previous_slice_bytes_denominator
    
    @property
    def slice_prefix_bytes(self):
        if self.is_fragment_parse():
            return self["fragment_parse"].inner_value.slice_prefix_bytes
        else:
            return self.previous_slice_prefix_bytes
    
    @property
    def slice_size_scaler(self):
        if self.is_fragment_parse():
            return self["fragment_parse"].inner_value.slice_size_scaler
        else:
            return self.previous_slice_size_scaler
    
    @property
    def dwt_depth(self):
        if self.is_fragment_parse():
            return self["fragment_parse"].inner_value.dwt_depth
        else:
            return self.previous_dwt_depth
    
    @property
    def dwt_depth_ho(self):
        if self.is_fragment_parse():
            return self["fragment_parse"].inner_value.dwt_depth_ho
        else:
            return self.previous_dwt_depth_ho
    
    @property
    def fragment_slices_received(self):
        if self.is_fragment_parse():
            return self["fragment_parse"].inner_value.fragment_slices_received
        else:
            return self.previous_fragment_slices_received


class AuxiliaryData(Array):
    """
    (10.4.4) Auxiliary data block.
    
    A :py:class:`Array` containing the bytes in the block as 8-bit
    :py:class:`NBits` values.
    """
    
    def __init__(self, num_bytes=0):
        self.num_bytes = num_bytes
        super(AuxiliaryData, self).__init__(
            lambda: NBits(length=8, formatter=Hex(2)),
            lambda: max(0, self.num_bytes),
        )
    
    num_bytes = function_property()


class Padding(Array):
    """
    (10.4.5) Padding data block.
    
    A :py:class:`Array` containing the bytes in the block as 8-bit
    :py:class:`NBits` values.
    """
    
    def __init__(self, num_bytes=0):
        self.num_bytes = num_bytes
        super(Padding, self).__init__(
            lambda: NBits(length=8, formatter=Hex(2)),
            lambda: max(0, self.num_bytes),
        )
    
    num_bytes = function_property()


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
    """
    
    def __init__(self,
                 base_video_format=BaseVideoFormats.custom_format,
                 picture_coding_mode=PictureCodingModes.pictures_are_frames):
        super(SequenceHeader, self).__init__(
            "sequence_header:",
            ("parse_parameters", ParseParameters()),
            (
                "base_video_format",
                UInt(base_video_format, enum=BaseVideoFormats),
            ),
            ("video_parameters", SourceParameters()),
            (
                "picture_coding_mode",
                UInt(picture_coding_mode, enum=PictureCodingModes),
            ),
        )
    
    @property
    def luma_dimensions(self):
        """
        (11.6.2) The (width, height) of the luminance picture component, as
        defined in this header by ``picture_dimensions()``.
        """
        # (11.4.2) set_source_defaults() -- Start off with preset dimensions
        try:
            base = BASE_VIDEO_FORMAT_PARAMETERS[
                BaseVideoFormats(self["base_video_format"].value)]
            luma_width = base.frame_width
            luma_height = base.frame_height
        except ValueError:
            # Arbitrary fallback value for out-of-spec base formats
            luma_width = 0
            luma_height = 0
        
        # (11.4.3) frame_size() -- Override with custom values
        frame_size = self["video_parameters"]["frame_size"]
        if frame_size["custom_dimensions_flag"].value:
            luma_width = frame_size["frame_width"].value
            luma_height = frame_size["frame_height"].value
        
        if self["picture_coding_mode"].value == PictureCodingModes.pictures_are_fields:
            luma_height //= 2
        
        return (luma_width, luma_height)
    
    @property
    def color_diff_dimensions(self):
        """
        (11.6.2) The (width, height) of the colour difference picture
        component, as defined in this header by ``picture_dimensions()``.
        """
        color_diff_width, color_diff_height = self.luma_dimensions
        
        # (11.4.2) set_source_defaults() -- Start off with preset color diff
        # sampling format aand source sampling mode
        try:
            base = BASE_VIDEO_FORMAT_PARAMETERS[
                BaseVideoFormats(self["base_video_format"].value)]
            color_diff_format_index = base.color_diff_format_index
        except ValueError:
            # Arbitrary fallback value for out-of-spec base formats
            color_diff_format_index = ColorDifferenceSamplingFormats.color_4_4_4

        # (11.4.4) color_diff_sampling_format() -- Override color diff sampling
        # format
        color_diff_sampling_format = self["video_parameters"]["color_diff_sampling_format"]
        if color_diff_sampling_format["custom_color_diff_format_flag"].value:
            color_diff_format_index = color_diff_sampling_format["color_diff_format_index"].value
        
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
    
    def __init__(self,
                 major_version=3,
                 minor_version=0,
                 profile=Profiles.high_quality,
                 level=0):
        super(ParseParameters, self).__init__(
            "parse_parameters:",
            ("major_version", UInt(major_version)),
            ("minor_version", UInt(minor_version)),
            ("profile", UInt(profile, enum=Profiles)),
            ("level", UInt(level)),
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
    
    def __init__(self, custom_dimensions_flag=False, frame_width=0, frame_height=0):
        flag = Bool(custom_dimensions_flag)
        is_custom = lambda: flag.value
        super(FrameSize, self).__init__(
            "frame_size:",
            ("custom_dimensions_flag", flag),
            ("frame_width", Maybe(UInt(frame_width), is_custom)),
            ("frame_height", Maybe(UInt(frame_height), is_custom)),
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
    
    def __init__(self,
                 custom_color_diff_format_flag=False,
                 color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4):
        flag = Bool(custom_color_diff_format_flag)
        super(ColorDiffSamplingFormat, self).__init__(
            "color_diff_sampling_format:",
            ("custom_color_diff_format_flag", flag),
            (
                "color_diff_format_index",
                Maybe(
                    UInt(
                        color_diff_format_index,
                        enum=ColorDifferenceSamplingFormats,
                    ),
                    lambda: flag.value,
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
    
    def __init__(self,
                 custom_scan_format_flag=False,
                 source_sampling=SourceSamplingModes.progressive):
        flag = Bool(custom_scan_format_flag)
        super(ScanFormat, self).__init__(
            "scan_format:",
            ("custom_scan_format_flag", flag),
            (
                "source_sampling",
                Maybe(
                    UInt(source_sampling, enum=SourceSamplingModes),
                    lambda: flag.value,
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
    
    def __init__(self,
                 custom_frame_rate_flag=False,
                 index=0,
                 frame_rate_numer=0,
                 frame_rate_denom=1):
        flag = Bool(custom_frame_rate_flag)
        index = Maybe(
            UInt(
                index,
                enum=PresetFrameRates,
                # Show the preset framerate in a more human-readable form than
                # the enum name
                get_value_name=(
                    lambda p:
                    "{} fps".format(PRESET_FRAME_RATES[PresetFrameRates(p)])
                ),
            ),
            lambda: flag.value,
        )
        is_full_custom = lambda: flag.value and index.value == 0
        super(FrameRate, self).__init__(
            "frame_rate:",
            ("custom_frame_rate_flag", flag),
            ("index", index),
            ("frame_rate_numer", Maybe(UInt(frame_rate_numer), is_full_custom)),
            ("frame_rate_denom", Maybe(UInt(frame_rate_denom), is_full_custom)),
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
    
    @staticmethod
    def _get_index_value_name(index):
        """
        A 'get_value_name' compatible function to return a human-readable
        version of an aspect ratio index.
        """
        enum_value = PresetPixelAspectRatios(index)
        ratio = PRESET_PIXEL_ASPECT_RATIOS[enum_value]
        return "{}:{}".format(ratio.numerator, ratio.denominator)
    
    def __init__(self,
                 custom_pixel_aspect_ratio_flag=False,
                 index=PresetPixelAspectRatios.ratio_1_1,
                 pixel_aspect_ratio_numer=1,
                 pixel_aspect_ratio_denom=1):
        flag = Bool(custom_pixel_aspect_ratio_flag)
        index = Maybe(
            UInt(
                index,
                enum=PresetPixelAspectRatios,
                get_value_name=PixelAspectRatio._get_index_value_name
            ),
            lambda: flag.value,
        )
        is_full_custom = lambda: flag.value and index.value == 0
        super(PixelAspectRatio, self).__init__(
            "pixel_aspect_ratio:",
            ("custom_pixel_aspect_ratio_flag", flag),
            ("index", index),
            ("pixel_aspect_ratio_numer", Maybe(UInt(pixel_aspect_ratio_numer), is_full_custom)),
            ("pixel_aspect_ratio_denom", Maybe(UInt(pixel_aspect_ratio_denom), is_full_custom)),
        )


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
    
    def __init__(self,
                 custom_clean_area_flag=False,
                 clean_width=1,
                 clean_height=1,
                 left_offset=0,
                 top_offset=0):
        flag = Bool(custom_clean_area_flag)
        is_custom = lambda: flag.value
        super(CleanArea, self).__init__(
            "clean_area:",
            ("custom_clean_area_flag", flag),
            ("clean_width", Maybe(UInt(clean_width), is_custom)),
            ("clean_height", Maybe(UInt(clean_height), is_custom)),
            ("left_offset", Maybe(UInt(left_offset), is_custom)),
            ("top_offset", Maybe(UInt(top_offset), is_custom)),
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
    
    def __init__(self,
                 custom_signal_range_flag=False,
                 index=0,
                 luma_offset=0,
                 luma_excursion=1,
                 color_diff_offset=0,
                 color_diff_excursion=1):
        flag = Bool(custom_signal_range_flag)
        index = Maybe(UInt(index, enum=PresetSignalRanges), lambda: flag.value)
        is_full_custom = lambda: flag.value and index.value == 0
        super(SignalRange, self).__init__(
            "signal_range:",
            ("custom_signal_range_flag", flag),
            ("index", index),
            ("luma_offset", Maybe(UInt(luma_offset), is_full_custom)),
            ("luma_excursion", Maybe(UInt(luma_excursion), is_full_custom)),
            ("color_diff_offset", Maybe(UInt(color_diff_offset), is_full_custom)),
            ("color_diff_excursion", Maybe(UInt(color_diff_excursion), is_full_custom)),
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
    
    def __init__(self,
                 custom_color_spec_flag=False,
                 index=PresetColorSpecs.custom,
                 custom_color_primaries_flag=False,
                 color_primaries_index=PresetColorPrimaries.hdtv,
                 custom_color_matrix_flag=False,
                 color_matrix_index=PresetColorMatrices.hdtv,
                 custom_transfer_function_flag=False,
                 transfer_function_index=PresetTransferFunctions.tv_gamma):
        flag = Bool(custom_color_spec_flag)
        index = Maybe(UInt(index, enum=PresetColorSpecs), lambda: flag.value)
        is_full_custom = lambda: flag.value and index.value == PresetColorSpecs.custom
        super(ColorSpec, self).__init__(
            "color_spec:",
            ("custom_color_spec_flag", flag),
            ("index", index),
            (
                "color_primaries",
                Maybe(
                    ColorPrimaries(
                        custom_color_primaries_flag,
                        color_primaries_index,
                    ),
                    is_full_custom,
                )
            ),
            (
                "color_matrix",
                Maybe(
                    ColorMatrix(
                        custom_color_matrix_flag,
                        color_matrix_index,
                    ),
                    is_full_custom,
                )
            ),
            (
                "transfer_function",
                Maybe(
                    TransferFunction(
                        custom_transfer_function_flag,
                        transfer_function_index,
                    ),
                    is_full_custom,
                )
            ),
        )


class ColorPrimaries(LabelledConcatenation):
    """
    (11.4.10.2) Colour primaries override defined by ``color_primaries()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_color_primaries_flag"`` (:py:class:`Bool`)
    * ``"index"`` (:py:class:`UInt` containing
      :py:class:`PresetColorPrimaries`, in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 custom_color_primaries_flag=False,
                 index=PresetColorPrimaries.hdtv):
        flag = Bool(custom_color_primaries_flag)
        super(ColorPrimaries, self).__init__(
            "color_primaries:",
            ("custom_color_primaries_flag", flag),
            (
                "index",
                Maybe(
                    UInt(index, enum=PresetColorPrimaries),
                    lambda: flag.value,
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
    
    def __init__(self,
                 custom_color_matrix_flag=False,
                 index=PresetColorMatrices.hdtv):
        flag = Bool(custom_color_matrix_flag)
        super(ColorMatrix, self).__init__(
            "color_matrix:",
            ("custom_color_matrix_flag", flag),
            (
                "index",
                Maybe(
                    UInt(index, enum=PresetColorMatrices),
                    lambda: flag.value,
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
    
    def __init__(self,
                 custom_transfer_function_flag=False,
                 index=PresetTransferFunctions.tv_gamma):
        flag = Bool(custom_transfer_function_flag)
        super(TransferFunction, self).__init__(
            "transfer_function:",
            ("custom_transfer_function_flag", flag),
            (
                "index",
                Maybe(
                    UInt(index, enum=PresetTransferFunctions),
                    lambda: flag.value,
                ),
            ),
        )


class PictureParse(LabelledConcatenation):
    """
    (12.1) A picture data unit defined by ``picture_parse()``
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"padding"`` (:py:class:`ByteAlign`)
    * ``"picture_header"`` (:py:class:`PictureHeader`)
    * ``"wavelet_transform"`` (:py:class:`WaveletTransform` in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 parse_code=ParseCodes.high_quality_picture,
                 major_version=3,
                 luma_dimensions=(0, 0),
                 color_diff_dimensions=(0, 0)):
        """
        ``parse_code`` should be the :py:class:`ParseCodes` (or a function
        returning one) from the associated :py:class:`ParseInfo`.
        
        ``major_version`` should be the version number (or a function returning
        one) from the associated :py:class:`ParseInfo`.
        
        ``luma_dimensions`` and ``color_diff_dimensions`` should be tuples
        (width, height) (or functions returning as such) giving the picture
        component dimensios for the luminance and color difference components
        respectively.
        """
        self.parse_code = parse_code
        self.major_version = major_version
        self.luma_dimensions = luma_dimensions
        self.color_diff_dimensions = color_diff_dimensions
        
        super(PictureParse, self).__init__(
            "picture_parse:",
            ("padding", ByteAlign()),
            ("picture_header", PictureHeader()),
            (
                "wavelet_transform",
                WaveletTransform(
                    lambda: self.parse_code,
                    lambda: self.major_version,
                    lambda: self.luma_dimensions,
                    lambda: self.color_diff_dimensions,
                ),
            ),
        )
    
    parse_code = function_property()
    major_version = function_property()
    luma_dimensions = function_property()
    color_diff_dimensions = function_property()


class PictureHeader(LabelledConcatenation):
    """
    (12.2) Picture header information defined by ``picture_header()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"picture_number"`` (a 32-bit :py:class:`NBits`)
    """
    
    def __init__(self, picture_number=0):
        super(PictureHeader, self).__init__(
            "picture_header:",
            ("picture_number", NBits(picture_number, length=32)),
        )


class WaveletTransform(LabelledConcatenation):
    """
    (12.3) Wavelet parameters and coefficients defined by
    ``wavelet_transform()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"transform_parameters"`` (:py:class:`TransformParameters`)
    * ``"padding"`` (:py:class:`ByteAlign`)
    * ``"transform_data"`` (:py:class:`TransformData`)
    """
    
    def __init__(self,
                 parse_code=ParseCodes.high_quality_picture,
                 major_version=3,
                 luma_dimensions=(0, 0),
                 color_diff_dimensions=(0, 0)):
        """
        ``parse_code`` should be the :py:class:`ParseCodes` (or a function
        returning one) from the associated :py:class:`ParseInfo`.
        
        ``major_version`` should be the version number (or a function returning
        one) from the associated :py:class:`ParseInfo`.
        
        ``luma_width``, ``luma_height``, ``color_diff_width`` and
        ``color_diff_height`` should be integers (or functions returning
        integers) giving the picture component dimensios for the luminance and
        color difference components respectively.
        """
        self.parse_code = parse_code
        self.major_version = major_version
        self.luma_dimensions = luma_dimensions
        self.color_diff_dimensions = color_diff_dimensions
        
        transform_parameters = TransformParameters(
            lambda: self.parse_code,
            lambda: self.major_version,
        )
        
        super(WaveletTransform, self).__init__(
            "wavelet_transform:",
            ("transform_parameters", transform_parameters),
            ("padding", ByteAlign()),
            (
                "transform_data",
                TransformData(
                    lambda: transform_parameters["slice_parameters"]["slices_x"].value,
                    lambda: transform_parameters["slice_parameters"]["slices_y"].value,
                    lambda: self.parse_code,
                    lambda: transform_parameters["slice_parameters"]["slice_bytes_numerator"].value,
                    lambda: transform_parameters["slice_parameters"]["slice_bytes_denominator"].value,
                    lambda: transform_parameters["slice_parameters"]["slice_prefix_bytes"].value,
                    lambda: transform_parameters["slice_parameters"]["slice_size_scaler"].value,
                    lambda: transform_parameters.dwt_depth,
                    lambda: transform_parameters.dwt_depth_ho,
                    lambda: self.luma_dimensions,
                    lambda: self.color_diff_dimensions,
                ),
            ),
        )
    
    parse_code = function_property()
    major_version = function_property()
    luma_dimensions = function_property()
    color_diff_dimensions = function_property()


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
    
    def __init__(self,
                 parse_code=ParseCodes.high_quality_picture,
                 major_version=3):
        """
        ``parse_code`` should be the :py:class:`ParseCodes` (or a function
        returning one) from the associated :py:class:`ParseInfo`.
        
        ``major_version`` should be the version number (or a function returning
        one) from the associated :py:class:`ParseInfo`.
        """
        self.parse_code = parse_code
        self.major_version = major_version
        
        self._wavelet_index = UInt(enum=WaveletFilters)
        self._dwt_depth = UInt()
        self._ext_transform_paramters = Maybe(ExtendedTransformParameters(), lambda: self.extended)
        
        super(TransformParameters, self).__init__(
            "transform_parameters:",
            ("wavelet_index", self._wavelet_index),
            ("dwt_depth", self._dwt_depth),
            ("extended_transform_parameters", self._ext_transform_paramters),
            ("slice_parameters", SliceParameters(lambda: self.parse_code)),
            ("quant_matrix", QuantMatrix(lambda: self.dwt_depth, lambda: self.dwt_depth_ho)),
        )
    
    parse_code = function_property()
    major_version = function_property()
    
    @property
    def extended(self):
        """Does this structure include the extended_transform_parameters?"""
        # As specified in (12.4.1)
        return self.major_version >= 3
    
    @property
    def dwt_depth(self):
        """
        The 2D wavelet depth specified by this structure.
        
        Alias for ``params["dwt_depth"].value``, provided for symmetry with
        :py:attr:`dwt_depth_ho`.
        """
        return self._dwt_depth.value
    
    @property
    def dwt_depth_ho(self):
        """
        The 2D wavelet depth specified by this structure.
        
        Computed in the manner specified by (12.4.1) ``transform_parameters()``
        and (12.4.4.1) ``extended_transform_parameters()``.
        """
        if self.extended and self._ext_transform_paramters["asym_transform_flag"].value:
            return self._ext_transform_paramters["dwt_depth_ho"].value
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
            ("wavelet_index_ho", Maybe(UInt(enum=WaveletFilters), lambda: index_flag.value)),
            ("asym_transform_flag", transform_flag),
            ("dwt_depth_ho", Maybe(UInt(), lambda: transform_flag.value)),
        )


class SliceParameters(LabelledConcatenation):
    """
    (12.4.5.2) Slice dimension parameters defined by ``slice_parameters()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"slices_x"`` (:py:class:`UInt`)
    * ``"slices_y"`` (:py:class:`UInt`)
    * ``"slice_bytes_numerator"`` (:py:class:`UInt` in a :py:class:`Maybe`
      predicated on a :py:attr:`ParseCodes.is_ld`)
    * ``"slice_bytes_denominator"`` (:py:class:`UInt` in a :py:class:`Maybe`
      predicated on a :py:attr:`ParseCodes.is_ld`)
    * ``"slice_prefix_bytes"`` (:py:class:`UInt` in a :py:class:`Maybe`
      predicated on a :py:attr:`ParseCodes.is_hq`)
    * ``"slice_size_scaler"`` (:py:class:`UInt` in a :py:class:`Maybe`
      predicated on a :py:attr:`ParseCodes.is_hq`)
    """
    
    def __init__(self, parse_code=ParseCodes.high_quality_picture):
        """
        ``parse_code`` should be the :py:class:`ParseCodes` (or a function
        returning one) from the associated :py:class:`ParseInfo`.
        """
        self.parse_code = parse_code
        
        def is_ld():
            try:
                return ParseCodes(self.parse_code).is_ld
            except ValueError:
                return False
        
        def is_hq():
            try:
                return ParseCodes(self.parse_code).is_hq
            except ValueError:
                return False
        
        super(SliceParameters, self).__init__(
            "slice_parameters:",
            ("slices_x", UInt(1)),
            ("slices_y", UInt(1)),
            ("slice_bytes_numerator", Maybe(UInt(0), is_ld)),
            ("slice_bytes_denominator", Maybe(UInt(1), is_ld)),
            ("slice_prefix_bytes", Maybe(UInt(0), is_hq)),
            ("slice_size_scaler", Maybe(UInt(1), is_hq)),
        )
    
    parse_code = function_property()


class QuantMatrix(LabelledConcatenation):
    """
    (12.4.5.3) Custom quantisation matrix override defined by ``quant_matrix()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"custom_quant_matrix"`` (:py:class:`Bool`)
    * ``"matrix"`` (a :py:class:`SubbandArray` of :py:class:`UInt` in a :py:class:`Maybe`)
    """
    
    def __init__(self, dwt_depth=0, dwt_depth_ho=0):
        """
        ``dwt_depth`` and ``dwt_depth_ho`` should be the depth of the 2D and
        horizontal-only wavelet transform stages (or functions returning those
        values).
        """
        self.dwt_depth = dwt_depth
        self.dwt_depth_ho = dwt_depth_ho
        
        flag = Bool()
        
        super(QuantMatrix, self).__init__(
            "quant_matrix:",
            ("custom_quant_matrix", flag),
            (
                "matrix",
                Maybe(
                    SubbandArray(
                        UInt,
                        lambda: self.dwt_depth,
                        lambda: self.dwt_depth_ho,
                    ),
                    lambda: flag.value,
                ),
            ),
        )
    
    dwt_depth = function_property()
    dwt_depth_ho = function_property()


class TransformData(RectangularArray):
    r"""
    (13.5.2) A :py:class:`RectangularArray` of :py:class:`Slice`\ s, arranged
    as defined by ``transform_data()``.
    
    For convenience, 2D indices may also be used to access slices::
    
        >>> d = TransformData(slices_x=4, slices_y=2)
        
        >>> assert d[0] is d[0, 0]
        >>> assert d[1] is d[1, 0]
        >>> assert d[2] is d[2, 0]
        >>> assert d[3] is d[3, 0]
        >>> assert d[4] is d[0, 1]
        >>> assert d[5] is d[1, 1]
        >>> assert d[6] is d[2, 1]
        >>> assert d[7] is d[3, 1]
    
    """
    
    def __init__(self,
                 slices_x=1,
                 slices_y=1,
                 parse_code=ParseCodes.high_quality_picture,
                 slice_bytes_numerator=0,
                 slice_bytes_denominator=1,
                 slice_prefix_bytes=0,
                 slice_size_scaler=1,
                 dwt_depth=0,
                 dwt_depth_ho=0,
                 luma_dimensions=(0, 0),
                 color_diff_dimensions=(0, 0)):
        """
        ``slices_x`` and ``slices_y`` should be ints (or functions returning
        ints) giving the number of slices in the array as defined by the
        associated :py:class:`SliceParameters`.
        
        ``parse_code`` should be the :py:class:`ParseCodes` (or a function
        returning one) from the associated :py:class:`ParseInfo`.
        
        
        ``slice_bytes_numerator``, ``slice_bytes_denominator``,
        ``slice_prefix_bytes`` and ``slice_size_scaler`` should be ints (or
        functions returning ints) with values taken from the associated
        :py:class:`SliceParameters`.
        
        ``dwt_depth`` and ``dwt_depth_ho`` should be the 2D and horizontal-only
        transform depths (or functions returning them) from the associated
        :py:class:`TransformParameters`.
        
        ``luma_width``, ``luma_height``, ``color_diff_width`` and
        ``color_diff_height`` should be integers (or functions returning
        integers) giving the picture component dimensios for the luminance and
        color difference components respectively.
        """
        self.slices_x = slices_x
        self.slices_y = slices_y
        self.parse_code = parse_code
        self.slice_bytes_numerator = slice_bytes_numerator
        self.slice_bytes_denominator = slice_bytes_denominator
        self.slice_prefix_bytes = slice_prefix_bytes
        self.slice_size_scaler = slice_size_scaler
        self.dwt_depth = dwt_depth
        self.dwt_depth_ho = dwt_depth_ho
        self.luma_dimensions = luma_dimensions
        self.color_diff_dimensions = color_diff_dimensions
        
        super(TransformData, self).__init__(
            # NB: the 'max' in sx and sy arguments below prevents
            # divide-by-zero exceptions when invalid input is provided
            # (meaningless values are produced instead).
            lambda i: Slice(lambda: i % max(1, self.slices_x),
                            lambda: i // max(1, self.slices_x),
                            lambda: self.slices_x,
                            lambda: self.slices_y,
                            lambda: self.parse_code,
                            lambda: self.slice_bytes_numerator,
                            lambda: self.slice_bytes_denominator,
                            lambda: self.slice_prefix_bytes,
                            lambda: self.slice_size_scaler,
                            lambda: self.dwt_depth,
                            lambda: self.dwt_depth_ho,
                            lambda: self.luma_dimensions,
                            lambda: self.color_diff_dimensions),
            None,
            None,
            pass_index=True,
        )
    
    @property
    def width(self):
        return self.slices_x
    
    @property
    def height(self):
        return self.slices_y
    
    slices_x = function_property()
    slices_y = function_property()
    parse_code = function_property()
    slice_bytes_numerator = function_property()
    slice_bytes_denominator = function_property()
    slice_prefix_bytes = function_property()
    slice_size_scaler = function_property()
    dwt_depth = function_property()
    dwt_depth_ho = function_property()
    luma_dimensions = function_property()
    color_diff_dimensions = function_property()


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
    * ``"fragment_data"`` (:py:class:`FragmentData` in a
      :py:class:`Maybe`)
    """
    
    def __init__(self,
                 parse_code=ParseCodes.high_quality_picture_fragment,
                 major_version=3,
                 luma_dimensions=(0, 0),
                 color_diff_dimensions=(0, 0),
                 previous_slices_x=1,
                 previous_slices_y=1,
                 previous_slice_bytes_numerator=0,
                 previous_slice_bytes_denominator=1,
                 previous_slice_prefix_bytes=0,
                 previous_slice_size_scaler=1,
                 previous_dwt_depth=0,
                 previous_dwt_depth_ho=0,
                 previous_fragment_slices_received=None):
        """
        ``parse_code`` should be the :py:class:`ParseCodes` (or a function
        returning one) from the associated :py:class:`ParseInfo`.
        
        ``major_version`` should be the version number (or a function returning
        one) from the associated :py:class:`ParseInfo`.
        
        ``luma_dimensions`` and ``color_diff_dimensions`` should be tuples
        (width, height) (or functions returning as such) giving the picture
        component dimensios for the luminance and color difference components
        respectively.
        
        The various arguments prefixed with ``previous_`` should be the
        last-known values of those parameters. These arguments are only used by
        certain data-unit types and so need not always be valid (and may be set
        to None). For each of these parameters, an equivalent property is
        provided by this class giving the new value following the receipt of
        this data-unit.
        
        ``previous_slices_x`` and ``previous_slices_y``
        should be integers (or functions returning them) giving the
        number of slices being used by the current fragment. Obtained
        from :py:class:`SliceParameters`.
        
        ``previous_slice_bytes_numerator``,
        ``previous_slice_bytes_denominator``, ``previous_slice_prefix_bytes``
        and ``previous_slice_size_scaler`` should be integers (or functions
        returning them) giving size information for the slices used by the
        current fragment. Obtained from :py:class:`SliceParameters`.
        
        ``previous_dwt_depth`` and ``previous_dwt_depth_ho`` should be integers
        (or functions returning them) giving wavelet transform depth
        information for the slices used by the current fragment. Obtained from
        :py:class:`TransformParameters` and
        :py:class:`ExtendedTransformParameters`.
        
        ``previous_fragment_slices_received`` should be an integer (or a
        function returning one) giving the number of slices received by
        previous fragments. Obtained from :py:class:`FragmentParse`.
        
        ``previous_fragment_slices_received`` may be None or an integer (or a
        function returning as such) giving the number of slices received in
        preceeding fragments since the last
        :py:class:`FragmentHeader`-containing :py:class:`FragmentParse` data
        unit. This value is used only to set the
        :py:attr:`fragment_slices_received` property of this instance and to
        insert an informational message in the string representation. It has no
        effect on the bitstream. Setting this value to None supresses the
        message. The update count following this fragment can be obtained from
        the :py:attr:`fragment_slices_received` property.
        """
        self.parse_code = parse_code
        self.major_version = major_version
        self.luma_dimensions = luma_dimensions
        self.color_diff_dimensions = color_diff_dimensions
        
        self.previous_slices_x = previous_slices_x
        self.previous_slices_y = previous_slices_y
        self.previous_slice_bytes_numerator = previous_slice_bytes_numerator
        self.previous_slice_bytes_denominator = previous_slice_bytes_denominator
        self.previous_slice_prefix_bytes = previous_slice_prefix_bytes
        self.previous_slice_size_scaler = previous_slice_size_scaler
        self.previous_dwt_depth = previous_dwt_depth
        self.previous_dwt_depth_ho = previous_dwt_depth_ho
        self.previous_fragment_slices_received = previous_fragment_slices_received
        
        self._fragment_header = FragmentHeader()
        
        super(FragmentParse, self).__init__(
            "fragment_parse:",
            ("padding", ByteAlign()),
            ("fragment_header", self._fragment_header),
            ("post_header_padding", ByteAlign()),
            (
                "transform_parameters",
                Maybe(
                    TransformParameters(
                        lambda: self.parse_code,
                        lambda: self.major_version,
                    ),
                    self.is_transform_parameters,
                ),
            ),
            (
                # <...> String substitution performed in __str__
                "fragment_data<FRAGMENT_SLICES_RECEIVED_MESSAGE>",
                Maybe(
                    FragmentData(
                        fragment_slice_count=lambda: self._fragment_header["fragment_slice_count"].value,
                        fragment_x_offset=lambda: self._fragment_header["fragment_x_offset"].value,
                        fragment_y_offset=lambda: self._fragment_header["fragment_y_offset"].value,
                        slices_x=lambda: self.previous_slices_x,
                        slices_y=lambda: self.previous_slices_y,
                        parse_code=lambda: self.parse_code,
                        slice_bytes_numerator=lambda: self.previous_slice_bytes_numerator,
                        slice_bytes_denominator=lambda: self.previous_slice_bytes_denominator,
                        slice_prefix_bytes=lambda: self.previous_slice_prefix_bytes,
                        slice_size_scaler=lambda: self.previous_slice_size_scaler,
                        dwt_depth=lambda: self.previous_dwt_depth,
                        dwt_depth_ho=lambda: self.previous_dwt_depth_ho,
                        luma_dimensions=lambda: self.luma_dimensions,
                        color_diff_dimensions=lambda: self.color_diff_dimensions,
                    ),
                    self.is_fragment_data,
                ),
            ),
        )
    
    def is_transform_parameters(self):
        """
        Does this :py:class:`FragmentParse` contain
        :py:class:`TransformParameters`?
        """
        return self._fragment_header["fragment_slice_count"].value == 0
    
    def is_fragment_data(self):
        """
        Does this :py:class:`FragmentParse` contain :py:class:`FragmentData`?
        """
        return self._fragment_header["fragment_slice_count"].value != 0
    
    def __str__(self):
        fragment_slices_received_message = ""
        if self.fragment_slices_received is not None:
            count = self._fragment_header["fragment_slice_count"].value
            last = self.fragment_slices_received
            first = last - count
            if count == 1:
                fragment_slices_received_message = " ({}{} slice received)".format(
                    first + 1, ordinal_indicator(first + 1),
                )
            elif count > 1:
                fragment_slices_received_message = " ({}{} - {}{} slices received)".format(
                    first + 1, ordinal_indicator(first + 1),
                    last, ordinal_indicator(last),
                )
        
        return super(FragmentParse, self).__str__().replace(
            "<FRAGMENT_SLICES_RECEIVED_MESSAGE>",
            fragment_slices_received_message
        )
    
    parse_code = function_property()
    major_version = function_property()
    luma_dimensions = function_property()
    color_diff_dimensions = function_property()
    
    previous_fragment_slices_received = function_property()
    previous_slices_x = function_property()
    previous_slices_y = function_property()
    previous_slice_bytes_numerator = function_property()
    previous_slice_bytes_denominator = function_property()
    previous_slice_prefix_bytes = function_property()
    previous_slice_size_scaler = function_property()
    previous_dwt_depth = function_property()
    previous_dwt_depth_ho = function_property()
    
    @property
    def fragment_slices_received(self):
        """
        The number of slices receieved in fragments prior to and including this
        one since the last set of transform parameters.
        
        If :py:class:`previous_fragment_slices_received` is None, this property
        will also be None.
        """
        if self.is_fragment_data():
            if self.previous_fragment_slices_received is not None:
                return (
                    self.previous_fragment_slices_received + 
                    self._fragment_header["fragment_slice_count"].value
                )
            else:
                return None
        else:
            return 0
    
    @property
    def slices_x(self):
        if self.is_transform_parameters():
            return self["transform_parameters"]["slice_parameters"]["slices_x"].value
        else:
            return self.previous_slices_x
    
    @property
    def slices_y(self):
        if self.is_transform_parameters():
            return self["transform_parameters"]["slice_parameters"]["slices_y"].value
        else:
            return self.previous_slices_y
    
    @property
    def slice_bytes_numerator(self):
        if self.is_transform_parameters():
            return self["transform_parameters"]["slice_parameters"]["slice_bytes_numerator"].value
        else:
            return self.previous_slice_bytes_numerator
    
    @property
    def slice_bytes_denominator(self):
        if self.is_transform_parameters():
            return self["transform_parameters"]["slice_parameters"]["slice_bytes_denominator"].value
        else:
            return self.previous_slice_bytes_denominator
    
    @property
    def slice_prefix_bytes(self):
        if self.is_transform_parameters():
            return self["transform_parameters"]["slice_parameters"]["slice_prefix_bytes"].value
        else:
            return self.previous_slice_prefix_bytes
    
    @property
    def slice_size_scaler(self):
        if self.is_transform_parameters():
            return self["transform_parameters"]["slice_parameters"]["slice_size_scaler"].value
        else:
            return self.previous_slice_size_scaler
    
    @property
    def dwt_depth(self):
        if self.is_transform_parameters():
            return self["transform_parameters"].inner_value.dwt_depth
        else:
            return self.previous_dwt_depth
    
    @property
    def dwt_depth_ho(self):
        if self.is_transform_parameters():
            return self["transform_parameters"].inner_value.dwt_depth_ho
        else:
            return self.previous_dwt_depth_ho


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
    
    def __init__(self,
                 picture_number=0,
                 fragment_data_length=0,
                 fragment_slice_count=0,
                 fragment_x_offset=0,
                 fragment_y_offset=0):
        fragment_slice_count = NBits(fragment_slice_count, length=16)
        super(FragmentHeader, self).__init__(
            "fragment_header:",
            ("picture_number", NBits(picture_number, length=32)),
            ("fragment_data_length", NBits(picture_number, length=16)),
            ("fragment_slice_count", fragment_slice_count),
            (
                "fragment_x_offset",
                Maybe(
                    NBits(fragment_x_offset, length=16),
                    lambda: fragment_slice_count.value != 0,
                ),
            ),
            (
                "fragment_y_offset",
                Maybe(
                    NBits(fragment_y_offset, length=16),
                    lambda: fragment_slice_count.value != 0,
                ),
            ),
        )


class FragmentData(Array):
    r"""
    (13.5.2) An :py:class:`Array` of :py:class:`Slice`\ s defined by
    ``fragment_data()``.
    """
    
    def __init__(self,
                 fragment_slice_count=1,
                 fragment_x_offset=0,
                 fragment_y_offset=0,
                 slices_x=1,
                 slices_y=1,
                 parse_code=ParseCodes.high_quality_picture,
                 slice_bytes_numerator=0,
                 slice_bytes_denominator=1,
                 slice_prefix_bytes=0,
                 slice_size_scaler=1,
                 dwt_depth=0,
                 dwt_depth_ho=0,
                 luma_dimensions=(0, 0),
                 color_diff_dimensions=(0, 0)):
        """
        ``slices_x`` and ``slices_y`` should be ints (or functions returning
        ints) giving the number of slices in the array as defined by the
        associated :py:class:`SliceParameters`.
        ``parse_code`` should be the :py:class:`ParseCodes` (or a function
        returning one) from the associated :py:class:`ParseInfo`.
        
        
        ``slice_bytes_numerator``, ``slice_bytes_denominator``,
        ``slice_prefix_bytes`` and ``slice_size_scaler`` should be ints (or
        functions returning ints) with values taken from the associated
        :py:class:`SliceParameters`.
        
        ``dwt_depth`` and ``dwt_depth_ho`` should be the 2D and horizontal-only
        transform depths (or functions returning them) from the associated
        :py:class:`TransformParameters`.
        
        ``luma_width``, ``luma_height``, ``color_diff_width`` and
        ``color_diff_height`` should be integers (or functions returning
        integers) giving the picture component dimensios for the luminance and
        color difference components respectively.
        """
        self.fragment_slice_count = fragment_slice_count
        self.fragment_x_offset = fragment_x_offset
        self.fragment_y_offset = fragment_y_offset
        self.slices_x = slices_x
        self.slices_y = slices_y
        self.parse_code = parse_code
        self.slice_bytes_numerator = slice_bytes_numerator
        self.slice_bytes_denominator = slice_bytes_denominator
        self.slice_prefix_bytes = slice_prefix_bytes
        self.slice_size_scaler = slice_size_scaler
        self.dwt_depth = dwt_depth
        self.dwt_depth_ho = dwt_depth_ho
        self.luma_dimensions = luma_dimensions
        self.color_diff_dimensions = color_diff_dimensions
        
        def slice_x(i):
            # NB: 'max' here to ensure malformed inputs don't result in a
            # divide-by-zero crashx
            return (
                ((self.fragment_y_offset*self.slices_x) + self.fragment_x_offset + i)
                % max(1, self.slices_x)
            )
        def slice_y(i):
            # NB: 'max' here to ensure malformed inputs don't result in a
            # divide-by-zero crash
            return (
                ((self.fragment_y_offset*self.slices_x) + self.fragment_x_offset + i)
                // max(1, self.slices_x)
            )
        
        super(FragmentData, self).__init__(
            lambda i: Slice(lambda: slice_x(i),
                            lambda: slice_y(i),
                            lambda: self.slices_x,
                            lambda: self.slices_y,
                            lambda: self.parse_code,
                            lambda: self.slice_bytes_numerator,
                            lambda: self.slice_bytes_denominator,
                            lambda: self.slice_prefix_bytes,
                            lambda: self.slice_size_scaler,
                            lambda: self.dwt_depth,
                            lambda: self.dwt_depth_ho,
                            lambda: self.luma_dimensions,
                            lambda: self.color_diff_dimensions),
            lambda: self.fragment_slice_count,
            pass_index=True,
        )
    
    fragment_slice_count = function_property()
    fragment_x_offset = function_property()
    fragment_y_offset = function_property()
    slices_x = function_property()
    slices_y = function_property()
    parse_code = function_property()
    slice_bytes_numerator = function_property()
    slice_bytes_denominator = function_property()
    slice_prefix_bytes = function_property()
    slice_size_scaler = function_property()
    dwt_depth = function_property()
    dwt_depth_ho = function_property()
    luma_dimensions = function_property()
    color_diff_dimensions = function_property()


class Slice(LabelledConcatenation):
    """
    (13.5.2) A slice of transform data defined by ``slice()``.
    
    A :py:class:`LabelledConcatenation` with the following fields (of which at
    most one will be included in the bitstream):
    
    * ``"ld_slice"`` (:py:class:`LDSlice` in a :py:class:`Maybe`)
    * ``"hq_slice"`` (:py:class:`HQSlice` in a :py:class:`Maybe`)
    """
    
    def __init__(self,
                 sx=0,
                 sy=0,
                 slices_x=1,
                 slices_y=1,
                 parse_code=ParseCodes.high_quality_picture,
                 slice_bytes_numerator=0,
                 slice_bytes_denominator=1,
                 slice_prefix_bytes=0,
                 slice_size_scaler=1,
                 dwt_depth=0,
                 dwt_depth_ho=0,
                 luma_dimensions=(0, 0),
                 color_diff_dimensions=(0, 0)):
        """
        ``sx`` and ``sy`` should be ints (or functions returning ints) giving
        the slice coordinates of this slice.
        
        ``slices_x`` and ``slices_y`` should be ints (or functions returning
        ints) giving the number of slices taken fomr the associated
        :py:class:`SliceParameters`.
        
        ``parse_code`` should be the :py:class:`ParseCodes` (or a function
        returning one) from the associated :py:class:`ParseInfo`.
        
        ``slice_bytes_numerator``, ``slice_bytes_denominator``,
        ``slice_prefix_bytes`` and ``slice_size_scaler`` should be ints (or
        functions returning ints) with values taken from the associated
        :py:class:`SliceParameters`.
        
        ``dwt_depth`` and ``dwt_depth_ho`` should be the depth of the 2D and
        horizontal-only wavelet transform stages (or functions returning those
        values).
        
        ``luma_width``, ``luma_height``, ``color_diff_width`` and
        ``color_diff_height`` should be integers (or functions returning
        integers) giving the picture component dimensios for the luminance and
        color difference components respectively.
        """
        self.sx = sx
        self.sy = sy
        self.slices_x = slices_x
        self.slices_y = slices_y
        self.parse_code = parse_code
        self.slice_bytes_numerator = slice_bytes_numerator
        self.slice_bytes_denominator = slice_bytes_denominator
        self.slice_prefix_bytes = slice_prefix_bytes
        self.slice_size_scaler = slice_size_scaler
        self.dwt_depth = dwt_depth
        self.dwt_depth_ho = dwt_depth_ho
        self.luma_dimensions = luma_dimensions
        self.color_diff_dimensions = color_diff_dimensions
        
        def is_ld():
            try:
                return ParseCodes(self.parse_code).is_ld
            except ValueError:
                return False
        
        def is_hq():
            try:
                return ParseCodes(self.parse_code).is_hq
            except ValueError:
                return False
        
        super(Slice, self).__init__(
            (
                "ld_slice",
                Maybe(
                    LDSlice(
                        lambda: self.sx,
                        lambda: self.sy,
                        lambda: self.slices_x,
                        lambda: self.slices_y,
                        lambda: self.slice_bytes_numerator,
                        lambda: self.slice_bytes_denominator,
                        lambda: self.dwt_depth,
                        lambda: self.dwt_depth_ho,
                        lambda: self.luma_dimensions,
                        lambda: self.color_diff_dimensions,
                    ),
                    is_ld,
                ),
            ),
            (
                "hq_slice",
                Maybe(
                    HQSlice(
                        lambda: self.sx,
                        lambda: self.sy,
                        lambda: self.slices_x,
                        lambda: self.slices_y,
                        lambda: self.slice_prefix_bytes,
                        lambda: self.slice_size_scaler,
                        lambda: self.dwt_depth,
                        lambda: self.dwt_depth_ho,
                        lambda: self.luma_dimensions,
                        lambda: self.color_diff_dimensions,
                    ),
                    is_hq,
                ),
            ),
        )
    
    sx = function_property()
    sy = function_property()
    slices_x = function_property()
    slices_y = function_property()
    parse_code = function_property()
    slice_bytes_numerator = function_property()
    slice_bytes_denominator = function_property()
    slice_prefix_bytes = function_property()
    slice_size_scaler = function_property()
    dwt_depth = function_property()
    dwt_depth_ho = function_property()
    luma_dimensions = function_property()
    color_diff_dimensions = function_property()
    
    def __str__(self):
        # NB: A custom __str__ is implemented to add a heading (rather than
        # just adding the heading to the value) because it includes function
        # properties in it which may change in value.
        s = super(Slice, self).__str__()
        if s:
            return "slice(sx={}, sy={}):\n{}".format(self.sx, self.sy, indent(s))
        else:
            return "slice(sx={}, sy={}):".format(self.sx, self.sy)


def slice_bytes(sx, sy, slices_x, slices_y,
                slice_bytes_numerator, slice_bytes_denominator):
    """
    (13.5.3.2) Compute the number of bytes in a low-delay picture slice.
    
    Produces lengths which vary from slice-to-slice to approximate the desired
    fractional length as closely as possible.
    """
    # NB: The 'max' below prevent divide-by-zero exceptions occurring when
    # malformed input is encountered.
    slice_number = (sy * slices_x) + sx
    bytes = (((slice_number + 1) * slice_bytes_numerator) //
             max(1, slice_bytes_denominator))
    bytes -= ((slice_number * slice_bytes_numerator) //
              max(1, slice_bytes_denominator))
    return bytes

def intlog2(n):
    """(5.5.3)"""
    # Definition in spec
    #return int(math.ceil(math.log(n, 2)))
    
    # Equivalent to the above but cheaper to evaluate and works on arbitrary
    # precision values.
    return (n-1).bit_length()


class LDSlice(LabelledConcatenation):
    """
    (13.5.3.1) A slice of low-delay transform data defined by ``ld_slice()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"qindex"`` (a 7-bit :py:class:`NBits`)
    * ``"slice_y_length"`` (a variable-length :py:class:`NBits`)
    * ``"y_transform"`` (a :py:class:`SubbandArray` of
      :py:class:`SliceBand` in a :py:class:`BoundedBlock`)
    * ``"c_transform"`` (a :py:class:`SubbandArray` of
      :py:class:`ColorDiffSliceBand` in a :py:class:`BoundedBlock`)
    """
    
    def __init__(self,
                 sx=0,
                 sy=0,
                 slices_x=1,
                 slices_y=1,
                 slice_bytes_numerator=0,
                 slice_bytes_denominator=1,
                 dwt_depth=0,
                 dwt_depth_ho=0,
                 luma_dimensions=(0, 0),
                 color_diff_dimensions=(0, 0)):
        """
        ``sx`` and ``sy`` should be ints (or functions returning ints) giving
        the slice coordinates of this slice.
        
        ``slices_x`` and ``slices_y`` should be ints (or functions returning
        ints) giving the number of slices taken fomr the associated
        :py:class:`SliceParameters`.
        
        ``slice_bytes_numerator`` and ``slice_bytes_denominator`` should be
        ints (or functions returning ints) giving the values from the
        associated :py:class:`SliceParameters`.
        
        ``dwt_depth`` and ``dwt_depth_ho`` should be the depth of the 2D and
        horizontal-only wavelet transform stages (or functions returning those
        values).
        
        ``luma_width``, ``luma_height``, ``color_diff_width`` and
        ``color_diff_height`` should be integers (or functions returning
        integers) giving the picture component dimensios for the luminance and
        color difference components respectively.
        """
        self.sx = sx
        self.sy = sy
        self.slices_x = slices_x
        self.slices_y = slices_y
        self.slice_bytes_numerator = slice_bytes_numerator
        self.slice_bytes_denominator = slice_bytes_denominator
        self.dwt_depth = dwt_depth
        self.dwt_depth_ho = dwt_depth_ho
        self.luma_dimensions = luma_dimensions
        self.color_diff_dimensions = color_diff_dimensions
        
        qindex = NBits(length=7)
        
        def length_without_qindex():
            slice_bits_left = 8 * slice_bytes(
                self.sx,
                self.sy,
                self.slices_x,
                self.slices_y,
                self.slice_bytes_numerator,
                self.slice_bytes_denominator
            )
            slice_bits_left -= qindex.length
            return slice_bits_left
        
        def length_bits():
            # Number of bits in the slice_y_length field
            slice_bits_left = length_without_qindex()
            if slice_bits_left >= 1:
                return intlog2(slice_bits_left)
            else:
                # Rather than crashing when the input values are out-of-range,
                # produce '0' instead.
                return 0
        
        slice_y_length = NBits(length=length_bits)
        
        def slice_c_length():
            # Color difference length (bits)
            return (
                length_without_qindex() -
                slice_y_length.length -
                slice_y_length.value
            )
        
        super(LDSlice, self).__init__(
            "ld_slice:",
            ("qindex", qindex),
            ("slice_y_length", slice_y_length),
            (
                "y_transform",
                BoundedBlock(
                    SubbandArray(
                        lambda i: SliceBand(
                            lambda: self.sx,
                            lambda: self.sy,
                            lambda: self.slices_x,
                            lambda: self.slices_y,
                            lambda: SubbandArray.index_to_subband(
                                i, self.dwt_depth, self.dwt_depth_ho)[0],
                            lambda: self.dwt_depth,
                            lambda: self.dwt_depth_ho,
                            lambda: self.luma_dimensions,
                        ),
                        lambda: self.dwt_depth,
                        lambda: self.dwt_depth_ho,
                        pass_index=True,
                    ),
                    lambda: slice_y_length.value
                ),
            ),
            # Errata:
            # In (13.5.3.1) ld_transform() the HO-transform is not applied to
            # the chromanance components for some reason. This is presumably in
            # error and so in the bitstream below, it is in fact applied.
            (
                "c_transform",
                BoundedBlock(
                    SubbandArray(
                        lambda i: ColorDiffSliceBand(
                            lambda: self.sx,
                            lambda: self.sy,
                            lambda: self.slices_x,
                            lambda: self.slices_y,
                            lambda: SubbandArray.index_to_subband(
                                i,
                                self.dwt_depth,
                                self.dwt_depth_ho,   # Errata: '0' in spec
                            )[0],
                            lambda: self.dwt_depth,
                            lambda: self.dwt_depth_ho,  # Errata: '0' in spec
                            lambda: self.color_diff_dimensions,
                        ),
                        lambda: self.dwt_depth,
                        lambda: self.dwt_depth_ho,  # Errata: '0' in spec
                        pass_index=True,
                    ),
                    slice_c_length,
                ),
            ),
        )
    
    sx = function_property()
    sy = function_property()
    slices_x = function_property()
    slices_y = function_property()
    slice_bytes_numerator = function_property()
    slice_bytes_denominator = function_property()
    dwt_depth = function_property()
    dwt_depth_ho = function_property()
    luma_dimensions = function_property()
    color_diff_dimensions = function_property()


class HQSlice(LabelledConcatenation):
    """
    (13.5.4) A slice of high-quality transform data defined by ``hq_slice()``.
    
    A :py:class:`LabelledConcatenation` with the following fields:
    
    * ``"prefix"`` (slice_prefix_bytes bytes long :py:class:`Padding`)
    * ``"qindex"`` (a 8-bit :py:class:`NBits`)
    * ``"slice_y_length"`` (the un-scaled size in an 8-bit :py:class:`NBits`)
    * ``"y_transform"`` (a :py:class:`SubbandArray` of
      :py:class:`SliceBand` in a :py:class:`BoundedBlock`)
    * ``"slice_c1_length"`` (the un-scaled size in an 8-bit :py:class:`NBits`)
    * ``"c1_transform"`` (a :py:class:`SubbandArray` of
      :py:class:`SliceBand` in a :py:class:`BoundedBlock`)
    * ``"slice_c2_length"`` (the un-scaled size in an 8-bit :py:class:`NBits`)
    * ``"c2_transform"`` (a :py:class:`SubbandArray` of
      :py:class:`SliceBand` in a :py:class:`BoundedBlock`)
    """
    
    def __init__(self,
                 sx=0,
                 sy=0,
                 slices_x=1,
                 slices_y=1,
                 slice_prefix_bytes=0,
                 slice_size_scaler=1,
                 dwt_depth=0,
                 dwt_depth_ho=0,
                 luma_dimensions=(0, 0),
                 color_diff_dimensions=(0, 0)):
        """
        ``sx`` and ``sy`` should be ints (or functions returning ints) giving
        the slice coordinates of this slice.
        
        ``slices_x`` and ``slices_y`` should be ints (or functions returning
        ints) giving the number of slices taken fomr the associated
        :py:class:`SliceParameters`.
        
        ``slice_prefix_bytes`` and ``slice_size_scaler`` should be ints (or
        functions returning ints) giving the values from the associated
        :py:class:`SliceParameters`.
        
        ``dwt_depth`` and ``dwt_depth_ho`` should be the depth of the 2D and
        horizontal-only wavelet transform stages (or functions returning those
        values).
        
        ``luma_width``, ``luma_height``, ``color_diff_width`` and
        ``color_diff_height`` should be integers (or functions returning
        integers) giving the picture component dimensios for the luminance and
        color difference components respectively.
        """
        self.sx = sx
        self.sy = sy
        self.slices_x = slices_x
        self.slices_y = slices_y
        self.slice_prefix_bytes = slice_prefix_bytes
        self.slice_size_scaler = slice_size_scaler
        self.dwt_depth = dwt_depth
        self.dwt_depth_ho = dwt_depth_ho
        self.luma_dimensions = luma_dimensions
        self.color_diff_dimensions = color_diff_dimensions
        
        qindex = NBits(length=8)
        
        component_slices = []
        for component_name, component_dimensions_fn in [
                ("y", lambda: self.luma_dimensions),
                ("c1", lambda: self.color_diff_dimensions),
                ("c2", lambda: self.color_diff_dimensions)]:

            slice_length = NBits(length=8)
            
            component_slices.append(("slice_{}_length".format(component_name), slice_length))
            
            # NB: Due to lambda binding to the same 'slice_length' variable in
            # each iteration, not the value in the current iteration, a nested
            # expression is required here to produce a 'length' function with
            # the correct value
            length = (lambda slice_length:
                (lambda: self.slice_size_scaler * slice_length.value * 8)
            )(slice_length)
            
            component_slices.append((
                "{}_transform".format(component_name),
                BoundedBlock(
                    SubbandArray(
                        lambda i: SliceBand(
                            lambda: self.sx,
                            lambda: self.sy,
                            lambda: self.slices_x,
                            lambda: self.slices_y,
                            lambda: SubbandArray.index_to_subband(
                                i, self.dwt_depth, self.dwt_depth_ho)[0],
                            lambda: self.dwt_depth,
                            lambda: self.dwt_depth_ho,
                            component_dimensions_fn,
                        ),
                        lambda: self.dwt_depth,
                        lambda: self.dwt_depth_ho,
                        pass_index=True,
                    ),
                    length,
                ),
            ))
        
        super(HQSlice, self).__init__(
            "hq_slice:",
            ("slice_prefix_bytes", Padding(lambda: self.slice_prefix_bytes)),
            ("qindex", qindex),
            *component_slices,
        )
    
    sx = function_property()
    sy = function_property()
    slices_x = function_property()
    slices_y = function_property()
    slice_prefix_bytes = function_property()
    slice_size_scaler = function_property()
    dwt_depth = function_property()
    dwt_depth_ho = function_property()
    luma_dimensions = function_property()
    color_diff_dimensions = function_property()


class BaseSliceBand(RectangularArray):
    """
    A common base for implementing (13.5.6.3) ``slice_band()`` and
    (13.5.6.4)``color_diff_slice_band()``.
    
    A :py:class:`RectangularArray` containing coefficients in the block. The
    coordinates for this array are offset such that (:py:attr:`slice_top`,
    :py:attr:`slice_left`) is at (0, 0).
    """
    
    def __init__(self,
                 value_constructor,
                 sx=0,
                 sy=0,
                 slices_x=1,
                 slices_y=1,
                 level=0,
                 dwt_depth=0,
                 dwt_depth_ho=0,
                 component_dimensions=(0, 0)):
        """
        ``sx`` and ``sy`` should be ints (or functions returning ints) giving
        the slice coordinates of this slice.
        
        ``slices_x`` and ``slices_y`` should be ints (or functions returning
        ints) giving the number of slices taken fomr the associated
        :py:class:`SliceParameters`.
        
        ``level`` should be the wavelet transform level (or a function
        returning the same) this slice contains the coefficients for.
        
        ``dwt_depth`` and ``dwt_depth_ho`` should be the depth of the 2D and
        horizontal-only wavelet transform stages (or functions returning those
        values).
        
        ``component_dimensions`` should be a tuple (width, height) (or a
        function returning one) giving the width and height of the picture
        component this is a slice of.
        """
        self.sx = sx
        self.sy = sy
        self.slices_x = slices_x
        self.slices_y = slices_y
        self.level = level
        self.dwt_depth = dwt_depth
        self.dwt_depth_ho = dwt_depth_ho
        self.component_dimensions = component_dimensions
        
        super(BaseSliceBand, self).__init__(
            value_constructor=value_constructor,
            height=lambda: self.slice_bottom - self.slice_top,
            width=lambda: self.slice_right - self.slice_left,
        )
    
    sx = function_property()
    sy = function_property()
    slices_x = function_property()
    slices_y = function_property()
    level = function_property()
    dwt_depth = function_property()
    dwt_depth_ho = function_property()
    component_dimensions = function_property()
    
    @property
    def label(self):
        raise NotImplementedError()
    
    @property
    def subband_width(self):
        """
        (13.2.3) The width of the whole subband this slice is a piece of
        defined by ``subband_width()``.
        """
        w = self.component_dimensions[0]
        
        # NB: 'max' here to ensure malformed inputs don't result in a
        # shift-by-negative-number crash
        scale_w = 1 << max(0, (self.dwt_depth_ho + self.dwt_depth))
        
        pw = scale_w * ( (w+scale_w-1) // scale_w)
        
        if self.level == 0:
            return pw // (1 << max(0, (self.dwt_depth_ho + self.dwt_depth)))
        else:
            return pw // (1 << max(0, (self.dwt_depth_ho + self.dwt_depth - self.level + 1)))
    
    @property
    def subband_height(self):
        """
        (13.2.3) The height of the whole subband this slice is a piece of
        defined by ``subband_width()``.
        """
        h = self.component_dimensions[1]
        
        # NB: 'max' here to ensure malformed inputs don't result in a
        # shift-by-negative-number crash
        scale_h = 1 << max(0, self.dwt_depth)
        
        ph = scale_h * ( (h+scale_h-1) // scale_h)
        
        if self.level <= self.dwt_depth_ho:
            return ph // (1 << max(0, self.dwt_depth))
        else:
            return ph // (1 << max(0, (self.dwt_depth_ho + self.dwt_depth - self.level + 1)))
    
    @property
    def slice_left(self):
        """
        (13.5.6.2) The offset of this slice into its subband defined by
        ``slice_left()``.
        """
        # NB: 'max' here to ensure malformed inputs don't result in a
        # divide-by-zero crash
        return (self.subband_width * self.sx) // max(1, self.slices_x)
    
    @property
    def slice_right(self):
        """
        (13.5.6.2) The offset of this slice into its subband defined by
        ``slice_right()``.
        """
        # NB: 'max' here to ensure malformed inputs don't result in a
        # divide-by-zero crash
        return (self.subband_width * (self.sx + 1)) // max(1, self.slices_x)
    
    @property
    def slice_top(self):
        """
        (13.5.6.2) The offset of this slice into its subband defined by
        ``slice_top()``.
        """
        # NB: 'max' here to ensure malformed inputs don't result in a
        # divide-by-zero crash
        return (self.subband_height * self.sy) // max(1, self.slices_y)
    
    @property
    def slice_bottom(self):
        """
        (13.5.6.2) The offset of this slice into its subband defined by
        ``slice_bottom()``.
        """
        # NB: 'max' here to ensure malformed inputs don't result in a
        # divide-by-zero crash
        return (self.subband_height * (self.sy + 1)) // max(1, self.slices_y)
    
    def __str__(self):
        return concat_labelled_strings([(
            "{} x=[{}, {}) y=[{}, {})".format(
                self.label,
                self.slice_left,
                self.slice_right,
                self.slice_top,
                self.slice_bottom,
            ),
            super(BaseSliceBand, self).__str__(),
        )])


class SliceBand(BaseSliceBand):
    """
    (13.5.6.3) Value coefficients for a slice of a subband. ``slice_band()``.
    
    A :py:class:`RectangularArray` of :py:class:`SInt`. The coordinates for
    this array are offset such that (:py:attr:`slice_top`,
    :py:attr:`slice_left`) is at (0, 0).
    """
    
    def __init__(self, *args, **kwargs):
        super(SliceBand, self).__init__(SInt, *args, **kwargs)
    
    @property
    def label(self):
        return "slice_band"


class ColorDiffSliceBand(BaseSliceBand):
    """
    (13.5.6.4) Value coefficients for a low-delay color-difference slice of a
    subband. ``color_diff_slice_band()``.
    
    A :py:class:`RectangularArray` of concatenated pairs of :py:class:`SInt`.
    The coordinates for this array are offset such that (:py:attr:`slice_top`,
    :py:attr:`slice_left`) is at (0, 0).
    """
    
    def __init__(self, *args, **kwargs):
        super(ColorDiffSliceBand, self).__init__(
            lambda: Concatenation(SInt(), SInt()),
            *args,
            **kwargs,
        )
    
    @property
    def label(self):
        return "color_diff_slice_band"
