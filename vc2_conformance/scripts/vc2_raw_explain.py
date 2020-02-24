"""
``vc2-raw-explain``
===================

An command-line utility which provides informative descriptions the raw video
format produced by the conformance software.

"""

from argparse import ArgumentParser

from fractions import Fraction

from vc2_data_tables import (
    SourceSamplingModes,
    PictureCodingModes,
    PresetColorPrimaries,
    PRESET_COLOR_PRIMARIES,
    PresetColorMatrices,
    PRESET_COLOR_MATRICES,
    PresetTransferFunctions,
    PRESET_TRANSFER_FUNCTIONS,
    ColorDifferenceSamplingFormats,
    PRESET_SIGNAL_RANGES,
    PresetSignalRanges,
    SignalRangeParameters,
)

from vc2_conformance.file_format import (
    get_metadata_and_picture_filenames,
    get_picture_filename_pattern,
    read_metadata,
    compute_dimensions_and_depths,
)


def is_rgb_color(video_parameters):
    """
    Return True if the specified video parameters use RGB colour. Returns False
    if a Luma+Chroma representation is used instead.
    """
    return (
        video_parameters["preset_color_matrix_index"] ==
        PresetColorMatrices.rgb
    )


PICTURE_COMPONENT_NAMES = {
    PresetColorMatrices.hdtv: ("Y", "Cb", "Cr"),
    PresetColorMatrices.sdtv: ("Y", "Cb", "Cr"),
    PresetColorMatrices.reversible: ("Y", "Cg", "Co"),
    PresetColorMatrices.rgb: ("G", "B", "R"),
    PresetColorMatrices.uhdtv: ("Y", "Cb", "Cr"),
}
"""
A lookup from :py:class:`~vc2_data_tables.PresetColorMatrices` to triples of
strings naming the components used by that format
"""

COLOR_DIFF_FORMAT_NAMES = {
    ColorDifferenceSamplingFormats.color_4_4_4: "4:4:4",
    ColorDifferenceSamplingFormats.color_4_2_2: "4:2:2",
    ColorDifferenceSamplingFormats.color_4_2_0: "4:2:0",
}
"""
Strings giving the normal human-readable name for a color difference sampling
format.
"""


def explain_interleaving(video_parameters, picture_coding_mode):
    """
    Produce a human-readable informative description of the source sampling and
    picture coding modes in use.
    """
    
    out = ""
    
    pictures_are_frames = picture_coding_mode == PictureCodingModes.pictures_are_frames
    progressive = video_parameters["source_sampling"] == SourceSamplingModes.progressive
    
    out += "Each raw picture contains a {}{}.".format(
        "whole frame" if pictures_are_frames else "single field",
        " (though the underlying video is {})".format(
            "progressive" if progressive else "interlaced"
        ) if progressive != pictures_are_frames else "",
    )
    
    if not progressive or not pictures_are_fields:
        out += " The {} field comes first.".format(
            "top" if video_parameters["top_field_first"] else "bottom"
        )
    
    return out


def explain_component_order_and_sampling(video_parameters, picture_coding_mode):
    """
    Produce a human-readable informative definition of the component names,
    order and sampling mode.
    """
    y, c1, c2 = PICTURE_COMPONENT_NAMES[video_parameters["preset_color_matrix_index"]]
    
    return (
        "Pictures contain three planar components: "
        "{}, {} and {}, in that order, which are {} subsampled."
    ).format(
        y, c1, c2,
        COLOR_DIFF_FORMAT_NAMES[video_parameters["color_diff_format_index"]],
    )


def explain_component_sizes(video_parameters, picture_coding_mode):
    """
    Produce a human-readable informative definition of the picture component
    sizes and bit depths.
    """
    out = ""
    
    dimensions_and_depths = compute_dimensions_and_depths(
        video_parameters,
        picture_coding_mode,
    )
    
    y_dd = dimensions_and_depths["Y"]
    c_dd = dimensions_and_depths["C1"]
    
    explanations = []
    
    if y_dd == c_dd:
        explanations.append(("Each component consists of", y_dd))
    else:
        y_name, c1_name, c2_name = PICTURE_COMPONENT_NAMES[
            video_parameters["preset_color_matrix_index"]
        ]
        explanations.append((
            "The {} component consists of".format(y_name),
            y_dd,
        ))
        explanations.append((
            "The {} and {} components consist of".format(c1_name, c2_name),
            c_dd,
        ))
    
    for prefix, dd in explanations:
        out += "{} {}x{} {} bit ({} byte) values{}{}.\n\n".format(
            prefix,
            dd.width,
            dd.height,
            8 * dd.bytes_per_sample,
            dd.bytes_per_sample,
            " in big-endian byte order" if dd.bytes_per_sample > 1 else "",
            (
                " with {} significant bits (most significant bit aligned)".format(dd.depth_bits)
                if 8 * dd.bytes_per_sample != dd.depth_bits else
                ""
            ),
        )
    
    return out.rstrip()


