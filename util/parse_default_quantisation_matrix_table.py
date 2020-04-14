"""
Dirty script which turns quantisation matrix tables in Annex D of the VC-2 spec
into python-style dictionaries.

Select and copy the table using Okulars table-selection mode and pass as input
to this script.

Sample text input::

    state[dwt_depth_ho]=0
    state[wavelet_depth]
    Level  Orientation  0  1  2  3  4
    0  LL  0  5  5  5  5
    1  HL, LH , HH  -  3, 3, 0  3, 3, 0  3, 3, 0  3, 3, 0
    2  HL, LH, HH  -  -  4, 4, 1  4, 4, 1  4, 4 ,1
    3  HL, LH, HH  -  -  -  5, 5 ,2  5, 5, 2
    4  HL, LH, HH  -  -  -  -  6, 6, 3
    state[dwt_depth_ho]=1
    state[wavelet_depth]
    Level  Orientation  0  1  2  3  4
    0  L  3  3  3  3  3
    1  H  0  0  0  0  0
    2  HL, LH, HH  -  3, 3, 0  3, 3, 0  3, 3, 0  3, 3, 0
    3  HL, LH, HH  -  -  4, 4, 1  4, 4, 1  4, 4, 1
    4  HL, LH, HH  -  -  -  5, 5, 2  5, 5, 2
    5  HL, LH, HH  -  -  -  -  6, 6, 3
    state[dwt_depth_ho]=2
    state[wavelet_depth]
    Level  Orientation  0  1  2  3  4
    0  L  3  3  3  3  -
    1  H  0  0  0  0  -
    2  H  3  3  3  3  -
    3  HL, LH, HH  -  5, 5, 3  5, 5, 3  5, 5, 3  -
    4  HL, LH, HH  -  -  6, 6, 4  6, 6, 4  -
    5  HL, LH, HH  -  -  -  7, 7, 5  -
    state[dwt_depth_ho]=3
    state[wavelet_depth]
    Level  Orientation  0  1  2  3  4
    0  L  3  3  3  -  -
    1  H  0  0  0  -  -
    2  H  3  3  3  -  -
    3  H  5  5  5  -  -
    4  HL, LH, HH  -  8, 8, 5  8, 8, 5  -  -
    5  HL, LH, HH  -  -  9, 9, 6  -  -
    state[dwt_depth_ho]=4
    state[wavelet_depth]
    Level  Orientation  0  1  2  3  4
    0  L  3  3  -  -  -
    1  H  0  0  -  -  -
    2  H  3  3  -  -  -
    3  H  5  5  -  -  -
    4  H  8  8  -  -  -
    5  HL, LH, HH  -  10, 10, 8  -  -  -
"""

import sys
import re

from collections import defaultdict


# {(dwt_depth_ho, dwt_depth): {level: {band: value, ...}, ...}, ...}
out = defaultdict(lambda: defaultdict(dict))


# Parse the table
dwt_depth_ho = None
for line in sys.stdin:
    cols = line.split("  ")

    # Parse dwt_depth_ho headers
    match = re.match(r"^state\[dwt_depth_ho\]=(\d+)\s*$", cols[0])
    if match:
        dwt_depth_ho = int(match.group(1))

    # Parse main rows of table
    match = re.match(r"^(\d)+\s*$", cols[0])
    if match:
        level = int(cols[0])
        subbands = re.split(r"\s*,\s*", cols[1])

        for dwt_depth, values_string in enumerate(cols[2:]):
            if "-" in values_string:
                continue

            values = list(map(int, re.split(r"\s*,\s*", values_string)))
            for subband, value in zip(subbands, values):
                out[(dwt_depth_ho, dwt_depth)][level][subband] = value


def subband_key(b):
    return ["L", "H", "LL", "HL", "LH", "HH"].index(b)


# Generate output
for (dwt_depth_ho, dwt_depth), quant_matrix in sorted(out.items()):
    print("    ({}, {}): {{".format(dwt_depth_ho, dwt_depth))

    for level, subbands in sorted(quant_matrix.items()):
        print(
            "        {}: {{{}}},".format(
                level,
                ", ".join(
                    "{}: {}".format(subband, value)
                    for subband, value in sorted(
                        subbands.items(), key=lambda sv: subband_key(sv[0])
                    )
                ),
            )
        )

    print("    },")
