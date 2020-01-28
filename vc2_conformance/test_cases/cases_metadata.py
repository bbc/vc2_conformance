"""
Metadata Test Cases
===================

Testcases related to metadata components of the VC-2 bitstream. These
parameters have no other effect on decoding.
"""

from vc2_conformance.test_cases.registry import test_group, test_case, XFail

from vc2_conformance import decoder

from vc2_conformance.test_cases.common import (
    TINY_VIDEO_OPTIONS,
    get_base_video_format_with,
    get_base_video_format_without,
    get_illigal_enum_values,
)

from vc2_data_tables import (
    ParseCodes,
    SourceSamplingModes,
    PictureCodingModes,
    PresetFrameRates,
    PresetPixelAspectRatios,
    PresetColorSpecs,
    PresetColorPrimaries,
    PresetColorMatrices,
    PresetTransferFunctions,
)

from vc2_conformance.bitstream import (
    Sequence,
    DataUnit,
    ParseInfo,
    SequenceHeader,
    SourceParameters,
    ScanFormat,
    FrameRate,
    PixelAspectRatio,
    CleanArea,
    ColorSpec,
    ColorPrimaries,
    ColorMatrix,
    TransferFunction,
)


with test_group("metadata_passthrough"):
    
    with test_group("scan_format"):
        @test_case(parameters=[
            ("source_sampling_mode", SourceSamplingModes),
            ("contradict_picture_coding_mode", [True, False]),
            ("contradict_base_video_format", [True, False]),
        ])
        def custom_scan_format(source_sampling_mode, contradict_base_video_format, contradict_picture_coding_mode):
            """
            Ensure that custom sampling modes (i.e. the 'progressive' vs
            'interlaced' metadata flags) are passed through.
            
            These test cases check that the correct output is achieved:
            
            * Regardless of whether the source sampling mode matches or contradicts
              the picture coding mode.
            * Regardless of whether the custom source sampling mode matches the
              default mode for the current base video format or contradicts it.
            """
            if contradict_base_video_format:
                base_video_format = get_base_video_format_without(
                    "source_sampling",
                    source_sampling_mode,
                )
            else:
                base_video_format = get_base_video_format_with(
                    "source_sampling",
                    source_sampling_mode,
                )
            
            if contradict_picture_coding_mode:
                picture_coding_mode = {
                    SourceSamplingModes.progressive: PictureCodingModes.pictures_are_fields,
                    SourceSamplingModes.interlaced: PictureCodingModes.pictures_are_frames,
                }[source_sampling_mode]
            else:
                picture_coding_mode = {
                    SourceSamplingModes.progressive: PictureCodingModes.pictures_are_frames,
                    SourceSamplingModes.interlaced: PictureCodingModes.pictures_are_fields,
                }[source_sampling_mode]
            
            seq = Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        base_video_format=base_video_format,
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            scan_format=ScanFormat(
                                custom_scan_format_flag=True,
                                source_sampling=source_sampling_mode,
                            )
                        ),
                        picture_coding_mode=picture_coding_mode,
                    ),
                ),
            ])
            
            seq["data_units"].append(DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)))
            if picture_coding_mode == PictureCodingModes.pictures_are_fields:
                seq["data_units"].append(DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)))
            
            seq["data_units"].append(DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)))
            
            return seq
        
        @test_case(xfail=decoder.BadSourceSamplingMode, parameters=[
            ("source_sampling_mode", get_illigal_enum_values(SourceSamplingModes)),
        ])
        def invalid_scan_format(source_sampling_mode):
            """
            Source sampling mode is set to an illegal value.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            scan_format=ScanFormat(
                                custom_scan_format_flag=True,
                                source_sampling=source_sampling_mode,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
    
    with test_group("frame_rate"):
        @test_case(parameters=("frame_rate_index", PresetFrameRates))
        def custom_preset_frame_rate(frame_rate_index):
            """
            Ensure that all defined preset frame rates may be used.
            """
            # Pick a base video format which does not use the specified frame rate
            # (to ensure the override is enforced)
            base_video_format = get_base_video_format_without("frame_rate_index", frame_rate_index)
            
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        base_video_format=base_video_format,
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            frame_rate=FrameRate(
                                custom_frame_rate_flag=True,
                                index=frame_rate_index,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(xfail=decoder.BadPresetFrameRateIndex, parameters=[
            ("frame_rate_index", get_illigal_enum_values(PresetFrameRates, non_zero=True)),
        ])
        def invalid_frame_rate_index(frame_rate_index):
            """
            Frame rate index is set to an illegal value.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            frame_rate=FrameRate(
                                custom_frame_rate_flag=True,
                                index=frame_rate_index,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case
        def custom_frame_rate():
            """
            Check that a custom fractional frame-rate may be specified.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            frame_rate=FrameRate(
                                custom_frame_rate_flag=True,
                                index=0,
                                # An arbitrary frame rate which doesn't appear in
                                # the predefined frame rate list but is low enough
                                # to be supportable by any codec.
                                frame_rate_numer=12,
                                frame_rate_denom=5,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(parameters=[
            ("numer,denom,exp_error", [
                (0, 1, decoder.FrameRateHasZeroNumerator),  # 0 FPS
                (1, 0, decoder.FrameRateHasZeroDenominator),  # Division by zero
            ]),
        ])
        def invalid_frame_rate_index(numer, denom, exp_error):
            """
            Custom frame rate is set to an illegal value (zero FPS or frame rate
            which is a division by zero).
            """
            seq = Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            frame_rate=FrameRate(
                                custom_frame_rate_flag=True,
                                index=0,
                                frame_rate_numer=numer,
                                frame_rate_denom=denom,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
            
            return XFail(seq, exp_error)
    
    with test_group("pixel_aspect_ratio"):
        @test_case(parameters=("pixel_aspect_ratio_index", PresetPixelAspectRatios))
        def custom_preset_pixel_aspect_ratio(pixel_aspect_ratio_index):
            """
            Ensure that all defined preset pixel aspect ratios may be used.
            """
            # Pick a base video format which does not use the specified pixel
            # aspect ratio (to ensure the override is enforced)
            base_video_format = get_base_video_format_without("pixel_aspect_ratio_index", pixel_aspect_ratio_index)
            
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        base_video_format=base_video_format,
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            pixel_aspect_ratio=PixelAspectRatio(
                                custom_pixel_aspect_ratio_flag=True,
                                index=pixel_aspect_ratio_index,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(xfail=decoder.BadPresetPixelAspectRatio, parameters=[
            ("pixel_aspect_ratio_index", get_illigal_enum_values(PresetPixelAspectRatios, non_zero=True)),
        ])
        def invalid_pixel_aspect_ratio_index(pixel_aspect_ratio_index):
            """
            Pixel aspect ratio index is set to an illegal value.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            pixel_aspect_ratio=PixelAspectRatio(
                                custom_pixel_aspect_ratio_flag=True,
                                index=pixel_aspect_ratio_index,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case
        def custom_pixel_aspect_ratio():
            """
            Check that a custom pixel aspect ratio may be specified.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            pixel_aspect_ratio=PixelAspectRatio(
                                custom_pixel_aspect_ratio_flag=True,
                                index=0,
                                # An arbitrary pixel aspect ratio which doesn't
                                # appear in the predefined list.
                                pixel_aspect_ratio_numer=2,
                                pixel_aspect_ratio_denom=3,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(parameters=[("numer,denom", [(0, 1), (1, 0)])])
        def invalid_pixel_aspect_ratio_index(numer, denom):
            """
            Custom pixel aspect ratio is set to an illegal value (containing a
            zero).
            """
            seq = Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            pixel_aspect_ratio=PixelAspectRatio(
                                custom_pixel_aspect_ratio_flag=True,
                                index=0,
                                pixel_aspect_ratio_numer=numer,
                                pixel_aspect_ratio_denom=denom,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
            
            return XFail(seq, decoder.PixelAspectRatioContainsZeros)
    
    with test_group("clean_area"):
        w = TINY_VIDEO_OPTIONS["frame_size"]["frame_width"]
        h = TINY_VIDEO_OPTIONS["frame_size"]["frame_height"]
        
        @test_case(parameters=("left_offset, top_offset, clean_width, clean_height", [
            # Full size
            (0, 0, w, h),
            # Not full size (in centre)
            (2, 1, w - 4, h - 2),
            # Not full size (in corners)
            (0, 0, w - 1, h - 1),
            (1, 0, w - 1, h - 1),
            (1, 1, w - 1, h - 1),
            (0, 1, w - 1, h - 1),
            # Zero size
            (0, 0, 0, 0),
            (w-1, h-1, 0, 0),
        ]))
        def custom_clean_area(left_offset, top_offset, clean_width, clean_height):
            """
            Ensure that the clean area may be set arbitrarily within the
            overall picture dimensions.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            clean_area=CleanArea(
                                custom_clean_area_flag=True,
                                left_offset=left_offset,
                                top_offset=top_offset,
                                clean_width=clean_width,
                                clean_height=clean_height,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
    
        @test_case(xfail=decoder.CleanAreaOutOfRange, parameters=(
            "left_offset, top_offset, clean_width, clean_height", [
                # Too big
                (0, 0, w+1, h),
                (0, 0, w, h+1),
                (0, 0, w+1, h+1),
                # Off the ends (with left/top offsets included)
                (1, 0, w, h),
                (0, 1, w, h),
                (1, 1, w, h),
            ]
        ))
        def clean_area_out_of_range(left_offset, top_offset, clean_width, clean_height):
            """
            Invalid (out-of-range) clean areas which specify an area beyond the
            boundaries of the frame size.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            clean_area=CleanArea(
                                custom_clean_area_flag=True,
                                left_offset=left_offset,
                                top_offset=top_offset,
                                clean_width=clean_width,
                                clean_height=clean_height,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
    
    with test_group("color_spec"):
        @test_case(parameters=("color_spec_index", PresetColorSpecs))
        def custom_preset_color_spec(color_spec_index):
            """
            Ensure that all defined color specifications may be used.
            """
            # Pick a base video format which does not use the specified color
            # spec (to ensure the override is enforced)
            base_video_format = get_base_video_format_without("color_spec_index", color_spec_index)
            
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        base_video_format=base_video_format,
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            color_spec=ColorSpec(
                                custom_color_spec_flag=True,
                                index=color_spec_index,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(xfail=decoder.BadPresetColorSpec, parameters=[
            ("color_spec_index", get_illigal_enum_values(PresetColorSpecs)),
        ])
        def invalid_color_spec_index(color_spec_index):
            """
            Color spec index is set to an illegal value.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            color_spec=ColorSpec(
                                custom_color_spec_flag=True,
                                index=color_spec_index,
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(parameters=("color_primaries_index", PresetColorPrimaries))
        def custom_preset_color_primaries(color_primaries_index):
            """
            Ensure that all defined color primaries may be used.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            color_spec=ColorSpec(
                                custom_color_spec_flag=True,
                                index=0,
                                color_primaries=ColorPrimaries(
                                    custom_color_primaries_flag=True,
                                    index=color_primaries_index,
                                ),
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(xfail=decoder.BadPresetColorPrimaries, parameters=[
            ("color_primaries_index", get_illigal_enum_values(PresetColorPrimaries)),
        ])
        def invalid_color_primaries_index(color_primaries_index):
            """
            Color primaries index is set to an illegal value.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            color_spec=ColorSpec(
                                custom_color_spec_flag=True,
                                index=0,
                                color_primaries=ColorPrimaries(
                                    custom_color_primaries_flag=True,
                                    index=color_primaries_index,
                                ),
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(parameters=("color_matrix_index", PresetColorMatrices))
        def custom_preset_color_matrix(color_matrix_index):
            """
            Ensure that all defined color matrices may be used.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            color_spec=ColorSpec(
                                custom_color_spec_flag=True,
                                index=0,
                                color_matrix=ColorMatrix(
                                    custom_color_matrix_flag=True,
                                    index=color_matrix_index,
                                ),
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(xfail=decoder.BadPresetColorMatrix, parameters=[
            ("color_matrix_index", get_illigal_enum_values(PresetColorMatrices)),
        ])
        def invalid_color_matrix_index(color_matrix_index):
            """
            Color matrix index is set to an illegal value.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            color_spec=ColorSpec(
                                custom_color_spec_flag=True,
                                index=0,
                                color_matrix=ColorMatrix(
                                    custom_color_matrix_flag=True,
                                    index=color_matrix_index,
                                ),
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(parameters=("transfer_function_index", PresetTransferFunctions))
        def custom_preset_transfer_function(transfer_function_index):
            """
            Ensure that all defined transfer functions may be used.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            color_spec=ColorSpec(
                                custom_color_spec_flag=True,
                                index=0,
                                transfer_function=TransferFunction(
                                    custom_transfer_function_flag=True,
                                    index=transfer_function_index,
                                ),
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
        
        @test_case(xfail=decoder.BadPresetTransferFunction, parameters=[
            ("transfer_function_index", get_illigal_enum_values(PresetTransferFunctions)),
        ])
        def invalid_transfer_function_index(transfer_function_index):
            """
            Transfer function index is set to an illegal value.
            """
            return Sequence(data_units=[
                DataUnit(
                    parse_info=ParseInfo(parse_code=ParseCodes.sequence_header),
                    sequence_header=SequenceHeader(
                        video_parameters=SourceParameters(
                            TINY_VIDEO_OPTIONS,
                            color_spec=ColorSpec(
                                custom_color_spec_flag=True,
                                index=0,
                                transfer_function=TransferFunction(
                                    custom_transfer_function_flag=True,
                                    index=transfer_function_index,
                                ),
                            )
                        ),
                    ),
                ),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.high_quality_picture)),
                DataUnit(parse_info=ParseInfo(parse_code=ParseCodes.end_of_sequence)),
            ])