def explain_color_model(video_parameters, picture_coding_mode):
    """
    Produce a human-readable informative definition of the color model in use.
    """
    primaries = PRESET_COLOR_PRIMARIES[video_parameters["preset_color_primaries_index"]]
    matrix = PRESET_COLOR_MATRICES[video_parameters["preset_color_matrix_index"]]
    transfer_function = PRESET_TRANSFER_FUNCTIONS[video_parameters["preset_transfer_function_index"]]
    
    out = (
        "The color model uses the '{}' primaries ({}), "
        "the '{}' color matrix ({}) "
        "and the '{}' transfer function ({})."
    ).format(
        primaries.name,
        primaries.specification,
        matrix.name,
        matrix.specification,
        transfer_function.name,
        transfer_function.specification,
    )
    
    return out.rstrip()


class CommandExplainer(object):
    """
    Build up a command line with notes explaining each part.
    
    Parameters
    ==========
    prefix : str
        Optionally add a prefix to the command (e.g. "$ ").
    
    Attributes
    ==========
    command : str
        The command.
    notes : [(start, end, note), ...]
        Notes relating to various substrings within the command.
        Non-overlapping.
    """
    
    def __init__(self, prefix=""):
        self._prefix = prefix
        self.command = prefix
        
        # [(fragment, note), ...]
        self.notes = []
    
    def append(self, fragment, note=None):
        """
        Append a fragment of text to the end of the command.
        
        Parameters
        ==========
        fragment : str
            The text to append
        note : str or None
            If given, a note explaining this fragment of the command.
        strip : bool
            If True (the default), the note will not apply to whitespace at
            either end of the fragment.
        """
        self.command += fragment
        
        if note is not None:
            self.notes.append((fragment, note))
    
    def append_line_break(self, indent=2):
        self.append(" \\\n{}".format(
            " "*(indent + len(self._prefix)),
        ))
    
    def explain(self):
        """
        Return a markdown-formatted explanation of this command.
        """
        out = ""
        
        out += "    {}\n".format("\n    ".join(self.command.split("\n")))
        
        out += "\n"
        
        for fragment, note in self.notes:
            out += "* `{}`: {}\n".format(fragment, note)
        
        out = out.rstrip()
        out += "\n"
        
        return out
    
    def __repr__(self):
        return "<{!r} {!r}>".format(
            type(self).name,
            self.command,
        )

class UnsupportedPictureFormat(Exception):
    """
    Thrown when a picture format is not supported by a command line tool.
    """


COLOR_PRIMARIES_TO_FFMPEG_COLOR_PRIMARIES = {
    PresetColorPrimaries.hdtv: "bt709",
    PresetColorPrimaries.sdtv_525: "smpte170m",
    PresetColorPrimaries.sdtv_625: "bt470bg",
    PresetColorPrimaries.d_cinema: "smpte428",
    PresetColorPrimaries.uhdtv: "bt2020",
}
"""
Mapping from VC-2 :py:class:`~vc2_data_tables.PresetColorPrimaries` to
equivalent FFMpeg ``-color_primaries`` argument values.
"""

COLOR_MATRICES_TO_FFMPEG_COLORSPACE = {
    PresetColorMatrices.hdtv: "bt709",
    PresetColorMatrices.sdtv: "bt470bg",
    PresetColorMatrices.reversible: "ycgco",
    PresetColorMatrices.rgb: "rgb",
    PresetColorMatrices.uhdtv: "bt2020ncl",
}
"""
Mapping from VC-2 :py:class:`~vc2_data_tables.PresetColorMatrices` to
equivalent FFMpeg ``-colorspace`` argument values.
"""

