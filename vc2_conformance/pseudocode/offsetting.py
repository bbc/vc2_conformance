"""
Picture component offsetting routines (15)

This module collects picture component value offsetting functions from (15) and
augments these with complementary de-offsetting functions (inferred from, but
not defined by the standard).
"""

from vc2_conformance.pseudocode.metadata import ref_pseudocode

from vc2_conformance.pseudocode.arrays import (
    width,
    height,
)


__all__ = [
    "offset_picture",
    "offset_component",
    "remove_offset_picture",
    "remove_offset_component",
]


@ref_pseudocode
def offset_picture(state, current_picture):
    """(15.5) Remove picture value offsets (added during encoding).

    Parameters
    ==========
    state : :py:class:`vc2_conformance.pseudocode.state.State`
        Where ``luma_depth`` and ``color_diff_depth`` are defined.
    current_picture : {comp: [[pixel_value, ...], ...], ...}
        Will be mutated in-place.
    """
    for c in ["Y", "C1", "C2"]:
        offset_component(state, current_picture[c], c)


@ref_pseudocode
def offset_component(state, comp_data, c):
    """(15.5) Remove picture value offsets from a single component."""
    for y in range(height(comp_data)):
        for x in range(width(comp_data)):
            if c == "Y":
                comp_data[y][x] += 2 ** (state["luma_depth"] - 1)
            else:
                comp_data[y][x] += 2 ** (state["color_diff_depth"] - 1)


def remove_offset_picture(state, current_picture):
    """Inverse of offset_picture (15.5). Centers picture values around zero."""
    for c in ["Y", "C1", "C2"]:
        remove_offset_component(state, current_picture[c], c)


def remove_offset_component(state, comp_data, c):
    """
    Inverse of offset_component (15.5). Centers picture values around zero.

    Parameters
    ==========
    state : :py:class:`vc2_conformance.pseudocode.state.State`
        Where ``luma_depth`` and ``color_diff_depth`` are defined.
    current_picture : {comp: [[pixel_value, ...], ...], ...}
        Will be mutated in-place.
    """
    for y in range(height(comp_data)):
        for x in range(width(comp_data)):
            if c == "Y":
                comp_data[y][x] -= 2 ** (state["luma_depth"] - 1)
            else:
                comp_data[y][x] -= 2 ** (state["color_diff_depth"] - 1)
