r"""
.. _vc2-picture-compare:

``vc2-picture-compare``
=======================

A command-line utility which compares pairs of raw pictures (see
:ref:`file-format`), or pairs of directories containing a series of raw
pictures.

Usage
-----

Given a pair of images in raw format (see :ref:`file-format`), these images can
be compared as follows::

    $ vc2-picture-compare image_a.raw image_b.raw
    Pictures are different:
      Y: Different: PSNR = 55.6 dB, 1426363 pixels (68.8%) differ
      C1: Different: PSNR = 57.7 dB, 662607 pixels (63.9%) differ
      C2: Different: PSNR = 56.8 dB, 703531 pixels (67.9%) differ

Alternatively a pair of directories containing images whose filenames end
with a number (and the extensions ``.raw`` and ``.json``). For example::

    $ vc2-picture-compare ./directory_a/ ./directory_b/
    Comparing ./directory_a/picture_0.raw and ./directory_b/picture_0.raw:
      Pictures are identical
    Comparing ./directory_a/picture_1.raw and ./directory_b/picture_1.raw:
      Pictures are different:
        Y: Different: PSNR = 55.6 dB, 1426363 pixels (68.8%) differ
        C1: Different: PSNR = 57.7 dB, 662607 pixels (63.9%) differ
        C2: Different: PSNR = 56.8 dB, 703531 pixels (67.9%) differ
    Comparing ./directory_a/picture_2.raw and ./directory_b/picture_2.raw:
      Pictures are identical
    Summary: 2 identical, 1 different

Differences in the encoded values are reported separately for each picture
component.

Peak Signal to Noise Ratio (PSNR) figures give the PSNR of the raw signal
values (and not, for example, linear light levels).

The number of pixels which are not bit-for-bit identical is also reported.

The tool also compares the metadata of the raw images and will flag up
differences here too, for example::

    $ vc2-picture-compare picture_hd.raw picture_cif.raw
    Picture numbers are different:
    Video parameters are different:
      - frame_width: 1920
      + frame_width: 352
      - frame_height: 1080
      + frame_height: 288
      - color_diff_format_index: color_4_2_2 (1)
      + color_diff_format_index: color_4_2_0 (2)
        source_sampling: progressive (0)
        top_field_first: True
      - frame_rate_numer: 50
      + frame_rate_numer: 25
      - frame_rate_denom: 1
      + frame_rate_denom: 2
      - pixel_aspect_ratio_numer: 1
      + pixel_aspect_ratio_numer: 12
      - pixel_aspect_ratio_denom: 1
      + pixel_aspect_ratio_denom: 11
      - clean_width: 1920
      + clean_width: 352
      - clean_height: 1080
      + clean_height: 288
        left_offset: 0
        top_offset: 0
      - luma_offset: 64
      + luma_offset: 0
      - luma_excursion: 876
      + luma_excursion: 255
      - color_diff_offset: 512
      + color_diff_offset: 128
      - color_diff_excursion: 896
      + color_diff_excursion: 255
      - color_primaries_index: hdtv (0)
      + color_primaries_index: sdtv_625 (2)
      - color_matrix_index: hdtv (0)
      + color_matrix_index: sdtv (1)
        transfer_function_index: tv_gamma (0)

When picture metadata differs, the pixel values will not be compared since the
difference in metadata typically means a difference in format making the
pictures incomparable.


Generating difference masks
---------------------------

The ``vc2-picture-compare`` tool can optionally output a simple difference mask
image using ``--difference-mask``/``-D``. The generated image contains white
pixels wherever the inputs differed and black pixels wherever they were
identical. The generated difference mask is output as a raw file of the same
format as the two input files. This mode is only supported when two individual
files are provided, not two directories.

For example::

    $ vc2-picture-compare \
          image_a.raw \
          image_b.raw \
          --difference-mask difference_mask.raw
    Pictures are different:
      Y: Different: PSNR = 55.6 dB, 1426363 pixels (68.8%) differ
      C1: Different: PSNR = 57.7 dB, 662607 pixels (63.9%) differ
      C2: Different: PSNR = 56.8 dB, 703531 pixels (67.9%) differ


Arguments
---------

The complete set of arguments can be listed using ``--help``

.. program-output:: vc2-picture-compare --help

"""

