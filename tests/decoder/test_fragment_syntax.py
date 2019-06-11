import pytest

from decoder_test_utils import serialise_to_bytes, bytes_to_state

from vc2_conformance import bitstream
from vc2_conformance import tables
from vc2_conformance import decoder


class TestFragmentHeader(object):
    
    @pytest.mark.parametrize("fragment_slice_count,fragment_slices_remaining,exp_fail", [
        # Fragment 0 with no outstanding slices
        (0, 0, False),
        # Fragment 0 with some outstanding slices
        (0, 1, True),
    ])
    def test_first_fragment_must_have_slice_count_zero(
        self, fragment_slice_count, fragment_slices_remaining, exp_fail,
    ):
        state = bytes_to_state(serialise_to_bytes(bitstream.FragmentHeader(
            fragment_slice_count=fragment_slice_count,
        )))
        state["_picture_initial_fragment_offset"] = (-1, 7)
        state["fragment_slices_received"] = 0
        state["_fragment_slices_remaining"] = fragment_slices_remaining
        
        # Required only when not failing
        state["_num_pictures_in_sequence"] = 0
        state["_picture_coding_mode"] = tables.PictureCodingModes.pictures_are_frames
        
        if exp_fail:
            with pytest.raises(decoder.FragmentedPictureRestarted) as exc_info:
                decoder.fragment_header(state)
            assert exc_info.value.initial_fragment_offset == (-1, 7)
            assert exc_info.value.this_fragment_offset == (0, 7)
            assert exc_info.value.fragment_slices_received == 0
            assert exc_info.value.fragment_slices_remaining == fragment_slices_remaining
        else:
            decoder.fragment_header(state)
    
    def test_picture_numbering_sanity_check(self):
        # Only a sanity check as assert_picture_number_incremented_as_expected
        # (which performs these checks) is tested fully elsewhere
        fh1 = serialise_to_bytes(bitstream.FragmentHeader(picture_number=1000))
        fh2 = serialise_to_bytes(bitstream.FragmentHeader(picture_number=1001))
        fh3 = serialise_to_bytes(bitstream.FragmentHeader(picture_number=1003))
        
        state = bytes_to_state(fh1 + fh2 + fh3)
        state["_picture_coding_mode"] = tables.PictureCodingModes.pictures_are_frames
        state["_num_pictures_in_sequence"] = 0
        state["_fragment_slices_remaining"] = 0
        
        decoder.fragment_header(state)
        decoder.fragment_header(state)
        with pytest.raises(decoder.NonConsecutivePictureNumbers) as exc_info:
            decoder.fragment_header(state)
        assert exc_info.value.last_picture_number_offset == (len(fh1) + 4, 7)
        assert exc_info.value.picture_number_offset == (len(fh1) + len(fh2) + 4, 7)
        assert exc_info.value.last_picture_number == 1001
        assert exc_info.value.picture_number == 1003
    
    def test_picture_not_allowed_to_change_between_fragments(self):
        fh1 = serialise_to_bytes(bitstream.FragmentHeader(
            fragment_slice_count=1,
            picture_number=1000,
        ))
        fh2 = serialise_to_bytes(bitstream.FragmentHeader(
            fragment_slice_count=1,
            picture_number=1001,
        ))
        
        state = bytes_to_state(fh1 + fh2)
        state["_last_picture_number"] = 1000
        state["_last_picture_number_offset"] = (-1, 4)
        state["_picture_initial_fragment_offset"] = (-1, 0)
        state["_picture_coding_mode"] = tables.PictureCodingModes.pictures_are_frames
        state["_num_pictures_in_sequence"] = 0
        state["_fragment_slices_remaining"] = 1
        state["fragment_slices_received"] = 0
        state["slices_x"] = 1
        state["slices_y"] = 1
        
        decoder.fragment_header(state)
        with pytest.raises(decoder.PictureNumberChangedMidFragmentedPicture) as exc_info:
            decoder.fragment_header(state)
        assert exc_info.value.last_picture_number_offset == (-1, 4)
        assert exc_info.value.picture_number_offset == (len(fh1) + 4, 7)
        assert exc_info.value.last_picture_number == 1000
        assert exc_info.value.picture_number == 1001
    
    @pytest.mark.parametrize("fragment_slice_count,fragment_slices_remaining,exp_fail", [
        # Exactly the right number remaining
        (1, 1, False),
        (100, 100, False),
        # More than enough remaining
        (1, 100, False),
        (99, 100, False),
        # No slices remaining
        (1, 0, True),
        (100, 0, True),
        # Not enough slices remaining
        (6, 5, True),
        (100, 5, True),
    ])
    def test_must_not_have_too_many_slices(
        self, fragment_slice_count, fragment_slices_remaining, exp_fail,
    ):
        state = bytes_to_state(serialise_to_bytes(bitstream.FragmentHeader(
            fragment_slice_count=fragment_slice_count,
            picture_number=0,
        )))
        state["_picture_initial_fragment_offset"] = (-1, 7)
        state["_fragment_slices_remaining"] = fragment_slices_remaining
        state["fragment_slices_received"] = 0
        state["_last_picture_number"] = 0
        
        # Only required in non-failing cases
        state["slices_x"] = 1
        state["slices_y"] = 1
        
        if exp_fail:
            with pytest.raises(decoder.TooManySlicesInFragmentedPicture) as exc_info:
                decoder.fragment_header(state)
            assert exc_info.value.initial_fragment_offset == (-1, 7)
            assert exc_info.value.this_fragment_offset == (0, 7)
            assert exc_info.value.fragment_slices_received == 0
            assert exc_info.value.fragment_slices_remaining == fragment_slices_remaining
            assert exc_info.value.fragment_slice_count == fragment_slice_count
        else:
            decoder.fragment_header(state)
    
    @pytest.mark.parametrize("fragment_x_offset,fragment_y_offset,expected_fragment_x_offset,expected_fragment_y_offset,exp_fail", [
        # Match expectations
        (0, 0, 0, 0, False),
        (4, 5, 4, 5, False),
        # After expected
        (1, 0, 0, 0, True),
        (0, 1, 0, 0, True),
        (1, 1, 0, 0, True),
        # Before expected
        (4, 5, 5, 5, True),
        (5, 4, 5, 5, True),
        (4, 4, 5, 5, True),
    ])
    def test_must_have_contiguous_slices(
        self,
        fragment_x_offset, fragment_y_offset,
        expected_fragment_x_offset, expected_fragment_y_offset,
        exp_fail,
    ):
        state = bytes_to_state(serialise_to_bytes(bitstream.FragmentHeader(
            picture_number=0,
            fragment_slice_count=1,
            fragment_x_offset=fragment_x_offset,
            fragment_y_offset=fragment_y_offset,
        )))
        state["_picture_initial_fragment_offset"] = (-1, 7)
        state["_fragment_slices_remaining"] = 1
        state["fragment_slices_received"] = (
            expected_fragment_y_offset*10 +
            expected_fragment_x_offset
        )
        state["_last_picture_number"] = 0
        state["slices_x"] = 10
        state["slices_y"] = 10
        
        if exp_fail:
            with pytest.raises(decoder.FragmentSlicesNotContiguous) as exc_info:
                decoder.fragment_header(state)
            assert exc_info.value.initial_fragment_offset == (-1, 7)
            assert exc_info.value.this_fragment_offset == (0, 7)
            assert exc_info.value.fragment_x_offset == fragment_x_offset
            assert exc_info.value.fragment_y_offset == fragment_y_offset
            assert exc_info.value.expected_fragment_x_offset == expected_fragment_x_offset
            assert exc_info.value.expected_fragment_y_offset == expected_fragment_y_offset
        else:
            decoder.fragment_header(state)


@pytest.mark.xfail
def test_todo_whole_picture():
    # TODO: Test decoding of whole pictures worth of fragment bitstreams
    # including testing _fragment_slices_remaining
    assert False