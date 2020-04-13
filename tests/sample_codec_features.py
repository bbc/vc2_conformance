"""
Sample :Py:class:`vc2_conformance.codec_features.CodecFeatures`
objects for use in this test suite.
"""

import os

from vc2_conformance.codec_features import read_codec_features_csv


MINIMAL_CODEC_FEATURES = read_codec_features_csv(open(os.path.join(
    os.path.dirname(__file__),
    "sample_codec_features.csv",
)))["minimal"]
"""
A set of minimal codec features. A progressive, 8x4, 8bit, 4:4:4, YCbCr format
with a single 2D Haar transform applied in two horizontal slices and 4:1
compression ratio.
"""


