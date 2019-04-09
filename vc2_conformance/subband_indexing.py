"""
Utility functions for converting between subband index specifications (e.g.
level 3, subband HL) and flat integer subband indices.

The VC-2 specification (and bitstream format) specify a particular convention
for ordering subbands which can be seen in:

* (12.4.5.3) ``quant_matrix()``
* (13.5.3.1) ``ld_slice()``
* (13.5.4) ``hq_slice()``
* (13.5.5) ``slice_quantizers()``

The array order is defined as being:

1. DC/L/LL subband
2. 'H' Horizontal-only subbands bands
3. 'HL', 'LH' and 'HH' bands (in that order).

The name of the DC component is "DC" when no transforms are used, "LL" when
only a 2D transform is used and "L" when a horizontal-only transform is used.
"""

__all__ = [
    "index_to_subband",
    "subband_to_index",
]


def index_to_subband(index, dwt_depth=0, dwt_depth_ho=0):
    """
    Convert from an index into a corresponding (level, subband) tuple where
    level is an int and subband is one of "DC", "L", "LL", "H", "HL", "LH" and
    "HH".
    """
    if index == 0:
        level = 0
        if dwt_depth == 0 and dwt_depth_ho == 0:
            subband = "DC"
        elif dwt_depth_ho != 0:
            subband = "L"
        else:
            subband = "LL"
    elif index < dwt_depth_ho + 1:
        level = index
        subband = "H"
    else:
        offset_index = (index - dwt_depth_ho - 1)
        level = 1 + dwt_depth_ho + (offset_index // 3)
        subband = {
            0: "HL",
            1: "LH",
            2: "HH",
        }[offset_index % 3]
    
    if level > dwt_depth + dwt_depth_ho:
        raise ValueError(level)
    
    return (level, subband)


def subband_to_index(level, subband, dwt_depth=0, dwt_depth_ho=0):
    """
    Static method. Convert from level and subband into a flat (integer) index.
    """
    if level == 0:
        if dwt_depth_ho == 0 and dwt_depth == 0:
            if subband != "DC":
                raise ValueError((level, subband))
        elif dwt_depth_ho > 0:
            if subband != "L":
                raise ValueError((level, subband))
        elif dwt_depth > 0:
            if subband != "LL":
                raise ValueError((level, subband))
        return 0
    elif level < 1 + dwt_depth_ho:
        if subband != "H":
            raise ValueError((level, subband))
        return level
    elif level < 1 + dwt_depth_ho + dwt_depth:
        if subband not in ("HL", "LH", "HH"):
            raise ValueError((level, subband))
        return (
            1 +
            dwt_depth_ho +
            ((level - dwt_depth_ho - 1) * 3)
        ) + {
            "HL": 0,
            "LH": 1,
            "HH": 2,
        }[subband]
    else:
        raise ValueError((level, subband))
