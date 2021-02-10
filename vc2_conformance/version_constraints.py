"""
This module defines the rules which define which version number a sequence must
be labelled with according to (11.2.2).
"""

from vc2_data_tables import Profiles

from vc2_conformance.pseudocode.state import State
from vc2_conformance.pseudocode.parse_code_functions import is_fragment


MINIMUM_MAJOR_VERSION = 1


def preset_frame_rate_version_implication(index):
    if index > 11:
        return 3
    else:
        return MINIMUM_MAJOR_VERSION


def preset_signal_range_version_implication(index):
    if index > 4:
        return 3
    else:
        return MINIMUM_MAJOR_VERSION


def preset_color_spec_version_implication(index):
    if index > 4:
        return 3
    else:
        return MINIMUM_MAJOR_VERSION


def preset_color_primaries_version_implication(index):
    if index > 3:
        return 3
    else:
        return MINIMUM_MAJOR_VERSION


def preset_color_matrix_version_implication(index):
    if index > 3:
        return 3
    else:
        return MINIMUM_MAJOR_VERSION


def preset_transfer_function_version_implication(index):
    if index > 3:
        return 3
    else:
        return MINIMUM_MAJOR_VERSION


def wavelet_transform_version_implication(
    wavelet_index, wavelet_index_ho, dwt_depth_ho
):
    if dwt_depth_ho != 0:
        return 3
    elif wavelet_index != wavelet_index_ho:
        return 3
    else:
        return MINIMUM_MAJOR_VERSION


def parse_code_version_implication(parse_code):
    if is_fragment(State(parse_code=parse_code)):
        return 3
    else:
        return MINIMUM_MAJOR_VERSION


# Errata: Previously major_version 2 was specified if a high quality picture
# appeared in a sequence. This, however, is insufficient as an empty sequence
# marked with the 'high quality' profile would not be supported by an older
# decoder so a new condition on the profile field has been added.
def profile_version_implication(profile):
    if profile == Profiles.high_quality:
        return 2
    else:
        return MINIMUM_MAJOR_VERSION
