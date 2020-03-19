import pytest

from bitarray import bitarray

import os

import sys

from io import BytesIO

from fractions import Fraction

from collections import defaultdict

from vc2_data_tables import (
    Profiles,
    ParseCodes,
)

from vc2_conformance.state import State

from vc2_conformance.bitstream import (
    Serialiser,
    BitstreamWriter,
    HQSlice,
    LDSlice,
    hq_slice,
    ld_slice,
    autofill_and_serialise_sequence,
)

from vc2_conformance.picture_generators import (
    repeat_pictures,
    mid_gray,
)

from vc2_conformance.encoder import (
    make_sequence,
)

# Add test root directory to path for sample_codec_features test utility module
sys.path.append(os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
))

from sample_codec_features import MINIMAL_CODEC_FEATURES

from vc2_conformance.test_cases.decoder.pictures import (
    generate_filled_padding,
    fill_hq_slice_padding,
    fill_ld_slice_padding,
    iter_slices_in_sequence,
    slice_padding_data,
)


class TestGenerateFiledPadding(object):
    
    def test_empty(self):
        assert generate_filled_padding(0, b"\x00", 0) == bitarray()
        assert generate_filled_padding(0, b"\x00", 1) == bitarray()
    
    def test_partial_filler_copy(self):
        assert generate_filled_padding(12, b"\xAA\xFF") == bitarray(
            "10101010"
            "1111"
        )
    
    def test_full_filler_copy(self):
        assert generate_filled_padding(16, b"\xAA\xFF") == bitarray(
            "10101010"
            "11111111"
        )
    
    def test_multiple_filler_copies(self):
        assert generate_filled_padding(32, b"\xAA\xFF") == bitarray(
            "10101010"
            "11111111"
            "10101010"
            "11111111"
        )
    
    def test_multiple_partial_filler_copies(self):
        assert generate_filled_padding(40, b"\xAA\xFF") == bitarray(
            "10101010"
            "11111111"
            "10101010"
            "11111111"
            "10101010"
        )
        assert generate_filled_padding(44, b"\xAA\xFF") == bitarray(
            "10101010"
            "11111111"
            "10101010"
            "11111111"
            "10101010"
            "1111"
        )
    
    def test_byte_alignment_not_required(self):
        assert generate_filled_padding(32, b"\xAA\xFF", 8) == bitarray(
            "10101010"
            "11111111"
            "10101010"
            "11111111"
        )
    
    def test_byte_alignment_required(self):
        assert generate_filled_padding(32, b"\xAA\xFF", 14) == bitarray(
            # Byte align
            "00"
            # Filler
            "10101010"
            "11111111"
            "10101010"
            "111111"  # Truncated
        )


