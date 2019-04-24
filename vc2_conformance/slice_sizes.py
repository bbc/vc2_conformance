"""
Slice size computation functions defined by VC-2 in (13).

All of the functions below take a 'state' argument which should be a dictionary-like
object containing the following entries:

* ``"slices_x"``
* ``"slices_y"``
* ``"luma_width"``
* ``"luma_height"``
* ``"color_diff_width"``
* ``"color_diff_height"``
* ``"dwt_depth"``
* ``"dwt_depth_ho"``

The :py:func:`slice_bytes` function requires the following additional values:

* ``"slice_bytes_numerator"``
* ``"slice_bytes_denominator"``

The 'c' or 'comp' arguments should be set to one of the following strings:

* ``"Y"``
* ``"C1"``
* ``"C2"``
"""

__all__ = [
    "subband_width",
    "subband_height",
    "slice_bytes",
    "slice_left",
    "slice_right",
    "slice_top",
    "slice_bottom",
]


def subband_width(state, level, comp):
    """(13.2.3)"""
    if comp == "Y":
        w = state["luma_width"]
    elif comp == "C1" or comp == "C2":
        w = state["color_diff_width"]
    
    # Round up (pad) the picture width to the nearest multiple of the scale
    # width
    scale_w = 1 << (state["dwt_depth_ho"] + state["dwt_depth"])
    pw = scale_w * ((w + scale_w - 1) // scale_w)
    
    if level == 0:
        return pw // (1 << (state["dwt_depth_ho"] + state["dwt_depth"]))
    elif level <= state["dwt_depth_ho"]:
        return pw // (1 << (state["dwt_depth_ho"] + state["dwt_depth"] - level + 1))
    elif level > state["dwt_depth_ho"]:
        return pw // (1 << (state["dwt_depth_ho"] + state["dwt_depth"] - level + 1))

def subband_height(state, level, comp):
    """(13.2.3)"""
    if comp == "Y":
        h = state["luma_height"]
    elif comp == "C1" or comp == "C2":
        h = state["color_diff_height"]
    
    # Round up (pad) the picture height to the nearest multiple of the scale
    # height
    scale_h = 1 << state["dwt_depth"]
    ph = scale_h * ((h + scale_h - 1) // scale_h)
    
    if level == 0:
        return ph // (1 << state["dwt_depth"])
    elif level <= state["dwt_depth_ho"]:
        return ph // (1 << state["dwt_depth"])
    elif level > state["dwt_depth_ho"]:
        return ph // (1 << (state["dwt_depth_ho"] + state["dwt_depth"] - level + 1))


def slice_bytes(state, sx, sy):
    """(13.5.3.2) Compute the number of bytes in a low-delay picture slice."""
    slice_number = (sy * state["slices_x"]) + sx
    bytes = (((slice_number + 1) * state["slice_bytes_numerator"]) //
             state["slice_bytes_denominator"])
    bytes -= ((slice_number * state["slice_bytes_numerator"]) //
              state["slice_bytes_denominator"])
    return bytes

def slice_left(state, sx, c, level):
    """(13.5.6.2) Get the x coordinate of the LHS of the given slice."""
    return (subband_width(state, level, c) * sx) // state["slices_x"]

def slice_right(state, sx, c, level):
    """(13.5.6.2) Get the x coordinate of the RHS of the given slice."""
    return (subband_width(state, level, c) * (sx + 1)) // state["slices_x"]

def slice_top(state, sy, c, level):
    """(13.5.6.2) Get the y coordinate of the top of the given slice."""
    return (subband_height(state, level, c) * sy) // state["slices_y"]

def slice_bottom(state, sy, c, level):
    """(13.5.6.2) Get the y coordinate of the bottom of the given slice."""
    return (subband_height(state, level, c) * (sy + 1)) // state["slices_y"]