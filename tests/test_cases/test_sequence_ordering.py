import pytest

from vc2_data_tables import ParseCodes

from vc2_conformance.test_cases.sequence_ordering import (
    find_minimal_sequence,
    ImpossibleSequenceError,
)


def test_empty_no_patterns():
    assert find_minimal_sequence([]) == []

def test_arbitrary_no_patterns():
    # When no patterns are supplied, any sequence should match
    assert find_minimal_sequence([
        ParseCodes.end_of_sequence,
        ParseCodes.sequence_header,
    ]) == [
        ParseCodes.end_of_sequence,
        ParseCodes.sequence_header,
    ]

@pytest.mark.parametrize("patterns", [
    # Single patterns which would allow an empty sequence
    [""],
    [".*"],
    ["$"],
    [".*$"],
    # Multiple patterns at once which would allow an empty sequence
    ["", ".*", "$", ".*$"],
])
def test_patterns_allow_empty_sequence(patterns):
    assert find_minimal_sequence([], *patterns) == []

@pytest.mark.parametrize("patterns", [
    ["sequence_header high_quality_picture end_of_sequence$"],
    ["...$"],
    [".*"],
    [
        "sequence_header . . $",
        ". high_quality_picture . $",
        ". . end_of_sequence $",
    ],
])
def test_fully_matched_pattern(patterns):
    # Patterns which match the test sequence exactly
    assert find_minimal_sequence([
        ParseCodes.sequence_header,
        ParseCodes.high_quality_picture,
        ParseCodes.end_of_sequence,
    ], *patterns) == [
        ParseCodes.sequence_header,
        ParseCodes.high_quality_picture,
        ParseCodes.end_of_sequence,
    ]


@pytest.mark.parametrize("patterns", [
    # Only one option
    ["sequence_header end_of_sequence$"],
    # Two options, one shorter
    ["sequence_header sequence_header? end_of_sequence$"],
    # All patterns together enforce the solution
    [
        "sequence_header .*",
        ".* end_of_sequence",
        ". .",
    ],
    # Wildcard options first
    [
        ". .",
        ".* end_of_sequence",
        "sequence_header .*",
    ],
])
def test_find_shortest_possible_filler_values(patterns):
    assert find_minimal_sequence([], *patterns) == [
        ParseCodes.sequence_header,
        ParseCodes.end_of_sequence,
    ]


def test_mixture_of_matched_and_fillled_in_values():
    assert find_minimal_sequence([
        ParseCodes.padding_data,
    ], "sequence_header .* end_of_sequence") == [
        ParseCodes.sequence_header,
        ParseCodes.padding_data,
        ParseCodes.end_of_sequence,
    ]


@pytest.mark.parametrize("data_units,patterns,works", [
    # When no requirements given, should work up to (but not past) the depth limit
    ([], ["sequence_header sequence_header end_of_sequence"], True),
    ([], ["sequence_header sequence_header sequence_header end_of_sequence"], False),
    # Depth limit should reset when a data unit is matched
    (
        [ParseCodes.padding_data],
        [
            (
                "sequence_header sequence_header sequence_header "
                "padding_data "
                "sequence_header sequence_header end_of_sequence"
            ),
        ],
        True,
    ),
    (
        [ParseCodes.padding_data],
        [
            (
                "sequence_header sequence_header sequence_header sequence_header "
                "padding_data "
                "sequence_header sequence_header end_of_sequence"
            ),
        ],
        False,
    ),
    # Depth limit should be reset even when wildcard matching is included
    (
        [ParseCodes.padding_data],
        [
            (
                "sequence_header sequence_header sequence_header "
                "padding_data "
                "sequence_header sequence_header end_of_sequence"
            ),
            ".*"
        ],
        True,
    ),
    (
        [ParseCodes.padding_data],
        [
            (
                "sequence_header sequence_header sequence_header sequence_header "
                "padding_data "
                "sequence_header sequence_header end_of_sequence"
            ),
            ".*",
        ],
        False,
    ),
])
def test_search_depth_limit(data_units, patterns, works):
    if works:
        find_minimal_sequence(data_units, *patterns, depth_limit=3)
    else:
        with pytest.raises(ImpossibleSequenceError):
            find_minimal_sequence(data_units, *patterns, depth_limit=3)


@pytest.mark.parametrize("patterns", [
    # Pattern shorter than sequence
    ["end_of_sequence"],
    # Pattern does not match sequence
    ["sequence_header low_delay_picture low_delay_picture end_of_sequence"],
    # One pattern doesn't match sequence
    [".*", "end_of_sequence"],
])
def test_sequence_not_allowed_by_patterns(patterns):
    with pytest.raises(ImpossibleSequenceError):
        find_minimal_sequence([
            ParseCodes.sequence_header,
            ParseCodes.high_quality_picture,
            ParseCodes.high_quality_picture,
            ParseCodes.end_of_sequence,
        ], *patterns, depth_limit=3)