class TestFillHQSlicePadding(object):
    
    def sanity_check(self, slice_size_scaler, slice):
        """
        Checks that the provided slice serializes correctly.
        """
        slice.setdefault("prefix_bytes", bytes())
        slice.setdefault("y_block_padding", bitarray())
        slice.setdefault("c1_block_padding", bitarray())
        slice.setdefault("c2_block_padding", bitarray())
        
        f = BytesIO()
        with Serialiser(BitstreamWriter(f), slice) as ser:
            hq_slice(ser, State(
                slice_prefix_bytes=0,
                slice_size_scaler=slice_size_scaler,
                dwt_depth=0,
                dwt_depth_ho=0,
                luma_width=len(slice["y_transform"]),
                luma_height=1,
                color_diff_width=len(slice["c1_transform"]),
                color_diff_height=1,
                slices_x=1,
                slices_y=1,
            ), 0, 0)
    
    @pytest.mark.parametrize("slice_size_scaler", [1, 10])
    @pytest.mark.parametrize("transform_data", [
        ([], [], []),
        ([0, 0, 0, 0, 0, 0], [0, 0, 0], [0, 0, 0]),
        ([1, 2, 3, 4, 5, 6], [1, 2, 3], [4, 5, 6]),
    ])
    @pytest.mark.parametrize("component", ["Y", "C1", "C2"])
    @pytest.mark.parametrize("byte_align", [True, False])
    def test_zero_size_slice(self,
        slice_size_scaler,
        transform_data,
        byte_align,
        component,
    ):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=0,
            slice_c1_length=0,
            slice_c2_length=0,
            y_transform=transform_data[0],
            c1_transform=transform_data[1],
            c2_transform=transform_data[2],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=slice_size_scaler),
            0,
            0,
            hq_slice,
            component,
            b"\xAA\xBB",
            byte_align,
        )
        
        assert hq_slice["slice_y_length"] == 0
        assert hq_slice["slice_c1_length"] == 0
        assert hq_slice["slice_c2_length"] == 0
        
        if all(transform_data):
            assert hq_slice["y_transform"] == [0]*6
            assert hq_slice["c1_transform"] == [0]*3
            assert hq_slice["c2_transform"] == [0]*3
        else:
            assert hq_slice["y_transform"] == []
            assert hq_slice["c1_transform"] == []
            assert hq_slice["c2_transform"] == []
        
        assert hq_slice.get("y_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()
        
        self.sanity_check(slice_size_scaler, hq_slice)
    
    def test_clears_transform_coeffs(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[1, 2, 3, 4, 5, 6],
            c1_transform=[7, 8, 9],
            c2_transform=[0, 1, 2],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=1),
            0,
            0,
            hq_slice,
            "Y",
            b"\x00",
        )
        
        assert hq_slice["y_transform"] == [0, 0, 0, 0, 0, 0]
        assert hq_slice["c1_transform"] == [0, 0, 0]
        assert hq_slice["c2_transform"] == [0, 0, 0]
        
        self.sanity_check(1, hq_slice)
    
    @pytest.mark.parametrize("slice_size_scaler", [1, 10])
    @pytest.mark.parametrize("component", ["Y", "C1", "C2"])
    def test_sums_lengths(self, slice_size_scaler, component):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=slice_size_scaler),
            0,
            0,
            hq_slice,
            component,
            b"\x00",
        )
        
        if component == "Y":
            assert hq_slice["slice_y_length"] == 1 + 2 + 3
        else:
            assert hq_slice["slice_y_length"] == 0
        
        if component == "C1":
            assert hq_slice["slice_c1_length"] == 1 + 2 + 3
        else:
            assert hq_slice["slice_c1_length"] == 0
        
        if component == "C2":
            assert hq_slice["slice_c2_length"] == 1 + 2 + 3
        else:
            assert hq_slice["slice_c2_length"] == 0
        
        self.sanity_check(slice_size_scaler, hq_slice)
    
    def test_fill_unaligned(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=1),
            0,
            0,
            hq_slice,
            "Y",
            b"\x00\xFF\xAA",
        )
        
        assert hq_slice["y_block_padding"] == bitarray(
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two
            "00000000"
            "11111111"
            "10"  # Truncated
        )
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()
        
        self.sanity_check(1, hq_slice)
    
    def test_fill_aligned(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=1),
            0,
            0,
            hq_slice,
            "Y",
            b"\x00\xFF\xAA",
            True,
        )
        
        assert hq_slice["y_block_padding"] == bitarray(
            # Byte align
            "00"
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two
            "00000000"
            "11111111"
            # Trunacated!
        )
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()
        
        self.sanity_check(1, hq_slice)
    
    
    def test_fill_already_aligned(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0, 0],
            c2_transform=[0, 0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=1),
            0,
            0,
            hq_slice,
            "Y",
            b"\x00\xFF\xAA",
            True,
        )
        
        assert hq_slice["y_block_padding"] == bitarray(
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two
            "00000000"
            "11111111"
            # Trunacated!
        )
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()
        
        self.sanity_check(1, hq_slice)
    
    def test_slice_size_scaler(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=2),
            0,
            0,
            hq_slice,
            "Y",
            b"\x00\xFF\xAA",
            True,
        )
        
        assert hq_slice["y_block_padding"] == bitarray(
            # Byte align
            "00"
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two...
            "00000000"
            "11111111"
            "10101010"
            # Repeat three...
            "00000000"
            "11111111"
            "10101010"
            # Repeat four
            "00000000"
            "11111111"
            # Trunacated!
        )
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()
        
        self.sanity_check(2, hq_slice)
    
    def test_min_length(self):
        hq_slice = HQSlice(
            qindex=0,
            slice_y_length=1,
            slice_c1_length=2,
            slice_c2_length=3,
            y_transform=[0, 0, 0, 0, 0, 0],
            c1_transform=[0, 0, 0],
            c2_transform=[0, 0, 0],
        )
        fill_hq_slice_padding(
            State(slice_size_scaler=2),
            0,
            0,
            hq_slice,
            "Y",
            b"\x00\xFF\xAA",
            True,
            7,
        )
        
        assert hq_slice["slice_y_length"] == 7
        assert hq_slice["slice_c1_length"] == 0
        assert hq_slice["slice_c2_length"] == 0
        
        assert hq_slice["y_block_padding"] == bitarray(
            # Byte align
            "00"
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two...
            "00000000"
            "11111111"
            "10101010"
            # Repeat three...
            "00000000"
            "11111111"
            "10101010"
            # Repeat four...
            "00000000"
            "11111111"
            "10101010"
            # Repeat five
            "00000000"
            # Truncated
        )
        assert hq_slice.get("c1_block_padding", bitarray()) == bitarray()
        assert hq_slice.get("c2_block_padding", bitarray()) == bitarray()
        
        self.sanity_check(2, hq_slice)


