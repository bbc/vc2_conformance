from vc2_conformance.test_cases import EncoderTestSequence


def picture_generator_to_test_case(picture_generator, codec_features):
    """
    Internal utility. Takes a function from
    :py:mod:`vc2_conformance.picture_generators` and a set of
    :py:class:`~vc2_conformance.codec_features.CodecFeatures` and
    returns a :py:class:`~vc2_conformance.test_cases.EncoderTestSequence`.
    """
    out = EncoderTestSequence(
        pictures=[],
        video_parameters=codec_features["video_parameters"],
        picture_coding_mode=codec_features["picture_coding_mode"],
    )

    for picture in picture_generator(
        codec_features["video_parameters"],
        codec_features["picture_coding_mode"],
    ):
        out.pictures.append(picture)

    return out
