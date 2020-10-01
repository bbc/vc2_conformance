from vc2_data_tables import PictureCodingModes

from vc2_conformance.bitstream import Stream

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
    **Tests picture numbers are correctly read from the bitstream.**

    Each test case contains 8 blank pictures numbered in a particular way.

    ``picture_numbers[start_at_zero]``
        The first picture has picture number 0.

    ``picture_numbers[non_zero_start]``
        The first picture has picture number 1000.

    ``picture_numbers[wrap_around]``
        The first picture has picture number 4294967292, with the picture
        numbers wrapping around to 0 on the 4th picture in the sequence.

    ``picture_numbers[odd_first_picture]``
        The first picture has picture number 7. This test case is only included
        when the picture coding mode is 0 (i.e. pictures are frames) since the
        first field of each frame must have an even number when the picture
        coding mode is 1 (i.e. pictures are fields) (11.5).
    """
    # Create a sequence with at least 8 pictures (and 4 frames)
    mid_gray_pictures = list(
        mid_gray(
            codec_features["video_parameters"],
            codec_features["picture_coding_mode"],
        )
    )
    mid_gray_pictures = list(
        repeat_pictures(
            mid_gray_pictures,
            8 // len(mid_gray_pictures),
        )
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
            Stream(
                sequences=[
                    make_sequence(
                        codec_features,
                        [
                            dict(picture, pic_num=pic_num)
                            for picture, pic_num in zip(
                                mid_gray_pictures, picture_numbers
                            )
                        ],
                    )
                ]
            ),
            description,
        )
