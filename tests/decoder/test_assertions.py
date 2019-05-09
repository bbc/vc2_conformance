import pytest

from vc2_conformance.tables import ParseCodes

from vc2_conformance.decoder.assertions import (
    assert_in_enum,
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
