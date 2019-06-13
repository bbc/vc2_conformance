import pytest

from decoder_test_utils import serialise_to_bytes, bytes_to_state

from vc2_conformance.state import reset_state
from vc2_conformance import bitstream
from vc2_conformance import tables
from vc2_conformance import decoder


class TestSequenceHeader(object):

    def test_byte_for_byte_identical(self):
        sh1 = serialise_to_bytes(bitstream.SequenceHeader(
            parse_parameters=bitstream.ParseParameters(minor_version=0),
        ))
        sh2 = serialise_to_bytes(bitstream.SequenceHeader(
            parse_parameters=bitstream.ParseParameters(minor_version=1),
        ))
        
        state = bytes_to_state(sh1 + sh1 + sh2)
        
        decoder.sequence_header(state)
        decoder.sequence_header(state)
        with pytest.raises(decoder.SequenceHeaderChangedMidSequence) as exc_info:
            decoder.sequence_header(state)
        
        assert exc_info.value.last_sequence_header_offset == len(sh1)
        assert exc_info.value.last_sequence_header_bytes == sh1
        assert exc_info.value.this_sequence_header_offset == len(sh1)*2
        assert exc_info.value.this_sequence_header_bytes == sh2
    
    def test_supported_base_video_format(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.SequenceHeader(
            base_video_format=tables.BaseVideoFormats.custom_format
        )))
        decoder.sequence_header(state)
    
    def test_unsupported_base_video_format(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.SequenceHeader(
            base_video_format=9999
        )))
        with pytest.raises(decoder.BadBaseVideoFormat) as exc_info:
            decoder.sequence_header(state)
        assert exc_info.value.base_video_format == 9999
    
    def test_supported_picture_coding_mode(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.SequenceHeader(
            picture_coding_mode=tables.PictureCodingModes.pictures_are_frames
        )))
        decoder.sequence_header(state)
    
    def test_unsupported_picture_coding_mode(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.SequenceHeader(
            picture_coding_mode=2
        )))
        with pytest.raises(decoder.BadPictureCodingMode) as exc_info:
            decoder.sequence_header(state)
        assert exc_info.value.picture_coding_mode == 2
    
    @pytest.mark.parametrize("frame_width,frame_height,exp_luma_width,exp_luma_height,exp_color_diff_width,exp_color_diff_height,exp_error", [
        # Divides both dimensions exactly
        (1000, 1000, 1000, 500, 500, 250, False),
        # Doesn't divide color-diff width
        (1001, 1000, 1001, 500, 500, 250, True),
        # Doesn't divide color-diff height
        (1000, 1002, 1000, 501, 500, 250, True),
        # Doesn't divide luma height
        (1000, 1001, 1000, 500, 500, 250, True),
        # Color-diff width evaluates to zero
        (1, 1000, 1, 500, 0, 250, True),
        # Color-diff height evaluates to zero
        (1000, 2, 1000, 1, 500, 0, True),
        # Luma height evaluates to zero
        (1000, 1, 1000, 0, 500, 0, True),
    ])
    def test_picture_dimensions_must_be_multiple_of_frame_dimensions(
        self,
        frame_width,
        frame_height,
        exp_luma_width,
        exp_luma_height,
        exp_color_diff_width,
        exp_color_diff_height,
        exp_error,
    ):
        state = bytes_to_state(serialise_to_bytes(bitstream.SequenceHeader(
            picture_coding_mode=tables.PictureCodingModes.pictures_are_fields,
            video_parameters=bitstream.SourceParameters(
                frame_size=bitstream.FrameSize(
                    custom_dimensions_flag=True,
                    frame_width=frame_width,
                    frame_height=frame_height,
                ),
                clean_area=bitstream.CleanArea(
                    custom_clean_area_flag=True,
                    clean_width=frame_width,
                    clean_height=frame_height,
                ),
                color_diff_sampling_format=bitstream.ColorDiffSamplingFormat(
                    custom_color_diff_format_flag=True,
                    color_diff_format_index=tables.ColorDifferenceSamplingFormats.color_4_2_0,
                ),
            ),
        )))
        if exp_error:
            with pytest.raises(decoder.PictureDimensionsNotMultipleOfFrameDimensions) as exc_info:
                decoder.sequence_header(state)
            assert exc_info.value.luma_width == exp_luma_width
            assert exc_info.value.luma_height == exp_luma_height
            assert exc_info.value.color_diff_width == exp_color_diff_width
            assert exc_info.value.color_diff_height == exp_color_diff_height
            assert exc_info.value.frame_width == frame_width
            assert exc_info.value.frame_height == frame_height
        else:
            decoder.sequence_header(state)
            assert state["luma_width"] == exp_luma_width
            assert state["luma_height"] == exp_luma_height
            assert state["color_diff_width"] == exp_color_diff_width
            assert state["color_diff_height"] == exp_color_diff_height


