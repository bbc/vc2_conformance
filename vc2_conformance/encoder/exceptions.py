class InvalidCodecFeaturesError(ValueError):
    """
    Base class for exceptions thrown by the encoder when it is unable to
    generate a stream in the desired format due to some invalid
    :py:class:`~vc2_conformance.codec_features.CodecFeatures` configuration.
    """


class MissingQuantizationMatrixError(InvalidCodecFeaturesError):
    """
    Thrown when the codec features specified did not include a quantization
    matrix when one was required.
    """


class AsymmetricTransformPreVersion3Error(InvalidCodecFeaturesError):
    """
    Thrown when an asymmetric wavelet transform is used in a stream specified
    as being version 2 or under.
    """


class IncompatibleLevelAndVideoFormatError(InvalidCodecFeaturesError):
    """
    Thrown when the codec features specified a particular VC-2 level which is
    incompatible with the video format specified.
    """


class IncompatibleLevelAndExtendedTransformParametersError(InvalidCodecFeaturesError):
    """
    Thrown when the codec features specified a particular VC-2 level which is
    incompatible with the extended transform parameter encoding required.
    """


class IncompatibleLevelAndDataUnitError(InvalidCodecFeaturesError):
    """
    Thrown when a sequence of data unit types is requested which is not allowed
    by the current level.
    """