class TestFillLDSlicePadding(object):
    
    def make_state(self):
        return State(
            slice_bytes_numerator=6,
            slice_bytes_denominator=1,
            slices_x=1,
            slices_y=1,
        )
    
    @pytest.fixture
    def state(self):
        return self.make_state()
    
    def sanity_check(self, slice):
        """
        Checks that the provided slice serializes correctly.
        """
        slice.setdefault("y_block_padding", bitarray())
        slice.setdefault("c_block_padding", bitarray())
        
        f = BytesIO()
        state = self.make_state()
        state.update(State(
            dwt_depth=0,
            dwt_depth_ho=0,
            luma_width=len(slice["y_transform"]),
            luma_height=1,
            color_diff_width=len(slice["c_transform"])//2,
            color_diff_height=1,
        ))
        with Serialiser(BitstreamWriter(f), slice) as ser:
            ld_slice(ser, state, 0, 0)
    
    def test_clears_transform_coeffs(self, state):
        ld_slice = LDSlice(
            qindex=0,
            slice_y_length=1,
            y_transform=[1, 2, 3, 4, 5, 6],
            c_transform=[7, 8, 9, 10],
        )
        fill_ld_slice_padding(
            state,
            0,
            0,
            ld_slice,
            "Y",
            b"\x00",
        )
        
        assert ld_slice["y_transform"] == [0, 0, 0, 0, 0, 0]
        assert ld_slice["c_transform"] == [0, 0, 0, 0]
        
        self.sanity_check(ld_slice)
    
    @pytest.mark.parametrize("component", ["Y", "C"])
    def test_sums_lengths(self, component, state):
        ld_slice = LDSlice(
            qindex=0,
            slice_y_length=1,
            y_transform=[0, 0, 0, 0, 0, 0],
            c_transform=[0, 0, 0, 0],
        )
        fill_ld_slice_padding(
            state,
            0,
            0,
            ld_slice,
            component,
            b"\x00",
        )
        
        if component == "Y":
            assert ld_slice["slice_y_length"] == (6 * 8) - 7 - 6
        else:
            assert ld_slice["slice_y_length"] == 0
        
        self.sanity_check(ld_slice)
    
    @pytest.mark.parametrize("component", ["Y", "C"])
    def test_fill_unaligned(self, state, component):
        ld_slice = LDSlice(
            qindex=0,
            slice_y_length=1,
            y_transform=[0, 0, 0, 0, 0, 0],
            c_transform=[0, 0, 0, 0],
        )
        fill_ld_slice_padding(
            state,
            0,
            0,
            ld_slice,
            component,
            b"\x00\xFF\xAA",
        )
        
        # 35 - 6 = 29 bits to fill
        expected = bitarray(
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two
            "00000"  # Truncated
        )
        if component == "Y":
            assert ld_slice["y_block_padding"] == expected
            assert ld_slice.get("c_block_padding", bitarray()) == bitarray()
        else:
            assert ld_slice.get("y_block_padding", bitarray()) == bitarray()
            # Extra bits of filler due to two fewer transform components
            assert ld_slice["c_block_padding"] == expected + bitarray("00")
        
        self.sanity_check(ld_slice)
    
    @pytest.mark.parametrize("component", ["Y", "C"])
    def test_fill_aligned(self, state, component):
        ld_slice = LDSlice(
            qindex=0,
            slice_y_length=1,
            y_transform=[0, 0, 0, 0, 0, 0],
            c_transform=[0, 0, 0, 0],
        )
        fill_ld_slice_padding(
            state,
            0,
            0,
            ld_slice,
            component,
            b"\x00\xFF\xAA",
            True,
        )
        
        # 7 + 6 = 13 bits of header so 3 bits required for byte alignment
        # 35 - 6 - 3 = 25 bits to fill
        expected = bitarray(
            # Byte alignment bits
            "000"
            # Repeat one...
            "00000000"
            "11111111"
            "10101010"
            # Repeat two
            "00"  # Truncated
        )
        if component == "Y":
            assert ld_slice["y_block_padding"] == expected
            assert ld_slice.get("c_block_padding", bitarray()) == bitarray()
        else:
            assert ld_slice.get("y_block_padding", bitarray()) == bitarray()
            # Extra bits of filler due to two fewer transform components
            assert ld_slice["c_block_padding"] == expected + bitarray("00")
        
        self.sanity_check(ld_slice)