class TestParseParameters(object):
    
    @pytest.mark.parametrize("kwargs1,kwargs2,exc_type", [
        (
            {"profile": tables.Profiles.high_quality},
            {"profile": tables.Profiles.low_delay},
            decoder.ProfileChanged,
        ),
        (
            {"level": tables.Levels.unconstrained},
            {"level": tables.Levels.hd},
            decoder.LevelChanged,
        ),
    ])
    def test_profile_and_level_must_not_change_between_sequences(self, kwargs1, kwargs2, exc_type):
        pp1 = serialise_to_bytes(bitstream.ParseParameters(**kwargs1))
        pp2 = serialise_to_bytes(bitstream.ParseParameters(**kwargs2))
        
        state = bytes_to_state(pp1 + pp1 + pp2)
        
        decoder.parse_parameters(state)
        reset_state(state)
        last_pp_offset = decoder.tell(state)
        decoder.parse_parameters(state)
        reset_state(state)
        this_pp_offset = decoder.tell(state)
        with pytest.raises(exc_type) as exc_info:
            decoder.parse_parameters(state)
        
        assert exc_info.value.last_parse_parameters_offset == last_pp_offset
        assert exc_info.value.this_parse_parameters_offset == this_pp_offset
        
        change_type = list(kwargs1.keys())[0]
        change_value1 = list(kwargs1.values())[0]
        change_value2 = list(kwargs2.values())[0]
        assert getattr(exc_info.value, "last_" + change_type) == change_value1
        assert getattr(exc_info.value, "this_" + change_type) == change_value2
    
    def test_profile_must_be_valid(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.ParseParameters(
            profile=tables.Profiles.high_quality
        )))
        decoder.parse_parameters(state)
        
        state = bytes_to_state(serialise_to_bytes(bitstream.ParseParameters(profile=9999)))
        with pytest.raises(decoder.BadProfile) as exc_info:
            decoder.parse_parameters(state)
        assert exc_info.value.profile == 9999
    
    def test_level_must_be_valid(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.ParseParameters(
            level=tables.Levels.unconstrained
        )))
        decoder.parse_parameters(state)
        
        state = bytes_to_state(serialise_to_bytes(bitstream.ParseParameters(level=9999)))
        with pytest.raises(decoder.BadLevel) as exc_info:
            decoder.parse_parameters(state)
        assert exc_info.value.level == 9999
    
    def test_level_sequence_matcher(self):
        # This level requires alternating HQ pictures and sequence headers.
        state = bytes_to_state(serialise_to_bytes(bitstream.ParseParameters(
            level=tables.Levels.uhd_over_hd_sdi,
            profile=tables.Profiles.high_quality,
            major_version=3,
            minor_version=0,
        )))
        decoder.parse_parameters(state)
        
        # The matcher should start *after* the sequence header this
        # parse_parameters was in
        assert state["_level_sequence_matcher"].match_symbol("high_quality_picture")
        assert state["_level_sequence_matcher"].match_symbol("sequence_header")
        assert not state["_level_sequence_matcher"].match_symbol("sequence_header")
    
    def test_constraints(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.ParseParameters(
            level=0,
            profile=0,
            major_version=3,
            minor_version=0,
        )))
        decoder.parse_parameters(state)
        assert state["_level_constrained_values"] == {
            "level": 0,
            "profile": 0,
            "major_version": 3,
            "minor_version": 0,
        }


