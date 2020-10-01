"""
Generic synthetic test sequences.
"""

from vc2_conformance.test_cases import encoder_test_case_generator

from vc2_conformance.test_cases.encoder.common import picture_generator_to_test_case

from vc2_conformance import picture_generators


@encoder_test_case_generator
def synthetic_moving_sprite(codec_features):
    """
    **Tests that an encoder produces sensible results for motion.**

    A sequence of 10 frames containing a graphic moving from left to right
    along the top of the frame. In successive each frame, the graphic moves
    16 luma samples to the right (i.e. 8 samples every field, for
    interlaced formats).

    .. image:: /_static/user_guide/interlace_mode_and_pixel_aspect_ratio_moving_sequence.svg

    For progressive formats, the graphic should appear with smooth edges in
    each frame.

    For interlaced formats, the graphic should move smoothly when displayed
    on an interlaced monitor. If displayed as progressive frames (as in the
    illustration above), the pictures will appear to have ragged edges.
    """
    return picture_generator_to_test_case(
        picture_generators.moving_sprite,
        codec_features,
    )


@encoder_test_case_generator
def synthetic_linear_ramps(codec_features):
    """
    **Tests that an encoder correctly encodes color specification
    information.**

    A static frame containing linear signal ramps for white and primary
    red, green and blue (in that order, from top-to-bottom) as illustrated
    below:

    .. image:: /_static/user_guide/static_ramps.png

    The red, green and blue colors correspond to the red, green and blue
    primaries for the color specification (11.4.10.2).

    .. note::

        When D-Cinema primaries are specified (preset color primaries index 3),
        red, green and blue are replaced with CIE X, Y and Z respectively. Note
        that these may not represent physically realisable colors.

    The left-most pixels in each band are video black and the right-most pixels
    video white, red, green and blue (respectively). That is, oversaturated
    signals (e.g. 'super-blacks' and 'super-white') are not included.

    The value ramps in the test picture are linear meaning that the (linear)
    pixel values increase at a constant rate from left (black) to right
    (saturated white/red/green/blue). Due to the non-linear response of human
    vision, this will produce a non-linear brightness ramp which appears to
    quickly saturate. Further, when a non-linear transfer function is specified
    (11.4.10.4) the raw picture values will not be linearly spaced.

    .. note::

        When the D-Cinema transfer function is specified (preset transfer
        function index 3), the saturated signals do not correspond to a
        non-linear signal value of 1.0 but instead approximately 0.97. This is
        because the D-Cinema transfer function allocates part of its nominal
        output range to over-saturated signals.
    """
    return picture_generator_to_test_case(
        picture_generators.linear_ramps,
        codec_features,
    )


@encoder_test_case_generator
def synthetic_gray(codec_features):
    """
    **Tests that the encoder can encode a maximally compressible sequence.**

    This sequence contains an image in which every transform coefficient is
    zero. For most color specifications (11.4.10), this decodes to a mid-gray
    frame.

    This special case image is maximally compressible since no transform
    coefficients need to be explicitly coded in the bitstream. For lossless
    coding modes, this should also produce produce the smallest possible
    bitstream.
    """
    return picture_generator_to_test_case(
        picture_generators.mid_gray,
        codec_features,
    )


@encoder_test_case_generator
def synthetic_noise(codec_features):
    """
    **Tests that an encoder correctly encodes a noise plate.**

    A static frame containing pseudo-random uniform noise as illustrated below:

    .. image:: /_static/user_guide/noise.png

    .. note::

        It is likely that lossy encoders will be unable to compress this test
        case without a fairly significant loss of fidelity. As such, it is
        acceptable for this test case for an encoder to produce only visually
        similar results.
    """
    return picture_generator_to_test_case(
        picture_generators.white_noise,
        codec_features,
    )
