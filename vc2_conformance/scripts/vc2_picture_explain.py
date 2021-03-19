r"""
.. _vc2-picture-explain:

``vc2-picture-explain``
=======================

A command-line utility which provides informative descriptions the raw video
format (see :ref:`file-format`) used by the VC-2 conformance software. As well
as providing an explanation of the format, where possible sample invocations of
`FFmpeg <https://ffmpeg.org/>`_ and `ImageMagick <https://imagemagick.org/>`_
are provided for viewing the raw files directly.

Example usage
-------------

An example invocation is shown below::

    $ vc2-picture-explain path/to/raw/picture_0.json
    Normative description
    =====================

    Picture coding mode: pictures_are_fields (1)

    Video parameters:

    * frame_width: 352
    * frame_height: 288
    * color_diff_format_index: color_4_2_0 (2)
    * source_sampling: progressive (0)
    * top_field_first: True
    * frame_rate_numer: 25
    * frame_rate_denom: 2
    * pixel_aspect_ratio_numer: 12
    * pixel_aspect_ratio_denom: 11
    * clean_width: 352
    * clean_height: 288
    * left_offset: 0
    * top_offset: 0
    * luma_offset: 0
    * luma_excursion: 255
    * color_diff_offset: 128
    * color_diff_excursion: 255
    * color_primaries_index: sdtv_625 (2)
    * color_matrix_index: sdtv (1)
    * transfer_function_index: tv_gamma (0)

    Explanation (informative)
    =========================

    Each raw picture contains a single field (though the underlying video is
    progressive). The top field comes first.

    Pictures contain three planar components: Y, Cb and Cr, in that order, which are
    4:2:0 subsampled.

    The Y component consists of 352x144 8 bit values. Values run from 0 (video level
    0.00) to 255 (video level 1.00).

    The Cb and Cr components consist of 176x72 8 bit values. Values run from 0
    (video level -0.50) to 255 (video level 0.50).

    The color model uses the 'sdtv_625' primaries (ITU-R BT.601), the 'sdtv' color
    matrix (ITU-R BT.601) and the 'tv_gamma' transfer function (ITU-R BT.2020).

    The pixel aspect ratio is 12:11 (not to be confused with the frame aspect
    ratio).

    Example FFMPEG command (informative)
    ====================================

    The following command can be used to play back this video format using FFMPEG:

        $ ffplay \
            -f image2 \
            -video_size 352x144 \
            -framerate 25 \
            -pixel_format yuv420p \
            -i path/to/raw/picture_%d.raw \
            -vf weave=t,scale='trunc((iw*12)/11):ih'

    Where:

    * `-f image2` = Read pictures from individual files
    * `-video_size 352x144` = Picture size (not frame size).
    * `-framerate 25` = Picture rate (not frame rate)
    * `-pixel_format` = Specifies raw picture encoding.
    * `yuv` = Y C1 C2 color.
    * `420` = 4:2:0 color difference subsampling.
    * `p` = Planar format.
    * `-i path/to/raw/picture_%d.raw` = Input raw picture filename pattern
    * `-vf` = define a pipeline of video filtering operations
    * `weave=t` = interleave pairs of pictures, top field first
    * `scale='trunc((iw*12)/11):ih'` = rescale non-square pixels for display with
      square pixels

    This command is provided as a minimal example for basic playback of this raw
    video format.  While it attempts to ensure correct frame rate, pixel aspect
    ratio, interlacing mode and basic pixel format, color model options are omitted
    due to inconsistent handling by FFMPEG.

    Example ImageMagick command (informative)
    =========================================

    The following command can be used to convert a single raw picture into PNG
    format for viewing in a conventional image viewer:

        $ convert \
            -size 352x144 \
            -depth 8 \
            -sampling-factor 4:2:0 \
            -interlace plane \
            -colorspace sRGB \
            yuv:path/to/raw/picture_%d.raw \
            -resize 109.0909090909091%,100% \
            png24:path/to/raw/picture_%d.png

    Where:

    * `-size 352x144` = Picture size.
    * `-depth 8` = 8 bit values.
    * `-sampling-factor 4:2:0` = 4:2:0 color difference subsampling.
    * `-interlace plane` = Planar format (not related to video interlace mode).
    * `-colorspace sRGB` = Display as if using sRGB color.
    * `yuv:` = Input is Y C1 C2 picture.
    * `path/to/raw/picture_%d.raw` = Input filename.
    * `-resize 109.0909090909091%,100%` = rescale non-square pixels for display with
      square pixels
    * `png24:path/to/raw/picture_%d.png` = Save as 24-bit PNG (e.g. 8 bit channels)

    This command is provided as a minimal example for basic viewing of pictures.
    Interlacing and correct color model conversion are not implemented.


Arguments
---------

The complete set of arguments can be listed using ``--help``

.. program-output:: vc2-picture-explain --help

"""

