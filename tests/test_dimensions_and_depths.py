from vc2_data_tables import (
    BaseVideoFormats,
    PictureCodingModes,
    ColorDifferenceSamplingFormats,
)

from vc2_conformance.pseudocode.video_parameters import set_source_defaults

from vc2_conformance.dimensions_and_depths import (
    compute_dimensions_and_depths,
    DimensionsAndDepths,
)


def test_compute_dimensions_and_depths():
    # Just to set all unimportant fields to something sensible
    vp = set_source_defaults(BaseVideoFormats.cif)

    vp["frame_width"] = 1000
    vp["frame_height"] = 600

    # Make luma and chroma different sizes
    vp["color_diff_format_index"] = ColorDifferenceSamplingFormats.color_4_2_0

    # Make luma and chroma different depths
    vp["luma_excursion"] = 200  # 8 bits
    vp["color_diff_excursion"] = (1 << 18) - 100  # 18 bits

    # Make frame size differ from picture size
    pcm = PictureCodingModes.pictures_are_fields

    dd = compute_dimensions_and_depths(vp, pcm)

    assert list(dd.items()) == [
        (
            "Y",
            DimensionsAndDepths(
                width=1000, height=300, depth_bits=8, bytes_per_sample=1
            ),
        ),
        (
            "C1",
            DimensionsAndDepths(
                width=500, height=150, depth_bits=18, bytes_per_sample=4
            ),
        ),
        (
            "C2",
            DimensionsAndDepths(
                width=500, height=150, depth_bits=18, bytes_per_sample=4
            ),
        ),
    ]
