import pytest

from vc2_conformance.tables import ParseCodes

from vc2_conformance._symbol_re import Matcher

from vc2_conformance.decoder.assertions import (
    assert_in_enum,
    assert_parse_code_in_sequence,
    assert_parse_code_sequence_ended,
)

def test_assert_in_enum():
    class CustomException(Exception):
        pass
    
    assert_in_enum(0x10, ParseCodes, CustomException)
    assert_in_enum(ParseCodes.end_of_sequence, ParseCodes, CustomException)
    
    with pytest.raises(CustomException) as exc_info:
        assert_in_enum(-1, ParseCodes, CustomException)
    assert exc_info.type is CustomException
    assert exc_info.value.args == (-1, )


@pytest.mark.parametrize("regex,expected_parse_codes,expected_end", [
    # Only one possibility allowed
    (
        "sequence_header",
        set([ParseCodes.sequence_header]),
        False,
    ),
    # Several possibilities allowed
    (
        "sequence_header | padding_data",
        set([ParseCodes.sequence_header, ParseCodes.padding_data]),
        False,
    ),
    # End-of-file allowed
    (
        "$",
        set([]),
        True,
    ),
])
def test_parse_code_in_sequence(regex, expected_parse_codes, expected_end):
    m = Matcher(regex)
    
    class CustomException(Exception):
        def __init__(self, parse_code, actual_expected_parse_codes, actual_expected_end):
            assert parse_code is ParseCodes.auxiliary_data
            assert set(actual_expected_parse_codes) == expected_parse_codes
            assert actual_expected_end == expected_end
    
    with pytest.raises(CustomException):
        assert_parse_code_in_sequence(ParseCodes.auxiliary_data, m, CustomException)

@pytest.mark.parametrize("regex,expected_parse_codes", [
    # Only one possibility allowed
    (
        "sequence_header",
        set([ParseCodes.sequence_header]),
    ),
    # Several possibilities allowed
    (
        "sequence_header | padding_data",
        set([ParseCodes.sequence_header, ParseCodes.padding_data]),
    ),
    # All possibilities allowed
    (
        "sequence_header | padding_data | .",
        None,
    ),
])
def test_parse_code_sequence_ended(regex, expected_parse_codes):
    m = Matcher(regex)
    
    class CustomException(Exception):
        def __init__(self, parse_code, actual_expected_parse_codes, actual_expected_end):
            assert parse_code is None
            if expected_parse_codes is None:
                assert actual_expected_parse_codes is None
            else:
                assert set(actual_expected_parse_codes) == expected_parse_codes
            assert actual_expected_end is False
    
    with pytest.raises(CustomException):
        assert_parse_code_sequence_ended(m, CustomException)