import sys

from argparse import ArgumentParser

from fractions import Fraction

from vc2_data_tables import (
    SourceSamplingModes,
    PictureCodingModes,
    PRESET_COLOR_PRIMARIES,
    PresetColorMatrices,
    PRESET_COLOR_MATRICES,
    PRESET_TRANSFER_FUNCTIONS,
    ColorDifferenceSamplingFormats,
)

from vc2_conformance import __version__

from vc2_conformance.file_format import (
    get_metadata_and_picture_filenames,
    get_picture_filename_pattern,
    read_metadata,
)

from vc2_conformance.dimensions_and_depths import compute_dimensions_and_depths

from vc2_conformance.color_conversion import int_to_float

from vc2_conformance.py2x_compat import get_terminal_size
from vc2_conformance.string_utils import indent, wrap_paragraphs


def is_rgb_color(video_parameters):
    """
    Return True if the specified video parameters use RGB color. Returns False
    if a Luma+Chroma representation is used instead.
    """
    return video_parameters["color_matrix_index"] == PresetColorMatrices.rgb


PICTURE_COMPONENT_NAMES = {
    PresetColorMatrices.hdtv: ("Y", "Cb", "Cr"),
    PresetColorMatrices.sdtv: ("Y", "Cb", "Cr"),
    PresetColorMatrices.reversible: ("Y", "Cg", "Co"),
    PresetColorMatrices.rgb: ("G", "R", "B"),
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
        )
        if progressive != pictures_are_frames
        else "",
    )

    if not progressive or not pictures_are_frames:
        out += " The {} field comes first.".format(
            "top" if video_parameters["top_field_first"] else "bottom"
        )

    return out