import os

import sys

import re

from argparse import ArgumentParser

from collections import OrderedDict

import numpy as np

from vc2_data_tables import ColorDifferenceSamplingFormats

from vc2_conformance import __version__

from vc2_conformance.string_utils import indent

from vc2_conformance.color_conversion import (
    from_xyz,
    matmul_colors,
    LINEAR_RGB_TO_XYZ,
)

from vc2_conformance.file_format import (
    get_metadata_and_picture_filenames,
    read_metadata,
    read_picture,
    write,
)

from vc2_conformance.dimensions_and_depths import compute_dimensions_and_depths

from vc2_conformance.pseudocode.video_parameters import VideoParameters


def read_pictures_with_only_one_metadata_file_required(filename_a, filename_b):
    """
    Read a pair of raw image files. If one of the two is missing its
    corresponding JSON metadata file, the metadata for the other file will be
    used.

    Returns a tuple with the following values:
    * ``(picture_a, video_parameters_a, picture_coding_mode_a)``
    * ``(picture_b, video_parameters_b, picture_coding_mode_b)``
    * ``byte_for_byte_identical``: This indicates that the two raw files
      are byte-for-byte identical, including the bits not responsible for
      encoding images (e.g. when 10-bit values are encoded as 16-bit words,
      this includes a check of the upper 6 bits). This may catch mistakes in
      formatting raw data files.
    """
    meta_fn_a, pic_fn_a = get_metadata_and_picture_filenames(filename_a)
    meta_fn_b, pic_fn_b = get_metadata_and_picture_filenames(filename_b)

    try:
        with open(meta_fn_a, "rb") as f:
            metadata_a = read_metadata(f)
    except (OSError, IOError):
        metadata_a = None

    try:
        with open(meta_fn_b, "rb") as f:
            metadata_b = read_metadata(f)
    except (OSError, IOError):
        metadata_b = None

    if metadata_a is None and metadata_b is None:
        sys.stderr.write("Error: Missing JSON metadata file for both pictures.\n")
        sys.exit(100)
    elif metadata_a is None:
        metadata_a = metadata_b
        sys.stderr.write(
            "Warning: Metadata missing for first picture. "
            "Will assume it is the same as the second.\n"
        )
    elif metadata_b is None:
        metadata_b = metadata_a
        sys.stderr.write(
            "Warning: Metadata missing for second picture. "
            "Will assume it is the same as the first.\n"
        )

    (
        video_parameters_a,
        picture_coding_mode_a,
        picture_number_a,
    ) = metadata_a

    (
        video_parameters_b,
        picture_coding_mode_b,
        picture_number_b,
    ) = metadata_b

    try:
        with open(pic_fn_a, "rb") as f:
            picture_a = read_picture(
                video_parameters_a,
                picture_coding_mode_a,
                picture_number_a,
                f,
            )
            if len(f.read(1)) != 0:
                raise ValueError()
    except (OSError, IOError):
        sys.stderr.write("Error: Could not open first picture.\n")
        sys.exit(101)
    except ValueError:
        sys.stderr.write("Error: First picture file has incorrect size.\n")
        sys.exit(102)

    try:
        with open(pic_fn_b, "rb") as f:
            picture_b = read_picture(
                video_parameters_b,
                picture_coding_mode_b,
                picture_number_b,
                f,
            )
            if len(f.read(1)) != 0:
                raise ValueError()
    except (OSError, IOError):
        sys.stderr.write("Error: Could not open second picture.\n")
        sys.exit(101)
    except ValueError:
        sys.stderr.write("Error: Second picture file has incorrect size.\n")
        sys.exit(102)

    with open(pic_fn_a, "rb") as fa:
        with open(pic_fn_b, "rb") as fb:
            byte_for_byte_identical = fa.read() == fb.read()

    return (
        (picture_a, video_parameters_a, picture_coding_mode_a),
        (picture_b, video_parameters_b, picture_coding_mode_b),
        byte_for_byte_identical,
    )