TRANSFER_FUNCTIONS_TO_FFMPEG_COLOR_TRC = {
    PresetTransferFunctions.tv_gamma: "bt2020-10",
    PresetTransferFunctions.extended_gamut: "bt1361e",
    PresetTransferFunctions.linear: "linear",
    PresetTransferFunctions.d_cinema: "smpte428",
    #PresetTransferFunctions.perceptual_quality: "unspecified",
    PresetTransferFunctions.hybrid_log_gamma: "arib_std_b67",
}
"""
Mapping from VC-2 :py:class:`~vc2_data_tables.PresetTransferFunctions` to
equivalent FFMpeg ``-color_trc`` argument values.

.. warning::

    There is no implementation of the
    :py:data:`~vc2_data_tables.PresetTransferFunctions.perceptual_quality`
    transfer function in ffmpeg. Consequently, no corresponding entry is
    provided in this lookup.
"""

SIGNAL_RANGE_TO_FFMPEG_COLOR_RANGE = {
    PRESET_SIGNAL_RANGES[PresetSignalRanges.video_8bit]: "mpeg",
    PRESET_SIGNAL_RANGES[PresetSignalRanges.video_10bit]: "mpeg",
    PRESET_SIGNAL_RANGES[PresetSignalRanges.video_12bit]: "mpeg",
    PRESET_SIGNAL_RANGES[PresetSignalRanges.video_16bit]: "mpeg",
    PRESET_SIGNAL_RANGES[PresetSignalRanges.video_8bit_full_range]: "jpeg",
    PRESET_SIGNAL_RANGES[PresetSignalRanges.video_10bit_full_range]: "jpeg",
    PRESET_SIGNAL_RANGES[PresetSignalRanges.video_12bit_full_range]: "jpeg",
    PRESET_SIGNAL_RANGES[PresetSignalRanges.video_16bit_full_range]: "jpeg",
    # Typical RGB signal ranges
    SignalRangeParameters(0, 255, 0, 255): "jpeg",  # 8 bit
    SignalRangeParameters(0, 1023, 0, 1023): "jpeg",  # 10 bit
    SignalRangeParameters(0, 4095, 0, 4095): "jpeg",  # 12 bit
    SignalRangeParameters(0, 65535, 0, 65535): "jpeg",  # 16 bit
}
"""
Mapping from VC-2 :py:class:`~vc2_data_tables.SignalRangeParameters` tuples to
equivalent FFMpeg ``-color_range`` argument values.
"""


