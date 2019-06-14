import pytest

from vc2_conformance.tables import ParseCodes, PictureCodingModes

from vc2_conformance.state import State

from vc2_conformance._symbol_re import Matcher

from vc2_conformance._constraint_table import ValueSet

from vc2_conformance.decoder.exceptions import (
    ValueNotAllowedInLevel,
    NonConsecutivePictureNumbers,
    EarliestFieldHasOddPictureNumber,
)

from vc2_conformance.decoder.assertions import (
    assert_in,
    assert_in_enum,
    assert_parse_code_in_sequence,
    assert_parse_code_sequence_ended,
    assert_level_constraint,
    assert_picture_number_incremented_as_expected,
)


def test_assert_in():
    class CustomException(Exception):
        pass
    
    lst = [1, 2, 3]
    
    assert_in(1, lst, CustomException, "bar")
    assert_in(2, lst, CustomException, "bar")
    assert_in(3, lst, CustomException, "bar")
    
    with pytest.raises(CustomException) as exc_info:
        assert_in(0, lst, CustomException, "bar")
    assert exc_info.value.args == (0, lst, "bar")

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
        def __init__(self, parse_code, actual_expected_parse_codes, actual_expected_end, foo):
            assert parse_code is ParseCodes.auxiliary_data
            assert set(actual_expected_parse_codes) == expected_parse_codes
            assert actual_expected_end == expected_end
            assert foo == "bar"
    
    with pytest.raises(CustomException):
        assert_parse_code_in_sequence(ParseCodes.auxiliary_data, m, CustomException, "bar")

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
        def __init__(self, parse_code, actual_expected_parse_codes, actual_expected_end, foo):
            assert parse_code is None
            if expected_parse_codes is None:
                assert actual_expected_parse_codes is None
            else:
                assert set(actual_expected_parse_codes) == expected_parse_codes
            assert actual_expected_end is False
            assert foo == "bar"
    
    with pytest.raises(CustomException):
        assert_parse_code_sequence_ended(m, CustomException, "bar")

def test_level_constraints():
    state = State()
    
    # Should be allowed
    assert_level_constraint(state, "level", 1)
    assert state["_level_constrained_values"] == {"level": 1}
    
    # Should not be allowed
    with pytest.raises(ValueNotAllowedInLevel) as exc_info:
        assert_level_constraint(state, "base_video_format", 0)
    
    assert exc_info.value.level_constrained_values == {"level": 1}
    assert exc_info.value.key == "base_video_format"
    assert exc_info.value.value == 0
    assert exc_info.value.allowed_values == ValueSet(1, 2, 3, 4, 5, 6)


class TestPictureNumberIncrementedAsExpected(object):
    
    def test_picture_numbers_must_be_consecutive(self):
        state = {
            "_picture_coding_mode": PictureCodingModes.pictures_are_frames,
            "_num_pictures_in_sequence": 0,
        }
        
        state["picture_number"] = 1000
        assert_picture_number_incremented_as_expected(state, (1, 7))
        
        state["picture_number"] = 1001
        assert_picture_number_incremented_as_expected(state, (2, 7))
        
        state["picture_number"] = 1003
        with pytest.raises(NonConsecutivePictureNumbers) as exc_info:
            assert_picture_number_incremented_as_expected(state, (3, 7))
        
        assert exc_info.value.last_picture_number_offset == (2, 7)
        assert exc_info.value.picture_number_offset == (3, 7)
        assert exc_info.value.last_picture_number == 1001
        assert exc_info.value.picture_number == 1003
    
    def test_picture_numbers_wrap_around_correctly(self):
        state = {
            "_picture_coding_mode": PictureCodingModes.pictures_are_frames,
            "_num_pictures_in_sequence": 0,
        }
        
        state["picture_number"] = (2**32) - 1
        assert_picture_number_incremented_as_expected(state, (1, 7))
        
        state["picture_number"] = 0
        assert_picture_number_incremented_as_expected(state, (2, 7))

    def test_picture_numbers_dont_wrap_around_correctly(self):
        state = {
            "_picture_coding_mode": PictureCodingModes.pictures_are_frames,
            "_num_pictures_in_sequence": 0,
        }
        
        state["picture_number"] = (2**32) - 1
        assert_picture_number_incremented_as_expected(state, (1, 7))
        
        state["picture_number"] = 1
        with pytest.raises(NonConsecutivePictureNumbers) as exc_info:
            assert_picture_number_incremented_as_expected(state, (2, 7))
        assert exc_info.value.last_picture_number_offset == (1, 7)
        assert exc_info.value.picture_number_offset == (2, 7)
        assert exc_info.value.last_picture_number == (2**32)-1
        assert exc_info.value.picture_number == 1
    
    @pytest.mark.parametrize("picture_coding_mode,picture_number,exp_fail", [
        (PictureCodingModes.pictures_are_frames, 0, False),
        (PictureCodingModes.pictures_are_frames, 1, False),
        (PictureCodingModes.pictures_are_frames, 2, False),
        (PictureCodingModes.pictures_are_frames, 3, False),
        (PictureCodingModes.pictures_are_frames, 4, False),
        (PictureCodingModes.pictures_are_fields, 0, False),
        (PictureCodingModes.pictures_are_fields, 1, True),
        (PictureCodingModes.pictures_are_fields, 2, False),
        (PictureCodingModes.pictures_are_fields, 3, True),
        (PictureCodingModes.pictures_are_fields, 4, False),
    ])
    def test_early_fields_must_have_even_numbers(self, picture_coding_mode, picture_number, exp_fail):
        state = {
            "_picture_coding_mode": picture_coding_mode,
            "_num_pictures_in_sequence": 100,
            "picture_number": picture_number,
        }
        
        if exp_fail:
            with pytest.raises(EarliestFieldHasOddPictureNumber) as exc_info:
                assert_picture_number_incremented_as_expected(state, (1, 7))
            assert exc_info.value.picture_number == picture_number
        else:
            assert_picture_number_incremented_as_expected(state, (1, 7))
            
            # Also check that the pictures in sequence count is incremented
            assert state["_num_pictures_in_sequence"] == 101
