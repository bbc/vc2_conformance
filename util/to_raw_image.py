"""
This script may be used to convert from a master image file into the RAW file
format expected by the VC-2 conformance software. It is intended for use only
by developers of the VC-2 conformance software.

Usage:

    $ python to_raw_image.py path/to/image path/tp/output.raw
"""

import av

import numpy as np

import argparse

from vc2_data_tables import (
    ColorDifferenceSamplingFormats,
    SourceSamplingModes,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
    PictureCodingModes,
)

from vc2_conformance.video_parameters import VideoParameters

from vc2_conformance import file_format


parser = argparse.ArgumentParser()
parser.add_argument("input_filename")
parser.add_argument("output_filename")

args = parser.parse_args()

# Decode picture
container = av.open(args.input_filename)
frame = next(iter(container.decode(video=0)))
if frame.format.name == "rgb48le":
    dtype = np.uint16
    picture_bit_width = 16
elif frame.format.name in ("rgb", "rgba"):
    dtype = np.uint8
    picture_bit_width = 8
else:
    raise Exception("Unsupported image format: {}".format(frame.format.name))

# Load into Numpy array
orig_image = np.frombuffer(frame.planes[0].to_bytes(), dtype=dtype,).reshape(
    frame.height, frame.width, -1,
)

r = orig_image[:, :, 0]
g = orig_image[:, :, 1]
b = orig_image[:, :, 2]

height, width = r.shape

picture = {
    "Y": g.tolist(),
    "C1": b.tolist(),
    "C2": r.tolist(),
    "pic_num": 0,
}

video_parameters = VideoParameters(
    frame_width=width,
    frame_height=height,
    color_diff_format_index=ColorDifferenceSamplingFormats.color_4_4_4,
    source_sampling=SourceSamplingModes.progressive,
    top_field_first=True,
    frame_rate_numer=1,
    frame_rate_denom=1,
    pixel_aspect_ratio_numer=1,
    pixel_aspect_ratio_denom=1,
    clean_width=width,
    clean_height=height,
    left_offset=0,
    top_offset=0,
    luma_offset=0,
    luma_excursion=(1 << picture_bit_width) - 1,
    color_diff_offset=0,
    color_diff_excursion=(1 << picture_bit_width) - 1,
    # XXX: This may/may not match the supplied image's actual colour model...
    color_primaries_index=PresetColorPrimaries.hdtv,
    color_matrix_index=PresetColorMatrices.rgb,
    transfer_function_index=PresetTransferFunctions.tv_gamma,
)

picture_coding_mode = PictureCodingModes.pictures_are_frames

file_format.write(
    picture, video_parameters, picture_coding_mode, args.output_filename,
)