def example_ffmpeg_command(picture_filename, video_parameters, picture_coding_mode):
    """
    Create a :py:class:`CommandExplainer` defining an FFmpeg ``ffplay`` command
    to play the specified video format.
    
    The resulting commands attempt to achieve the correct:
    
    * Resolution
    * Bit depth
    * Pixel aspect ratio
    * Colour subsampling mode
    * Frame rate
    * Interlacing (fields are always converted into frames and, if the
      underlying picture is interlaced, deinterlacing is applied)
    * RGB vs Luma + Chroma representation
    
    In some cases, :py:exc:`UnsupportedPictureFormat` will be raised where the
    format is sufficiently unusual as to be completely unsupported by FFMPEG
    (e.g.  extremely high bit depths or colour subsampling under RGB mode).
    
    For the the following color related features, a 'best effort' attempt is
    made to set the correct ffmpeg options. Unfortunately, ``ffplay`` is not
    sophisticated enough to automatically convert the specified format to suit
    your display. You may be able to manually use the ``colorspace`` video
    filter to convert into your own display's color space. Alternatively, the
    ``ffmpeg`` command appears to pay attention to these options for some
    output codecs, 
    
    * Luma/Chroma Offset/Excursion (i.e. signal range)
    * Color primaries
    * Color matrix
    * Transfer function
    
    Finally, the 'clean area' parameters are ignored completely.
    """
    command = CommandExplainer("$ ")
    
    command.append("ffplay")
    
    command.append_line_break()
    
    #------------------------------------------------------------------------
    # Set input image format
    #------------------------------------------------------------------------
    
    command.append("-f image2", "Read pictures from individual files")
    
    command.append_line_break()
    
    #------------------------------------------------------------------------
    # Set picture size
    #------------------------------------------------------------------------
    
    dimensions_and_depths = compute_dimensions_and_depths(
        video_parameters,
        picture_coding_mode,
    )
    
    command.append(
        "-video_size {}x{}".format(
            dimensions_and_depths["Y"].width,
            dimensions_and_depths["Y"].height,
        ),
        (
            "Frame size."
            if picture_coding_mode == PictureCodingModes.pictures_are_frames else
            "Field size (NOT frame size)."
        )
    )
    
    command.append_line_break()
    
    #------------------------------------------------------------------------
    # Set frame rate
    #------------------------------------------------------------------------
    
    frame_rate = Fraction(video_parameters["frame_rate_numer"], video_parameters["frame_rate_denom"])
    command.append(
        "-framerate {}".format(
            frame_rate
            if picture_coding_mode == PictureCodingModes.pictures_are_frames else
            frame_rate * 2
        ),
        "actually the *picture* rate (may differ from frame rate)",
    )
    
    command.append_line_break()
    
    #------------------------------------------------------------------------
    # Set pixel format (e.g. RGB-vs-YCbCr, bit depth, color subsampling)
    #------------------------------------------------------------------------
    
    pixel_format_command = "-pixel_format "
    pixel_format_note = "Specifies raw picture encoding."
    
    if is_rgb_color(video_parameters):
        pixel_format_command += "gbr"
        pixel_format_note += " `gbr` = RGB colour."
        
        if video_parameters["color_diff_format_index"] != ColorDifferenceSamplingFormats.color_4_4_4:
            raise UnsupportedPictureFormat(
                "Only 4:4:4 colour difference sampling is supported for RGB video."
            )
    else:
        pixel_format_command += "yuv"
        pixel_format_note += " `yuv` = Y C1 C2 colour."
        
        color_difference_sampling_format = COLOR_DIFF_FORMAT_NAMES[
            video_parameters["color_diff_format_index"]
        ]
        pixel_format_command += color_difference_sampling_format.replace(":", "")
        pixel_format_note += " `{}` = {} color difference subsampling.".format(
            color_difference_sampling_format.replace(":", ""),
            color_difference_sampling_format,
        )
    
    pixel_format_command += "p"
    pixel_format_note += " `p` = planar video."
    
    if (
        dimensions_and_depths["Y"].bytes_per_sample !=
        dimensions_and_depths["C1"].bytes_per_sample
    ):
        raise UnsupportedPictureFormat(
            "Luma and chroma components differ in depth ({} bits and {} bits)".format(
                dimensions_and_depths["Y"].bytes_per_sample,
                dimensions_and_depths["C1"].bytes_per_sample,
            )
        )
    
    depth_bits = dimensions_and_depths["Y"].depth_bits
    bytes_per_sample = dimensions_and_depths["Y"].bytes_per_sample
    if bytes_per_sample == 1:
        pass
    elif bytes_per_sample == 2:
        pixel_format_command += "16be"
        pixel_format_note += " `16be` = 16 bit big-endian values."
    else:
        raise UnsupportedPictureFormat("Unsupported bit depth: {} bits".format(
            dimensions_and_depths["Y"].depth_bits
        ))
    
    command.append(pixel_format_command, pixel_format_note)
    
    command.append_line_break()
    
    #------------------------------------------------------------------------
    # Set pixel format (e.g. RGB-vs-YCbCr, bit depth, color subsampling)
    #------------------------------------------------------------------------
    
    range_tuple = SignalRangeParameters(
        luma_offset=video_parameters["luma_offset"],
        luma_excursion=video_parameters["luma_excursion"],
        color_diff_offset=video_parameters["color_diff_offset"],
        color_diff_excursion=video_parameters["color_diff_excursion"],
    )
    if range_tuple in SIGNAL_RANGE_TO_FFMPEG_COLOR_RANGE:
        command.append(
            "-color_range {}".format(
                SIGNAL_RANGE_TO_FFMPEG_COLOR_RANGE[range_tuple]
            ),
            "Set luma and color difference signal range ",
        )
    else:
        raise UnsupportedPictureFormat("Unsupported luma/color difference signal range.")
    
    command.append_line_break()
    
    #------------------------------------------------------------------------
    # Set colour model options
    #------------------------------------------------------------------------
    
    color_primaries = COLOR_PRIMARIES_TO_FFMPEG_COLOR_PRIMARIES[
        video_parameters["preset_color_primaries_index"]
    ]
    command.append(
        "-color_primaries {}".format(color_primaries),
        "set colour primaries",
    )
    
    command.append_line_break()
    
    colorspace = COLOR_MATRICES_TO_FFMPEG_COLORSPACE[
        video_parameters["preset_color_matrix_index"]
    ]
    command.append(
        "-colorspace {}".format(colorspace),
        "set colour matrix",
    )
    
    command.append_line_break()
    
    color_trc = TRANSFER_FUNCTIONS_TO_FFMPEG_COLOR_TRC[
        video_parameters["preset_transfer_function_index"]
    ]
    command.append(
        "-color_trc {}".format(color_trc),
        "set transfer function",
    )
    
    command.append_line_break()
    
    command.append(
        "-i {}".format(get_picture_filename_pattern(picture_filename)),
        "Input raw picture filename pattern",
    )
    
    vf_args = []
    
    #------------------------------------------------------------------------
    # Frames-from-Fields (de)interlacing
    #------------------------------------------------------------------------
    
    if picture_coding_mode == PictureCodingModes.pictures_are_fields:
        # When pictures are fields we (at least) need to interleave pairs of
        # pictures into whole frames. For truly interlaced content, a
        # deinterlace filter can also be applied for clean display.
        vf_args.append((
            "weave={}".format(
                "t" if video_parameters["top_field_first"] else "b",
            ),
            "interleave pairs of pictures, {} field first".format(
                "top" if video_parameters["top_field_first"] else "bottom",
            ),
        ))
        
        if video_parameters["source_sampling"] == SourceSamplingModes.interlaced:
            vf_args.append((",", ))
            vf_args.append(("yadif", "(optional) apply a deinterlacing filter for display purposes"))
    elif (
        picture_coding_mode == PictureCodingModes.pictures_are_frames and
        video_parameters["source_sampling"] == SourceSamplingModes.interlaced
    ):
        # When pictures are frames containing interlaced content, we can
        # optionally apply a deinterlace filter
        vf_args.append((
            "setfield={}".format(
                "tff" if video_parameters["top_field_first"] else "bff",
            ),
            "define the field order as {} field first".format(
                "top" if video_parameters["top_field_first"] else "bottom",
            ),
        ))
        
        vf_args.append((",", ))
        vf_args.append(("yadif", "(optional) apply a deinterlacing filter for display purposes"))
    
    #------------------------------------------------------------------------
    # Pixel aspect ratio
    #------------------------------------------------------------------------
    pixel_aspect_ratio = Fraction(
        video_parameters["pixel_aspect_ratio_numer"],
        video_parameters["pixel_aspect_ratio_denom"],
    )
    if pixel_aspect_ratio != 1:
        if vf_args:
            vf_args.append((",", ))
        vf_args.append((
            "setsar={}/{}".format(
                pixel_aspect_ratio.numerator,
                pixel_aspect_ratio.denominator,
            ),
            "set pixel aspect ratio",
        ))
    
    if vf_args:
        command.append_line_break()
        command.append("-vf ", "define a pipeline of video filtering operations")
        for args in vf_args:
            command.append(*args)
    
    return command