@pytest.mark.parametrize("frame_width,frame_height", [
    (0, 1000),
    (1000, 0),
    (0, 0),
])
def test_frame_size_must_not_be_zero(frame_width, frame_height):
    state = bytes_to_state(serialise_to_bytes(
        bitstream.FrameSize(
            custom_dimensions_flag=True,
            frame_width=frame_width,
            frame_height=frame_height,
        ),
        {}, {},
    ))
    
    with pytest.raises(decoder.ZeroPixelFrameSize) as exc_info:
        decoder.frame_size(state, {})
    
    assert exc_info.value.frame_width == frame_width
    assert exc_info.value.frame_height == frame_height


def test_color_diff_sampling_format_index_must_be_valid():
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ColorDiffSamplingFormat(
            custom_color_diff_format_flag=True,
            color_diff_format_index=tables.ColorDifferenceSamplingFormats.color_4_4_4,
        ),
        {}, {},
    ))
    decoder.color_diff_sampling_format(state, {})
    
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ColorDiffSamplingFormat(
            custom_color_diff_format_flag=True,
            color_diff_format_index=9999,
        ),
        {}, {},
    ))
    with pytest.raises(decoder.BadColorDifferenceSamplingFormat) as exc_info:
        decoder.color_diff_sampling_format(state, {})
    assert exc_info.value.color_diff_format_index == 9999


def test_scan_format_source_sampling_mode_must_be_valid():
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ScanFormat(
            custom_scan_format_flag=True,
            source_sampling=tables.SourceSamplingModes.progressive,
        ),
        {}, {},
    ))
    decoder.scan_format(state, {})
    
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ScanFormat(
            custom_scan_format_flag=True,
            source_sampling=9999,
        ),
        {}, {},
    ))
    with pytest.raises(decoder.BadSourceSamplingMode) as exc_info:
        decoder.scan_format(state, {})
    assert exc_info.value.source_sampling == 9999


class TestFrameRate(object):
    
    def test_index_must_be_valid(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.FrameRate(
            custom_frame_rate_flag=True,
            index=tables.PresetFrameRates.fps_25,
        ), {}, {}))
        decoder.frame_rate(state, {})
        
        state = bytes_to_state(serialise_to_bytes(bitstream.FrameRate(
            custom_frame_rate_flag=True,
            index=9999,
        ), {}, {}))
        with pytest.raises(decoder.BadPresetFrameRateIndex) as exc_info:
            decoder.frame_rate(state, {})
        assert exc_info.value.index == 9999
    
    def test_denominator_must_not_be_zero(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.FrameRate(
            custom_frame_rate_flag=True,
            index=0,
            frame_rate_numer=1,
            frame_rate_denom=0,
        ), {}, {}))
        
        with pytest.raises(decoder.FrameRateHasZeroDenominator) as exc_info:
            decoder.frame_rate(state, {})
        
        assert exc_info.value.frame_rate_numer == 1
    
    def test_must_not_be_zero_fps(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.FrameRate(
            custom_frame_rate_flag=True,
            index=0,
            frame_rate_numer=0,
            frame_rate_denom=1,
        ), {}, {}))
        
        with pytest.raises(decoder.FrameRateHasZeroNumerator) as exc_info:
            decoder.frame_rate(state, {})
        
        assert exc_info.value.frame_rate_denom == 1
    
    def test_valid_custom_value(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.FrameRate(
            custom_frame_rate_flag=True,
            index=0,
            frame_rate_numer=1,
            frame_rate_denom=2,
        ), {}, {}))
        
        decoder.frame_rate(state, {})