def parse_args(*args, **kwargs):
    parser = ArgumentParser(
        description="""
        Compare a pair of pictures in the raw format used by the VC-2
        conformance software.
    """
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {}".format(__version__),
    )

    parser.add_argument(
        "filename_a",
        help="""
            The filename of a .raw or .json raw picture, or a directory
            containing a series of .raw and .json files whose names end in a
            number.
        """,
    )

    parser.add_argument(
        "filename_b",
        help="""
            The filename of a .raw or .json raw picture, or a directory
            containing a series of .raw and .json files whose names end in a
            number.
        """,
    )

    output_group = parser.add_argument_group(
        "difference image options",
    )

    output_group.add_argument(
        "--difference-mask",
        "-D",
        type=str,
        metavar="FILENAME",
        help="""
            Output a difference mask image to the specified file. This mask
            will contain white pixels wherever the input images differ and
            black pixels where they match. Only available when comparing files
            (not directories).
        """,
    )

    return parser.parse_args(*args, **kwargs)


def video_parameter_diff(a, b):
    """
    Given a pair of :py:class:`~vc2_conformance.VideoParameters` dictionaries,
    return a diff-style string describing the difference between them.
    """
    # [(prefix, name, value), ...]
    out_lines = []
    for name, entry_obj in VideoParameters.entry_objs.items():
        if name not in a and name not in b:
            continue
        elif name not in b:
            out_lines.append(("-", name, entry_obj.to_string(a[name])))
        elif name not in a:
            out_lines.append(("+", name, entry_obj.to_string(b[name])))
        elif a[name] == b[name]:
            out_lines.append((" ", name, entry_obj.to_string(a[name])))
        else:
            out_lines.append(("-", name, entry_obj.to_string(a[name])))
            out_lines.append(("+", name, entry_obj.to_string(b[name])))

    return "\n".join(
        "{} {}: {}".format(prefix, name, value) for prefix, name, value in out_lines
    )


def picture_coding_mode_diff(a, b):
    """
    Return a string showing the difference between two picture coding modes.
    """
    return "- {} ({:d})\n+ {} ({:d})".format(a.name, a, b.name, b)


def picture_number_diff(a, b):
    """
    Return a string showing the difference between two picture numbers.
    """
    return "- {}\n+ {}".format(a, b)


def psnr(deltas, max_value):
    """
    Compute the peak signal to noise ratio (in dB) given a series of error
    values and associated maximum signal value.

    Returns None if the deltas are zero.
    """
    mean_square_error = np.mean(deltas * deltas)
    if mean_square_error == 0:
        return None
    else:
        return (20 * (np.log(max_value) / np.log(10))) - (
            10 * (np.log(mean_square_error) / np.log(10))
        )


def measure_differences(all_deltas, video_parameters, picture_coding_mode):
    """
    Given a 2D array of pixel value differences for each picture component,
    returns a string summarising the differences.
    """
    dimensions_and_depths = compute_dimensions_and_depths(
        video_parameters,
        picture_coding_mode,
    )

    delta_counts = {c: np.count_nonzero(d) for c, d in all_deltas.items()}
    psnrs = {
        component: psnr(deltas, (1 << dimensions_and_depths[component].depth_bits) - 1)
        for component, deltas in all_deltas.items()
    }

    identical = all(psnr is None for psnr in psnrs.values())

    differences = "\n".join(
        "{}: Identical".format(component)
        if psnrs[component] is None
        else "{}: Different: PSNR = {:.1f} dB, {} pixel{} ({:.1f}%) differ{}".format(
            component,
            psnrs[component],
            delta_counts[component],
            "s" if delta_counts[component] != 1 else "",
            (delta_counts[component] * 100.0) / all_deltas[component].size,
            "s" if delta_counts[component] == 1 else "",
        )
        for component in ["Y", "C1", "C2"]
    )

    return identical, differences


