import pytest

from bitarray import bitarray

from decoder_test_utils import serialise_to_bytes, bytes_to_state

from vc2_conformance.vc2_math import intlog2

from vc2_conformance import bitstream
from vc2_conformance import tables
from vc2_conformance import decoder

# State dictionary with a minimal set of pre-populated values for the unpacking
# of a single-sample, single pixel picture.
single_sample_transform_base_state = {
    "slices_x": 1,
    "slices_y": 1,
    "luma_width": 1,
    "luma_height": 1,
    "color_diff_width": 1,
    "color_diff_height": 1,
    "dwt_depth": 0,
    "dwt_depth_ho": 0,
    "quant_matrix": {0: {"LL": 0}},
    "y_transform": {0: {"LL": [[None]]}},
    "c1_transform": {0: {"LL": [[None]]}},
    "c2_transform": {0: {"LL": [[None]]}},
}


class TestLDSlice(object):
    
    @pytest.mark.parametrize("slice_y_length,exp_fail", [
        # In range
        (0, False),
        (40, False),
        (80 - 7 - intlog2(80 - 7), False),
        # Too long
        (80 - 7 - intlog2(80 - 7) + 1, True),
        (127, True),
    ])
    def test_slice_y_length_must_be_valid(self, slice_y_length, exp_fail):
        slice_bits = 8 * 10
        length_bits = intlog2(slice_bits-7)
        max_y_block_length = slice_bits - 7  - length_bits
        
        state = single_sample_transform_base_state.copy()
        state.update({
            "slice_bytes_numerator": 10,
            "slice_bytes_denominator": 1,
        })
        ld_slice_bytes = serialise_to_bytes(
            bitstream.LDSlice(slice_y_length=slice_y_length),
            state, 0, 0,
        )
        state.update(bytes_to_state(ld_slice_bytes))
        
        if exp_fail:
            with pytest.raises(decoder.InvalidSliceYLength) as exc_info:
                decoder.ld_slice(state, 0, 0)
            assert exc_info.value.slice_y_length == slice_y_length
            assert exc_info.value.max_slice_y_length == max_y_block_length
        else:
            decoder.ld_slice(state, 0, 0)
    
    def test_qindex_constrained_by_level(self):
        state = single_sample_transform_base_state.copy()
        state.update({
            "slice_bytes_numerator": 1,
            "slice_bytes_denominator": 1,
        })
        state.update(bytes_to_state(serialise_to_bytes(
            bitstream.LDSlice(
                qindex=0,
            ),
            state, 0, 0,
        )))
        
        decoder.ld_slice(state, 0, 0)
        
        # Just check that assert_level_constraint has added the index to the
        # dictionary.
        assert state["_level_constrained_values"]["qindex"] == 0


class TestHQSlice(object):

    def test_total_slice_bytes_constraint(self):
        state = single_sample_transform_base_state.copy()
        state.update({
            "slice_prefix_bytes": 10,
            "slice_size_scaler": 20,
        })
        hq_slice_bytes = serialise_to_bytes(
            bitstream.HQSlice(
                slice_y_length=1,
                slice_c1_length=2,
                slice_c2_length=3,
            ),
            state, 0, 0,
        )
        state.update(bytes_to_state(hq_slice_bytes))
        
        decoder.hq_slice(state, 0, 0)
        
        assert state["_level_constrained_values"]["total_slice_bytes"] == len(hq_slice_bytes)
    
    def test_qindex_constrained_by_level(self):
        state = single_sample_transform_base_state.copy()
        state.update({
            "slice_prefix_bytes": 0,
            "slice_size_scaler": 1,
        })
        hq_slice_bytes = serialise_to_bytes(
            bitstream.HQSlice(qindex=0),
            state, 0, 0,
        )
        state.update(bytes_to_state(hq_slice_bytes))
        
        decoder.hq_slice(state, 0, 0)
        
        # Just check that assert_level_constraint has added the index to the
        # dictionary.
        assert state["_level_constrained_values"]["qindex"] == 0