class TestPixelAspectRatio(object):

    def test_index_must_be_valid(self):
        state = bytes_to_state(serialise_to_bytes(bitstream.PixelAspectRatio(
            custom_pixel_aspect_ratio_flag=True,
            index=tables.PresetPixelAspectRatios.ratio_1_1,
        ), {}, {}))
        decoder.pixel_aspect_ratio(state, {})
        
        state = bytes_to_state(serialise_to_bytes(bitstream.PixelAspectRatio(
            custom_pixel_aspect_ratio_flag=True,
            index=9999,
        ), {}, {}))
        with pytest.raises(decoder.BadPresetPixelAspectRatio) as exc_info:
            decoder.pixel_aspect_ratio(state, {})
        assert exc_info.value.index == 9999

    @pytest.mark.parametrize("numer,denom,exp_fail", [
        (1, 1, False),
        (0, 1, True),
        (1, 0, True),
        (0, 0, True),
    ])
    def test_must_not_contain_zeros(self, numer, denom, exp_fail):
        state = bytes_to_state(serialise_to_bytes(bitstream.PixelAspectRatio(
            custom_pixel_aspect_ratio_flag=True,
            index=0,
            pixel_aspect_ratio_numer=numer,
            pixel_aspect_ratio_denom=denom,
        ), {}, {}))
        
        if exp_fail:
            with pytest.raises(decoder.PixelAspectRatioContainsZeros) as exc_info:
                decoder.pixel_aspect_ratio(state, {})
            
            assert exc_info.value.pixel_aspect_ratio_numer == numer
            assert exc_info.value.pixel_aspect_ratio_denom == denom
        else:
            decoder.pixel_aspect_ratio(state, {})

@pytest.mark.parametrize("via_custom_clean_width", [False, True])
@pytest.mark.parametrize("clean_width,clean_height,left_offset,top_offset,exp_fail", [
    # Exactly match picture size
    (1920, 1080, 0, 0, False),
    # Smaller than picture size, top-left-aligned
    (1910, 1076, 0, 0, False),
    # Smaller than picture size, center-aligned
    (1910, 1076, 5, 2, False),
    # Smaller than picture size, bottom-right-aligned
    (1910, 1076, 10, 4, False),
    # Overlapping right-hand side
    (1910, 1076, 11, 4, True),
    # Overlapping bottom edge
    (1910, 1076, 10, 5, True),
])
def test_custom_clean_area(via_custom_clean_width,
                           clean_width, clean_height, left_offset, top_offset, exp_fail):
    frame_width = 1920
    frame_height = 1080
    
    if via_custom_clean_width:
        video_parameters = {
            "frame_width": frame_width,
            "frame_height": frame_height,
        }
        state = bytes_to_state(serialise_to_bytes(
            bitstream.CleanArea(
                custom_clean_area_flag=True,
                clean_width=clean_width,
                clean_height=clean_height,
                left_offset=left_offset,
                top_offset=top_offset,
            ),
            {}, video_parameters,
        ))
    else:
        video_parameters = {
            "frame_width": frame_width,
            "frame_height": frame_height,
            "clean_width": clean_width,
            "clean_height": clean_height,
            "left_offset": left_offset,
            "top_offset": top_offset,
        }
        state = bytes_to_state(serialise_to_bytes(
            bitstream.CleanArea(
                custom_clean_area_flag=False,
            ),
            {}, video_parameters,
        ))
    
    if exp_fail:
        with pytest.raises(decoder.CleanAreaOutOfRange) as exc_info:
            decoder.clean_area(state, video_parameters)
        assert exc_info.value.clean_width == clean_width
        assert exc_info.value.clean_height == clean_height
        assert exc_info.value.left_offset == left_offset
        assert exc_info.value.top_offset == top_offset
        assert exc_info.value.frame_width == frame_width
        assert exc_info.value.frame_height == frame_height
    else:
        decoder.clean_area(state, video_parameters)


