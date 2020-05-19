import pytest

from vc2_conformance.pseudocode.state import State

from vc2_conformance.pseudocode.slice_sizes import slices_have_same_dimensions


@pytest.mark.parametrize(
    "slices_x,slices_y,state_override,exp_same_dimensions",
    [
        (1, 1, {}, True),
        (192, 108, {}, True),
        # Up to limit
        (960, 540, {}, True),
        # Too small for colour diff
        (1920, 1, {}, False),
        (1, 1080, {}, False),
        # Not a multiple of either
        (111, 1, {}, False),
        (1, 111, {}, False),
        # Too small for either
        (3840, 1, {}, False),
        (1, 2160, {}, False),
        # With increased transform depths
        (1, 1, {"dwt_depth": 1, "dwt_depth_ho": 1}, True),
        # Up to limit
        (240, 270, {"dwt_depth": 1, "dwt_depth_ho": 1}, True),
        # Past new limit should fail
        (192, 1, {"dwt_depth": 1, "dwt_depth_ho": 1}, False),
        (1, 108, {"dwt_depth": 1, "dwt_depth_ho": 1}, False),
    ],
)
def test_slices_have_same_dimensions(
    slices_x, slices_y, state_override, exp_same_dimensions
):
    state = State(
        luma_width=1920,
        luma_height=1080,
        color_diff_width=960,
        color_diff_height=540,
        dwt_depth=0,
        dwt_depth_ho=0,
        slices_x=slices_x,
        slices_y=slices_y,
    )
    state.update(state_override)

    assert slices_have_same_dimensions(state) is exp_same_dimensions