@pytest.mark.parametrize("profile", Profiles)
@pytest.mark.parametrize("fragment_slice_count", [0, 3])
def test_iter_slices_in_sequence(profile, fragment_slice_count):
    codec_features = MINIMAL_CODEC_FEATURES.copy()
    codec_features["profile"] = profile
    codec_features["fragment_slice_count"] = fragment_slice_count
    codec_features["slices_x"] = 3
    codec_features["slices_y"] = 2
    
    num_pictures = 2
    
    sequence = make_sequence(
        codec_features,
        repeat_pictures(
            mid_gray(
                codec_features["video_parameters"],
                codec_features["picture_coding_mode"],
            ),
            num_pictures,
        )
    )
    
    slices = list(iter_slices_in_sequence(codec_features, sequence))
    
    # Should have found every slice
    assert len(slices) == (
        codec_features["slices_x"] *
        codec_features["slices_y"] * 
        num_pictures
    )
    
    # Should have correct states
    if profile == Profiles.high_quality:
        for state, _, _, _ in slices:
            assert state == State(
                slice_prefix_bytes=0,
                slice_size_scaler=1,
                slices_x=codec_features["slices_x"],
                slices_y=codec_features["slices_y"],
            )
    elif profile == Profiles.low_delay:
        slice_bytes = Fraction(
            codec_features["picture_bytes"], 
            codec_features["slices_x"] * codec_features["slices_y"]
        )
        for state, _, _, _ in slices:
            assert state == State(
                slice_bytes_numerator=slice_bytes.numerator,
                slice_bytes_denominator=slice_bytes.denominator,
                slices_x=codec_features["slices_x"],
                slices_y=codec_features["slices_y"],
            )
    
    # Should have correct coordinates
    it = iter(slices)
    for _ in range(num_pictures):
        for exp_sy in range(codec_features["slices_y"]):
            for exp_sx in range(codec_features["slices_x"]):
                _, sx, sy, _ = next(it)
                assert exp_sx == sx
                assert exp_sy == sy


@pytest.mark.parametrize("profile,lossless", [
    (Profiles.high_quality, False),
    (Profiles.high_quality, True),
    (Profiles.low_delay, False),
])
def test_slice_padding_data(profile, lossless):
    # Check that the expected padding data for each picture component makes it
    # into the stream
    
    codec_features = MINIMAL_CODEC_FEATURES.copy()
    codec_features["profile"] = profile
    codec_features["lossless"] = lossless
    if lossless:
        codec_features["picture_bytes"] = 0
    
    # The first 10 bytes of padding data for each component
    # {padding_field_name: set([bitarray, ...]), ...}
    component_padding_first_16_bits = defaultdict(set)
    
    # The number of times "BBCD" appears (byte aligned) in the bitstream
    end_of_sequence_counts = []
    
    def find_slice_padding_bytes(d):
        if isinstance(d, dict):
            for key, value in d.items():
                if key.endswith("_block_padding"):
                    component_padding_first_16_bits[key].add(value[:16].to01())
                else:
                    find_slice_padding_bytes(value)
        elif isinstance(d, list):
            for v in d:
                find_slice_padding_bytes(v)
    
    for test_case in slice_padding_data(codec_features):
        find_slice_padding_bytes(test_case.value)
        f = BytesIO()
        
        autofill_and_serialise_sequence(f, test_case.value)
        
        end_of_sequence = b"BBCD" + bytearray([ParseCodes.end_of_sequence])
        end_of_sequence_counts.append(f.getvalue().count(end_of_sequence))
    
    if profile == Profiles.high_quality:
        components = ["Y", "C1", "C2"]
    elif profile == Profiles.low_delay:
        components = ["Y", "C"]
    
    # Check that the non-aligned padding values appear as expected
    for component in components:
        key = "{}_block_padding".format(component.lower())
        assert "0000000000000000" in component_padding_first_16_bits[key]
        assert "1111111111111111" in component_padding_first_16_bits[key]
        assert "1010101010101010" in component_padding_first_16_bits[key]
        assert "0101010101010101" in component_padding_first_16_bits[key]
    
    # Check the final test cases insert extra (byte aligned!) end-of-sequence
    # blocks in the padding data (NB: we don't test that they appear in the
    # right places... but hey...)
    for count in end_of_sequence_counts[:-len(components)]:
        assert count == 1
    for count in end_of_sequence_counts[-len(components):]:
        assert count > 1