def generate_difference_mask_picture(deltas, video_parameters, picture_number=0):
    """
    Given a set of pixel delta values, produce a difference mask picture (which
    is white where the pixels have a non-zero difference and black otherwise).

    Parameters
    ==========
    deltas : {"Y": np.array, "C1": np.array, "C2": np.array}
        Deltas for each pixel in the input images.
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    picture_number : int

    Returns
    =======
    mask_picture : {"Y": [[...]], "C1": [[...]], "C2": [[...]], "pic_num": int}
        A mask picture, in the same format as the original pictures.

        The mask will be white in all pixels for which *any* picture component
        differs at the corresponding pixel location. For formats using
        subsampled color differences, a difference in a color difference
        component will result in 2 or 4 pixels in the mask being illuminated.

        The 'white' and 'black' reported in the mask are video white and video
        black, not super white or super black (for color formats which support
        this).
    """
    masks = {c: deltas[c] != 0 for c, d in deltas.items()}

    # Upsample color difference components
    repeat_x, repeat_y = {
        ColorDifferenceSamplingFormats.color_4_4_4: (1, 1),
        ColorDifferenceSamplingFormats.color_4_2_2: (2, 1),
        ColorDifferenceSamplingFormats.color_4_2_0: (2, 2),
    }[video_parameters["color_diff_format_index"]]

    for c in ["C1", "C2"]:
        if repeat_x != 1:
            masks[c] = np.repeat(masks[c], repeat_x, axis=1)
        if repeat_y != 1:
            masks[c] = np.repeat(masks[c], repeat_y, axis=0)

    # Create the mask
    mask = masks["Y"] | masks["C1"] | masks["C2"]

    # Convert to RGB color image with signals in the range 0.0 - 1.0
    rgb = np.repeat(mask, 3).reshape(mask.shape + (3,)).astype(float)

    # Convert to native color encoding
    xyz = matmul_colors(
        LINEAR_RGB_TO_XYZ[video_parameters["color_primaries_index"]], rgb
    )
    y, c1, c2 = from_xyz(xyz, video_parameters)

    return {
        "Y": y,
        "C1": c1,
        "C2": c2,
        "pic_num": picture_number,
    }


def enumerate_directories(dirname_a, dirname_b):
    """
    Given two directory names, return a list [(file_a, file_b), ...] of
    pictures to compare.

    Produces an error on stderr and call sys.exit if the files in the
    directories contain duplicate numbers, mismatched numbers or no numbered
    files at all.
    """
    file_lists = []  # [{number: filename_a, ...}, {number: filename_b, ...}]
    for dirname in [dirname_a, dirname_b]:
        # Find just the .raw files
        filenames = [
            os.path.join(dirname, name)
            for name in os.listdir(dirname)
            if name.endswith(".raw") and os.path.isfile(os.path.join(dirname, name))
        ]

        # Extract the numbers (checking for duplicates)
        numbered_filenames = {}  # {number: filename, ...}
        for filename in filenames:
            match = re.search(r"([0-9]+)\.raw$", filename)
            if match is None:
                sys.stderr.write(
                    "Error: An unnumbered file was found: {}\n".format(filename)
                )
                sys.exit(105)
            number = int(match.group(1))
            if number in numbered_filenames:
                sys.stderr.write(
                    "Error: More than one filename with number {} found in {}\n".format(
                        number,
                        dirname,
                    )
                )
                sys.exit(106)
            numbered_filenames[number] = filename

        if len(numbered_filenames) == 0:
            sys.stderr.write(
                "Error: No pictures found in directory {}\n".format(dirname)
            )
            sys.exit(107)

        file_lists.append(numbered_filenames)

    # Check numbers in filenames match
    filenames_a, filenames_b = file_lists
    unmatched_numbers = set(filenames_a).symmetric_difference(set(filenames_b))
    if unmatched_numbers:
        sys.stderr.write(
            "Error: Pictures numbered {} found in only one directory\n".format(
                ", ".join(map(str, sorted(unmatched_numbers)))
            )
        )
        sys.exit(108)

    return [
        (filename_a, filenames_b[num])
        for num, filename_a in sorted(filenames_a.items())
    ]