def main(*args, **kwargs):
    parser = ArgumentParser(description="""
        Informatively explain the video format used a raw video
        file generated by the VC-2 conformance software.
    """)
    
    parser.add_argument("filename",
        help="""
            The filename of a .raw or .json raw video file.
        """
    )

    args = parser.parse_args(*args, **kwargs)
    
    metadata_filename, picture_filename = get_metadata_and_picture_filenames(
        args.filename
    )
    
    with open(metadata_filename, "rb") as f:
        (
            video_parameters,
            picture_coding_mode,
            picture_number,
        ) = read_metadata(f)
    
    dimensions_and_depths = compute_dimensions_and_depths(
        video_parameters,
        picture_coding_mode,
    )
    
    print("Normative description")
    print("=====================")
    print("Picture coding mode: {} ({:d})".format(
        picture_coding_mode.name,
        picture_coding_mode,
    ))
    print(video_parameters)
    print("")
    print("Informative description")
    print("=======================")
    print("")
    print(explain_interleaving(video_parameters, picture_coding_mode))
    print("")
    print(explain_component_order_and_sampling(video_parameters, picture_coding_mode))
    print("")
    print(explain_component_sizes(video_parameters, picture_coding_mode))
    print("")
    print(explain_color_model(video_parameters, picture_coding_mode))
    print("")
    print("Example FFMPEG Command")
    print("======================")
    print(example_ffmpeg_command(picture_filename, video_parameters, picture_coding_mode).explain())
    

if __name__ == "__main__":
    sys.exit(main())
