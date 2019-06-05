import pytest

from decoder_test_utils import seriallise_to_bytes, bytes_to_state

from vc2_conformance import bitstream
from vc2_conformance import tables
from vc2_conformance import decoder


def picture_header_to_bytes(**kwargs):
    """
    Seriallise a PictureHeader block, returning a bytes object.
    """
    return seriallise_to_bytes(
        bitstream.PictureHeader(**kwargs),
        bitstream.picture_header,
    )

class TestPictureHeader(object):

    def test_picture_numbers_must_be_consecutive(self):
        ph1 = picture_header_to_bytes(picture_number=1000)
        ph2 = picture_header_to_bytes(picture_number=1001)
        ph3 = picture_header_to_bytes(picture_number=1003)
        
        state = bytes_to_state(ph1 + ph2 + ph3)
        state["_picture_coding_mode"] = tables.PictureCodingModes.pictures_are_frames
        state["_num_pictures_in_sequence"] = 0
        
        decoder.picture_header(state)
        decoder.picture_header(state)
        with pytest.raises(decoder.NonConsecutivePictureNumbers) as exc_info:
            decoder.picture_header(state)
        assert exc_info.value.last_picture_header_offset == (len(ph1), 7)
        assert exc_info.value.picture_header_offset == (len(ph1) + len(ph2), 7)
        assert exc_info.value.last_picture_number == 1001
        assert exc_info.value.picture_number == 1003
    
    def test_picture_numbers_wrap_around_correctly(self):
        ph1 = picture_header_to_bytes(picture_number=(2**32)-1)
        ph2 = picture_header_to_bytes(picture_number=0)
        state = bytes_to_state(ph1 + ph2)
        state["_picture_coding_mode"] = tables.PictureCodingModes.pictures_are_frames
        state["_num_pictures_in_sequence"] = 0
        
        decoder.picture_header(state)
        decoder.picture_header(state)

    def test_picture_numbers_dont_wrap_around_correctly(self):
        ph1 = picture_header_to_bytes(picture_number=(2**32)-1)
        ph2 = picture_header_to_bytes(picture_number=1)
        state = bytes_to_state(ph1 + ph2)
        state["_picture_coding_mode"] = tables.PictureCodingModes.pictures_are_frames
        state["_num_pictures_in_sequence"] = 0
        
        decoder.picture_header(state)
        with pytest.raises(decoder.NonConsecutivePictureNumbers) as exc_info:
            decoder.picture_header(state)
        assert exc_info.value.last_picture_header_offset == (0, 7)
        assert exc_info.value.picture_header_offset == (len(ph1), 7)
        assert exc_info.value.last_picture_number == (2**32)-1
        assert exc_info.value.picture_number == 1
    
    @pytest.mark.parametrize("picture_coding_mode,picture_number,exp_fail", [
        (tables.PictureCodingModes.pictures_are_frames, 0, False),
        (tables.PictureCodingModes.pictures_are_frames, 1, False),
        (tables.PictureCodingModes.pictures_are_frames, 2, False),
        (tables.PictureCodingModes.pictures_are_frames, 3, False),
        (tables.PictureCodingModes.pictures_are_frames, 4, False),
        (tables.PictureCodingModes.pictures_are_fields, 0, False),
        (tables.PictureCodingModes.pictures_are_fields, 1, True),
        (tables.PictureCodingModes.pictures_are_fields, 2, False),
        (tables.PictureCodingModes.pictures_are_fields, 3, True),
        (tables.PictureCodingModes.pictures_are_fields, 4, False),
    ])
    def test_early_fields_must_have_even_numbers(self, picture_coding_mode, picture_number, exp_fail):
        ph = picture_header_to_bytes(picture_number=picture_number)
        state = bytes_to_state(ph)
        state["_picture_coding_mode"] = picture_coding_mode
        state["_num_pictures_in_sequence"] = 100
        
        if exp_fail:
            with pytest.raises(decoder.EarliestFieldHasOddPictureNumber) as exc_info:
                decoder.picture_header(state)
            assert exc_info.value.picture_number == picture_number
        else:
            decoder.picture_header(state)
            
            # Also check that the pictures in sequence count is incremented
            assert state["_num_pictures_in_sequence"] == 101