def explain_component_order_and_sampling(video_parameters, picture_coding_mode):
    """
    Produce a human-readable informative definition of the component names,
    order and sampling mode.
    """
    y, c1, c2 = PICTURE_COMPONENT_NAMES[video_parameters["color_matrix_index"]]

    return (
        "Pictures contain three planar components: "
        "{}, {} and {}, in that order, which are {} subsampled."
    ).format(
        y,
        c1,
        c2,
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

    y_off_exc = (
        video_parameters["luma_offset"],
        video_parameters["luma_excursion"],
    )

    c_off_exc = (
        video_parameters["color_diff_offset"],
        video_parameters["color_diff_excursion"],
    )

    explanations = []

    if y_dd == c_dd and y_off_exc == c_off_exc:
        explanations.append(
            (
                "Each component consists of",
                y_dd,
                video_parameters["luma_offset"],
                video_parameters["luma_excursion"],
            )
        )
    else:
        y_name, c1_name, c2_name = PICTURE_COMPONENT_NAMES[
            video_parameters["color_matrix_index"]
        ]
        explanations.append(
            (
                "The {} component consists of".format(y_name),
                y_dd,
                video_parameters["luma_offset"],
                video_parameters["luma_excursion"],
            )
        )
        explanations.append(
            (
                "The {} and {} components consist of".format(c1_name, c2_name),
                c_dd,
                video_parameters["color_diff_offset"],
                video_parameters["color_diff_excursion"],
            )
        )

    for prefix, dd, offset, excursion in explanations:
        padding_bits = (dd.bytes_per_sample * 8) - dd.depth_bits
        out += (
            "{} {}x{} {} bit values{}{}. "
            "Values run from 0 (video level {:0.2f}) "
            "to {} (video level {:0.2f})."
            "\n\n"
        ).format(
            prefix,
            dd.width,
            dd.height,
            dd.depth_bits,
            (
                (
                    " stored as {} bit ({} byte) values "
                    "(with the {} most significant bit{} set to 0)"
                ).format(
                    dd.bytes_per_sample * 8,
                    dd.bytes_per_sample,
                    padding_bits,
                    "s" if padding_bits != 1 else "",
                )
                if 8 * dd.bytes_per_sample != dd.depth_bits
                else ""
            ),
            " in little-endian byte order" if dd.bytes_per_sample > 1 else "",
            int_to_float(0, offset, excursion),
            (2 ** dd.depth_bits) - 1,
            int_to_float((2 ** dd.depth_bits) - 1, offset, excursion),
        )

    return out.rstrip()


def explain_color_model(video_parameters, picture_coding_mode):
    """
    Produce a human-readable informative definition of the color model in use.
    """
    primaries = PRESET_COLOR_PRIMARIES[video_parameters["color_primaries_index"]]
    matrix = PRESET_COLOR_MATRICES[video_parameters["color_matrix_index"]]
    transfer_function = PRESET_TRANSFER_FUNCTIONS[
        video_parameters["transfer_function_index"]
    ]

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


def explain_pixel_aspect_ratio(video_parameters, picture_coding_mode):
    """
    Produce a human-readable informative definition of the pixel aspect ratio.
    """
    return (
        "The pixel aspect ratio is {}:{} (not to be confused with the frame aspect ratio)."
    ).format(
        video_parameters["pixel_aspect_ratio_numer"],
        video_parameters["pixel_aspect_ratio_denom"],
    )


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
        self.prefix = prefix
        self.command = ""

        # [(fragment, note), ...]
        self.notes = []

    def append(self, fragment, note=None, strip=True):
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
            if strip:
                self.notes.append((fragment.strip(), note))
            else:
                self.notes.append((fragment, note))

    def append_linebreak(self):
        self.append(" \\\n  ")

    def explain(self):
        """
        Return a markdown-formatted explanation of this command.
        """
        out = ""

        out += "    {}{}\n".format(
            self.prefix,
            indent(self.command, "    " + " " * len(self.prefix)).lstrip(),
        )

        # Add list of explanations
        if self.notes:
            out += "\n"
            out += "Where:\n"
            out += "\n"

            for (fragment, note) in self.notes:
                out += "* `{}` = {}\n".format(
                    fragment,
                    note,
                )

        out = out.rstrip()

        return out

    def __repr__(self):
        return "<{!r} {!r}>".format(
            type(self).__name__,
            self.command,
        )


class UnsupportedPictureFormat(Exception):
    """
    Thrown when a picture format is not supported by a command line tool.
    """


def example_ffmpeg_command(picture_filename, video_parameters, picture_coding_mode):
    """
    Create a :py:class:`CommandExplainer` defining an FFmpeg ``ffplay`` command
    to play the specified video format.

    The resulting commands attempt to achieve the correct:

    * Resolution
    * Bit depth
    * Pixel aspect ratio
    * Color subsampling mode
    * Frame rate
    * Interlacing (fields are always converted into frames and, if the
      underlying picture is interlaced, deinterlacing is applied)
    * RGB vs Luma + Chroma representation

    In some cases, :py:exc:`UnsupportedPictureFormat` will be raised where the
    format is sufficiently unusual as to be completely unsupported by FFMPEG
    (e.g.  extremely high bit depths or color subsampling under RGB mode).

    Color model parameters are essentially ignored.

    Finally, the 'clean area' parameters are ignored completely.
    """
    command = CommandExplainer("$ ")

    command.append("ffplay")

    # ------------------------------------------------------------------------
    # Set input image format
    # ------------------------------------------------------------------------

    command.append_linebreak()
    command.append("-f image2", "Read pictures from individual files")

    # ------------------------------------------------------------------------
    # Set picture size
    # ------------------------------------------------------------------------

    dimensions_and_depths = compute_dimensions_and_depths(
        video_parameters,
        picture_coding_mode,
    )

    command.append_linebreak()
    command.append(
        "-video_size {}x{}".format(
            dimensions_and_depths["Y"].width,
            dimensions_and_depths["Y"].height,
        ),
        "Picture size (not frame size).",
    )

    # ------------------------------------------------------------------------
    # Set frame rate
    # ------------------------------------------------------------------------

    frame_rate = Fraction(
        video_parameters["frame_rate_numer"], video_parameters["frame_rate_denom"]
    )

    command.append_linebreak()
    command.append(
        "-framerate {}".format(
            frame_rate
            if picture_coding_mode == PictureCodingModes.pictures_are_frames
            else frame_rate * 2
        ),
        "Picture rate (not frame rate)",
    )

    # ------------------------------------------------------------------------
    # Set pixel format (e.g. RGB-vs-YCbCr, bit depth, color subsampling)
    # ------------------------------------------------------------------------

    command.append_linebreak()
    command.append("-pixel_format ", "Specifies raw picture encoding.")

    if is_rgb_color(video_parameters):
        command.append("gbr", "RGB color.")

        if (
            video_parameters["color_diff_format_index"]
            != ColorDifferenceSamplingFormats.color_4_4_4
        ):
            raise UnsupportedPictureFormat(
                "Only 4:4:4 color difference sampling is supported for RGB video."
            )
    elif video_parameters["color_matrix_index"] == PresetColorMatrices.reversible:
        raise UnsupportedPictureFormat(
            "Y Cg Co color ('reversible' color matrix) unsupported."
        )
    else:
        command.append("yuv", "Y C1 C2 color.")

        color_difference_sampling_format = COLOR_DIFF_FORMAT_NAMES[
            video_parameters["color_diff_format_index"]
        ]
        command.append(
            color_difference_sampling_format.replace(":", ""),
            "{} color difference subsampling.".format(
                color_difference_sampling_format,
            ),
        )

    command.append("p", "Planar format.")

    if (
        dimensions_and_depths["Y"].bytes_per_sample
        != dimensions_and_depths["C1"].bytes_per_sample
    ):
        raise UnsupportedPictureFormat(
            "Luma and color difference components differ in depth ({} bits and {} bits)".format(
                dimensions_and_depths["Y"].bytes_per_sample,
                dimensions_and_depths["C1"].bytes_per_sample,
            )
        )

    depth_bits = dimensions_and_depths["Y"].depth_bits
    if depth_bits == 8:
        # No extension required for 8-bit values
        pass
    elif depth_bits in (9, 10, 12, 14, 16):
        command.append(
            "{}le".format(depth_bits),
            "{} bit little-endian values, LSB-aligned within 16 bit words.".format(
                depth_bits
            ),
        )
    else:
        raise UnsupportedPictureFormat(
            "Unsupported bit depth: {} bits".format(
                dimensions_and_depths["Y"].depth_bits
            )
        )

    # ------------------------------------------------------------------------
    # Input file format
    # ------------------------------------------------------------------------

    command.append_linebreak()
    command.append(
        "-i {}".format(get_picture_filename_pattern(picture_filename)),
        "Input raw picture filename pattern",
    )

    # ------------------------------------------------------------------------
    # Frames-from-Fields (de)interlacing
    # ------------------------------------------------------------------------

    vf_args = []

    if picture_coding_mode == PictureCodingModes.pictures_are_fields:
        # When pictures are fields we (at least) need to interleave pairs of
        # pictures into whole frames. For truly interlaced content, a
        # deinterlace filter can also be applied for clean display.
        vf_args.append(
            (
                "weave={}".format(
                    "t" if video_parameters["top_field_first"] else "b",
                ),
                "interleave pairs of pictures, {} field first".format(
                    "top" if video_parameters["top_field_first"] else "bottom",
                ),
            )
        )

        if video_parameters["source_sampling"] == SourceSamplingModes.interlaced:
            vf_args.append((",",))
            vf_args.append(
                (
                    "yadif",
                    "(optional) apply a deinterlacing filter for display purposes",
                )
            )
    elif (
        picture_coding_mode == PictureCodingModes.pictures_are_frames
        and video_parameters["source_sampling"] == SourceSamplingModes.interlaced
    ):
        # When pictures are frames containing interlaced content, we can
        # optionally apply a deinterlace filter
        vf_args.append(
            (
                "setfield={}".format(
                    "tff" if video_parameters["top_field_first"] else "bff",
                ),
                "define the field order as {} field first".format(
                    "top" if video_parameters["top_field_first"] else "bottom",
                ),
            )
        )

        vf_args.append((",",))
        vf_args.append(
            ("yadif", "(optional) apply a deinterlacing filter for display purposes")
        )

    # ------------------------------------------------------------------------
    # Pixel aspect ratio
    # ------------------------------------------------------------------------
    pixel_aspect_ratio = Fraction(
        video_parameters["pixel_aspect_ratio_numer"],
        video_parameters["pixel_aspect_ratio_denom"],
    )
    if pixel_aspect_ratio != 1:
        if vf_args:
            vf_args.append((",",))
        vf_args.append(
            (
                "scale='trunc((iw*{})/{}):ih'".format(
                    pixel_aspect_ratio.numerator,
                    pixel_aspect_ratio.denominator,
                ),
                "rescale non-square pixels for display with square pixels",
            )
        )

    if vf_args:
        command.append_linebreak()
        command.append("-vf ", "define a pipeline of video filtering operations")
        for args in vf_args:
            command.append(*args)

    return command


def example_imagemagick_command(
    picture_filename, video_parameters, picture_coding_mode
):
    """
    Create a :py:class:`CommandExplainer` defining an ImagMagick ``display``
    command to display a single picture in the raw video format.

    The resulting commands attempt to achieve the correct:

    * Resolution
    * Color subsampling mode
    * RGB vs Luma + Color Difference representation

    Unfortunately, bit depths greater than 8 bits are unsupported due to
    the unreliability of ImageMagick's handling of 16-bit color.

    In some cases, :py:exc:`UnsupportedPictureFormat` will be raised where the
    format is sufficiently unusual as to be completely unsupported by
    ImageMagick (e.g.  extremely high bit depths or color subsampling under
    RGB mode).

    Color model parameters are essentially ignored.

    Interlaced pictures (or progressive frames encoded as fields) are not
    (de)interlaced: pictures are shown as-is.

    Finally, the 'clean area' parameters are ignored completely.
    """
    command = CommandExplainer("$ ")

    command.append("convert")

    # ------------------------------------------------------------------------
    # Set picture size
    # ------------------------------------------------------------------------

    dimensions_and_depths = compute_dimensions_and_depths(
        video_parameters,
        picture_coding_mode,
    )

    command.append_linebreak()
    command.append(
        "-size {}x{}".format(
            dimensions_and_depths["Y"].width,
            dimensions_and_depths["Y"].height,
        ),
        "Picture size.",
    )

    # ------------------------------------------------------------------------
    # Depth
    # ------------------------------------------------------------------------

    if dimensions_and_depths["Y"].depth_bits != dimensions_and_depths["C1"].depth_bits:
        raise UnsupportedPictureFormat(
            "Luma and chroma components differ in depth ({} bits and {} bits)".format(
                dimensions_and_depths["Y"].depth_bits,
                dimensions_and_depths["C1"].depth_bits,
            )
        )

    depth_bits = dimensions_and_depths["Y"].depth_bits
    if depth_bits == 8:
        command.append_linebreak()
        command.append(
            "-depth {}".format(depth_bits),
            "{} bit values.".format(depth_bits),
        )
    else:
        raise UnsupportedPictureFormat(
            "Unsupported bit depth: {} bits".format(
                dimensions_and_depths["Y"].depth_bits
            )
        )

    # ------------------------------------------------------------------------
    # Sampling factor
    # ------------------------------------------------------------------------

    if is_rgb_color(video_parameters):
        if (
            video_parameters["color_diff_format_index"]
            != ColorDifferenceSamplingFormats.color_4_4_4
        ):
            raise UnsupportedPictureFormat(
                "Only 4:4:4 color difference sampling is supported for RGB video."
            )
    elif video_parameters["color_matrix_index"] == PresetColorMatrices.reversible:
        raise UnsupportedPictureFormat(
            "Y Cg Co color ('reversible' color matrix) unsupported."
        )
    else:
        color_difference_sampling_format = COLOR_DIFF_FORMAT_NAMES[
            video_parameters["color_diff_format_index"]
        ]
        command.append_linebreak()
        command.append(
            "-sampling-factor {}".format(color_difference_sampling_format),
            "{} color difference subsampling.".format(
                color_difference_sampling_format,
            ),
        )

    # ------------------------------------------------------------------------
    # Planar video format
    # ------------------------------------------------------------------------

    command.append_linebreak()
    command.append(
        "-interlace plane", "Planar format (not related to video interlace mode)."
    )

    # ------------------------------------------------------------------------
    # Colorspace
    # ------------------------------------------------------------------------

    command.append_linebreak()
    command.append("-colorspace sRGB", "Display as if using sRGB color.")

    # ------------------------------------------------------------------------
    # Input file
    # ------------------------------------------------------------------------

    command.append_linebreak()
    if is_rgb_color(video_parameters):
        command.append(
            "rgb:",
            "Input is RGB picture.",
        )
    else:
        command.append(
            "yuv:",
            "Input is Y C1 C2 picture.",
        )

    command.append(picture_filename, "Input filename.")

    # ------------------------------------------------------------------------
    # Convert GBR to RGB channel order expected by ImageMagick
    # ------------------------------------------------------------------------

    if is_rgb_color(video_parameters):
        command.append_linebreak()
        command.append(
            "-separate -swap 1,2 -swap 0,1 -combine",
            "Change from GRB to RGB channel order (expected by ImageMagick).",
        )

    # ------------------------------------------------------------------------
    # Pixel aspect ratio
    # ------------------------------------------------------------------------
    pixel_aspect_ratio = Fraction(
        video_parameters["pixel_aspect_ratio_numer"],
        video_parameters["pixel_aspect_ratio_denom"],
    )
    if pixel_aspect_ratio != 1:
        command.append_linebreak()
        command.append(
            "-resize {}%,100%".format(float(pixel_aspect_ratio * 100)),
            "rescale non-square pixels for display with square pixels",
        )

    # ------------------------------------------------------------------------
    # Output file (PNG)
    # ------------------------------------------------------------------------

    command.append_linebreak()
    command.append(
        "png24:{}png".format(picture_filename[:-3]),
        "Save as 24-bit PNG (e.g. 8 bit channels)",
    )

    return command


def explain_ffmpeg_command(picture_filename, video_parameters, picture_coding_mode):
    """
    Produce a human-readable informative message explaining how FFMPEG can be
    used to playback the raw video format.
    """
    try:
        command = example_ffmpeg_command(
            picture_filename, video_parameters, picture_coding_mode
        )
    except UnsupportedPictureFormat as e:
        return "No FFMPEG command is available for this raw video format ({}).".format(
            e
        )

    out = ""

    out += (
        "The following command can be used to play back this video format using FFMPEG:"
    )

    out += "\n"
    out += "\n"

    out += command.explain()

    out += "\n"
    out += "\n"

    out += "This command is provided as a minimal example for basic playback "
    out += "of this raw video format.  While it attempts to ensure correct "
    out += "frame rate, pixel aspect ratio, interlacing mode and basic pixel "
    out += "format, color model options are omitted due to inconsistent "
    out += "handling by FFMPEG."

    return out


def explain_imagemagick_command(
    picture_filename, video_parameters, picture_coding_mode
):
    """
    Produce a human-readable informative message explaining how ImageMagick can be
    used to display a picture in the raw format.
    """
    try:
        command = example_imagemagick_command(
            picture_filename, video_parameters, picture_coding_mode
        )
    except UnsupportedPictureFormat as e:
        return "No ImageMagick command is available for this raw picture format ({}).".format(
            e
        )

    out = ""

    out += "The following command can be used to convert a single raw picture "
    out += "into PNG format for viewing in a conventional image viewer:"

    out += "\n"
    out += "\n"

    out += command.explain()

    out += "\n"
    out += "\n"

    out += "This command is provided as a minimal example for basic viewing "
    out += "of pictures. Interlacing and correct color model conversion are "
    out += "not implemented."

    return out


def main(*args, **kwargs):
    parser = ArgumentParser(
        description="""
        Informatively explain the video format used a raw video
        file generated by the VC-2 conformance software.
    """
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {}".format(__version__),
    )

    parser.add_argument(
        "filename",
        help="""
            The filename of a .raw or .json raw video file.
        """,
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

    out = ""

    out += "Normative description\n"
    out += "=====================\n"
    out += "\n"
    out += "Picture coding mode: {} ({:d})\n".format(
        picture_coding_mode.name,
        picture_coding_mode,
    )
    out += "\n"
    out += "Video parameters:\n"
    out += "\n"
    out += str(video_parameters).partition("\n")[2].replace("  ", "* ") + "\n"
    out += "\n"
    out += "Explanation (informative)\n"
    out += "=========================\n"
    out += "\n"
    out += explain_interleaving(video_parameters, picture_coding_mode) + "\n"
    out += "\n"
    out += (
        explain_component_order_and_sampling(video_parameters, picture_coding_mode)
        + "\n"
    )
    out += "\n"
    out += explain_component_sizes(video_parameters, picture_coding_mode) + "\n"
    out += "\n"
    out += explain_color_model(video_parameters, picture_coding_mode) + "\n"
    out += "\n"
    out += explain_pixel_aspect_ratio(video_parameters, picture_coding_mode) + "\n"
    out += "\n"
    out += "Example FFMPEG command (informative)\n"
    out += "====================================\n"
    out += "\n"
    out += (
        explain_ffmpeg_command(picture_filename, video_parameters, picture_coding_mode)
        + "\n"
    )
    out += "\n"
    out += "Example ImageMagick command (informative)\n"
    out += "=========================================\n"
    out += "\n"
    out += (
        explain_imagemagick_command(
            picture_filename, video_parameters, picture_coding_mode
        )
        + "\n"
    )

    width = get_terminal_size()[0]
    print(wrap_paragraphs(out, width))

    return 0


if __name__ == "__main__":
    sys.exit(main())
