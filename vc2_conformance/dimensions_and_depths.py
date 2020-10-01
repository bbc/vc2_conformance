"""
The :py:mod:`vc2_conformance.dimensions_and_depths` module contains the
:py:func:`compute_dimensions_and_depths` function which returns the picture
dimensions and bit depths implied by a VC-2 video format.

.. autofunction:: compute_dimensions_and_depths

.. autoclass:: DimensionsAndDepths

"""

from collections import OrderedDict, namedtuple

from vc2_conformance.pseudocode.vc2_math import intlog2

from vc2_conformance.pseudocode.state import State

from vc2_conformance.pseudocode.video_parameters import set_coding_parameters


__all__ = [
    "DimensionsAndDepths",
    "compute_dimensions_and_depths",
]


DimensionsAndDepths = namedtuple(
    "DimensionsAndDepths",
    "width,height,depth_bits,bytes_per_sample",
)
"""
A set of picture component dimensions and bit depths.

Parameters
==========
width, height : int
    The dimensions of the picture.
depth_bits : int
    The number of bits per pixel.
bytes_per_sample : int
    The number of bytes used to store each pixel value in raw file formats (see
    :py:mod:`vc2_conformance.file_format`).
"""


def compute_dimensions_and_depths(video_parameters, picture_coding_mode):
    """
    Compute the dimensions, bit depth and bytes-per-sample of a picture.

    Parameters
    ==========
    video_parameters : :py:class:`~vc2_conformance.pseudocode.video_parameters.VideoParameters`
    picture_coding_mode : :py:class:`~vc2_data_tables.PictureCodingModes`

    Returns
    =======
    OrderedDict
        An ordered dictionary mapping from component name ("Y", "C1" and "C2")
        to a :py:class:`DimensionsAndDepths` (width, height, depth_bits,
        bytes_per_sample) namedtuple.
    """
    # NB: We use the pseudocode to actually compute the dimensions and signal
    # range to avoid mistakes
    state = State(picture_coding_mode=picture_coding_mode)
    set_coding_parameters(state, video_parameters)

    out = OrderedDict()

    for component in ["Y", "C1", "C2"]:
        if component == "Y":
            width = state["luma_width"]
            height = state["luma_height"]
            depth_bits = state["luma_depth"]
        else:
            width = state["color_diff_width"]
            height = state["color_diff_height"]
            depth_bits = state["color_diff_depth"]

        bytes_per_sample = (depth_bits + 7) // 8  # Round up to whole number of bytes
        bytes_per_sample = 1 << intlog2(bytes_per_sample)  # Round up to power of two

        out[component] = DimensionsAndDepths(
            width, height, depth_bits, bytes_per_sample
        )

    return out