def compare_pictures(filename_a, filename_b, difference_mask_filename=None):
    """
    Compare a pair of pictures.

    Returns a string describing the differences
    between the pictures (if any) and integer return code which is non-zero iff
    the pictures differ.

    If a difference_mask filename is given, writes a difference mask to that
    file.
    """
    out = ""

    (
        (picture_a, video_parameters_a, picture_coding_mode_a),
        (picture_b, video_parameters_b, picture_coding_mode_b),
        byte_for_byte_identical,
    ) = read_pictures_with_only_one_metadata_file_required(filename_a, filename_b)

    if video_parameters_a != video_parameters_b:
        out += "Video parameters are different:\n"
        out += indent(video_parameter_diff(video_parameters_a, video_parameters_b))
        out += "\n"
        return (out.rstrip(), 1)

    if picture_coding_mode_a != picture_coding_mode_b:
        out += "Picture coding modes are different:\n"
        out += indent(
            picture_coding_mode_diff(picture_coding_mode_a, picture_coding_mode_b)
        )
        out += "\n"
        return (out.rstrip(), 2)

    if picture_a["pic_num"] != picture_b["pic_num"]:
        out += "Picture numbers are different:\n"
        out += indent(picture_number_diff(picture_a["pic_num"], picture_b["pic_num"]))
        out += "\n"
        return (out.rstrip(), 3)

    deltas = OrderedDict(
        (
            c,
            # NB: Convert pictures into Numpy arrays (for easier comparison)
            # using object mode (to ensure unlimited integer precision)
            np.array(picture_b[c], dtype=object) - np.array(picture_a[c], dtype=object),
        )
        for c in ["Y", "C1", "C2"]
    )

    identical, differences = measure_differences(
        deltas, video_parameters_a, picture_coding_mode_a
    )
    if identical:
        if not byte_for_byte_identical:
            out += (
                "Warning: Padding bits in raw picture data are different "
                "(is file endianness correct?)\n"
            )
        out += "Pictures are identical\n"
    else:
        out += "Pictures are different:\n"
        out += indent(differences)
        out += "\n"

    # Write difference mask, as required
    if difference_mask_filename is not None:
        mask = generate_difference_mask_picture(
            deltas,
            video_parameters_a,
            picture_number=picture_a["pic_num"],
        )
        write(mask, video_parameters_a, picture_coding_mode_a, difference_mask_filename)

    return (out.rstrip(), 0 if identical else 4)


def main(*args, **kwargs):
    args = parse_args(*args, **kwargs)

    a_is_dir = os.path.isdir(args.filename_a)
    b_is_dir = os.path.isdir(args.filename_b)

    if a_is_dir != b_is_dir:
        sys.stderr.write(
            "Error: Arguments must both be files or both be directories.\n"
        )
        return 103

    if a_is_dir and b_is_dir:
        if args.difference_mask is not None:
            sys.stderr.write(
                "Error: --difference-mask/-D may only be used "
                "when files (not directories) are compared.\n"
            )
            return 104

        final_exitcode = 0
        num_different = 0
        num_same = 0
        for filename_a, filename_b in enumerate_directories(
            args.filename_a, args.filename_b
        ):
            print("Comparing {} and {}:".format(filename_a, filename_b))
            message, exitcode = compare_pictures(filename_a, filename_b)
            print(indent(message))
            if exitcode != 0:
                final_exitcode = exitcode
                num_different += 1
            else:
                num_same += 1

        print("Summary: {} identical, {} different".format(num_same, num_different))
        return final_exitcode
    else:
        message, exitcode = compare_pictures(
            args.filename_a,
            args.filename_b,
            args.difference_mask,
        )
        print(message)
        return exitcode


if __name__ == "__main__":
    sys.exit(main())