def test_signal_range_index_must_be_valid():
    state = bytes_to_state(serialise_to_bytes(
        bitstream.SignalRange(
            custom_signal_range_flag=True,
            index=tables.PresetSignalRanges.video_8bit,
        ),
        {}, {},
    ))
    decoder.signal_range(state, {})
    
    state = bytes_to_state(serialise_to_bytes(
        bitstream.SignalRange(
            custom_signal_range_flag=True,
            index=9999,
        ),
        {}, {},
    ))
    with pytest.raises(decoder.BadPresetSignalRange) as exc_info:
        decoder.signal_range(state, {})
    assert exc_info.value.index == 9999


def test_color_spec_index_must_be_valid():
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ColorSpec(
            custom_color_spec_flag=True,
            index=tables.PresetColorSpecs.uhdtv,
        ),
        {}, {},
    ))
    decoder.color_spec(state, {})
    
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ColorSpec(
            custom_color_spec_flag=True,
            index=9999,
        ),
        {}, {},
    ))
    with pytest.raises(decoder.BadPresetColorSpec) as exc_info:
        decoder.color_spec(state, {})
    assert exc_info.value.index == 9999


def test_color_primaries_index_must_be_valid():
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ColorPrimaries(
            custom_color_primaries_flag=True,
            index=tables.PresetColorPrimaries.hdtv,
        ),
        {}, {},
    ))
    decoder.color_primaries(state, {})
    
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ColorPrimaries(
            custom_color_primaries_flag=True,
            index=9999,
        ),
        {}, {},
    ))
    with pytest.raises(decoder.BadPresetColorPrimaries) as exc_info:
        decoder.color_primaries(state, {})
    assert exc_info.value.index == 9999


def test_color_matrix_index_must_be_valid():
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ColorMatrix(
            custom_color_matrix_flag=True,
            index=tables.PresetColorMatrices.hdtv,
        ),
        {}, {},
    ))
    decoder.color_matrix(state, {})
    
    state = bytes_to_state(serialise_to_bytes(
        bitstream.ColorMatrix(
            custom_color_matrix_flag=True,
            index=9999,
        ),
        {}, {},
    ))
    with pytest.raises(decoder.BadPresetColorMatrix) as exc_info:
        decoder.color_matrix(state, {})
    assert exc_info.value.index == 9999


def test_transfer_function_index_must_be_valid():
    state = bytes_to_state(serialise_to_bytes(
        bitstream.TransferFunction(
            custom_transfer_function_flag=True,
            index=tables.PresetTransferFunctions.hybrid_log_gamma,
        ),
        {}, {},
    ))
    decoder.transfer_function(state, {})
    
    state = bytes_to_state(serialise_to_bytes(
        bitstream.TransferFunction(
            custom_transfer_function_flag=True,
            index=9999,
        ),
        {}, {},
    ))
    with pytest.raises(decoder.BadPresetTransferFunction) as exc_info:
        decoder.transfer_function(state, {})
    assert exc_info.value.index == 9999


