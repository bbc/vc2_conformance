"""
``vc2-raw-compare``
===================

An command-line utility which compares pairs of pictures.
"""

import sys

from argparse import ArgumentParser

from collections import OrderedDict

import numpy as np

from vc2_conformance._string_utils import indent

from vc2_conformance.file_format import (
    get_metadata_and_picture_filenames,
    compute_dimensions_and_depths,
    read_metadata,
    read_picture,
)

from vc2_conformance.video_parameters import VideoParameters


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
    except OSError:
        metadata_a = None

    try:
        with open(meta_fn_b, "rb") as f:
            metadata_b = read_metadata(f)
    except OSError:
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

    (video_parameters_a, picture_coding_mode_a, picture_number_a,) = metadata_a

    (video_parameters_b, picture_coding_mode_b, picture_number_b,) = metadata_b

    try:
        with open(pic_fn_a, "rb") as f:
            picture_a = read_picture(
                video_parameters_a, picture_coding_mode_a, picture_number_a, f,
            )
            if len(f.read(1)) != 0:
                raise ValueError()
    except OSError:
        sys.stderr.write("Error: Could not open first picture.\n")
        sys.exit(101)
    except ValueError:
        sys.stderr.write("Error: First picture file has incorrect size.\n")
        sys.exit(102)

    try:
        with open(pic_fn_b, "rb") as f:
            picture_b = read_picture(
                video_parameters_b, picture_coding_mode_b, picture_number_b, f,
            )
            if len(f.read(1)) != 0:
                raise ValueError()
    except OSError:
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
        "filename_a",
        help="""
            The filename of a .raw or .json raw picture.
        """,
    )

    parser.add_argument(
        "filename_b",
        help="""
            The filename of a .raw or .json raw picture.
        """,
    )

    output_group = parser.add_argument_group("difference image options",)

    output_group.add_argument(
        "--difference",
        "-d",
        type=str,
        metavar="FILENAME",
        help="""
            Output a difference image to the specified file.
        """,
    )

    output_group.add_argument(
        "--difference-mask",
        "-D",
        type=str,
        metavar="FILENAME",
        help="""
            Output a difference mask image to the specified file. This mask
            will contain white pixels wherever the input images differ.
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
        video_parameters, picture_coding_mode,
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


def main(*args, **kwargs):
    args = parse_args(*args, **kwargs)

    (
        (picture_a, video_parameters_a, picture_coding_mode_a),
        (picture_b, video_parameters_b, picture_coding_mode_b),
        byte_for_byte_identical,
    ) = read_pictures_with_only_one_metadata_file_required(
        args.filename_a, args.filename_b,
    )

    if video_parameters_a != video_parameters_b:
        print("Video parameters are different:")
        print(indent(video_parameter_diff(video_parameters_a, video_parameters_b)))
        return 1

    if picture_coding_mode_a != picture_coding_mode_b:
        print("Picture coding modes are different:")
        print(
            indent(
                picture_coding_mode_diff(picture_coding_mode_a, picture_coding_mode_b)
            )
        )
        return 2

    if picture_a["pic_num"] != picture_b["pic_num"]:
        print("Picture numbers are different:")
        print(indent(picture_number_diff(picture_a["pic_num"], picture_b["pic_num"])))
        return 3

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
            print(
                "Warning: Padding bits in raw picture data are different "
                "(is file endianness correct?)"
            )
        print("Pictures are identical")
    else:
        print("Pictures are different:")
        print(indent(differences))

    return 0 if identical else 4


if __name__ == "__main__":
    sys.exit(main())
