from vc2_data_tables import PictureCodingModes

from vc2_conformance.test_cases import (
    TestCase,
    decoder_test_case_generator,
)

from vc2_conformance.encoder import make_sequence

from vc2_conformance.picture_generators import (
    mid_gray,
    repeat_pictures,
)


@decoder_test_case_generator
def picture_numbers(codec_features):
    """
    Tests that picture numbers are read correctly from the stream, including
    handling cases such as picture number wrap-arounds.

    The following test cases will be produced:

    * ``start_at_zero``: Picture numbers starting at 0.
    * ``non_zero_start``: Picture numbers starting at 1000.
    * ``wrap_around``: Picture numbers which overflow/wrap-around the 32 bit
      picture number field.
    * ``odd_first_picture``: Picture numbers starting at 7. Included only when
      pictures are frames.
    """
    # Create a sequence with at least 8 pictures (and 4 frames)
    mid_gray_pictures = list(
        mid_gray(
            codec_features["video_parameters"], codec_features["picture_coding_mode"],
        )
    )
    mid_gray_pictures = list(
        repeat_pictures(mid_gray_pictures, 8 // len(mid_gray_pictures),)
    )

    test_cases = [
        ("start_at_zero", [0, 1, 2, 3, 4, 5, 6, 7]),
        ("non_zero_start", [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007]),
        ("wrap_around", [4294967292, 4294967293, 4294967294, 4294967295, 0, 1, 2, 3]),
    ]

    if codec_features["picture_coding_mode"] == PictureCodingModes.pictures_are_frames:
        test_cases.append(("odd_first_picture", [7, 8, 9, 10, 11, 12, 13, 14]))

    for description, picture_numbers in test_cases:
        yield TestCase(
            make_sequence(
                codec_features,
                [
                    dict(picture, pic_num=pic_num)
                    for picture, pic_num in zip(mid_gray_pictures, picture_numbers)
                ],
            ),
            description,
        )
