"""
The exceptions defined in :py:mod:`vc2_conformance.encoder.exceptions` derive
from :py:exc:`UnsatisfiableCodecFeaturesError` and are thrown when the
presented encoder configuration makes encoding impossible. These exceptions
provide detailed explanations of why encoding was not possible.

.. autoexception:: UnsatisfiableCodecFeaturesError
    :members:

"""

from vc2_conformance.string_utils import wrap_paragraphs


class UnsatisfiableCodecFeaturesError(ValueError):
    """
    Base class for exceptions thrown by the encoder when it is unable to
    generate a stream in the desired format due to some invalid
    :py:class:`~vc2_conformance.codec_features.CodecFeatures` configuration.
    """

    def __str__(self):
        return wrap_paragraphs(self.explain()).partition("\n")[0]

    def explain(self):
        """
        Produce a detailed human readable explanation of the failure.

        Should return a string which can be re-linewrapped by
        :py:func:`vc2_conformance.string_utils.wrap_paragraphs`.

        The first line will be used as a summary when the exception is printed
        using :py:func:`str`.
        """
        raise NotImplementedError()


class MissingQuantizationMatrixError(UnsatisfiableCodecFeaturesError):
    """
    Thrown when the codec features specified did not include a quantization
    matrix when one was required.
    """

    def explain(self):
        (codec_features,) = self.args

        return """
            No default quantization matrix is available for the wavelet
            transform specified for {} and no custom quantization matrix was
            provided.

            * wavelet_index: {} ({:d})
            * wavelet_index_ho: {} ({:d})
            * dwt_depth: {}
            * dwt_depth_ho: {}
        """.format(
            codec_features["name"],
            codec_features["wavelet_index"].name,
            codec_features["wavelet_index"],
            codec_features["wavelet_index_ho"].name,
            codec_features["wavelet_index_ho"],
            codec_features["dwt_depth"],
            codec_features["dwt_depth_ho"],
        )


class PictureBytesSpecifiedForLosslessModeError(UnsatisfiableCodecFeaturesError):
    """
    Thrown when the 'picture_bytes' field of a
    :py:class:`vc2_conformance.codec_features.CodecFeatures` is set at the same
    time as the lossless field being true.
    """

    def explain(self):
        (codec_features,) = self.args

        return """
            The codec configuration {} specifies a lossless format but did not
            omit picture_bytes (it is set to {}).
        """.format(
            codec_features["name"],
            codec_features["picture_bytes"],
        )


class InsufficientHQPictureBytesError(UnsatisfiableCodecFeaturesError):
    """
    Thrown when the 'picture_bytes' field of a
    :py:class:`vc2_conformance.codec_features.CodecFeatures` is set too low for
    the coding options chosen.
    """

    def explain(self):
        (codec_features,) = self.args

        return """
            The codec configuration {} specifies picture_bytes as {} but this
            is too small.

            A {} by {} slice high quality profile encoding must allow at least
            4*{}*{} = {} bytes. (That is, 1 byte for the qindex field and 3
            bytes for the length fields of each high quality slice (13.5.4))
        """.format(
            codec_features["name"],
            codec_features["picture_bytes"],
            codec_features["slices_x"],
            codec_features["slices_y"],
            codec_features["slices_x"],
            codec_features["slices_y"],
            4 * codec_features["slices_x"] * codec_features["slices_y"],
        )


class InsufficientLDPictureBytesError(UnsatisfiableCodecFeaturesError):
    """
    Thrown when the 'picture_bytes' field of a
    :py:class:`vc2_conformance.codec_features.CodecFeatures` is set too low for
    the coding options chosen.
    """

    def explain(self):
        (codec_features,) = self.args

        return """
            The codec configuration {} specifies picture_bytes as {} but this
            is too small.

            A {} by {} slice low delay profile encoding must allow at least
            {}*{} = {} bytes. (That is, 7 bits for the qindex field and 1 bit
            for the slice_y_length field of each low delay slice (13.5.3.1))
        """.format(
            codec_features["name"],
            codec_features["picture_bytes"],
            codec_features["slices_x"],
            codec_features["slices_y"],
            codec_features["slices_x"],
            codec_features["slices_y"],
            codec_features["slices_x"] * codec_features["slices_y"],
        )


class LosslessUnsupportedByLowDelayError(UnsatisfiableCodecFeaturesError):
    """
    Thrown when lossless coding is chosen for the low delay profile (which only
    supports lossy coding).
    """

    def explain(self):
        (codec_features,) = self.args

        return """
            Low delay profile does not support lossless encoding for {}.
        """.format(
            codec_features["name"],
        )


class IncompatibleLevelAndVideoFormatError(UnsatisfiableCodecFeaturesError):
    """
    Thrown when the codec features specified a particular VC-2 level which is
    incompatible with the video format specified.
    """

    def explain(self):
        (codec_features,) = self.args

        return """
            Level {} ({:d}) specified for {} but the video format requested is
            not permitted by this level.
        """.format(
            codec_features["level"].name,
            codec_features["level"],
            codec_features["name"],
        )


class IncompatibleLevelAndExtendedTransformParametersError(
    UnsatisfiableCodecFeaturesError
):
    """
    Thrown when the codec features specified a particular VC-2 level which is
    incompatible with the extended transform parameter encoding required.
    """

    def explain(self):
        (codec_features,) = self.args

        return """
            Level {} ({:d}) specified for {} but the asymmetric transform type
            specified is not not permitted by this level.

            * wavelet_index: {} ({:d})
            * wavelet_index_ho: {} ({:d})
            * dwt_depth: {}
            * dwt_depth_ho: {}
        """.format(
            codec_features["level"].name,
            codec_features["level"],
            codec_features["name"],
            codec_features["wavelet_index"].name,
            codec_features["wavelet_index"],
            codec_features["wavelet_index_ho"].name,
            codec_features["wavelet_index_ho"],
            codec_features["dwt_depth"],
            codec_features["dwt_depth_ho"],
        )


class IncompatibleLevelAndDataUnitError(UnsatisfiableCodecFeaturesError):
    """
    Thrown when a sequence of data unit types is requested which is not allowed
    by the current level.
    """

    def explain(self):
        (codec_features,) = self.args

        return """
            Internal error in conformance software (sorry about that!).

            A test case was generated for {} whose level, {} ({:d}), prohibited
            the sequence of data units the test case required.
        """.format(
            codec_features["name"],
            codec_features["level"].name,
            codec_features["level"],
        )