def test_level_constraints():
    # Simply check that all constrainted level values get asserted. We check
    # this by making sure assert_level_constraint has added the relevant values
    # to # state["_level_constrained_values"].
    state = bytes_to_state(serialise_to_bytes(bitstream.SequenceHeader(
        base_video_format=tables.BaseVideoFormats.custom_format,
        picture_coding_mode=tables.PictureCodingModes.pictures_are_frames,
        parse_parameters=bitstream.ParseParameters(
            level=tables.Levels.unconstrained,
            profile=tables.Profiles.high_quality,
            major_version=3,
            minor_version=0,
        ),
        video_parameters=bitstream.SourceParameters(
            frame_size=bitstream.FrameSize(
                custom_dimensions_flag=True,
                frame_width=1280,
                frame_height=1080,
            ),
            color_diff_sampling_format=bitstream.ColorDiffSamplingFormat(
                custom_color_diff_format_flag=True,
                color_diff_format_index=tables.ColorDifferenceSamplingFormats.color_4_4_4,
            ),
            scan_format=bitstream.ScanFormat(
                custom_scan_format_flag=True,
                source_sampling=tables.SourceSamplingModes.progressive,
            ),
            frame_rate=bitstream.FrameRate(
                custom_frame_rate_flag=True,
                index=0,
                frame_rate_numer=25,
                frame_rate_denom=1,
            ),
            pixel_aspect_ratio=bitstream.PixelAspectRatio(
                custom_pixel_aspect_ratio_flag=True,
                index=0,
                pixel_aspect_ratio_numer=1,
                pixel_aspect_ratio_denom=1,
            ),
            clean_area=bitstream.CleanArea(
                custom_clean_area_flag=True,
                clean_width=1,
                clean_height=2,
                left_offset=3,
                top_offset=4,
            ),
            signal_range=bitstream.SignalRange(
                custom_signal_range_flag=True,
                index=0,
                luma_offset=1,
                luma_excursion=2,
                color_diff_offset=3,
                color_diff_excursion=4,
            ),
            color_spec=bitstream.ColorSpec(
                custom_color_spec_flag=True,
                index=0,
                color_primaries=bitstream.ColorPrimaries(
                    custom_color_primaries_flag=True,
                    index=tables.PresetColorPrimaries.uhdtv,
                ),
                color_matrix=bitstream.ColorMatrix(
                    custom_color_matrix_flag=True,
                    index=tables.PresetColorMatrices.uhdtv,
                ),
                transfer_function=bitstream.TransferFunction(
                    custom_transfer_function_flag=True,
                    index=tables.PresetTransferFunctions.hybrid_log_gamma,
                ),
            ),
        ),
    )))
    decoder.sequence_header(state)
    assert state["_level_constrained_values"] == {
        # sequence_header
        "base_video_format": tables.BaseVideoFormats.custom_format,
        "picture_coding_mode": tables.PictureCodingModes.pictures_are_frames,
        # parse_parameters
        "level": tables.Levels.unconstrained,
        "profile": tables.Profiles.high_quality,
        "major_version": 3,
        "minor_version": 0,
        # frame_size
        "custom_dimensions_flag": True,
        "frame_width": 1280,
        "frame_height": 1080,
        # color_diff_sampling_format
        "custom_color_diff_format_flag": True,
        "color_diff_format_index": tables.ColorDifferenceSamplingFormats.color_4_4_4,
        # scan_format
        "custom_scan_format_flag": True,
        "source_sampling": tables.SourceSamplingModes.progressive,
        # frame_rate
        "custom_frame_rate_flag": True,
        "frame_rate_index": 0,
        "frame_rate_numer": 25,
        "frame_rate_denom": 1,
        # pixel_aspect_ratio
        "custom_pixel_aspect_ratio_flag": True,
        "pixel_aspect_ratio_index": 0,
        "pixel_aspect_ratio_numer": 1,
        "pixel_aspect_ratio_denom": 1,
        # clean_area
        "custom_clean_area_flag": True,
        "clean_width": 1,
        "clean_height": 2,
        "left_offset": 3,
        "top_offset": 4,
        # signal_range
        "custom_signal_range_flag": True,
        "custom_signal_range_index": 0,
        "luma_offset": 1,
        "luma_excursion": 2,
        "color_diff_offset": 3,
        "color_diff_excursion": 4,
        # color_spec
        "custom_color_spec_flag": True,
        "custom_color_spec_index": 0,
        # color_primaries
        "custom_color_primaries_flag": True,
        "custom_color_primaries_index": tables.PresetColorPrimaries.uhdtv,
        # color_matrix
        "custom_color_matrix_flag": True,
        "custom_color_matrix_index": tables.PresetColorMatrices.uhdtv,
        # transfer_function
        "custom_transfer_function_flag": True,
        "custom_transfer_function_index": tables.PresetTransferFunctions.hybrid_log_gamma,
    }
